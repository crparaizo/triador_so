"""
Pipeline completo da abordagem de triagem híbrida (LLM extrai, regras classificam).

Combina extração via LLM com classificação determinística por regras de produção:
  1. LLM extrai informações estruturadas do texto livre — sem classificar urgência,
     prioridade ou equipe.
  2. Se a extração LLM falhar (erro_parse ou exceção), KeywordExtractor assume como
     fallback e a revisão humana é sinalizada obrigatoriamente.
  3. Categoria da falha detectada de forma determinística por KeywordExtractor.
  4. enrich_context cruza os dados extraídos com a base local de ativos e equipes.
  5. Motor de regras classifica urgência, prioridade e equipe responsável.
  6. Pós-processamento consolida revisão humana, campos_sem_suporte e evidências.

Separação explícita marcada em comentários em português:
  '# LLM extrai'      → etapa de extração via LLM (sem classificação)
  '# Regras classificam' → etapa de classificação via motor de regras

Nunca lança exceção ao chamador — erros internos retornam TriageResult com
requer_revisao_humana=True e descrição do problema em motivo_revisao.

AVISO: Protótipo acadêmico. Não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança. Toda saída deve ser revisada por
profissional habilitado antes de qualquer ação operacional.
"""

import logging
import time

from src.data.context_enricher import enrich_context
from src.data.loader import load_categories, load_knowledge_base
from src.extraction.keyword_extractor import KeywordExtractor
from src.extraction.llm_extractor import LLMExtractor
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


def run_hybrid(texto: str) -> TriageResult:
    """
    Executa o pipeline de triagem pela abordagem híbrida.

    Fluxo principal:
        1. Sanitizar texto de entrada.
        2. Carregar base de conhecimento, categorias e regras (cacheados).
        3. LLM extrai informações do texto livre (sem classificação).
        4. Se extração falhar (erro_parse ou exceção), KeywordExtractor assume
           como fallback e a revisão humana é sinalizada obrigatoriamente.
        5. Detectar categoria de forma determinística com KeywordExtractor.
        6. Enriquecer contexto com dados locais de ativos e equipes.
        7. Motor de regras classifica urgência, prioridade e equipe.
        8. Pós-processamento: revisão humana, campos_sem_suporte, evidências compostas.

    Nunca lança exceção ao chamador — qualquer falha retorna TriageResult com
    requer_revisao_humana=True e motivo_revisao descritivo.

    Args:
        texto: relato livre da ocorrência.

    Returns:
        TriageResult com resultado da triagem híbrida ou sinalização de revisão humana.
    """
    inicio = time.perf_counter()

    # Sanitizar texto vazio (TriageResult.texto_entrada exige min_length=1)
    texto_entrada = texto if texto and texto.strip() else "(relato vazio)"

    try:
        # Carregar dados (cacheados após primeira chamada)
        kb = load_knowledge_base()
        cats = load_categories()
        rules = load_rules()

        # -------------------------------------------------------------------
        # LLM extrai informações do texto — sem classificação
        # -------------------------------------------------------------------
        llm_extractor = LLMExtractor()
        fallback_ativado = False
        erro_extracao: str | None = None

        try:
            extracted = llm_extractor.extract(texto_entrada)
            # Verificar se a extração retornou com erro de parse
            erro_extracao = extracted.erro_parse
        except Exception as exc_llm:
            # Exceção direta do extrator (ex: mock com side_effect em testes)
            erro_extracao = str(exc_llm) or type(exc_llm).__name__
            logger.warning(
                "LLMExtractor lançou exceção inesperada: %s — ativando fallback.",
                erro_extracao,
            )
            # Placeholder substituído pelo fallback abaixo
            extracted = ExtractedInfo()

        # Ativar fallback KeywordExtractor se a extração LLM falhou
        if erro_extracao is not None:
            logger.warning(
                "Fallback para KeywordExtractor: extração LLM falhou (%s).",
                erro_extracao,
            )
            keyword_extractor = KeywordExtractor(kb, cats)
            extracted_kw = keyword_extractor.extract(texto_entrada)
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
            fallback_ativado = True

        # -------------------------------------------------------------------
        # Detectar categoria sempre com extrator determinístico
        # -------------------------------------------------------------------
        keyword_extractor_cat = KeywordExtractor(kb, cats)
        categoria = keyword_extractor_cat.detect_category(texto_entrada)

        # -------------------------------------------------------------------
        # Enriquecer contexto com dados locais de ativos e equipes
        # -------------------------------------------------------------------
        context = enrich_context(extracted, kb, cats, categoria.value)

        # Preparar dicionário de evidências composto (LLM + dados locais)
        evidencias = dict(extracted.evidencias)
        if context.ativo_encontrado:
            evidencias["ativo_encontrado"] = (
                f"recuperado de assets.yaml: {context.ativo_encontrado.tag}"
                f" — {context.ativo_encontrado.nome}"
            )

        # -------------------------------------------------------------------
        # Regras classificam urgência, prioridade e equipe — não o LLM
        # -------------------------------------------------------------------
        resultado = apply_rules(
            extracted,
            context,
            rules,
            texto_original=texto_entrada,
            categoria_detectada=categoria.value,
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
        # Calcular campos_sem_suporte (D5: extraídos + ativo + urgência indireta)
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

        latencia = (time.perf_counter() - inicio) * 1000

        return TriageResult(
            abordagem=ApproachType.HIBRIDO,
            texto_entrada=texto_entrada,
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
            campos_sem_suporte=campos_sem_suporte,
        )

    except Exception as exc:
        # Registrar erro sem expor traceback ao chamador
        logger.error("Erro em run_hybrid: %s", type(exc).__name__, exc_info=True)
        latencia = (time.perf_counter() - inicio) * 1000

        return TriageResult(
            abordagem=ApproachType.HIBRIDO,
            texto_entrada=texto_entrada,
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
