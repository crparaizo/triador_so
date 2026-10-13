"""
Abordagem de triagem baseada exclusivamente em LLM puro.

Implementa run_llm_only() que envia um único prompt ao modelo com o contexto
completo de ativos e equipes da planta, solicitando extração, classificação e
encaminhamento num único passo — sem motor de regras.

O fluxo é uma cadeia LCEL com o mesmo envelope de falha segura dos demais fluxos
(src.orchestration.triage_flow.envolver_com_falha_segura):

    preparacao_entrada
    | triagem_com_falha_segura(
          preparacao_prompt     (contexto de ativos/equipes + relato → prompt em texto)
        | chamada_llm           (ChatOllama instanciado em runtime; llm.invoke(prompt))
        | parser_defensivo      (parsear_json_llm: json direto → regex → erro)
        | montagem_resultado    (TriageResult ou fallback de parse)
      , fallback = resultado_seguro)   (falha de conexão/exceção → "LLM indisponível")

A chamada ao modelo fica dentro de um nó RunnableLambda (e não como
"| ChatOllama(...)" direto) porque o modelo precisa ser instanciado em tempo de
execução — o runner constrói as chains no import e os testes substituem a classe —
e porque o prompt é uma string montada com str.format, enviada como args[0].

Características desta abordagem:
  - O LLM é responsável por toda análise: extração + classificação + encaminhamento.
  - regras_acionadas é SEMPRE lista vazia (nunca preenchida).
  - Fallback defensivo: qualquer falha retorna TriageResult com revisão humana.
  - ChatOllama instanciado no nó chamada_llm, nunca em escopo de módulo.

AVISO: Protótipo acadêmico. Não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança. Toda saída deve ser revisada
por profissional habilitado antes de qualquer ação operacional.
"""

import logging
import re
import time
import unicodedata
from typing import Optional

from langchain_core.runnables import RunnablePassthrough, RunnableSequence
from langchain_ollama import ChatOllama  # import seguro — sem conexão TCP

from src.config.loader import get_settings
from src.data.loader import load_knowledge_base
from src.orchestration.triage_flow import (
    FLUXO_LLM,
    NO_CHAMADA_LLM,
    NO_MONTAGEM_RESULTADO,
    NO_PARSER_DEFENSIVO,
    NO_PREPARACAO_PROMPT,
    envolver_com_falha_segura,
    no,
)
from src.schemas.triage import (
    ApproachType,
    FailureCategory,
    PriorityLevel,
    TriageResult,
    UrgencyLevel,
)
from src.utils.parsers import parsear_json_llm

# Logger do módulo — erros registrados sem expor traceback ao usuário final
logger = logging.getLogger(__name__)

# Prompt único para triagem completa via LLM puro.
# Placeholders substituídos no nó preparacao_prompt (_preparar_prompt):
#   {ativos_resumo}, {equipes_resumo}, {equipes_lista_nomes}, {texto}
_PROMPT_LLM_ONLY = (
    "Você é um sistema de triagem de ordens de serviço industriais.\n\n"
    "ATIVOS CADASTRADOS NA PLANTA:\n"
    "{ativos_resumo}\n\n"
    "EQUIPES DE MANUTENÇÃO DISPONÍVEIS:\n"
    "{equipes_resumo}\n\n"
    "TAREFA: Analise o relato abaixo e classifique a ordem de serviço preenchendo o JSON.\n\n"
    "Campos obrigatórios:\n"
    '- urgencia: "IMEDIATA" | "ALTA" | "MEDIA" | "BAIXA" | "DESCONHECIDA"\n'
    '- prioridade: "P1" | "P2" | "P3" | "P4" | "DESCONHECIDA"\n'
    '- categoria: "MECANICA" | "ELETRICA" | "INSTRUMENTACAO" | "UTILIDADES" | "SEGURANCA" |\n'
    '             "QUALIDADE" | "PROCESSO" | "INFRAESTRUTURA" | "TI_AUTOMACAO" |\n'
    '             "OUTROS" | "FORA_DO_ESCOPO" | "DESCONHECIDA"\n'
    "- equipe_sugerida: COPIE EXATAMENTE um dos nomes abaixo (sem alterar letras nem espaços):\n"
    "  {equipes_lista_nomes}\n"
    "  PROIBIDO: tags de ativos (ex: BOMB-001), categorias, siglas ou localizações.\n"
    "- regras_acionadas: [] (sempre lista vazia — esta abordagem não usa regras)\n"
    "- evidencias: objeto com trechos do texto que justificam cada campo classificado\n"
    "- requer_revisao_humana: true | false\n"
    "- motivo_revisao: string justificando revisão (obrigatório se requer_revisao_humana=true,"
    " null caso contrário)\n"
    "- confianca: número de 0.0 a 1.0 indicando confiança na classificação\n"
    "- campos_sem_suporte: lista de campos classificados sem evidência direta no texto\n\n"
    "REGRAS OBRIGATÓRIAS:\n"
    "- Use apenas os valores exatos listados acima para urgencia, prioridade e categoria.\n"
    "- Para equipe_sugerida use EXCLUSIVAMENTE um dos nomes listados no campo equipe_sugerida.\n"
    "- Não invente ativos ou equipes que não estejam nas listas fornecidas.\n"
    "- Se não tiver certeza, use DESCONHECIDA e marque requer_revisao_humana=true.\n"
    "- Se requer_revisao_humana for true, preencha motivo_revisao com a justificativa.\n\n"
    "RELATO:\n"
    "---\n"
    "{texto}\n"
    "---\n\n"
    "Retorne APENAS o JSON puro. Sem explicações, sem markdown, sem comentários."
)


# ---------------------------------------------------------------------------
# Funções auxiliares de normalização e mapeamento de enums
# ---------------------------------------------------------------------------


def _normalizar_enum(valor: str) -> str:
    """Remove acentos e converte para maiúsculas para correspondência de enum."""
    nfd = unicodedata.normalize("NFD", valor.upper().strip())
    return nfd.encode("ascii", "ignore").decode()


def _mapear_urgencia(valor: str) -> UrgencyLevel:
    """Mapeia string para UrgencyLevel. 'imediata'→IMEDIATA, valores inválidos→DESCONHECIDA."""
    try:
        return UrgencyLevel[_normalizar_enum(valor)]
    except KeyError:
        return UrgencyLevel.DESCONHECIDA


def _mapear_prioridade(valor: str) -> PriorityLevel:
    """Mapeia string para PriorityLevel. 'p1'→P1, 'p2'→P2, valores inválidos→DESCONHECIDA."""
    try:
        return PriorityLevel[_normalizar_enum(valor)]
    except KeyError:
        return PriorityLevel.DESCONHECIDA


def _mapear_categoria(valor: str) -> FailureCategory:
    """Normaliza acentos e espaços, tenta FailureCategory[...], inválidos→DESCONHECIDA."""
    try:
        chave = _normalizar_enum(valor).replace(" ", "_")
        return FailureCategory[chave]
    except KeyError:
        return FailureCategory.DESCONHECIDA


# ---------------------------------------------------------------------------
# Funções de fallback e conversão
# ---------------------------------------------------------------------------


def _fallback_conexao(texto_entrada: str, latencia: float, motivo: str) -> TriageResult:
    """Retorna TriageResult de erro quando Ollama está indisponível ou ocorreu exceção."""
    return TriageResult(
        abordagem=ApproachType.LLM,
        texto_entrada=texto_entrada,
        urgencia=UrgencyLevel.DESCONHECIDA,
        prioridade=PriorityLevel.DESCONHECIDA,
        categoria=FailureCategory.DESCONHECIDA,
        equipe_sugerida="Revisão Manual",
        regras_acionadas=[],
        requer_revisao_humana=True,
        motivo_revisao=f"LLM indisponível: {motivo}",
        confianca=0.0,
        latencia_ms=max(latencia, 0.0),
    )


def _fallback_parse(texto_entrada: str, latencia: float, motivo: str) -> TriageResult:
    """Retorna TriageResult de erro quando o JSON retornado pelo LLM é inválido."""
    return TriageResult(
        abordagem=ApproachType.LLM,
        texto_entrada=texto_entrada,
        urgencia=UrgencyLevel.DESCONHECIDA,
        prioridade=PriorityLevel.DESCONHECIDA,
        categoria=FailureCategory.DESCONHECIDA,
        equipe_sugerida="Revisão Manual",
        regras_acionadas=[],
        requer_revisao_humana=True,
        motivo_revisao=f"Falha na classificação: {motivo}",
        confianca=0.0,
        latencia_ms=max(latencia, 0.0),
    )


def _mapear_equipe_valida(valor: str, equipes_validas: list[str]) -> str:
    """
    Valida o nome de equipe retornado pelo LLM contra a lista de equipes cadastradas.

    Tenta match exato normalizado (sem acentos, uppercase) e depois match por
    contenção: o nome completo de exatamente UMA equipe deve aparecer, como
    palavras inteiras, dentro do valor retornado. Fragmentos do nome ("TI",
    "MECANICA", "MANUTENCAO") não são aceitos, e valores que contêm mais de uma
    equipe são ambíguos. Nesses casos retorna 'Revisão Manual'.

    Isso é necessário porque modelos pequenos frequentemente retornam nomes inválidos
    como tags de ativos (BOMB-001), categorias (MECANICA) ou fragmentos do texto.

    Args:
        valor: nome de equipe retornado pelo LLM.
        equipes_validas: lista de nomes exatos de equipes do KnowledgeBase.

    Returns:
        Nome exato da equipe correspondente, ou 'Revisão Manual' se inválido.
    """
    if not valor:
        return "Revisão Manual"
    if not equipes_validas:
        # Sem lista de referência: aceitar o valor (fallback seguro para testes sem KB)
        return str(valor).strip() or "Revisão Manual"

    val_norm = _normalizar_enum(valor)

    # Passo 1: match exato normalizado (case-insensitive, sem acentos)
    for equipe in equipes_validas:
        if _normalizar_enum(equipe) == val_norm:
            return equipe

    # Passo 2: contenção em um só sentido — o nome COMPLETO da equipe aparece
    # como palavras inteiras dentro do valor (ex: "Manutenção Mecânica Turno A"
    # → "Manutenção Mecânica"). O sentido inverso (valor contido no nome) foi
    # descartado porque aceitava fragmentos: "TI" casava com "UTILIDADES" e
    # "MECANICA" (categoria) com "Manutenção Mecânica", encaminhando sem revisão.
    candidatas = [
        equipe
        for equipe in equipes_validas
        if re.search(rf"(?<!\w){re.escape(_normalizar_enum(equipe))}(?!\w)", val_norm)
    ]
    if len(candidatas) == 1:
        return candidatas[0]

    # Nenhum match (ou match ambíguo): valor inválido, sinalizar para revisão manual
    logger.warning(
        "Equipe inválida retornada pelo LLM: '%s'. Valores válidos: %s",
        valor,
        equipes_validas,
    )
    return "Revisão Manual"


def _dict_para_triage_result(
    data: dict,
    texto_entrada: str,
    latencia: float,
    equipes_validas: list[str] | None = None,
) -> TriageResult:
    """
    Converte o dict retornado pelo LLM para TriageResult com mapeamento defensivo de enums.

    regras_acionadas é SEMPRE [] — mesmo que o LLM retorne valores nesse campo.
    equipes_validas: lista de nomes exatos do KnowledgeBase para validar equipe_sugerida.
    """
    # Mapeamento defensivo de enums
    urgencia = _mapear_urgencia(str(data.get("urgencia", "")))
    prioridade = _mapear_prioridade(str(data.get("prioridade", "")))
    categoria = _mapear_categoria(str(data.get("categoria", "")))

    # Equipe: validar contra lista de equipes cadastradas para descartar alucinações
    equipe_raw = data.get("equipe_sugerida")
    equipe_str = str(equipe_raw).strip() if equipe_raw and str(equipe_raw).strip() else ""
    equipe = _mapear_equipe_valida(equipe_str, equipes_validas or [])

    # Evidências e campos_sem_suporte com tipagem defensiva.
    # O LLM pode retornar evidencias como dict, lista ou outro tipo — normalizar para dict.
    evidencias_raw = data.get("evidencias")
    if isinstance(evidencias_raw, dict):
        evidencias = {k: str(v) for k, v in evidencias_raw.items() if isinstance(k, str)}
    else:
        # Lista, None ou tipo inesperado → ignorar, sem evidências
        evidencias = {}
    campos_sem_suporte = [
        str(c) for c in (data.get("campos_sem_suporte") or []) if isinstance(c, str)
    ]

    # Confiança: aceitar apenas float/int dentro do intervalo [0.0, 1.0]
    confianca_raw = data.get("confianca")
    if isinstance(confianca_raw, (int, float)) and 0.0 <= float(confianca_raw) <= 1.0:
        confianca = float(confianca_raw)
    else:
        confianca = 0.0

    # Revisão humana e motivo
    requer_revisao = bool(data.get("requer_revisao_humana", False))
    motivo_revisao_raw = data.get("motivo_revisao")
    motivo_revisao: Optional[str] = (
        str(motivo_revisao_raw).strip()
        if motivo_revisao_raw and str(motivo_revisao_raw).strip()
        else None
    )

    # Garantir motivo_revisao quando requer_revisao=True (evitar ValidationError do model_validator)
    if requer_revisao and not motivo_revisao:
        motivo_revisao = "Revisão solicitada pelo LLM — verificar manualmente."

    return TriageResult(
        abordagem=ApproachType.LLM,
        texto_entrada=texto_entrada,
        urgencia=urgencia,
        prioridade=prioridade,
        categoria=categoria,
        equipe_sugerida=equipe,
        regras_acionadas=[],  # SEMPRE lista vazia para abordagem LLM — nunca preenchido
        evidencias=evidencias,
        requer_revisao_humana=requer_revisao,
        motivo_revisao=motivo_revisao,
        confianca=confianca,
        latencia_ms=max(latencia, 0.0),
        campos_sem_suporte=campos_sem_suporte,
    )


# ---------------------------------------------------------------------------
# Etapas (nós) do fluxo LLM puro
# ---------------------------------------------------------------------------


def _preparar_entrada(entrada: dict) -> dict:
    """Nó preparacao_entrada: marca o início e sanitiza texto vazio.

    TriageResult.texto_entrada exige min_length=1.
    """
    inicio = time.perf_counter()
    texto = entrada["texto"]
    texto_entrada = texto if texto and texto.strip() else "(relato vazio)"
    return {"texto": texto, "texto_entrada": texto_entrada, "inicio": inicio}


def _preparar_prompt(estado: dict) -> dict:
    """Nó preparacao_prompt: monta o prompt em texto com o contexto da planta."""
    # Carregar contexto da base de conhecimento (resultado cacheado após primeira chamada)
    kb = load_knowledge_base()
    settings = get_settings()

    # Construir resumo de ativos para o prompt
    ativos_resumo = (
        "\n".join(
            f"- {a.tag}: {a.nome} ({a.tipo}, {a.localizacao})"
            for a in kb.assets
        )
        or "Nenhum ativo cadastrado."
    )

    # Construir resumo de equipes para o prompt (contexto com especialidades)
    equipes_resumo = (
        "\n".join(
            f"- {t.nome}: {', '.join(t.especialidades)}"
            for t in kb.teams
        )
        or "Nenhuma equipe cadastrada."
    )

    # Lista compacta de nomes de equipe para a instrução do campo equipe_sugerida.
    # Formato "A" | "B" | "C" facilita para modelos pequenos copiarem o valor exato.
    equipes_lista_nomes = (
        " | ".join(f'"{t.nome}"' for t in kb.teams)
        or '"(sem equipes cadastradas)"'
    )

    # Montar prompt com contexto e relato
    prompt = _PROMPT_LLM_ONLY.format(
        ativos_resumo=ativos_resumo,
        equipes_resumo=equipes_resumo,
        equipes_lista_nomes=equipes_lista_nomes,
        texto=estado["texto_entrada"],
    )
    return {
        "prompt": prompt,
        "settings": settings,
        "equipes_validas": [t.nome for t in kb.teams],
    }


def _chamar_llm(estado: dict):
    """Nó chamada_llm: instancia ChatOllama em runtime e envia o prompt."""
    settings = estado["preparo"]["settings"]
    # Instanciar ChatOllama em runtime (não em escopo de módulo nem em __init__).
    # temperature=0 e seed fixos (settings) favorecem a reprodutibilidade.
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=settings.ollama_temperature,
        seed=settings.ollama_seed,
        format="json",  # força geração de JSON válido no nível do tokenizador
        # Limite de tokens: com format="json" o modelo pode repetir chaves
        # indefinidamente sem fechar o objeto (observado no qwen3:0.6b, CASE-050).
        num_predict=settings.ollama_num_predict,
    )
    return llm.invoke(estado["preparo"]["prompt"])


def _parsear_resposta(estado: dict) -> dict:
    """Nó parser_defensivo: três passos (json direto → regex → erro)."""
    resposta = estado["resposta"]
    # Extrair texto da resposta (AIMessage.content ou str)
    texto_resposta = resposta.content if hasattr(resposta, "content") else str(resposta)
    data, erro = parsear_json_llm(texto_resposta)
    return {"dados": data, "erro": erro}


def _montar_resultado(estado: dict) -> TriageResult:
    """Nó montagem_resultado: TriageResult do LLM ou fallback de parse."""
    data = estado["analise"]["dados"]
    erro = estado["analise"]["erro"]
    latencia_ms = (time.perf_counter() - estado["inicio"]) * 1000
    # Equipes válidas armazenadas por _preparar_prompt para validação pós-parse
    equipes_validas = estado.get("preparo", {}).get("equipes_validas", [])

    if erro or data is None:
        return _fallback_parse(
            estado["texto_entrada"], latencia_ms, f"Resposta inválida do LLM: {erro}"
        )

    return _dict_para_triage_result(data, estado["texto_entrada"], latencia_ms, equipes_validas)


def _resultado_seguro(estado: dict) -> TriageResult:
    """Fallback resultado_seguro: conexão recusada ou qualquer exceção do núcleo."""
    erro = estado["erro"]
    # Registrar erro sem expor traceback ao usuário final
    logger.error("Erro em run_llm_only: %s", type(erro).__name__, exc_info=erro)
    latencia_ms = (time.perf_counter() - estado["inicio"]) * 1000
    return _fallback_conexao(estado["texto_entrada"], latencia_ms, str(erro))


# ---------------------------------------------------------------------------
# Fluxo LCEL e função principal da abordagem
# ---------------------------------------------------------------------------


def build_llm_flow() -> RunnableSequence:
    """
    Constrói o fluxo LCEL da abordagem LLM puro.

    Construir o fluxo não conecta ao Ollama: o ChatOllama só é instanciado
    quando o nó chamada_llm executa.

    Returns:
        Runnable que aceita {"texto": ...} e retorna TriageResult.
    """
    nucleo = RunnableSequence(
        RunnablePassthrough.assign(preparo=no(_preparar_prompt, NO_PREPARACAO_PROMPT)),
        RunnablePassthrough.assign(resposta=no(_chamar_llm, NO_CHAMADA_LLM)),
        RunnablePassthrough.assign(analise=no(_parsear_resposta, NO_PARSER_DEFENSIVO)),
        no(_montar_resultado, NO_MONTAGEM_RESULTADO),
    )
    return envolver_com_falha_segura(
        nome=FLUXO_LLM,
        preparar_entrada=_preparar_entrada,
        nucleo=nucleo,
        resultado_seguro=_resultado_seguro,
    )


def run_llm_only(texto: str) -> TriageResult:
    """
    Executa triagem completa via LLM puro (extração + classificação + encaminhamento).

    Um único prompt inclui o contexto completo de ativos e equipes da KnowledgeBase.
    O LLM é responsável por toda análise — sem motor de regras de produção.
    Delegação direta para build_llm_flow().invoke({"texto": texto}).

    Decisão de design: regras_acionadas é SEMPRE [] nesta abordagem.
    Não lança exceção ao chamador: qualquer falha retorna TriageResult
    com requer_revisao_humana=True e confianca=0.0.

    Args:
        texto: relato livre da ocorrência.

    Returns:
        TriageResult com resultado da triagem ou sinalização de revisão humana em falha.
    """
    return build_llm_flow().invoke({"texto": texto})
