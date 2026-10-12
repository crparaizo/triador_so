"""
Testes para src/rules/engine.py (apply_rules) e src/approaches/rules_only.py
(run_rules_only) e src/orchestration/chains.py (build_rules_chain).

Testes 1-12: unidade do motor — criam regras artificiais inline, sem usar rules.yaml.
Testes 13-18: integração com YAMLs reais para run_rules_only e build_rules_chain.
Nenhum teste requer Ollama rodando.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import pytest

from src.approaches.rules_only import run_rules_only
from src.data.loader import load_categories, load_knowledge_base
from src.orchestration.chains import build_rules_chain
from src.rules.definitions import Rule, RuleAction, RuleCondition, load_rules
from src.rules.engine import apply_rules
from src.schemas.assets import Asset
from src.schemas.extraction import ContextData, ExtractedInfo
from src.schemas.triage import ApproachType, TriageResult


# ---------------------------------------------------------------------------
# Fixture autouse: limpar cache antes e depois de cada teste
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def limpar_caches():
    """Garante isolamento dos testes limpando o cache de todos os loaders."""
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    load_rules.cache_clear()
    yield
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    load_rules.cache_clear()


# ---------------------------------------------------------------------------
# Helpers para criação de regras de teste
# ---------------------------------------------------------------------------


def _regra(
    rule_id: str = "RULE-MOCK",
    risco_seguranca: bool | None = None,
    impacto_producao: bool | None = None,
    categoria: str | None = None,
    criticidade_ativo: str | None = None,
    palavras_chave: list[str] | None = None,
    operador: str = "AND",
    urgencia: str | None = None,
    prioridade: str | None = None,
    equipe: str | None = None,
    requer_revisao: bool | None = None,
    motivo: str | None = None,
    confianca: float | None = None,
    prioridade_regra: int = 50,
) -> Rule:
    """Cria uma Rule de teste com os parâmetros fornecidos."""
    return Rule(
        id=rule_id,
        descricao=f"Regra de teste {rule_id}",
        condicoes=RuleCondition(
            risco_seguranca=risco_seguranca,
            impacto_producao=impacto_producao,
            categoria=categoria,
            criticidade_ativo=criticidade_ativo,
            palavras_chave=palavras_chave,
            operador=operador,
        ),
        acoes=RuleAction(
            urgencia=urgencia,
            prioridade=prioridade,
            equipe=equipe,
            requer_revisao_humana=requer_revisao,
            motivo_revisao=motivo,
            confianca=confianca,
        ),
        prioridade_regra=prioridade_regra,
    )


# ---------------------------------------------------------------------------
# Testes unitários do motor (12 testes) — regras artificiais inline
# ---------------------------------------------------------------------------


def test_apply_rules_risco_seguranca_imediata():
    """risco_seguranca=True deve disparar regra → urgencia IMEDIATA e prioridade P1."""
    regra = _regra(
        rule_id="RULE-MOCK-001",
        risco_seguranca=True,
        urgencia="IMEDIATA",
        prioridade="P1",
        requer_revisao=True,
        motivo="Risco de segurança confirmado",
        prioridade_regra=100,
    )
    extracted = ExtractedInfo(risco_seguranca=True)
    context = ContextData()

    resultado = apply_rules(extracted, context, [regra])

    assert resultado["urgencia"] == "IMEDIATA"
    assert resultado["prioridade"] == "P1"
    assert "RULE-MOCK-001" in resultado["regras_acionadas"]


def test_apply_rules_retorna_revisao_humana_com_motivo():
    """Quando requer_revisao_humana=True, motivo_revisao nunca deve ser None."""
    # Cenário 1: fallback (nenhuma regra dispara)
    resultado = apply_rules(ExtractedInfo(), ContextData(), [])

    assert resultado["requer_revisao_humana"] is True
    assert resultado["motivo_revisao"] is not None
    assert len(resultado["motivo_revisao"]) > 0

    # Cenário 2: regra dispara e seta revisão
    regra = _regra(
        rule_id="RULE-MOCK-REV",
        risco_seguranca=True,
        urgencia="IMEDIATA",
        prioridade="P1",
        requer_revisao=True,
        motivo="Revisão de teste",
        prioridade_regra=90,
    )
    resultado2 = apply_rules(
        ExtractedInfo(risco_seguranca=True), ContextData(), [regra]
    )
    assert resultado2["requer_revisao_humana"] is True
    assert resultado2["motivo_revisao"] is not None


def test_apply_rules_ativo_critico_com_impacto():
    """impacto_producao=True + criticidade_ativo=ALTA deve resultar em P1."""
    ativo_critico = Asset(
        id="test-001",
        nome="Bomba Teste",
        tag="BOMB-TEST",
        tipo="Mecânico",
        localizacao="Setor A",
        equipe_responsavel="Manutenção Mecânica",
        criticidade="ALTA",
    )
    regra = _regra(
        rule_id="RULE-MOCK-004",
        impacto_producao=True,
        criticidade_ativo="ALTA",
        urgencia="ALTA",
        prioridade="P1",
        requer_revisao=False,
        prioridade_regra=85,
    )
    extracted = ExtractedInfo(impacto_producao=True)
    context = ContextData(ativo_encontrado=ativo_critico)

    resultado = apply_rules(extracted, context, [regra])

    assert resultado["prioridade"] == "P1"
    assert "RULE-MOCK-004" in resultado["regras_acionadas"]


def test_apply_rules_categoria_eletrica_equipe_correta():
    """Categoria ELETRICA deve acionar regra e retornar equipe elétrica."""
    regra = _regra(
        rule_id="RULE-MOCK-010",
        categoria="ELETRICA",
        urgencia="ALTA",
        prioridade="P2",
        equipe="Manutenção Elétrica",
        requer_revisao=False,
        prioridade_regra=65,
    )
    extracted = ExtractedInfo()
    context = ContextData()

    resultado = apply_rules(
        extracted, context, [regra], categoria_detectada="ELETRICA"
    )

    assert "Elétrica" in resultado["equipe"]
    assert "RULE-MOCK-010" in resultado["regras_acionadas"]


def test_apply_rules_sem_regras_disparadas_desconhecida():
    """Com lista de regras vazia, resultado deve ser DESCONHECIDA + revisão humana."""
    resultado = apply_rules(ExtractedInfo(), ContextData(), [])

    assert resultado["urgencia"] == "DESCONHECIDA"
    assert resultado["prioridade"] == "DESCONHECIDA"
    assert resultado["requer_revisao_humana"] is True
    assert resultado["regras_acionadas"] == []


def test_apply_rules_regras_acionadas_listadas():
    """ID da regra disparada deve aparecer em regras_acionadas."""
    regra = _regra(
        rule_id="RULE-MOCK-LISTA",
        risco_seguranca=True,
        urgencia="IMEDIATA",
        prioridade="P1",
        requer_revisao=True,
        motivo="Teste de listagem",
        prioridade_regra=50,
    )
    resultado = apply_rules(
        ExtractedInfo(risco_seguranca=True), ContextData(), [regra]
    )

    assert "RULE-MOCK-LISTA" in resultado["regras_acionadas"]


def test_apply_rules_maior_prioridade_ganha():
    """Regra com maior prioridade_regra deve prevalecer no campo urgencia."""
    regra_alta = _regra(
        rule_id="RULE-MOCK-ALTA",
        risco_seguranca=True,
        urgencia="IMEDIATA",
        prioridade="P1",
        prioridade_regra=100,
    )
    regra_baixa = _regra(
        rule_id="RULE-MOCK-BAIXA",
        risco_seguranca=True,
        urgencia="BAIXA",
        prioridade="P4",
        prioridade_regra=40,
    )
    # Ambas disparam (risco_seguranca=True) — maior prioridade_regra vence
    resultado = apply_rules(
        ExtractedInfo(risco_seguranca=True),
        ContextData(),
        [regra_baixa, regra_alta],  # propositalmente fora de ordem
    )

    assert resultado["urgencia"] == "IMEDIATA", (
        "Regra de prioridade 100 deve prevalecer sobre a de prioridade 40"
    )


def test_apply_rules_operador_or_dispara_com_uma_condicao():
    """Regra OR deve disparar quando apenas uma de suas condições for satisfeita."""
    regra_or = _regra(
        rule_id="RULE-MOCK-OR",
        categoria="ELETRICA",          # não satisfeita (categoria=MECANICA)
        risco_seguranca=True,          # satisfeita
        operador="OR",
        urgencia="IMEDIATA",
        prioridade="P1",
        prioridade_regra=50,
    )
    # risco_seguranca=True mas categoria detectada é MECANICA, não ELETRICA
    resultado = apply_rules(
        ExtractedInfo(risco_seguranca=True),
        ContextData(),
        [regra_or],
        categoria_detectada="MECANICA",
    )

    assert "RULE-MOCK-OR" in resultado["regras_acionadas"], (
        "Regra OR deve disparar quando pelo menos uma condição for satisfeita"
    )


def test_apply_rules_operador_and_exige_todas_condicoes():
    """Regra AND não deve disparar quando apenas uma condição for satisfeita."""
    regra_and = _regra(
        rule_id="RULE-MOCK-AND",
        categoria="ELETRICA",          # não satisfeita (categoria=MECANICA)
        risco_seguranca=True,          # satisfeita
        operador="AND",
        urgencia="IMEDIATA",
        prioridade="P1",
        prioridade_regra=50,
    )
    # risco_seguranca=True mas categoria=MECANICA (não ELETRICA) → AND falha
    resultado = apply_rules(
        ExtractedInfo(risco_seguranca=True),
        ContextData(),
        [regra_and],
        categoria_detectada="MECANICA",
    )

    assert "RULE-MOCK-AND" not in resultado["regras_acionadas"], (
        "Regra AND não deve disparar quando categoria não corresponde"
    )


def test_apply_rules_palavras_chave_nos_sintomas():
    """Palavra-chave presente nos sintomas extraídos deve disparar a regra."""
    regra = _regra(
        rule_id="RULE-MOCK-KW-SINT",
        palavras_chave=["vibração"],
        operador="AND",
        urgencia="ALTA",
        prioridade="P2",
        prioridade_regra=50,
    )
    # Palavra-chave nos sintomas (não no texto)
    resultado = apply_rules(
        ExtractedInfo(sintomas=["vibração excessiva"]),
        ContextData(),
        [regra],
        texto_original="",
    )

    assert "RULE-MOCK-KW-SINT" in resultado["regras_acionadas"], (
        "Regra deve disparar quando palavra-chave está nos sintomas"
    )


def test_apply_rules_criticidade_ativo_none_nao_dispara():
    """Regra com criticidade_ativo=ALTA não deve disparar sem ativo encontrado."""
    regra = _regra(
        rule_id="RULE-MOCK-CRIT",
        criticidade_ativo="ALTA",
        urgencia="ALTA",
        prioridade="P2",
        prioridade_regra=60,
    )
    # ativo_encontrado=None → condição criticidade_ativo não pode ser satisfeita
    resultado = apply_rules(ExtractedInfo(), ContextData(ativo_encontrado=None), [regra])

    assert "RULE-MOCK-CRIT" not in resultado["regras_acionadas"], (
        "Regra com criticidade_ativo não deve disparar quando ativo não é encontrado"
    )


def test_apply_rules_palavras_chave_no_texto_normalizado():
    """Palavra-chave no texto original (normalizado) deve disparar a regra."""
    regra = _regra(
        rule_id="RULE-MOCK-KW-TEXTO",
        palavras_chave=["incendio"],    # normalizado: "incendio"
        operador="AND",
        urgencia="IMEDIATA",
        prioridade="P1",
        requer_revisao=True,
        motivo="Palavra de emergência no texto",
        prioridade_regra=90,
    )
    # "incêndio" no texto original é normalizado para "incendio"
    resultado = apply_rules(
        ExtractedInfo(sintomas=[]),     # sintomas vazios
        ContextData(),
        [regra],
        texto_original="incêndio na área",
    )

    assert "RULE-MOCK-KW-TEXTO" in resultado["regras_acionadas"], (
        "Regra deve disparar via normalização do texto original"
    )


# ---------------------------------------------------------------------------
# Testes de integração: run_rules_only e build_rules_chain (6 testes)
# ---------------------------------------------------------------------------


def test_run_rules_only_texto_valido_retorna_triage_result():
    """run_rules_only com texto válido deve retornar TriageResult com abordagem REGRAS."""
    result = run_rules_only("BOMB-001 com vibração excessiva no Setor A")

    assert isinstance(result, TriageResult), (
        "run_rules_only deve retornar TriageResult"
    )
    assert result.abordagem == ApproachType.REGRAS, (
        f"Esperado abordagem REGRAS, obtido: {result.abordagem}"
    )


def test_run_rules_only_texto_minimo_revisao_humana():
    """Texto mínimo sem informações suficientes deve gerar revisão humana."""
    result = run_rules_only("problema")

    assert result.requer_revisao_humana is True, (
        "Texto genérico deve resultar em requer_revisao_humana=True"
    )


def test_run_rules_only_latencia_abaixo_2000ms():
    """Triagem por regras deve ser concluída em menos de 2000 ms."""
    result = run_rules_only("bomba com vazamento de óleo")

    assert result.latencia_ms < 2000.0, (
        f"Latência muito alta: {result.latencia_ms:.1f} ms (limite: 2000 ms)"
    )


def test_run_rules_only_revisao_humana_tem_motivo():
    """Todo resultado com requer_revisao_humana=True deve ter motivo_revisao preenchido."""
    result = run_rules_only("problema")  # texto vago → revisão obrigatória

    if result.requer_revisao_humana:
        assert result.motivo_revisao is not None, (
            "motivo_revisao não pode ser None quando requer_revisao_humana=True"
        )
        assert len(result.motivo_revisao) > 0, (
            "motivo_revisao não pode ser string vazia"
        )


def test_run_rules_only_regras_acionadas_para_risco():
    """Texto com risco de explosão deve acionar RULE-001 ou RULE-002."""
    result = run_rules_only("risco de explosão na caldeira, emergência")

    regras = result.regras_acionadas
    assert "RULE-001" in regras or "RULE-002" in regras, (
        f"Esperado RULE-001 ou RULE-002 nas regras acionadas, obtido: {regras}"
    )


def test_build_rules_chain_invoke_retorna_triage_result():
    """build_rules_chain().invoke({'texto': ...}) deve retornar TriageResult REGRAS."""
    chain = build_rules_chain()
    result = chain.invoke({"texto": "curto no painel elétrico"})

    assert isinstance(result, TriageResult), (
        "build_rules_chain().invoke() deve retornar TriageResult"
    )
    assert result.abordagem == ApproachType.REGRAS, (
        f"Esperado abordagem REGRAS, obtido: {result.abordagem}"
    )
