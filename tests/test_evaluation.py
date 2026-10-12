"""
Testes automatizados para src/evaluation/ — módulo de avaliação das abordagens
de triagem de ordens de serviço industriais.

Todos os testes usam mocks via pytest-mock. Nenhum teste conecta ao Ollama
nem depende de arquivos externos — todos os dados são criados inline.

Nota de implementação: runner.py armazena referências de função em _ABORDAGENS
em tempo de importação, portanto o padrão correto para mockar abordagens é
mocker.patch.dict('src.evaluation.runner._ABORDAGENS', ...) e não
mocker.patch('src.evaluation.runner.run_rules_only', ...).

Dados de teste são completamente sintéticos, gerados para fins acadêmicos.
Não representam eventos, equipamentos ou instalações industriais reais.

AVISO: Protótipo acadêmico — monografia de especialização em Controle e
Automação. Toda saída deve ser revisada por especialistas antes de qualquer
uso operacional.
"""

import csv
import json
from pathlib import Path

import pytest

from src.config.loader import Settings, get_settings
from src.data.dataset_loader import DatasetCase, ExpectedOutput
from src.evaluation.metrics import (
    classification_report_dict,
    confusion_matrix_dict,
    critical_underestimation_rate,
    human_review_rate,
    latency_stats,
    robustness_score,
    unsupported_fields_rate,
)
from src.evaluation.report import print_summary_table, save_evaluation_report
from src.evaluation.runner import ABORDAGENS_VALIDAS, evaluate_approach, run_evaluation
from src.schemas.triage import (
    ApproachType,
    FailureCategory,
    PriorityLevel,
    TriageResult,
    UrgencyLevel,
)


# ---------------------------------------------------------------------------
# Fixture autouse: limpar cache de settings entre testes
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def limpar_caches():
    """Garante isolamento limpando o cache de get_settings antes e após cada teste."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Helpers locais de criação de objetos sintéticos
# ---------------------------------------------------------------------------


def _make_triage_result(
    urgencia_val: str,
    prioridade_val: str,
    categoria_val: str,
    equipe: str,
    revisao: bool,
    campos_sem_suporte: list[str] | None = None,
    latencia_ms: float = 10.0,
    abordagem: ApproachType = ApproachType.REGRAS,
) -> TriageResult:
    """
    Cria um TriageResult sintético para uso nos testes.

    Se revisao=True, preenche motivo_revisao='Revisão de teste' para satisfazer
    o validador de TriageResult. Dados fictícios — não representam caso real.
    """
    return TriageResult(
        abordagem=abordagem,
        texto_entrada="Texto sintético de teste para avaliação automatizada",
        urgencia=UrgencyLevel(urgencia_val),
        prioridade=PriorityLevel(prioridade_val),
        categoria=FailureCategory(categoria_val),
        equipe_sugerida=equipe,
        requer_revisao_humana=revisao,
        motivo_revisao="Revisão de teste" if revisao else None,
        confianca=0.8,
        latencia_ms=latencia_ms,
        campos_sem_suporte=campos_sem_suporte if campos_sem_suporte is not None else [],
    )


def _make_dataset_case(
    case_id: str,
    tipo: str,
    urgencia_val: str,
    prioridade_val: str,
    categoria_val: str,
    equipe: str,
    revisao: bool,
    texto: str = "Texto sintético de teste",
    notas: str | None = None,
) -> DatasetCase:
    """
    Cria um DatasetCase sintético para uso nos testes.

    Usa tipo='CANONICO' por padrão, que não impõe restrições extras no
    validador de DatasetCase. Equipe deve ser um dos valores de VALID_DATASET_TEAMS.
    Dados fictícios — não representam caso real.
    """
    esperado = ExpectedOutput(
        urgencia=UrgencyLevel(urgencia_val),
        prioridade=PriorityLevel(prioridade_val),
        categoria=FailureCategory(categoria_val),
        equipe=equipe,
        requer_revisao_humana=revisao,
    )
    return DatasetCase(
        id=case_id,
        tipo=tipo,  # type: ignore[arg-type]
        texto=texto,
        esperado=esperado,
        referencia_caso_canonico=None,
        notas=notas,
    )


def _build_eval_data(
    results_list: list[TriageResult], cases_list: list[DatasetCase]
) -> dict:
    """
    Monta eval_data no formato retornado por run_evaluation(), para usar nos
    testes de report.py sem precisar executar run_evaluation.
    """
    return {
        "timestamp": "2024-01-01T00:00:00",
        "dataset_size": len(cases_list),
        "approaches": {
            "regras": {
                "results": [r.model_dump(mode="json") for r in results_list],
                "errors": [],
                "dataset_cases": [c.model_dump(mode="json") for c in cases_list],
            }
        },
    }


# ---------------------------------------------------------------------------
# Testes 1–11: metrics.py
# ---------------------------------------------------------------------------


def test_classification_report_perfeito():
    """y_true == y_pred deve produzir f1 weighted avg == 1.0."""
    y = ["ALTA", "MEDIA", "BAIXA"]
    report = classification_report_dict(y, y)
    assert report["weighted avg"]["f1-score"] == 1.0


def test_classification_report_errado():
    """y_true != y_pred (todos errados) deve produzir f1 weighted avg < 1.0."""
    y_true = ["ALTA", "ALTA"]
    y_pred = ["MEDIA", "MEDIA"]
    report = classification_report_dict(y_true, y_pred)
    assert report["weighted avg"]["f1-score"] < 1.0


def test_confusion_matrix_basico():
    """Verificar estrutura {'labels', 'matrix'} e valores para labels A e B."""
    y_true = ["A", "B"]
    y_pred = ["A", "A"]
    labels = ["A", "B"]

    result = confusion_matrix_dict(y_true, y_pred, labels)

    assert "labels" in result
    assert "matrix" in result
    matrix = result["matrix"]
    # A predito como A: correto — célula [0][0]
    assert matrix[0][0] == 1
    # B predito como A: incorreto — célula [1][0]
    assert matrix[1][0] == 1
    # B predito como B: nunca ocorreu — célula [1][1]
    assert matrix[1][1] == 0


def test_unsupported_fields_rate_vazio():
    """Lista vazia deve retornar taxa 0.0 sem erro."""
    assert unsupported_fields_rate([]) == 0.0


def test_unsupported_fields_rate_com_campos():
    """TriageResult com 2 campos sem suporte deve gerar taxa > 0.0."""
    r = _make_triage_result(
        "ALTA",
        "P2",
        "MECANICA",
        "Manutenção Mecânica",
        False,
        campos_sem_suporte=["urgencia", "prioridade"],
    )
    taxa = unsupported_fields_rate([r])
    # 2 campos / (1 resultado * 4 campos classificáveis) = 0.5
    assert taxa > 0.0


def test_critical_underestimation_rate_zero():
    """Sem casos críticos (urgência != IMEDIATA e prioridade != P1) deve retornar 0.0."""
    rate = critical_underestimation_rate(["ALTA"], ["ALTA"], ["P2"], ["P2"])
    assert rate == 0.0


def test_critical_underestimation_rate_maior_zero():
    """IMEDIATA predita como ALTA e P1 predita como P2 deve retornar 1.0 (subestimado)."""
    rate = critical_underestimation_rate(["IMEDIATA"], ["ALTA"], ["P1"], ["P2"])
    # 1 caso crítico, 1 subestimado → 1.0
    assert rate == 1.0


def test_human_review_rate():
    """1 resultado com revisao=True e 1 com revisao=False deve retornar taxa 0.5."""
    r1 = _make_triage_result("ALTA", "P2", "MECANICA", "Manutenção Mecânica", True)
    r2 = _make_triage_result("MEDIA", "P3", "ELETRICA", "Manutenção Elétrica", False)
    rate = human_review_rate([r1, r2])
    assert rate == 0.5


def test_robustness_score_identicos():
    """Par de resultados idênticos deve retornar score 1.0 em todos os campos."""
    r1 = _make_triage_result("ALTA", "P2", "MECANICA", "Manutenção Mecânica", False)
    r2 = _make_triage_result("ALTA", "P2", "MECANICA", "Manutenção Mecânica", False)
    score = robustness_score([r1], [r2])
    assert score["urgencia"] == 1.0
    assert score["prioridade"] == 1.0
    assert score["categoria"] == 1.0


def test_robustness_score_divergentes():
    """Par de resultados completamente diferentes deve retornar urgencia e prioridade == 0.0."""
    r1 = _make_triage_result("ALTA", "P2", "MECANICA", "Manutenção Mecânica", False)
    r2 = _make_triage_result("BAIXA", "P4", "ELETRICA", "Manutenção Elétrica", False)
    score = robustness_score([r1], [r2])
    assert score["urgencia"] == 0.0
    assert score["prioridade"] == 0.0


def test_latency_stats_basico():
    """Latências [10, 20, 30] devem produzir media=20, min=10, max=30."""
    r1 = _make_triage_result(
        "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False, latencia_ms=10.0
    )
    r2 = _make_triage_result(
        "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False, latencia_ms=20.0
    )
    r3 = _make_triage_result(
        "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False, latencia_ms=30.0
    )
    stats = latency_stats([r1, r2, r3])
    assert stats["media"] == 20.0
    assert stats["min"] == 10.0
    assert stats["max"] == 30.0


# ---------------------------------------------------------------------------
# Testes 12–14: runner.py — run_evaluation e evaluate_approach
# ---------------------------------------------------------------------------


def test_run_evaluation_tres_abordagens(mocker):
    """run_evaluation() deve retornar resultado com as 3 abordagens e 2 resultados cada."""
    case1 = _make_dataset_case(
        "CASE-001", "CANONICO", "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False
    )
    case2 = _make_dataset_case(
        "CASE-002", "CANONICO", "MEDIA", "P3", "ELETRICA", "Manutenção Elétrica", False
    )
    triage_result = _make_triage_result(
        "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False
    )

    # Mockar as 3 funções de abordagem via _ABORDAGENS (dict populado em import time)
    mock_fn = mocker.Mock(return_value=triage_result)
    mocker.patch.dict(
        "src.evaluation.runner._ABORDAGENS",
        {"regras": mock_fn, "llm": mock_fn, "hibrido": mock_fn},
    )
    mocker.patch(
        "src.evaluation.runner.load_dataset", return_value=[case1, case2]
    )
    mocker.patch(
        "src.evaluation.runner.get_settings",
        return_value=Settings(llm_timeout_seconds=60),
    )

    resultado = run_evaluation()

    assert "timestamp" in resultado
    assert resultado["dataset_size"] == 2
    assert "approaches" in resultado
    assert "regras" in resultado["approaches"]
    assert "llm" in resultado["approaches"]
    assert "hibrido" in resultado["approaches"]
    assert len(resultado["approaches"]["regras"]["results"]) == 2


def test_run_evaluation_abordagem_invalida():
    """run_evaluation com abordagem inválida deve lançar ValueError imediatamente."""
    with pytest.raises(ValueError):
        run_evaluation(approaches=["invalida"])


def test_run_evaluation_excecao_marca_erro_continua(mocker):
    """Exceção na abordagem deve registrar erros e gerar fallback para todos os casos."""
    case1 = _make_dataset_case(
        "CASE-001", "CANONICO", "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False
    )
    case2 = _make_dataset_case(
        "CASE-002", "CANONICO", "MEDIA", "P3", "ELETRICA", "Manutenção Elétrica", False
    )

    # Função de abordagem que sempre falha
    mock_fn = mocker.Mock(side_effect=RuntimeError("falha simulada no teste"))
    mocker.patch.dict("src.evaluation.runner._ABORDAGENS", {"regras": mock_fn})
    mocker.patch(
        "src.evaluation.runner.load_dataset", return_value=[case1, case2]
    )
    mocker.patch(
        "src.evaluation.runner.get_settings",
        return_value=Settings(llm_timeout_seconds=60),
    )

    resultado = run_evaluation(approaches=["regras"])

    # Erros devem ser registrados (um por caso)
    assert len(resultado["approaches"]["regras"]["errors"]) > 0
    # Fallback gerado para cada caso → results com 2 entradas
    assert len(resultado["approaches"]["regras"]["results"]) == 2


# ---------------------------------------------------------------------------
# Testes 15–18: report.py — save_evaluation_report e print_summary_table
# ---------------------------------------------------------------------------


def test_save_evaluation_report_quatro_arquivos(tmp_path):
    """save_evaluation_report deve criar exatamente 4 arquivos no diretório de saída."""
    r1 = _make_triage_result("ALTA", "P2", "MECANICA", "Manutenção Mecânica", False)
    r2 = _make_triage_result("MEDIA", "P3", "ELETRICA", "Manutenção Elétrica", False)
    c1 = _make_dataset_case(
        "CASE-001", "CANONICO", "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False
    )
    c2 = _make_dataset_case(
        "CASE-002", "CANONICO", "MEDIA", "P3", "ELETRICA", "Manutenção Elétrica", False
    )

    eval_data = _build_eval_data([r1, r2], [c1, c2])
    caminhos = save_evaluation_report(eval_data, output_dir=str(tmp_path))

    # Exatamente 4 arquivos criados
    arquivos = list(tmp_path.iterdir())
    assert len(arquivos) == 4

    # Todos os caminhos retornados devem existir
    for path in caminhos.values():
        assert Path(path).exists(), f"Arquivo ausente: {path}"


def test_csv_per_case_colunas(tmp_path):
    """CSV por caso deve conter todas as 20 colunas definidas em COLUNAS_PER_CASE."""
    r1 = _make_triage_result("ALTA", "P2", "MECANICA", "Manutenção Mecânica", False)
    c1 = _make_dataset_case(
        "CASE-001", "CANONICO", "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False
    )

    eval_data = _build_eval_data([r1], [c1])
    caminhos = save_evaluation_report(eval_data, output_dir=str(tmp_path))

    with open(caminhos["per_case"], encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])

    colunas_esperadas = [
        "case_id",
        "tipo",
        "texto",
        "abordagem",
        "urgencia_esperada",
        "urgencia_predita",
        "prioridade_esperada",
        "prioridade_predita",
        "categoria_esperada",
        "categoria_predita",
        "equipe_esperada",
        "equipe_predita",
        "revisao_esperada",
        "revisao_predita",
        "urgencia_correta",
        "prioridade_correta",
        "categoria_correta",
        "equipe_correta",
        "campos_sem_suporte",
        "latencia_ms",
    ]
    for col in colunas_esperadas:
        assert col in headers, f"Coluna ausente no CSV por caso: {col}"


def test_summary_json_campos_f1(tmp_path):
    """summary.json deve conter f1_urgencia, f1_prioridade, f1_categoria, f1_equipe."""
    r1 = _make_triage_result("ALTA", "P2", "MECANICA", "Manutenção Mecânica", False)
    c1 = _make_dataset_case(
        "CASE-001", "CANONICO", "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False
    )

    eval_data = _build_eval_data([r1], [c1])
    caminhos = save_evaluation_report(eval_data, output_dir=str(tmp_path))

    with open(caminhos["summary_json"], encoding="utf-8") as f:
        summary = json.load(f)

    assert "regras" in summary
    for chave in ("f1_urgencia", "f1_prioridade", "f1_categoria", "f1_equipe"):
        assert chave in summary["regras"], f"Chave ausente no summary.json: {chave}"


def test_print_summary_table_sem_excecao():
    """print_summary_table com dict mínimo válido não deve lançar nenhuma exceção."""
    summary = {
        "regras": {
            "f1_urgencia": 0.8,
            "f1_prioridade": 0.7,
            "f1_categoria": 0.6,
            "f1_equipe": 0.9,
            "human_review_rate": 0.1,
            "critical_underestimation_rate": 0.0,
            "latency": {"media": 15.0, "std": 2.0, "min": 10.0, "max": 20.0},
            "total_cases": 10,
        }
    }
    # Deve executar sem exceção
    print_summary_table(summary)


# ---------------------------------------------------------------------------
# Testes 19–20: runner.py — evaluate_approach diretamente
# ---------------------------------------------------------------------------


def test_evaluate_approach_errors_vazio(mocker):
    """evaluate_approach sem falhas deve retornar errors == []."""
    case1 = _make_dataset_case(
        "CASE-001", "CANONICO", "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False
    )
    triage_result = _make_triage_result(
        "ALTA", "P2", "MECANICA", "Manutenção Mecânica", False
    )

    mock_fn = mocker.Mock(return_value=triage_result)
    mocker.patch.dict("src.evaluation.runner._ABORDAGENS", {"regras": mock_fn})
    mocker.patch(
        "src.evaluation.runner.get_settings",
        return_value=Settings(llm_timeout_seconds=60),
    )

    result = evaluate_approach("regras", [case1])

    assert result["errors"] == []


def test_evaluate_approach_errors_com_case_id(mocker):
    """RuntimeError na abordagem deve registrar case_id correto em errors e criar fallback."""
    case1 = _make_dataset_case(
        "CASE-MOCK-001",
        "CANONICO",
        "ALTA",
        "P2",
        "MECANICA",
        "Manutenção Mecânica",
        False,
    )

    mock_fn = mocker.Mock(side_effect=RuntimeError("crash simulado no teste"))
    mocker.patch.dict("src.evaluation.runner._ABORDAGENS", {"regras": mock_fn})
    mocker.patch(
        "src.evaluation.runner.get_settings",
        return_value=Settings(llm_timeout_seconds=60),
    )

    result = evaluate_approach("regras", [case1])

    # O case_id deve ser registrado corretamente no erro
    assert result["errors"][0]["case_id"] == "CASE-MOCK-001"
    # Fallback gerado → results com 1 entrada (mesmo em falha)
    assert len(result["results"]) == 1
