"""
Pipeline completo da abordagem de triagem baseada somente em regras de produção.

O fluxo é uma cadeia LCEL (LangChain Expression Language) montada pela fábrica
comum src.orchestration.triage_flow.compor_fluxo_triagem. Cada etapa abaixo é
um nó nomeado:

    preparacao_entrada
    | triagem_com_falha_segura(
          carregamento_dados                       (kb, categorias, regras)
        | extracao_palavras_chave ∥ deteccao_categoria   (RunnableParallel)
        | enriquecimento_contexto                  (cruza com assets.yaml/teams.yaml)
        | motor_regras_producao                    (apply_rules — um único nó)
        | montagem_resultado                       (TriageResult)
      , fallback = resultado_seguro)

Não usa LLM. Qualquer exceção do núcleo é tratada pelo fallback resultado_seguro,
que retorna TriageResult com requer_revisao_humana=True — run_rules_only() nunca
lança exceção para o chamador (exceto pela validação do schema com texto vazio,
comportamento pré-existente: o app impede a entrada vazia).

As funções de etapa ficam neste módulo (e não na fábrica) para que os loaders sejam
resolvidos pelos nomes globais daqui em tempo de chamada, mantendo os patches dos
testes válidos.

AVISO: Protótipo acadêmico. Não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança.
"""

import logging
import time

from langchain_core.runnables import RunnableSequence

from src.data.context_enricher import enrich_context
from src.data.loader import load_categories, load_knowledge_base
from src.extraction.keyword_extractor import KeywordExtractor
from src.orchestration.triage_flow import (
    FLUXO_REGRAS,
    FLUXO_REGRAS_CATEGORIA_REF,
    NO_EXTRACAO_PALAVRAS_CHAVE,
    compor_fluxo_triagem,
    no,
)
from src.rules.definitions import RULE_FORA_DO_ESCOPO_ID, load_rules
from src.rules.engine import apply_rules
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
# Etapas (nós) do fluxo por regras
# ---------------------------------------------------------------------------


def _preparar_entrada(entrada: dict) -> dict:
    """Nó preparacao_entrada: marca o início e define o texto (sem sanitização)."""
    inicio = time.perf_counter()
    return {
        "texto": entrada["texto"],
        "texto_entrada": entrada["texto"],
        "categoria_ref": None,
        "inicio": inicio,
    }


def _preparar_entrada_com_categoria_ref(entrada: dict) -> dict:
    """Nó preparacao_entrada do cenário-diagnóstico: repassa a categoria de referência."""
    estado = _preparar_entrada(entrada)
    estado["categoria_ref"] = entrada.get("categoria_ref")
    return estado


def _carregar_dados(estado: dict) -> dict:
    """Nó carregamento_dados: base de conhecimento, categorias e regras (cacheados)."""
    kb = load_knowledge_base()
    cats = load_categories()
    rules = load_rules()
    return {"kb": kb, "cats": cats, "rules": rules}


def _extrair_palavras_chave(estado: dict) -> dict:
    """Nó extracao_palavras_chave: extração determinística por palavras-chave."""
    dados = estado["dados"]
    extractor = KeywordExtractor(dados["kb"], dados["cats"])
    return {"extraido": extractor.extract(estado["texto_entrada"]), "fallback_ativado": False}


def _detectar_categoria(estado: dict) -> FailureCategory:
    """Nó deteccao_categoria: categoria de referência (diagnóstico) ou por palavras-chave."""
    categoria_ref = estado["categoria_ref"]
    if categoria_ref is not None:
        try:
            return FailureCategory(categoria_ref)
        except ValueError:
            return FailureCategory.DESCONHECIDA
    dados = estado["dados"]
    return KeywordExtractor(dados["kb"], dados["cats"]).detect_category(estado["texto_entrada"])


def _enriquecer_contexto(estado: dict):
    """Nó enriquecimento_contexto: cruza a extração com ativos e equipes locais.

    A categoria é incluída para que a equipe-padrão da categoria também seja
    considerada, como no híbrido.
    """
    dados = estado["dados"]
    return enrich_context(
        estado["extracao"]["extraido"], dados["kb"], dados["cats"], estado["categoria"].value
    )


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
    """Nó montagem_resultado: converte a saída das regras em TriageResult."""
    extracted = estado["extracao"]["extraido"]
    resultado = estado["regras"]
    categoria = estado["categoria"]

    # Tratamento especial: RULE-017 força categoria FORA_DO_ESCOPO
    if RULE_FORA_DO_ESCOPO_ID in resultado["regras_acionadas"]:
        categoria = FailureCategory.FORA_DO_ESCOPO

    latencia = (time.perf_counter() - estado["inicio"]) * 1000

    return TriageResult(
        abordagem=ApproachType.REGRAS,
        texto_entrada=estado["texto_entrada"],
        urgencia=UrgencyLevel(resultado["urgencia"]),
        prioridade=PriorityLevel(resultado["prioridade"]),
        categoria=categoria,
        equipe_sugerida=resultado["equipe"],
        regras_acionadas=resultado["regras_acionadas"],
        evidencias=extracted.evidencias,
        requer_revisao_humana=resultado["requer_revisao_humana"],
        motivo_revisao=resultado.get("motivo_revisao"),
        confianca=resultado["confianca"],
        latencia_ms=latencia,
        campos_sem_suporte=extracted.campos_sem_suporte,
    )


def _resultado_seguro(estado: dict) -> TriageResult:
    """Fallback resultado_seguro: qualquer exceção do núcleo vira revisão humana."""
    erro = estado["erro"]
    # Registrar erro sem expor traceback ao chamador
    logger.error("Erro em run_rules_only: %s", type(erro).__name__, exc_info=erro)
    latencia = (time.perf_counter() - estado["inicio"]) * 1000

    return TriageResult(
        abordagem=ApproachType.REGRAS,
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


def build_rules_flow(usar_categoria_ref: bool = False) -> RunnableSequence:
    """
    Constrói o fluxo LCEL da abordagem por regras.

    Args:
        usar_categoria_ref: False (padrão) ignora 'categoria_ref' da entrada e
            detecta a categoria por palavras-chave; True usa 'categoria_ref'
            quando informada (cenário-diagnóstico "regras com categoria de
            referência"; None mantém a detecção por palavras-chave).

    Returns:
        Runnable que aceita {"texto": ..., "categoria_ref": ...} e retorna TriageResult.
    """
    return compor_fluxo_triagem(
        nome=FLUXO_REGRAS_CATEGORIA_REF if usar_categoria_ref else FLUXO_REGRAS,
        preparar_entrada=(
            _preparar_entrada_com_categoria_ref if usar_categoria_ref else _preparar_entrada
        ),
        carregar_dados=_carregar_dados,
        extrator=no(_extrair_palavras_chave, NO_EXTRACAO_PALAVRAS_CHAVE),
        detectar_categoria=_detectar_categoria,
        enriquecer_contexto=_enriquecer_contexto,
        aplicar_regras=_aplicar_regras,
        montar_resultado=_montar_resultado,
        resultado_seguro=_resultado_seguro,
    )


def run_rules_only(texto: str, categoria_ref: str | None = None) -> TriageResult:
    """
    Executa o pipeline completo de triagem pela abordagem de regras.

    Delegação para o fluxo LCEL de build_rules_flow(): com categoria_ref=None
    usa o fluxo padrão "fluxo_regras" (categoria detectada por palavras-chave);
    com categoria_ref informada usa o fluxo do cenário-diagnóstico
    "fluxo_regras_categoria_ref". Assim o nome registrado no trace corresponde
    ao cenário realmente executado.

    Tratamento especial:
        - RULE-017 em regras_acionadas → categoria forçada para FORA_DO_ESCOPO.

    Em caso de qualquer exceção interna, retorna TriageResult de revisão
    humana com motivo descritivo (fallback resultado_seguro).

    Args:
        texto: relato livre da ocorrência.
        categoria_ref: quando informado (valor de FailureCategory, ex.: "MECANICA"),
            a categoria é fixada neste valor em vez de ser detectada por
            palavras-chave. Usado apenas no cenário-diagnóstico opcional
            "regras com categoria de referência" (ver src/evaluation/runner.py);
            None (padrão) mantém a detecção determinística por palavras-chave.

    Returns:
        TriageResult com resultado da triagem ou sinalização de revisão humana.
    """
    if categoria_ref is None:
        return build_rules_flow().invoke({"texto": texto})
    return build_rules_flow(usar_categoria_ref=True).invoke(
        {"texto": texto, "categoria_ref": categoria_ref}
    )
