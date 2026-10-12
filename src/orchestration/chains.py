"""
Chains LangChain para os pipelines de triagem de ordens de serviço.

Encapsula as abordagens de triagem em RunnableLambda do LangChain, permitindo
composição com outros componentes de cadeia quando necessário.

Nenhuma chain neste módulo requer Ollama ou API externa — a chain de regras
é puramente local e determinística.

AVISO: Protótipo acadêmico. As chains aqui definidas são para fins de pesquisa
e comparação de abordagens. Não usar em ambiente industrial real.
"""

from langchain_core.runnables import RunnableLambda

from src.approaches.rules_only import run_rules_only
from src.schemas.triage import TriageResult


def build_rules_chain() -> RunnableLambda:
    """
    Constrói chain LangChain para a abordagem de triagem baseada em regras.

    A chain aceita um dict com a chave 'texto' (str) e retorna um TriageResult.
    Não depende de LLM nem de Ollama — execução completamente local.

    Uso:
        chain = build_rules_chain()
        resultado = chain.invoke({"texto": "BOMB-001 com vibração excessiva"})

    Returns:
        RunnableLambda que envolve run_rules_only().
    """

    def _invocar(inputs: dict) -> TriageResult:
        """Adaptador entre interface LangChain (dict) e run_rules_only (str)."""
        return run_rules_only(inputs["texto"])

    return RunnableLambda(_invocar)
