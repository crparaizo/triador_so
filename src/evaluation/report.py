"""
Módulo de geração e persistência de relatórios de avaliação.

Gera 4 arquivos por execução (todos com timestamp para evitar sobreescrita):
  1. evaluation_raw_<ts>.json    — dados brutos completos
  2. evaluation_per_case_<ts>.csv — comparativo predição vs gabarito por caso
  3. evaluation_summary_<ts>.json — métricas agregadas por abordagem
  4. evaluation_summary_<ts>.csv  — resumo tabular por abordagem

Fornece também print_summary_table() para visualização Rich no terminal.

AVISO: Protótipo acadêmico — toda interpretação dos resultados deve considerar
as limitações do dataset sintético. Não extrair conclusões operacionais sem
validação por especialistas habilitados.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.config.loader import get_settings
from src.evaluation.metrics import per_approach_summary

logger = logging.getLogger(__name__)

# Colunas do CSV por caso — ordem fixa para compatibilidade
COLUNAS_PER_CASE: list[str] = [
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
    "tokens_total",
]


def save_evaluation_report(
    eval_data: dict, output_dir: str | None = None
) -> dict[str, str]:
    """
    Salva o relatório de avaliação em 4 arquivos com timestamp.

    O diretório de saída é criado automaticamente se não existir.
    O timestamp no nome dos arquivos garante que execuções consecutivas
    não sobreescrevam resultados anteriores.

    Args:
        eval_data: dicionário retornado por run_evaluation().
        output_dir: diretório de saída. None usa settings.results_dir.

    Returns:
        Dicionário com caminhos absolutos resolvidos:
          {'raw': str, 'per_case': str, 'summary_json': str, 'summary_csv': str}
    """
    if output_dir is None:
        output_dir = get_settings().results_dir

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. JSON bruto completo
    raw_path = outdir / f"evaluation_raw_{ts}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(eval_data, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Relatório JSON bruto salvo: %s", raw_path)

    # 2. CSV por caso (predição vs gabarito)
    per_case_path = outdir / f"evaluation_per_case_{ts}.csv"
    _gerar_csv_por_caso(eval_data, per_case_path)
    logger.info("CSV por caso salvo: %s", per_case_path)

    # 3. JSON de resumo com métricas agregadas
    summary = _gerar_summary(eval_data)
    summary_json_path = outdir / f"evaluation_summary_{ts}.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Resumo JSON salvo: %s", summary_json_path)

    # 4. CSV de resumo tabular
    summary_csv_path = outdir / f"evaluation_summary_{ts}.csv"
    _gerar_summary_csv(summary, summary_csv_path)
    logger.info("Resumo CSV salvo: %s", summary_csv_path)

    return {
        "raw": str(raw_path.resolve()),
        "per_case": str(per_case_path.resolve()),
        "summary_json": str(summary_json_path.resolve()),
        "summary_csv": str(summary_csv_path.resolve()),
    }


def _gerar_csv_por_caso(eval_data: dict, path: Path) -> None:
    """
    Escreve CSV com comparativo de predição vs gabarito para cada caso.

    Itera sobre todas as abordagens e seus casos, calculando se cada campo
    classificativo foi acertado. O texto é truncado em 200 caracteres para
    manter o CSV legível.

    Args:
        eval_data: dados de avaliação brutos (estrutura de run_evaluation).
        path: caminho do arquivo CSV de saída.
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUNAS_PER_CASE)
        writer.writeheader()

        for approach_name, approach_data in eval_data.get("approaches", {}).items():
            results = approach_data.get("results", [])
            dataset_cases = approach_data.get("dataset_cases", [])

            for result, caso in zip(results, dataset_cases):
                esperado = caso.get("esperado", {})

                # Valores esperados (gabarito) — model_dump(mode='json') serializa
                # enums como strings, então esses valores já são strings
                urg_esp = str(esperado.get("urgencia", ""))
                pri_esp = str(esperado.get("prioridade", ""))
                cat_esp = str(esperado.get("categoria", ""))
                eq_esp = str(esperado.get("equipe", ""))

                # Valores preditos — mesmo formato por ser model_dump(mode='json')
                urg_pred = str(result.get("urgencia", ""))
                pri_pred = str(result.get("prioridade", ""))
                cat_pred = str(result.get("categoria", ""))
                eq_pred = str(result.get("equipe_sugerida", ""))

                writer.writerow({
                    "case_id": caso.get("id", ""),
                    "tipo": caso.get("tipo", ""),
                    "texto": str(caso.get("texto", ""))[:200],
                    "abordagem": approach_name,
                    "urgencia_esperada": urg_esp,
                    "urgencia_predita": urg_pred,
                    "prioridade_esperada": pri_esp,
                    "prioridade_predita": pri_pred,
                    "categoria_esperada": cat_esp,
                    "categoria_predita": cat_pred,
                    "equipe_esperada": eq_esp,
                    "equipe_predita": eq_pred,
                    "revisao_esperada": str(esperado.get("requer_revisao_humana", "")),
                    "revisao_predita": str(result.get("requer_revisao_humana", "")),
                    "urgencia_correta": str(urg_esp == urg_pred),
                    "prioridade_correta": str(pri_esp == pri_pred),
                    "categoria_correta": str(cat_esp == cat_pred),
                    "equipe_correta": str(eq_esp == eq_pred),
                    "campos_sem_suporte": len(result.get("campos_sem_suporte", [])),
                    "latencia_ms": result.get("latencia_ms", 0.0),
                    "tokens_total": result.get("tokens_total", 0),
                })


def _gerar_summary(eval_data: dict) -> dict:
    """
    Gera dicionário de resumo de métricas por abordagem.

    Reconstrói os objetos Pydantic a partir dos dados serializados e invoca
    per_approach_summary. Falhas de validação individual são registradas em
    log sem interromper o cálculo das demais abordagens.

    Args:
        eval_data: dados de avaliação brutos.

    Returns:
        Dicionário {approach_name: métricas} com 'total_errors' incluído.
    """
    from src.data.dataset_loader import DatasetCase
    from src.schemas.triage import TriageResult

    summary: dict = {}

    for approach_name, approach_data in eval_data.get("approaches", {}).items():
        results_raw = approach_data.get("results", [])
        cases_raw = approach_data.get("dataset_cases", [])
        errors = approach_data.get("errors", [])

        # Reconstruir TriageResult — None para itens que falhem validação
        results_obj: list = []
        for r in results_raw:
            try:
                results_obj.append(TriageResult.model_validate(r))
            except Exception as exc:
                logger.warning("Falha ao validar TriageResult no resumo: %s", exc)
                results_obj.append(None)

        # Reconstruir DatasetCase — None para itens que falhem validação
        cases_obj: list = []
        for c in cases_raw:
            try:
                cases_obj.append(DatasetCase.model_validate(c))
            except Exception as exc:
                logger.warning("Falha ao validar DatasetCase no resumo: %s", exc)
                cases_obj.append(None)

        metrics = per_approach_summary(results_obj, cases_obj)
        metrics["total_errors"] = len(errors)
        summary[approach_name] = metrics

    return summary


def _gerar_summary_csv(summary_data: dict, path: Path) -> None:
    """
    Escreve CSV tabular com uma linha por abordagem e métricas principais.

    Args:
        summary_data: dicionário {approach_name: métricas} de _gerar_summary().
        path: caminho do arquivo CSV de saída.
    """
    COLUNAS = [
        "abordagem",
        "f1_urgencia",
        "f1_prioridade",
        "f1_categoria",
        "f1_equipe",
        "taxa_revisao_humana",
        "taxa_subestimacao_critica",
        "latencia_media_ms",
        "tokens_total_medio",
        "tokens_total_soma",
        "equipes_alucinadas",
        "parse_falhou",
        "fallbacks_extracao",
        "total_cases",
        "total_errors",
    ]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUNAS)
        writer.writeheader()

        for approach_name, metrics in summary_data.items():
            writer.writerow({
                "abordagem": approach_name,
                "f1_urgencia": metrics.get("f1_urgencia", 0.0),
                "f1_prioridade": metrics.get("f1_prioridade", 0.0),
                "f1_categoria": metrics.get("f1_categoria", 0.0),
                "f1_equipe": metrics.get("f1_equipe", 0.0),
                "taxa_revisao_humana": metrics.get("human_review_rate", 0.0),
                "taxa_subestimacao_critica": metrics.get(
                    "critical_underestimation_rate", 0.0
                ),
                "latencia_media_ms": metrics.get("latency", {}).get("media", 0.0),
                "tokens_total_medio": metrics.get("tokens", {}).get("total_medio", 0.0),
                "tokens_total_soma": metrics.get("tokens", {}).get("total_soma", 0.0),
                "equipes_alucinadas": metrics.get("failure_events", {}).get(
                    "equipes_alucinadas", 0
                ),
                "parse_falhou": metrics.get("failure_events", {}).get("parse_falhou", 0),
                "fallbacks_extracao": metrics.get("failure_events", {}).get(
                    "fallbacks_extracao", 0
                ),
                "total_cases": metrics.get("total_cases", 0),
                "total_errors": metrics.get("total_errors", 0),
            })


def print_summary_table(summary: dict) -> None:
    """
    Exibe tabela resumo das métricas de avaliação no terminal com Rich.

    Imprime aviso sobre as limitações do dataset sintético antes da tabela
    e disclaimer de protótipo acadêmico após. Usa Rich Table para formatação
    legível mesmo em terminais sem suporte a cores (fallback automático).

    Args:
        summary: dicionário {approach_name: métricas} de _gerar_summary() ou
                 carregado do arquivo JSON gerado por save_evaluation_report().
    """
    console = Console()

    console.print(
        "\n[bold yellow]⚠ AVISO:[/bold yellow] Métricas calculadas em dataset sintético "
        "pequeno (100 casos). Não extrair conclusões estatísticas sem considerar "
        "as limitações documentadas.\n"
    )

    tabela = Table(
        title="Resumo de Avaliação — Abordagens de Triagem de OS Industriais",
        show_lines=True,
    )
    tabela.add_column("Abordagem", style="bold cyan")
    tabela.add_column("F1-Urgência", justify="right")
    tabela.add_column("F1-Prioridade", justify="right")
    tabela.add_column("F1-Categoria", justify="right")
    tabela.add_column("F1-Equipe", justify="right")
    tabela.add_column("Taxa Revisão", justify="right")
    tabela.add_column("Taxa Subest.", justify="right")
    tabela.add_column("Lat. Média (ms)", justify="right")
    tabela.add_column("Tokens (méd.)", justify="right")

    for approach_name, metrics in summary.items():
        tabela.add_row(
            approach_name.upper(),
            f"{metrics.get('f1_urgencia', 0.0):.3f}",
            f"{metrics.get('f1_prioridade', 0.0):.3f}",
            f"{metrics.get('f1_categoria', 0.0):.3f}",
            f"{metrics.get('f1_equipe', 0.0):.3f}",
            f"{metrics.get('human_review_rate', 0.0):.3f}",
            f"{metrics.get('critical_underestimation_rate', 0.0):.3f}",
            f"{metrics.get('latency', {}).get('media', 0.0):.1f}",
            f"{metrics.get('tokens', {}).get('total_medio', 0.0):.1f}",
        )

    console.print(tabela)
    console.print(
        "\n[dim]AVISO: Este é um protótipo acadêmico — monografia de especialização "
        "em Controle e Automação. Toda decisão operacional deve ser revisada por "
        "especialistas habilitados antes de qualquer ação industrial.[/dim]\n"
    )
