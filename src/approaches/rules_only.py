"""
Pipeline completo da abordagem de triagem baseada somente em regras de produção.

Implementa run_rules_only() que executa o fluxo completo:
    1. Carregar base de conhecimento, categorias e regras.
    2. Extrair informações do texto com KeywordExtractor.
    3. Enriquecer contexto cruzando com KnowledgeBase.
    4. Aplicar regras e montar TriageResult.

Não usa LLM. Todos os erros internos são capturados e retornam TriageResult
com requer_revisao_humana=True — a função nunca lança exceção para o chamador.

AVISO: Protótipo acadêmico. Não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança.
"""

import logging
import time

from src.data.context_enricher import enrich_context
from src.data.loader import load_categories, load_knowledge_base
from src.extraction.keyword_extractor import KeywordExtractor
from src.rules.definitions import load_rules
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



def run_rules_only(texto: str) -> TriageResult:
    """
    Executa o pipeline completo de triagem pela abordagem de regras.

    Fluxo:
        KnowledgeBase → KeywordExtractor.extract() → _enrich_context()
        → apply_rules() → TriageResult

    Tratamento especial:
        - RULE-017 em regras_acionadas → categoria forçada para FORA_DO_ESCOPO.

    Em caso de qualquer exceção interna, retorna TriageResult de revisão
    humana com motivo descritivo. A função nunca propaga exceção ao chamador.

    Args:
        texto: relato livre da ocorrência.

    Returns:
        TriageResult com resultado da triagem ou sinalização de revisão humana.
    """
    inicio = time.perf_counter()

    try:
        # Carregar dados (cacheados após primeira chamada)
        kb = load_knowledge_base()
        cats = load_categories()
        rules = load_rules()

        # Extrair informações do texto
        extractor = KeywordExtractor(kb, cats)
        extracted = extractor.extract(texto)
        categoria = extractor.detect_category(texto)

        # Enriquecer contexto com dados locais
        context = enrich_context(extracted, kb)

        # Aplicar motor de regras
        resultado = apply_rules(
            extracted,
            context,
            rules,
            texto_original=texto,
            categoria_detectada=categoria.value,
        )

        # Tratamento especial: RULE-017 força categoria FORA_DO_ESCOPO
        if "RULE-017" in resultado["regras_acionadas"]:
            categoria = FailureCategory.FORA_DO_ESCOPO

        latencia = (time.perf_counter() - inicio) * 1000

        return TriageResult(
            abordagem=ApproachType.REGRAS,
            texto_entrada=texto,
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

    except Exception as exc:
        # Registrar erro sem expor traceback ao chamador
        logger.error("Erro em run_rules_only: %s", type(exc).__name__, exc_info=True)
        latencia = (time.perf_counter() - inicio) * 1000

        return TriageResult(
            abordagem=ApproachType.REGRAS,
            texto_entrada=texto,
            urgencia=UrgencyLevel.DESCONHECIDA,
            prioridade=PriorityLevel.DESCONHECIDA,
            categoria=FailureCategory.DESCONHECIDA,
            equipe_sugerida="Revisão necessária",
            requer_revisao_humana=True,
            motivo_revisao=(
                f"Erro interno no processamento ({type(exc).__name__}) "
                "— revisar manualmente."
            ),
            confianca=0.0,
            latencia_ms=latencia,
        )
