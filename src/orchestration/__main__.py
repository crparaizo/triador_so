"""
Exporta os grafos LCEL dos três fluxos de triagem em Mermaid.

Uso:
    python -m src.orchestration

Grava docs/fluxos_langchain.md. Não conecta ao Ollama (só constrói os fluxos).

AVISO: Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from src.orchestration.chains import salvar_diagramas_mermaid


def main() -> None:
    """Gera docs/fluxos_langchain.md com os diagramas dos fluxos."""
    caminho = salvar_diagramas_mermaid()
    print(f"Diagramas salvos em: {caminho}")


if __name__ == "__main__":
    main()
