"""
Executor de avaliação das abordagens de triagem de OS industriais.

Orquestra a execução de cada abordagem sobre o conjunto de casos do dataset
sintético, aplica timeout por caso via ThreadPoolExecutor e captura todas as
exceções sem propagar ao chamador.

Casos com falha recebem um TriageResult de fallback com requer_revisao_humana=True,
garantindo que a avaliação continue sem interrupção mesmo quando o LLM estiver
indisponível ou lento.

AVISO: Protótipo acadêmico — não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança.
"""

import concurrent.futures
import datetime
import logging
import time

from src.config.loader import get_settings
from src.data.dataset_loader import DatasetCase, load_dataset
from src.orchestration.chains import (
    build_hybrid_chain,
    build_llm_chain,
    build_rules_catref_chain,
    build_rules_chain,
)
from src.schemas.triage import (
    ApproachType,
    FailureCategory,
    PriorityLevel,
    TriageResult,
    UrgencyLevel,
)

logger = logging.getLogger(__name__)

# Abordagens válidas — frozenset para checagem O(1).
# "regras_catref" é um cenário-diagnóstico opcional (regras com categoria de
# referência); não entra nas abordagens padrão de run_evaluation.
ABORDAGENS_VALIDAS: frozenset[str] = frozenset(
    {"regras", "llm", "hibrido", "regras_catref"}
)

# Mapeamento de nome para a chain LangChain (Runnable) de cada abordagem.
# A execução passa, assim, pela camada de orquestração do LangChain (invoke),
# e não por uma chamada direta à função do pipeline.
_ABORDAGENS: dict = {
    "regras": build_rules_chain(),
    "llm": build_llm_chain(),
    "hibrido": build_hybrid_chain(),
    "regras_catref": build_rules_catref_chain(),
}


def _fallback_result_erro(
    texto: str, approach_name: str, latencia_ms: float, motivo: str
) -> TriageResult:
    """
    Cria TriageResult de fallback para casos que falharam durante a avaliação.

    Garante que a lista de resultados mantenha o mesmo comprimento que o dataset,
    permitindo alinhamento correto em per_approach_summary.

    Args:
        texto: texto do relato original.
        approach_name: nome da abordagem ('regras', 'llm' ou 'hibrido').
        latencia_ms: latência já medida até o ponto de falha.
        motivo: descrição resumida do erro.

    Returns:
        TriageResult com DESCONHECIDA para campos classificativos e
        requer_revisao_humana=True.
    """
    _mapa: dict[str, ApproachType] = {
        "regras": ApproachType.REGRAS,
        "llm": ApproachType.LLM,
        "hibrido": ApproachType.HIBRIDO,
        "regras_catref": ApproachType.REGRAS,
    }
    abordagem = _mapa.get(approach_name, ApproachType.REGRAS)
    texto_seguro = texto.strip() if texto.strip() else "(relato vazio)"

    return TriageResult(
        abordagem=abordagem,
        texto_entrada=texto_seguro,
        urgencia=UrgencyLevel.DESCONHECIDA,
        prioridade=PriorityLevel.DESCONHECIDA,
        categoria=FailureCategory.DESCONHECIDA,
        equipe_sugerida="Revisão necessária",
        requer_revisao_humana=True,
        motivo_revisao=f"Erro na execução: {motivo}",
        confianca=0.0,
        latencia_ms=latencia_ms,
    )


def evaluate_approach(approach_name: str, cases: list[DatasetCase]) -> dict:
    """
    Executa uma abordagem de triagem sobre todos os casos do dataset.

    Para cada caso aplica um timeout igual a 2× settings.llm_timeout_seconds.
    Exceções (incluindo timeout) são capturadas individualmente — a função
    nunca propaga erros ao chamador.

    Args:
        approach_name: nome da abordagem: 'regras', 'llm' ou 'hibrido'.
        cases: lista de DatasetCase a avaliar.

    Returns:
        Dicionário com:
          - 'results': lista de dicts (model_dump mode='json') na mesma ordem
            de cases; fallbacks para casos com erro.
          - 'errors': lista de {'case_id', 'error'} para casos com falha.
          - 'dataset_cases': lista de dicts dos casos avaliados.

    Raises:
        ValueError: se approach_name não pertencer a ABORDAGENS_VALIDAS.
    """
    if approach_name not in ABORDAGENS_VALIDAS:
        raise ValueError(
            f"Abordagem inválida: '{approach_name}'. "
            f"Valores válidos: {sorted(ABORDAGENS_VALIDAS)}"
        )

    settings = get_settings()
    timeout = settings.llm_timeout_seconds * 2
    fn = _ABORDAGENS[approach_name]

    results: list[dict] = []
    errors: list[dict] = []

    # Um único executor por abordagem evita criar/destruir 100 thread pools.
    # Nota: com max_workers=1, uma thread que ultrapassar o timeout continuará
    # rodando até concluir antes que o próximo caso seja despachado, pois o
    # executor só tem uma worker thread. Isso é aceitável para o protótipo —
    # threads de Python não podem ser canceladas externamente. Para cancelamento
    # real em produção, usar ProcessPoolExecutor.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        for i, caso in enumerate(cases):
            print(
                f"  [{approach_name}] Caso {i + 1}/{len(cases)}: {caso.id}", flush=True
            )
            inicio = time.perf_counter()

            # Invoca a chain LangChain (Runnable). 'categoria_ref' (categoria do
            # gabarito) é usada apenas pelo cenário 'regras_catref'; as demais
            # abordagens leem somente 'texto' e ignoram essa chave.
            entrada = {
                "texto": caso.texto,
                "categoria_ref": caso.esperado.categoria.value,
            }
            future = executor.submit(fn.invoke, entrada)
            try:
                result = future.result(timeout=timeout)
                results.append(result.model_dump(mode="json"))
            except (concurrent.futures.TimeoutError, TimeoutError):
                latencia = (time.perf_counter() - inicio) * 1000
                motivo = f"Timeout após {timeout}s"
                logger.warning(
                    "Timeout no caso %s (abordagem=%s)", caso.id, approach_name
                )
                fallback = _fallback_result_erro(caso.texto, approach_name, latencia, motivo)
                results.append(fallback.model_dump(mode="json"))
                errors.append({"case_id": caso.id, "error": motivo})
            except Exception as exc:
                latencia = (time.perf_counter() - inicio) * 1000
                motivo = f"{type(exc).__name__}: {exc}"
                logger.error(
                    "Erro no caso %s (abordagem=%s): %s", caso.id, approach_name, motivo
                )
                fallback = _fallback_result_erro(caso.texto, approach_name, latencia, motivo)
                results.append(fallback.model_dump(mode="json"))
                errors.append({"case_id": caso.id, "error": motivo})

    return {
        "results": results,
        "errors": errors,
        "dataset_cases": [c.model_dump(mode="json") for c in cases],
    }


def run_evaluation(
    approaches: list[str] | None = None,
    dataset_path: str | None = None,
) -> dict:
    """
    Executa a avaliação completa das abordagens selecionadas sobre o dataset.

    Valida os nomes de abordagens antes de carregar o dataset. Para cada
    abordagem, chama evaluate_approach e agrega os resultados.

    Args:
        approaches: lista de abordagens a avaliar. None = todas as três
                    ['regras', 'llm', 'hibrido'].
        dataset_path: caminho absoluto ou relativo do JSON do dataset.
                      None = datasets/synthetic_cases.json (padrão).

    Returns:
        Dicionário com:
          - 'timestamp': ISO 8601 do início da avaliação.
          - 'dataset_size': número de casos carregados.
          - 'approaches': {approach_name: resultado de evaluate_approach}.

    Raises:
        ValueError: se alguma abordagem inválida for fornecida.
        FileNotFoundError: se o dataset não for encontrado.
    """
    if approaches is None:
        approaches = ["regras", "llm", "hibrido"]

    # Validar nomes antes de carregar dataset
    invalidas = [a for a in approaches if a not in ABORDAGENS_VALIDAS]
    if invalidas:
        raise ValueError(
            f"Abordagem(ns) inválida(s): {invalidas}. "
            f"Valores válidos: {sorted(ABORDAGENS_VALIDAS)}"
        )

    print("Carregando dataset...", flush=True)
    cases = load_dataset(dataset_path)
    print(f"Dataset carregado: {len(cases)} casos.", flush=True)

    result: dict = {
        "timestamp": datetime.datetime.now().isoformat(),
        "dataset_size": len(cases),
        "approaches": {},
    }

    for approach_name in approaches:
        print(f"\nExecutando abordagem: {approach_name.upper()}", flush=True)
        result["approaches"][approach_name] = evaluate_approach(approach_name, cases)

    print("\nAvaliação concluída.", flush=True)
    return result
