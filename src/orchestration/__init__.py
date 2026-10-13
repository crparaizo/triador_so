"""
Orquestração LangChain (LCEL) dos pipelines de triagem de ordens de serviço industriais.

Expõe (importados sob demanda, para evitar ciclo com src.approaches):
    build_rules_chain        — fluxo por regras de produção
    build_llm_chain          — fluxo LLM puro
    build_hybrid_chain       — fluxo híbrido (LLM extrai, regras classificam)
    build_rules_catref_chain — fluxo por regras com categoria de referência

A topologia comum dos fluxos fica em src.orchestration.triage_flow.
Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

__all__ = [
    "build_rules_chain",
    "build_llm_chain",
    "build_hybrid_chain",
    "build_rules_catref_chain",
]


def __getattr__(nome: str):
    """Importa src.orchestration.chains apenas quando um builder é solicitado (PEP 562)."""
    if nome in __all__:
        from src.orchestration import chains

        return getattr(chains, nome)
    raise AttributeError(f"module 'src.orchestration' has no attribute '{nome}'")
