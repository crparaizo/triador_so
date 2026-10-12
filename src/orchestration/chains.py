"""
Chains LangChain para os pipelines de triagem de ordens de serviço.

Encapsula as abordagens de triagem em RunnableLambda do LangChain, permitindo
composição com outros componentes de cadeia quando necessário.

Chains disponíveis:
  - build_rules_chain(): abordagem por regras de produção — sem LLM, execução local.
  - build_llm_chain(): abordagem LLM puro — requer Ollama rodando com modelo configurado.

AVISO: Protótipo acadêmico. As chains aqui definidas são para fins de pesquisa
e comparação de abordagens. Não usar em ambiente industrial real.
"""

from langchain_core.runnables import RunnableLambda

from src.approaches.llm_only import run_llm_only
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


def build_llm_chain() -> RunnableLambda:
    """
    Constrói chain LangChain para a abordagem de triagem baseada em LLM puro.

    A chain aceita um dict com a chave 'texto' (str) e retorna um TriageResult.
    Requer Ollama rodando com o modelo configurado em settings.ollama_model.
    A conexão com Ollama ocorre apenas em tempo de execução, nunca na construção da chain.

    Uso:
        chain = build_llm_chain()
        resultado = chain.invoke({"texto": "BOMB-001 com vibração excessiva"})

    Returns:
        RunnableLambda que envolve run_llm_only().
    """

    def _invocar(inputs: dict) -> TriageResult:
        """Adaptador entre interface LangChain (dict) e run_llm_only (str)."""
        return run_llm_only(inputs["texto"])

    return RunnableLambda(_invocar)
