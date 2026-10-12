"""
Módulo de avaliação e métricas das abordagens de triagem de OS industriais.

Fornece funções para calcular métricas de classificação (precisão, revocação,
F1 por classe e ponderado via sklearn), taxa de subestimação de casos críticos,
taxa de revisão humana, consistência em paráfrases (robustez) e estatísticas
de latência. Também fornece o executor de avaliação e as funções de relatório.

AVISO: Protótipo acadêmico — monografia de especialização em Controle e
Automação. Métricas calculadas em dataset sintético pequeno (100 casos).
Não extrair conclusões estatísticas sem considerar as limitações documentadas.
Toda saída deve ser revisada por especialistas antes de qualquer uso operacional.

Uso rápido:
    from src.evaluation import run_evaluation, save_evaluation_report
    eval_data = run_evaluation(approaches=['regras'])
    caminhos = save_evaluation_report(eval_data)

CLI:
    python -m src.evaluation --help
"""

from src.evaluation.metrics import (
    classification_report_dict,
    confusion_matrix_dict,
    critical_underestimation_rate,
    human_review_rate,
    latency_stats,
    per_approach_summary,
    robustness_score,
    unsupported_fields_rate,
)
from src.evaluation.report import print_summary_table, save_evaluation_report
from src.evaluation.runner import evaluate_approach, run_evaluation

__all__ = [
    # metrics.py
    "classification_report_dict",
    "confusion_matrix_dict",
    "unsupported_fields_rate",
    "critical_underestimation_rate",
    "human_review_rate",
    "robustness_score",
    "latency_stats",
    "per_approach_summary",
    # runner.py
    "run_evaluation",
    "evaluate_approach",
    # report.py
    "save_evaluation_report",
    "print_summary_table",
]
