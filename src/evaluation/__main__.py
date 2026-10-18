"""
Interface de linha de comando para avaliação das abordagens de triagem de OS.

Executa as abordagens selecionadas sobre o dataset sintético, salva os
relatórios em results/ e exibe a tabela resumo no terminal.

Uso:
    python -m src.evaluation
    python -m src.evaluation --approaches regras hibrido
    python -m src.evaluation --dataset caminho/para/dataset.json
    python -m src.evaluation --help

AVISO: Protótipo acadêmico — monografia de especialização em Controle e
Automação. Toda saída deve ser revisada por especialistas antes de qualquer
uso operacional. Este módulo NÃO executa ações em sistemas reais.

Pré-requisitos para abordagens LLM e híbrido:
  - Ollama instalado e rodando: ollama serve
  - Modelo baixado: ollama pull qwen3:0.6b  (ou o configurado em OLLAMA_MODEL)
"""

import argparse
import json
import sys


def _formatar_duracao(segundos: float) -> str:
    """Formata uma duração em segundos como '12,3 s', '4,5 min' ou '1,8 h'."""
    if segundos < 60:
        return f"{segundos:.1f} s"
    if segundos < 3600:
        return f"{segundos / 60:.1f} min"
    return f"{segundos / 3600:.2f} h"


def main() -> None:
    """Ponto de entrada da CLI de avaliação das abordagens de triagem."""
    # Forçar saída em UTF-8: no Windows, o console (cp1252) não codifica alguns
    # caracteres (ex.: o emoji de aviso), o que quebrava a impressão da tabela
    # final, sobretudo quando a saída é redirecionada (Tee-Object).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="python -m src.evaluation",
        description=(
            "Avalia as abordagens de triagem de OS industriais sobre o dataset sintético.\n\n"
            "AVISO: Protótipo acadêmico — não usar em ambiente industrial real.\n"
            "Para abordagens LLM/híbrido, o Ollama deve estar rodando:\n"
            "  ollama serve\n"
            "  ollama pull qwen3:0.6b"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--approaches",
        nargs="+",
        choices=["regras", "llm", "hibrido", "regras_catref"],
        default=["regras", "llm", "hibrido"],
        metavar="ABORDAGEM",
        help=(
            "Abordagens a avaliar: regras, llm, hibrido (padrão: as três). "
            "O cenário-diagnóstico opcional 'regras_catref' (regras com "
            "categoria de referência) pode ser adicionado explicitamente."
        ),
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        metavar="CAMINHO",
        help=(
            "Caminho para o dataset sintético JSON "
            "(padrão: datasets/synthetic_cases.json)"
        ),
    )

    args = parser.parse_args()

    try:
        from src.evaluation.report import print_summary_table, save_evaluation_report
        from src.evaluation.runner import run_evaluation

        print("Iniciando avaliação...", flush=True)
        eval_data = run_evaluation(
            approaches=args.approaches, dataset_path=args.dataset
        )

        caminhos = save_evaluation_report(eval_data)

        # Carregar o resumo gerado para exibir a tabela
        with open(caminhos["summary_json"], encoding="utf-8") as f:
            summary = json.load(f)

        print_summary_table(summary)

        # Tempo total de execução por abordagem (para a Seção 3.3 da monografia)
        print("\nTempo de execução por abordagem:")
        for nome_abordagem, dados in eval_data.get("approaches", {}).items():
            elapsed = dados.get("elapsed_seconds")
            if elapsed is not None:
                print(f"  {nome_abordagem}: {_formatar_duracao(elapsed)}")

        print("\nArquivos gerados:")
        for nome, caminho in caminhos.items():
            print(f"  {nome}: {caminho}")

    except FileNotFoundError as exc:
        print(
            f"\nErro: arquivo não encontrado — {exc}",
            file=sys.stderr,
        )
        print(
            "Verifique se o dataset existe em datasets/synthetic_cases.json",
            file=sys.stderr,
        )
        sys.exit(1)

    except ConnectionError as exc:
        print(
            "\nErro: Ollama indisponível. Verifique se o servidor está rodando.",
            file=sys.stderr,
        )
        print(
            "Dica: execute 'ollama serve' em outro terminal e tente novamente.",
            file=sys.stderr,
        )
        print(f"Detalhe: {exc}", file=sys.stderr)

    except Exception as exc:
        msg = str(exc).lower()
        if any(kw in msg for kw in ("connection refused", "ollama", "httpx")):
            print(
                "\nErro: Ollama indisponível. Verifique se o servidor está rodando.",
                file=sys.stderr,
            )
            print(
                "Dica: execute 'ollama serve' em outro terminal e tente novamente.",
                file=sys.stderr,
            )
            print(f"Detalhe: {type(exc).__name__}: {exc}", file=sys.stderr)
        else:
            print(
                f"\nErro inesperado: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
