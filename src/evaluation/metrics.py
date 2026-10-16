"""
Módulo de métricas para avaliação das abordagens de triagem de OS industriais.

AVISO: Métricas calculadas em dataset sintético pequeno (100 casos). Não extrair
conclusões estatísticas sem considerar as limitações documentadas no README.

As funções calculam métricas de classificação via scikit-learn, taxa de
subestimação de casos críticos, taxa de revisão humana, consistência em
paráfrases (robustez) e estatísticas de latência. Nenhuma função usa LLM
como avaliador de outro LLM — toda comparação é feita contra gabaritos.

Definições de métricas e limitações estão documentadas no arquivo docs/metrics.md.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from sklearn.metrics import (
    classification_report as skl_report,
    confusion_matrix as skl_confusion_matrix,
)

if TYPE_CHECKING:
    from src.data.dataset_loader import DatasetCase
    from src.schemas.triage import TriageResult

logger = logging.getLogger(__name__)

# Número de campos classificáveis usados no cálculo de taxa de campos sem suporte:
# urgencia, prioridade, categoria, equipe
NUM_CAMPOS_CLASSIFICAVEIS = 4


def classification_report_dict(
    y_true: list[str], y_pred: list[str], field_name: str = ""
) -> dict:
    """
    Gera relatório de classificação em formato dicionário.

    Usa sklearn.metrics.classification_report com output_dict=True e
    zero_division=0 para evitar avisos em classes sem ocorrências.

    Args:
        y_true: rótulos verdadeiros (strings).
        y_pred: rótulos preditos (strings).
        field_name: nome do campo avaliado (apenas para logging).

    Returns:
        Dicionário com métricas por classe e médias weighted/macro/micro,
        ou {} se y_true estiver vazio.
    """
    if not y_true:
        logger.debug(
            "classification_report_dict: y_true vazio para campo '%s'", field_name
        )
        return {}
    return skl_report(y_true, y_pred, output_dict=True, zero_division=0)


def confusion_matrix_dict(
    y_true: list[str], y_pred: list[str], labels: list[str]
) -> dict:
    """
    Gera matriz de confusão em formato serializável (JSON-safe).

    Args:
        y_true: rótulos verdadeiros.
        y_pred: rótulos preditos.
        labels: lista ordenada de rótulos de classe.

    Returns:
        Dicionário {'labels': [...], 'matrix': [[int, ...], ...]} ou
        {'labels': [...], 'matrix': []} se y_true estiver vazio.
    """
    if not y_true:
        return {"labels": labels, "matrix": []}
    mat = skl_confusion_matrix(y_true, y_pred, labels=labels)
    return {"labels": labels, "matrix": mat.tolist()}


def unsupported_fields_rate(results: list) -> float:
    """
    Calcula a taxa de campos sem suporte textual direto no relato.

    Indicador de possível alucinação ou preenchimento por inferência sem
    evidência explícita. Taxa = Σ|campos_sem_suporte| / (n × NUM_CAMPOS),
    em que NUM_CAMPOS (=4) é uma constante de normalização, e não o número de
    itens que podem aparecer em campos_sem_suporte.

    Limitação (importante para comparação entre abordagens): a semântica de
    campos_sem_suporte difere por abordagem. Em 'regras' e 'hibrido', a lista
    contém campos de EXTRAÇÃO sem evidência (ativo, localização, impacto, risco,
    urgência mencionada — até 5 itens); em 'llm', contém os campos de
    CLASSIFICAÇÃO que o próprio modelo declarou sem suporte. Portanto, a taxa é
    um indicador por abordagem, e não uma medida diretamente equivalente entre
    as três. O indicador também não distingue inferência contextual legítima de
    alucinação propriamente dita.

    Args:
        results: lista de TriageResult.

    Returns:
        Float entre 0.0 e 1.0; 0.0 se lista vazia.
    """
    if not results:
        return 0.0
    total = sum(len(r.campos_sem_suporte) for r in results)
    return total / (len(results) * NUM_CAMPOS_CLASSIFICAVEIS)


def critical_underestimation_rate(
    y_true_urgency: list[str],
    y_pred_urgency: list[str],
    y_true_priority: list[str],
    y_pred_priority: list[str],
) -> float:
    """
    Taxa de subestimação de casos críticos.

    Definição de caso crítico: urgência verdadeira == 'IMEDIATA' OU
    prioridade verdadeira == 'P1'.

    Definição de subestimação: caso crítico classificado com urgência
    ALTA/MEDIA/BAIXA (quando verdadeira é IMEDIATA) OU com prioridade
    P2/P3/P4 (quando verdadeira é P1).

    Limitação: a definição é conservadora — inclui casos onde apenas um
    dos critérios (urgência OU prioridade) foi subestimado.

    Args:
        y_true_urgency: urgências verdadeiras.
        y_pred_urgency: urgências preditas.
        y_true_priority: prioridades verdadeiras.
        y_pred_priority: prioridades preditas.

    Returns:
        Float entre 0.0 e 1.0; 0.0 se não houver casos críticos.
    """
    URGENCIA_BAIXAS = {"ALTA", "MEDIA", "BAIXA"}
    PRIORIDADE_BAIXAS = {"P2", "P3", "P4"}

    total_criticos = 0
    subestimados = 0

    for tu, pu, tp, pp in zip(
        y_true_urgency, y_pred_urgency, y_true_priority, y_pred_priority
    ):
        eh_critico = (tu == "IMEDIATA") or (tp == "P1")
        if eh_critico:
            total_criticos += 1
            urgencia_subest = (tu == "IMEDIATA") and (pu in URGENCIA_BAIXAS)
            prioridade_subest = (tp == "P1") and (pp in PRIORIDADE_BAIXAS)
            if urgencia_subest or prioridade_subest:
                subestimados += 1

    return subestimados / total_criticos if total_criticos > 0 else 0.0


def human_review_rate(results: list) -> float:
    """
    Taxa de casos sinalizados para revisão humana obrigatória.

    Inclui tanto casos corretamente sinalizados quanto falsos positivos.
    Taxas altas podem indicar conservadorismo excessivo; taxas muito baixas
    podem indicar sub-sinalização de casos ambíguos ou incompletos.

    Args:
        results: lista de TriageResult.

    Returns:
        Float entre 0.0 e 1.0; 0.0 se lista vazia.
    """
    if not results:
        return 0.0
    return sum(1 for r in results if r.requer_revisao_humana) / len(results)


def robustness_score(canonical_results: list, paraphrase_results: list) -> dict:
    """
    Mede consistência de classificação entre casos canônicos e suas paráfrases.

    Para cada par (canônico, paráfrase), verifica se a predição é igual nos
    campos urgência, prioridade e categoria. Um score de 1.0 indica que a
    abordagem produz a mesma classificação independente da formulação do relato.

    Limitação: depende da disponibilidade de pares anotados no dataset.
    A comparação usa os resultados preditos, não os gabaritos.

    Args:
        canonical_results: lista de TriageResult dos casos canônicos.
        paraphrase_results: lista de TriageResult das paráfrases correspondentes
                            (mesma ordem e tamanho).

    Returns:
        Dicionário {'urgencia': float, 'prioridade': float, 'categoria': float};
        todos 0.0 se listas vazias ou com tamanhos diferentes.
    """
    if (
        not canonical_results
        or not paraphrase_results
        or len(canonical_results) != len(paraphrase_results)
    ):
        return {"urgencia": 0.0, "prioridade": 0.0, "categoria": 0.0}

    n = len(canonical_results)
    urg = (
        sum(
            1
            for c, p in zip(canonical_results, paraphrase_results)
            if c.urgencia == p.urgencia
        )
        / n
    )
    pri = (
        sum(
            1
            for c, p in zip(canonical_results, paraphrase_results)
            if c.prioridade == p.prioridade
        )
        / n
    )
    cat = (
        sum(
            1
            for c, p in zip(canonical_results, paraphrase_results)
            if c.categoria == p.categoria
        )
        / n
    )
    return {"urgencia": urg, "prioridade": pri, "categoria": cat}


def latency_stats(results: list) -> dict:
    """
    Estatísticas descritivas de latência de processamento em milissegundos.

    Limitação: latência medida no executor inclui tempo de serialização e
    overhead do Python, além do processamento real. Para abordagem LLM,
    a variância costuma ser maior por depender do modelo local.

    Args:
        results: lista de TriageResult.

    Returns:
        Dicionário {'media': float, 'std': float, 'min': float, 'max': float}
        em ms; todos 0.0 se lista vazia.
    """
    if not results:
        return {"media": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

    latencias = [r.latencia_ms for r in results]
    return {
        "media": float(np.mean(latencias)),
        "std": float(np.std(latencias)),
        "min": float(np.min(latencias)),
        "max": float(np.max(latencias)),
    }


def token_stats(results: list) -> dict:
    """
    Estatísticas descritivas de consumo de tokens do LLM.

    Mede o custo computacional da abordagem. Para regras puras o consumo é
    sempre 0 (nenhuma chamada a LLM); para o híbrido reflete apenas a extração;
    para o LLM puro reflete extração + classificação + roteamento num só prompt.

    Limitação: a contagem depende dos metadados devolvidos pelo Ollama. Quando
    indisponíveis, os campos valem 0 e não devem ser confundidos com ausência
    de chamada ao modelo.

    Args:
        results: lista de TriageResult.

    Returns:
        Dicionário com 'entrada_media', 'saida_media', 'total_medio',
        'total_soma'; todos 0.0 se lista vazia.
    """
    if not results:
        return {
            "entrada_media": 0.0,
            "saida_media": 0.0,
            "total_medio": 0.0,
            "total_soma": 0.0,
        }

    entrada = [r.tokens_entrada for r in results]
    saida = [r.tokens_saida for r in results]
    total = [r.tokens_total for r in results]
    return {
        "entrada_media": float(np.mean(entrada)),
        "saida_media": float(np.mean(saida)),
        "total_medio": float(np.mean(total)),
        "total_soma": float(np.sum(total)),
    }


def per_approach_summary(
    approach_results: "list[TriageResult | None]",
    dataset_cases: "list[DatasetCase | None]",
) -> dict:
    """
    Calcula resumo completo de métricas para uma abordagem de triagem.

    Alinha results[i] com dataset_cases[i] e filtra pares onde qualquer
    elemento é None. Acessa .value nos campos de enum pois o TriageResult
    usa use_enum_values=False (enums armazenados como instâncias).

    Espera objetos TriageResult (não dicts). A desserialização de dicts para
    TriageResult é responsabilidade do chamador — em report.py isso é feito
    por _gerar_summary() via TriageResult.model_validate() antes desta chamada.

    Para robustez: identifica pares canônico/paráfrase pelos campos
    caso.tipo=='PARAFRASES' e caso.referencia_caso_canonico.

    Args:
        approach_results: lista de TriageResult ou None (None para casos com erro).
                          Deve ter o mesmo comprimento que dataset_cases.
        dataset_cases: lista de DatasetCase ou None correspondentes.
                       None para casos que falharam a validação do schema.

    Returns:
        Dicionário com classification, confusion_matrices, f1_urgencia,
        f1_prioridade, f1_categoria, f1_equipe, unsupported_fields_rate,
        critical_underestimation_rate, human_review_rate, latency, robustness,
        total_cases. Todos zerados se não houver pares válidos.
    """
    from src.schemas.triage import FailureCategory, PriorityLevel, UrgencyLevel

    # Filtrar apenas pares completamente válidos
    pares = [
        (r, c)
        for r, c in zip(approach_results, dataset_cases)
        if r is not None and c is not None
    ]

    _zerado: dict = {
        "classification": {},
        "confusion_matrices": {},
        "f1_urgencia": 0.0,
        "f1_prioridade": 0.0,
        "f1_categoria": 0.0,
        "f1_equipe": 0.0,
        "unsupported_fields_rate": 0.0,
        "critical_underestimation_rate": 0.0,
        "human_review_rate": 0.0,
        "latency": {"media": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
        "tokens": {
            "entrada_media": 0.0,
            "saida_media": 0.0,
            "total_medio": 0.0,
            "total_soma": 0.0,
        },
        "robustness": {"urgencia": 0.0, "prioridade": 0.0, "categoria": 0.0},
        "total_cases": 0,
    }

    if not pares:
        return _zerado

    # Rótulos verdadeiros e preditos — .value porque enums são instâncias
    y_true_urg = [c.esperado.urgencia.value for _, c in pares]
    y_pred_urg = [r.urgencia.value for r, _ in pares]

    y_true_pri = [c.esperado.prioridade.value for _, c in pares]
    y_pred_pri = [r.prioridade.value for r, _ in pares]

    y_true_cat = [c.esperado.categoria.value for _, c in pares]
    y_pred_cat = [r.categoria.value for r, _ in pares]

    y_true_eq = [c.esperado.equipe for _, c in pares]
    y_pred_eq = [r.equipe_sugerida for r, _ in pares]

    # Listas de rótulos para matrizes de confusão
    labels_urg = [e.value for e in UrgencyLevel]
    labels_pri = [e.value for e in PriorityLevel]
    labels_cat = [e.value for e in FailureCategory]

    # Relatórios de classificação
    report_urg = classification_report_dict(y_true_urg, y_pred_urg, "urgencia")
    report_pri = classification_report_dict(y_true_pri, y_pred_pri, "prioridade")
    report_cat = classification_report_dict(y_true_cat, y_pred_cat, "categoria")
    report_eq = classification_report_dict(y_true_eq, y_pred_eq, "equipe")

    # Matrizes de confusão
    cm_urg = confusion_matrix_dict(y_true_urg, y_pred_urg, labels_urg)
    cm_pri = confusion_matrix_dict(y_true_pri, y_pred_pri, labels_pri)
    cm_cat = confusion_matrix_dict(y_true_cat, y_pred_cat, labels_cat)

    # F1 weighted de cada campo
    f1_urg = report_urg.get("weighted avg", {}).get("f1-score", 0.0)
    f1_pri = report_pri.get("weighted avg", {}).get("f1-score", 0.0)
    f1_cat = report_cat.get("weighted avg", {}).get("f1-score", 0.0)
    f1_eq = report_eq.get("weighted avg", {}).get("f1-score", 0.0)

    # Métricas de taxa
    resultados = [r for r, _ in pares]
    taxa_unsupported = unsupported_fields_rate(resultados)
    taxa_criticos = critical_underestimation_rate(
        y_true_urg, y_pred_urg, y_true_pri, y_pred_pri
    )
    taxa_revisao = human_review_rate(resultados)

    # Latência
    lat = latency_stats(resultados)

    # Tokens (custo computacional)
    tok = token_stats(resultados)

    # Robustez: pares canônico → paráfrase identificados por referencia_caso_canonico
    id_to_result = {c.id: r for r, c in pares}
    canonical_res: list = []
    paraphrase_res: list = []
    for r, c in pares:
        if c.tipo == "PARAFRASES" and c.referencia_caso_canonico in id_to_result:
            paraphrase_res.append(r)
            canonical_res.append(id_to_result[c.referencia_caso_canonico])

    rob = robustness_score(canonical_res, paraphrase_res)

    return {
        "classification": {
            "urgencia": report_urg,
            "prioridade": report_pri,
            "categoria": report_cat,
            "equipe": report_eq,
        },
        "confusion_matrices": {
            "urgencia": cm_urg,
            "prioridade": cm_pri,
            "categoria": cm_cat,
        },
        "f1_urgencia": f1_urg,
        "f1_prioridade": f1_pri,
        "f1_categoria": f1_cat,
        "f1_equipe": f1_eq,
        "unsupported_fields_rate": taxa_unsupported,
        "critical_underestimation_rate": taxa_criticos,
        "human_review_rate": taxa_revisao,
        "latency": lat,
        "tokens": tok,
        "robustness": rob,
        "total_cases": len(pares),
    }
