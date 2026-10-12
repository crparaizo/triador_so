"""
Chains LangChain para os pipelines de triagem de ordens de serviço.

Encapsula as abordagens de triagem em RunnableLambda do LangChain, permitindo
composição com outros componentes de cadeia quando necessário.

Chains disponíveis:
  - build_rules_chain(): abordagem por regras de produção — sem LLM, execução local.
  - build_llm_chain(): abordagem LLM puro — requer Ollama rodando com modelo configurado.
  - build_hybrid_chain(): abordagem híbrida — LLM extrai, regras classificam.

AVISO: Protótipo acadêmico. As chains aqui definidas são para fins de pesquisa
e comparação de abordagens. Não usar em ambiente industrial real.
"""

from langchain_core.runnables import RunnableLambda

from src.approaches.hybrid import run_hybrid
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


def build_hybrid_chain() -> RunnableLambda:
    """
    Constrói chain LangChain para a abordagem de triagem híbrida (LLM + regras).

    A chain aceita um dict com a chave 'texto' (str) e retorna um TriageResult.
    O LLM é usado apenas para extração de informações — a classificação de urgência,
    prioridade e equipe é determinística via motor de regras de produção.
    Requer Ollama rodando com o modelo configurado em settings.ollama_model.
    A conexão com Ollama ocorre apenas em tempo de execução, nunca na construção da chain.

    Uso:
        chain = build_hybrid_chain()
        resultado = chain.invoke({"texto": "BOMB-001 com vibração excessiva"})

    Returns:
        RunnableLambda que envolve run_hybrid().
    """

    def _invocar(inputs: dict) -> TriageResult:
        """Adaptador entre interface LangChain (dict) e run_hybrid (str)."""
        return run_hybrid(inputs["texto"])

    return RunnableLambda(_invocar)


def build_rules_catref_chain() -> RunnableLambda:
    """
    Constrói chain do cenário-diagnóstico "regras com categoria de referência".

    Igual à abordagem por regras, mas a categoria é fixada no valor de referência
    (gabarito), em vez de detectada por palavras-chave. Serve para medir quanto do
    erro das regras decorre da detecção de categoria, isolando-o da decisão.

    IMPORTANTE: não é um teto por "fatos de referência" completos — o dataset não
    contém os atributos intermediários (risco, impacto, ativo) como gabarito; apenas
    a categoria está disponível. Risco/impacto continuam vindo da extração por
    palavras-chave. Cenário opcional, não executado por padrão.

    A chain aceita um dict com 'texto' (str) e 'categoria_ref' (str) e não depende
    de LLM nem de Ollama — execução completamente local.

    Returns:
        RunnableLambda que envolve run_rules_only(texto, categoria_ref).
    """

    def _invocar(inputs: dict) -> TriageResult:
        """Adaptador: repassa texto e categoria de referência a run_rules_only."""
        return run_rules_only(inputs["texto"], inputs.get("categoria_ref"))

    return RunnableLambda(_invocar)
