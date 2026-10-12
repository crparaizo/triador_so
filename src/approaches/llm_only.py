"""
Abordagem de triagem baseada exclusivamente em LLM puro.

Implementa run_llm_only() que envia um único prompt ao modelo com o contexto
completo de ativos e equipes da planta, solicitando extração, classificação e
encaminhamento num único passo — sem motor de regras.

Características desta abordagem:
  - O LLM é responsável por toda análise: extração + classificação + encaminhamento.
  - regras_acionadas é SEMPRE lista vazia (nunca preenchida).
  - Fallback defensivo: qualquer falha retorna TriageResult com revisão humana.
  - ChatOllama instanciado dentro de run_llm_only(), nunca em escopo de módulo.

AVISO: Protótipo acadêmico. Não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança. Toda saída deve ser revisada
por profissional habilitado antes de qualquer ação operacional.
"""

import logging
import time
import unicodedata
from typing import Optional

from langchain_ollama import ChatOllama  # import seguro — sem conexão TCP

from src.config.loader import get_settings
from src.data.loader import load_knowledge_base
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
# Placeholders substituídos em run_llm_only: {ativos_resumo}, {equipes_resumo}, {texto}
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
    "- equipe_sugerida: nome exato de uma equipe da lista acima (string)\n"
    "- regras_acionadas: [] (sempre lista vazia — esta abordagem não usa regras)\n"
    "- evidencias: objeto com trechos do texto que justificam cada campo classificado\n"
    "- requer_revisao_humana: true | false\n"
    "- motivo_revisao: string justificando revisão (obrigatório se requer_revisao_humana=true,"
    " null caso contrário)\n"
    "- confianca: número de 0.0 a 1.0 indicando confiança na classificação\n"
    "- campos_sem_suporte: lista de campos classificados sem evidência direta no texto\n\n"
    "REGRAS OBRIGATÓRIAS:\n"
    "- Use apenas os valores exatos listados acima para urgencia, prioridade e categoria.\n"
    "- Não invente ativos ou equipes que não estejam na lista fornecida.\n"
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


def _dict_para_triage_result(data: dict, texto_entrada: str, latencia: float) -> TriageResult:
    """
    Converte o dict retornado pelo LLM para TriageResult com mapeamento defensivo de enums.

    regras_acionadas é SEMPRE [] — mesmo que o LLM retorne valores nesse campo.
    """
    # Mapeamento defensivo de enums
    urgencia = _mapear_urgencia(str(data.get("urgencia", "")))
    prioridade = _mapear_prioridade(str(data.get("prioridade", "")))
    categoria = _mapear_categoria(str(data.get("categoria", "")))

    # Equipe: None ou string vazia → "Revisão Manual"
    equipe_raw = data.get("equipe_sugerida")
    equipe = str(equipe_raw).strip() if equipe_raw and str(equipe_raw).strip() else "Revisão Manual"

    # Evidências e campos_sem_suporte com tipagem defensiva
    evidencias = {
        k: str(v)
        for k, v in (data.get("evidencias") or {}).items()
        if isinstance(k, str)
    }
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
# Função principal da abordagem
# ---------------------------------------------------------------------------


def run_llm_only(texto: str) -> TriageResult:
    """
    Executa triagem completa via LLM puro (extração + classificação + encaminhamento).

    Um único prompt inclui o contexto completo de ativos e equipes da KnowledgeBase.
    O LLM é responsável por toda análise — sem motor de regras de produção.

    Decisão de design: regras_acionadas é SEMPRE [] nesta abordagem.
    Não lança exceção ao chamador: qualquer falha retorna TriageResult
    com requer_revisao_humana=True e confianca=0.0.

    Args:
        texto: relato livre da ocorrência.

    Returns:
        TriageResult com resultado da triagem ou sinalização de revisão humana em falha.
    """
    inicio = time.perf_counter()

    # Sanitizar texto vazio (TriageResult.texto_entrada exige min_length=1)
    texto_entrada = texto if texto and texto.strip() else "(relato vazio)"

    try:
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

        # Construir resumo de equipes para o prompt
        equipes_resumo = (
            "\n".join(
                f"- {t.nome}: {', '.join(t.especialidades)}"
                for t in kb.teams
            )
            or "Nenhuma equipe cadastrada."
        )

        # Montar prompt com contexto e relato
        prompt = _PROMPT_LLM_ONLY.format(
            ativos_resumo=ativos_resumo,
            equipes_resumo=equipes_resumo,
            texto=texto_entrada,
        )

        # Instanciar ChatOllama em runtime (não em escopo de módulo nem em __init__).
        # temperature=0 e seed fixos (settings) favorecem a reprodutibilidade.
        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
            seed=settings.ollama_seed,
        )
        resposta = llm.invoke(prompt)

        # Extrair texto da resposta (AIMessage.content ou str)
        texto_resposta = resposta.content if hasattr(resposta, "content") else str(resposta)

        # Parser defensivo: três passos (json direto → regex → erro)
        data, erro = parsear_json_llm(texto_resposta)
        latencia_ms = (time.perf_counter() - inicio) * 1000

        if erro or data is None:
            return _fallback_parse(
                texto_entrada, latencia_ms, f"Resposta inválida do LLM: {erro}"
            )

        return _dict_para_triage_result(data, texto_entrada, latencia_ms)

    except Exception as exc:
        # Registrar erro sem expor traceback ao usuário final
        logger.error("Erro em run_llm_only: %s", type(exc).__name__, exc_info=True)
        latencia_ms = (time.perf_counter() - inicio) * 1000
        return _fallback_conexao(texto_entrada, latencia_ms, str(exc))
