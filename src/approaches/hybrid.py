"""
Pipeline completo da abordagem de triagem híbrida (LLM extrai, regras classificam).

O fluxo é uma cadeia LCEL montada pela mesma fábrica do fluxo por regras
(src.orchestration.triage_flow.compor_fluxo_triagem). A única diferença de
topologia é o nó de extração:

    preparacao_entrada
    | triagem_com_falha_segura(
          carregamento_dados                    (kb, categorias, regras, LLMExtractor)
        | extracao_llm_com_fallback ∥ deteccao_categoria      (RunnableParallel)
            └─ extracao_llm  →(falha)→  extracao_palavras_chave
        | enriquecimento_contexto
        | motor_regras_producao                 (apply_rules — um único nó)
        | montagem_resultado                    (revisão humana, campos_sem_suporte)
      , fallback = resultado_seguro)

Etapas:
  1. LLM extrai informações estruturadas do texto livre — sem classificar urgência,
     prioridade ou equipe.
  2. Se a extração LLM falhar (erro_parse ou exceção), o fallback nativo do
     LangChain (RunnableWithFallbacks) aciona o KeywordExtractor e a revisão
     humana é sinalizada obrigatoriamente. Como o LLMExtractor sinaliza falha
     por erro_parse sem lançar exceção, o nó extracao_llm converte esse caso
     em FalhaExtracaoLLM.
  3. Categoria da falha detectada de forma determinística por KeywordExtractor,
     em paralelo com a extração.
  4. enrich_context cruza os dados extraídos com a base local de ativos e equipes.
  5. Motor de regras classifica urgência, prioridade e equipe responsável.
  6. Pós-processamento consolida revisão humana, campos_sem_suporte e evidências.

Separação explícita marcada em comentários em português:
  '# LLM extrai'      → etapa de extração via LLM (sem classificação)
  '# Regras classificam' → etapa de classificação via motor de regras

Nunca lança exceção ao chamador — erros internos retornam TriageResult com
requer_revisao_humana=True e descrição do problema em motivo_revisao.
Falha dupla (LLM e fallback por palavras-chave lançando): o resultado seguro
mostra a classe do erro do LLM (ver D3 em triage_flow).

AVISO: Protótipo acadêmico. Não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança. Toda saída deve ser revisada por
profissional habilitado antes de qualquer ação operacional.
"""

import logging
import time

from langchain_core.runnables import RunnableSequence

from src.data.context_enricher import enrich_context
from src.data.loader import load_categories, load_knowledge_base
from src.extraction.keyword_extractor import KeywordExtractor
from src.extraction.llm_extractor import LLMExtractor
from src.orchestration.triage_flow import (
    FLUXO_HIBRIDO,
    NO_EXTRACAO_LLM,
    NO_EXTRACAO_PALAVRAS_CHAVE,
    FalhaExtracaoLLM,
    compor_fluxo_triagem,
    extracao_com_fallback,
    no,
)
from src.rules.definitions import RULE_FORA_DO_ESCOPO_ID, load_rules
from src.rules.engine import apply_rules
from src.schemas.extraction import ExtractedInfo
from src.schemas.triage import (
    ApproachType,
    FailureCategory,
    PriorityLevel,
    TriageResult,
    UrgencyLevel,
)

# Logger do módulo — erros registrados sem expor traceback ao usuário final
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Etapas (nós) do fluxo híbrido
# ---------------------------------------------------------------------------


def _preparar_entrada(entrada: dict) -> dict:
    """Nó preparacao_entrada: marca o início e sanitiza texto vazio.

    TriageResult.texto_entrada exige min_length=1.
    """
    inicio = time.perf_counter()
    texto = entrada["texto"]
    texto_entrada = texto if texto and texto.strip() else "(relato vazio)"
    return {"texto": texto, "texto_entrada": texto_entrada, "inicio": inicio}


def _carregar_dados(estado: dict) -> dict:
    """Nó carregamento_dados: dados locais (cacheados) e instância do LLMExtractor.

    O LLMExtractor é criado aqui, fora do fallback da extração: falha no
    construtor vai para o resultado seguro, não para o extrator por palavras-chave.
    """
    kb = load_knowledge_base()
    cats = load_categories()
    rules = load_rules()
    return {"kb": kb, "cats": cats, "rules": rules, "llm_extractor": LLMExtractor()}


# LLM extrai informações do texto — sem classificação
def _extrair_llm(estado: dict) -> dict:
    """Nó extracao_llm: extração via LLM; erro_parse vira FalhaExtracaoLLM."""
    extracted = estado["dados"]["llm_extractor"].extract(estado["texto_entrada"])
    # Adaptador: LLMExtractor sinaliza falha por erro_parse, sem exceção.
    # 'is not None' preserva o comportamento anterior (erro_parse="" também falha).
    if extracted.erro_parse is not None:
        raise FalhaExtracaoLLM(extracted.erro_parse)
    return {"extraido": extracted, "fallback_ativado": False}


def _extrair_palavras_chave_fallback(estado: dict) -> dict:
    """Fallback extracao_palavras_chave: assume quando a extração LLM falha."""
    exc = estado["erro_extracao"]
    if isinstance(exc, FalhaExtracaoLLM):
        erro_extracao = exc.erro_parse
    else:
        # Exceção direta do extrator (ex: mock com side_effect em testes)
        erro_extracao = str(exc) or type(exc).__name__
        logger.warning(
            "LLMExtractor lançou exceção inesperada: %s — ativando fallback.",
            erro_extracao,
        )

    logger.warning(
        "Fallback para KeywordExtractor: extração LLM falhou (%s).",
        erro_extracao,
    )
    dados = estado["dados"]
    keyword_extractor = KeywordExtractor(dados["kb"], dados["cats"])
    extracted_kw = keyword_extractor.extract(estado["texto_entrada"])
    # Mesclar evidências do fallback com nota explicativa
    evidencias_com_fallback = dict(extracted_kw.evidencias)
    evidencias_com_fallback["extracao_fallback"] = (
        f"Extração LLM falhou ({erro_extracao}); "
        "usado extrator por palavras-chave."
    )
    # Recriar extracted com campos do KeywordExtractor e evidências mescladas
    extracted = ExtractedInfo(
        ativo_mencionado=extracted_kw.ativo_mencionado,
        sintomas=extracted_kw.sintomas,
        localizacao=extracted_kw.localizacao,
        impacto_producao=extracted_kw.impacto_producao,
        risco_seguranca=extracted_kw.risco_seguranca,
        urgencia_mencionada=extracted_kw.urgencia_mencionada,
        evidencias=evidencias_com_fallback,
        confianca_extracao=extracted_kw.confianca_extracao,
        campos_sem_suporte=extracted_kw.campos_sem_suporte,
    )
    return {"extraido": extracted, "fallback_ativado": True}


def _detectar_categoria(estado: dict) -> FailureCategory:
    """Nó deteccao_categoria: sempre com extrator determinístico."""
    dados = estado["dados"]
    return KeywordExtractor(dados["kb"], dados["cats"]).detect_category(estado["texto_entrada"])


def _enriquecer_contexto(estado: dict):
    """Nó enriquecimento_contexto: cruza a extração com ativos e equipes locais."""
    dados = estado["dados"]
    return enrich_context(
        estado["extracao"]["extraido"], dados["kb"], dados["cats"], estado["categoria"].value
    )


# Regras classificam urgência, prioridade e equipe — não o LLM
def _aplicar_regras(estado: dict) -> dict:
    """Nó motor_regras_producao: o motor de regras inteiro (data/rules.yaml)."""
    return apply_rules(
        estado["extracao"]["extraido"],
        estado["contexto"],
        estado["dados"]["rules"],
        texto_original=estado["texto_entrada"],
        categoria_detectada=estado["categoria"].value,
    )


def _montar_resultado(estado: dict) -> TriageResult:
    """Nó montagem_resultado: pós-processamento e TriageResult do híbrido."""
    extracted = estado["extracao"]["extraido"]
    fallback_ativado = estado["extracao"]["fallback_ativado"]
    categoria = estado["categoria"]
    context = estado["contexto"]
    resultado = estado["regras"]

    # Preparar dicionário de evidências composto (LLM + dados locais)
    evidencias = dict(extracted.evidencias)
    if context.ativo_encontrado:
        evidencias["ativo_encontrado"] = (
            f"recuperado de assets.yaml: {context.ativo_encontrado.tag}"
            f" — {context.ativo_encontrado.nome}"
        )
    if resultado["regras_acionadas"]:
        evidencias["regras_classificacao"] = (
            "Regras: " + ", ".join(resultado["regras_acionadas"])
        )

    # -------------------------------------------------------------------
    # Pós-processamento: revisão humana, confiança e motivo
    # -------------------------------------------------------------------
    requer_revisao: bool = resultado["requer_revisao_humana"]
    motivo: str | None = resultado.get("motivo_revisao")

    if fallback_ativado:
        # Fallback LLM ativo → revisão obrigatória independente das regras
        requer_revisao = True
        motivo = (
            "Falha na extração LLM — resultado baseado em extrator por "
            "palavras-chave. Revisar manualmente."
        )
    elif extracted.confianca_extracao < 0.4:
        # Baixa confiança na extração → revisão preventiva obrigatória
        requer_revisao = True
        motivo = "Baixa confiança na extração LLM — revisar manualmente."

    # Garantir motivo quando revisão obrigatória (evitar ValidationError do schema)
    if requer_revisao and not motivo:
        motivo = "Revisão solicitada pelas regras de triagem."

    # -------------------------------------------------------------------
    # Calcular campos_sem_suporte (extraídos + ativo + urgência indireta)
    # -------------------------------------------------------------------
    campos_sem_suporte = list(extracted.campos_sem_suporte)
    # Ativo mencionado no relato mas não encontrado na KB
    if context.ativo_encontrado is None and "ativo_mencionado" not in campos_sem_suporte:
        campos_sem_suporte.append("ativo_mencionado")
    # Urgência atribuída por regra sem evidência textual
    if (
        resultado["urgencia"] != "DESCONHECIDA"
        and extracted.urgencia_mencionada is None
        and "urgencia" not in campos_sem_suporte
    ):
        campos_sem_suporte.append("urgencia")

    # Tratar RULE-017: relato reconhecido como fora do escopo do sistema
    if RULE_FORA_DO_ESCOPO_ID in resultado["regras_acionadas"]:
        categoria = FailureCategory.FORA_DO_ESCOPO

    latencia = (time.perf_counter() - estado["inicio"]) * 1000

    return TriageResult(
        abordagem=ApproachType.HIBRIDO,
        texto_entrada=estado["texto_entrada"],
        urgencia=UrgencyLevel(resultado["urgencia"]),
        prioridade=PriorityLevel(resultado["prioridade"]),
        categoria=categoria,
        equipe_sugerida=resultado["equipe"],
        regras_acionadas=resultado["regras_acionadas"],
        evidencias=evidencias,
        requer_revisao_humana=requer_revisao,
        motivo_revisao=motivo,
        confianca=resultado["confianca"],
        latencia_ms=latencia,
        tokens_entrada=extracted.tokens_entrada,
        tokens_saida=extracted.tokens_saida,
        tokens_total=extracted.tokens_total,
        campos_sem_suporte=campos_sem_suporte,
    )


def _resultado_seguro(estado: dict) -> TriageResult:
    """Fallback resultado_seguro: qualquer exceção do núcleo vira revisão humana."""
    erro = estado["erro"]
    # Registrar erro sem expor traceback ao chamador
    logger.error("Erro em run_hybrid: %s", type(erro).__name__, exc_info=erro)
    latencia = (time.perf_counter() - estado["inicio"]) * 1000

    return TriageResult(
        abordagem=ApproachType.HIBRIDO,
        texto_entrada=estado["texto_entrada"],
        urgencia=UrgencyLevel.DESCONHECIDA,
        prioridade=PriorityLevel.DESCONHECIDA,
        categoria=FailureCategory.DESCONHECIDA,
        equipe_sugerida="Revisão necessária",
        requer_revisao_humana=True,
        motivo_revisao=(
            f"Erro interno no processamento ({type(erro).__name__}) "
            "— revisar manualmente."
        ),
        confianca=0.0,
        latencia_ms=latencia,
    )


# ---------------------------------------------------------------------------
# Fluxo LCEL e função pública
# ---------------------------------------------------------------------------


def build_hybrid_flow() -> RunnableSequence:
    """
    Constrói o fluxo LCEL da abordagem híbrida.

    Mesma topologia do fluxo por regras; o extrator é extracao_llm com fallback
    nativo (RunnableWithFallbacks) para extracao_palavras_chave.
    Construir o fluxo não conecta ao Ollama.

    Returns:
        Runnable que aceita {"texto": ...} e retorna TriageResult.
    """
    extrator = extracao_com_fallback(
        no(_extrair_llm, NO_EXTRACAO_LLM),
        no(_extrair_palavras_chave_fallback, NO_EXTRACAO_PALAVRAS_CHAVE),
    )
    return compor_fluxo_triagem(
        nome=FLUXO_HIBRIDO,
        preparar_entrada=_preparar_entrada,
        carregar_dados=_carregar_dados,
        extrator=extrator,
        detectar_categoria=_detectar_categoria,
        enriquecer_contexto=_enriquecer_contexto,
        aplicar_regras=_aplicar_regras,
        montar_resultado=_montar_resultado,
        resultado_seguro=_resultado_seguro,
    )


def run_hybrid(texto: str) -> TriageResult:
    """
    Executa o pipeline de triagem pela abordagem híbrida.

    Delegação direta para build_hybrid_flow().invoke({"texto": texto}).

    Nunca lança exceção ao chamador — qualquer falha retorna TriageResult com
    requer_revisao_humana=True e motivo_revisao descritivo.

    Args:
        texto: relato livre da ocorrência.

    Returns:
        TriageResult com resultado da triagem híbrida ou sinalização de revisão humana.
    """
    return build_hybrid_flow().invoke({"texto": texto})
