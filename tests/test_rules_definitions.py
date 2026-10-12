"""
Testes para src/rules/definitions.py — modelos Pydantic e carregamento de regras.

Verifica a estrutura dos modelos RuleCondition, RuleAction e Rule, além do
comportamento de load_rules() incluindo cache e validação do arquivo YAML.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import pytest

from src.rules.definitions import Rule, RuleAction, RuleCondition, load_rules


# ---------------------------------------------------------------------------
# Fixture autouse: limpar cache antes e depois de cada teste para isolamento
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def limpar_cache_regras():
    """Garante isolamento dos testes limpando o cache de load_rules."""
    load_rules.cache_clear()
    yield
    load_rules.cache_clear()


# ---------------------------------------------------------------------------
# Testes de load_rules()
# ---------------------------------------------------------------------------

def test_load_rules_retorna_lista_de_rules():
    """load_rules() deve retornar uma lista não-vazia de instâncias de Rule."""
    rules = load_rules()

    assert isinstance(rules, list), "load_rules() deve retornar uma lista"
    assert len(rules) > 0, "A lista de regras não deve estar vazia"
    assert isinstance(rules[0], Rule), "Cada elemento deve ser instância de Rule"


def test_load_rules_quantidade_entre_15_e_20():
    """O total de regras no YAML deve ser entre 15 e 20 inclusive."""
    rules = load_rules()

    assert 15 <= len(rules) <= 20, (
        f"Esperado entre 15 e 20 regras, encontrado: {len(rules)}"
    )


def test_todas_regras_tem_ids_unicos():
    """Todos os ids das regras devem ser únicos (sem duplicatas)."""
    rules = load_rules()
    ids = [r.id for r in rules]

    assert len(set(ids)) == len(ids), (
        f"IDs duplicados encontrados: {[i for i in ids if ids.count(i) > 1]}"
    )


def test_todas_regras_prioridade_regra_positivo():
    """Todas as regras devem ter prioridade_regra >= 1."""
    rules = load_rules()

    for rule in rules:
        assert rule.prioridade_regra >= 1, (
            f"Regra {rule.id} tem prioridade_regra inválida: {rule.prioridade_regra}"
        )


# ---------------------------------------------------------------------------
# Testes de RuleCondition
# ---------------------------------------------------------------------------

def test_rule_condition_operador_padrao_and():
    """RuleCondition instanciada sem argumentos deve ter operador='AND'."""
    cond = RuleCondition()

    assert cond.operador == "AND", (
        f"Operador padrão esperado 'AND', encontrado: '{cond.operador}'"
    )


# ---------------------------------------------------------------------------
# Testes de RuleAction
# ---------------------------------------------------------------------------

def test_rule_action_todos_campos_opcionais():
    """RuleAction deve instanciar sem erros e com todos os campos None."""
    action = RuleAction()

    # Todos os campos devem ser None quando nenhum argumento é passado
    assert action.urgencia is None
    assert action.prioridade is None
    assert action.equipe is None
    assert action.requer_revisao_humana is None
    assert action.motivo_revisao is None
    assert action.confianca is None


# ---------------------------------------------------------------------------
# Testes de Rule
# ---------------------------------------------------------------------------

def test_rule_revisao_com_motivo_valida():
    """Rule com requer_revisao_humana=True e motivo_revisao preenchido deve ser válida."""
    rule = Rule(
        id="RULE-TEST",
        descricao="Regra de teste para revisão humana",
        condicoes=RuleCondition(),
        acoes=RuleAction(
            requer_revisao_humana=True,
            motivo_revisao="Motivo de teste para validação"
        ),
        prioridade_regra=1,
    )

    # Deve instanciar sem ValidationError
    assert rule.id == "RULE-TEST"
    assert rule.acoes.requer_revisao_humana is True
    assert rule.acoes.motivo_revisao == "Motivo de teste para validação"


# ---------------------------------------------------------------------------
# Testes de cache
# ---------------------------------------------------------------------------

def test_load_rules_cache_clear():
    """load_rules.cache_clear() deve executar sem erro; segunda chamada retorna mesma lista."""
    # Primeira carga
    rules_primeira = load_rules()

    # Limpar cache e recarregar
    load_rules.cache_clear()
    rules_segunda = load_rules()

    # Deve retornar a mesma quantidade de regras após cache_clear()
    assert len(rules_primeira) == len(rules_segunda), (
        "Segunda carga após cache_clear() deve retornar o mesmo número de regras"
    )
    # Verificar que os ids são os mesmos
    ids_primeira = {r.id for r in rules_primeira}
    ids_segunda = {r.id for r in rules_segunda}
    assert ids_primeira == ids_segunda, (
        "Segunda carga após cache_clear() deve retornar as mesmas regras"
    )
