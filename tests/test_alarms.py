"""
Testes da entrada por alarmes do supervisório simulado e da regra da PMTA (RULE-021).

Cobrem a leitura de pressão no texto, o texto gerado pelo adaptador, o disparo
da RULE-021 acima da PMTA e a ausência de disparo abaixo dela ou sem PMTA
cadastrada. Nenhum teste requer Ollama rodando.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import json
from pathlib import Path

import pytest

from src.alarms import AlarmEvent, alarme_para_relato
from src.approaches.rules_only import run_rules_only
from src.data.dataset_loader import load_dataset
from src.data.loader import load_categories, load_knowledge_base
from src.extraction.medicoes import pressoes_kpa
from src.rules.definitions import load_rules

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def limpar_caches():
    """Garante isolamento dos testes limpando o cache dos loaders."""
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    load_rules.cache_clear()
    yield
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    load_rules.cache_clear()


def test_pressoes_em_kpa_e_mpa_no_formato_brasileiro():
    """Lê ponto como milhar e vírgula como decimal, e converte MPa para kPa."""
    assert pressoes_kpa("pressão de 1.080 kPa, limite de 950 kPa") == [1080.0, 950.0]
    assert pressoes_kpa("pressão de 1,04 MPa") == pytest.approx([1040.0])
    assert pressoes_kpa("vibração de 11,2 mm/s e 92 °C") == []


def test_adaptador_gera_texto_com_ativo_valor_e_limite():
    """O texto da OS traz o nome e a tag do ativo, o valor medido e o limite de alarme."""
    evento = AlarmEvent(id="T-1", tag="CAL-001", variavel="pressao", sentido="alto",
                        valor=1080, limite=950, unidade="kPa")
    texto = alarme_para_relato(evento, load_knowledge_base())
    assert texto == ("Alarme de pressão alta em Caldeira de Vapor (CAL-001), gerado pelo supervisório: "
                     "1.080 kPa, acima do limite de alarme de 950 kPa.")


def test_rule021_dispara_com_pressao_acima_da_pmta():
    """Pressão acima da PMTA cadastrada da caldeira leva a IMEDIATA/P1 com revisão."""
    result = run_rules_only("Alarme de pressão alta em Caldeira de Vapor (CAL-001), gerado pelo "
                            "supervisório: 1.080 kPa, acima do limite de alarme de 950 kPa.")
    assert "RULE-021" in result.regras_acionadas
    assert result.urgencia.value == "IMEDIATA"
    assert result.requer_revisao_humana is True


def test_rule021_nao_dispara_abaixo_da_pmta():
    """Pressão alta, mas abaixo da PMTA, não aciona a regra."""
    result = run_rules_only("Alarme de pressão alta em Caldeira de Vapor (CAL-001), gerado pelo "
                            "supervisório: 980 kPa, acima do limite de alarme de 950 kPa.")
    assert "RULE-021" not in result.regras_acionadas


def test_rule021_nao_dispara_sem_pmta_cadastrada():
    """Ativo sem PMTA cadastrada (compressor) não aciona a regra, mesmo com pressão no texto."""
    result = run_rules_only("Alarme de pressão baixa em Compressor de Ar Instrumento (COMP-001), gerado "
                            "pelo supervisório: 420 kPa, abaixo do limite de alarme de 550 kPa.")
    assert "RULE-021" not in result.regras_acionadas


def test_conjunto_principal_nao_tem_valores_de_pressao():
    """Nenhum dos 100 relatos traz pressão em kPa ou MPa, de modo que a RULE-021 não o altera."""
    assert all(pressoes_kpa(c.texto) == [] for c in load_dataset())


def test_casos_de_alarme_gerados_a_partir_dos_eventos():
    """alarm_cases.json é válido e tem um caso por evento, com o texto do adaptador."""
    eventos = json.loads((RAIZ / "datasets" / "alarm_events.json").read_text(encoding="utf-8"))
    casos = load_dataset(str(RAIZ / "datasets" / "alarm_cases.json"))
    kb = load_knowledge_base()
    assert [c.id for c in casos] == [e["evento"]["id"] for e in eventos]
    assert all(c.tipo == "ALARME" for c in casos)
    assert [c.texto for c in casos] == [alarme_para_relato(AlarmEvent(**e["evento"]), kb) for e in eventos]
