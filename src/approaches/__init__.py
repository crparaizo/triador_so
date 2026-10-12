"""
Implementação das três abordagens de triagem de ordens de serviço industriais.

Expõe:
    run_rules_only — pipeline completo de triagem baseado em regras de produção

As abordagens LLM e híbrida serão implementadas nas etapas seguintes.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from src.approaches.rules_only import run_rules_only

__all__ = [
    "run_rules_only",
]
