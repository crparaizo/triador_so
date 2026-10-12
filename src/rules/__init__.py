"""
Motor de regras de produção para classificação e encaminhamento de ordens de serviço.

Este pacote implementa as regras declarativas de triagem industrial usadas pela
abordagem 'REGRAS' e pelo componente de classificação da abordagem 'HÍBRIDO'.

Exporta:
    RuleCondition — condições de disparo de uma regra (Pydantic v2)
    RuleAction    — ações executadas quando uma regra dispara (Pydantic v2)
    Rule          — regra de produção completa com condições, ações e precedência
    load_rules    — carrega e valida as regras do arquivo data/rules.yaml (lru_cache)

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from src.rules.definitions import Rule, RuleAction, RuleCondition, load_rules

__all__ = [
    "RuleCondition",
    "RuleAction",
    "Rule",
    "load_rules",
]
