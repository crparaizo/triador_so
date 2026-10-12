"""
Orquestração LangChain dos pipelines de triagem de ordens de serviço industriais.

Expõe:
    build_rules_chain — chain LangChain para a abordagem baseada em regras

As chains de LLM e híbrida serão implementadas nas etapas seguintes.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from src.orchestration.chains import build_rules_chain

__all__ = [
    "build_rules_chain",
]
