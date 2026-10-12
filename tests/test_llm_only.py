"""
Testes para src/approaches/llm_only.py — abordagem de triagem baseada em LLM puro.

Todos os testes usam mock via pytest-mock — nenhum teste conecta ao Ollama.
Os dados de teste são sintéticos e não representam instalação industrial real.

Padrão de mock:
    mock_ollama patcha 'src.approaches.llm_only.ChatOllama'
    mock_kb     patcha 'src.approaches.llm_only.load_knowledge_base'
    limpar_caches (autouse) limpa caches de funções cacheadas antes e após cada teste
"""

import json
from unittest.mock import MagicMock

import pytest

from src.approaches.llm_only import run_llm_only
from src.schemas.triage import (
    ApproachType,
    PriorityLevel,
    TriageResult,
    UrgencyLevel,
)

# ---------------------------------------------------------------------------
# JSON de referência para os testes
# ---------------------------------------------------------------------------

# JSON válido completo com todos os campos esperados
JSON_VALIDO = json.dumps(
    {
        "urgencia": "ALTA",
        "prioridade": "P2",
        "categoria": "MECANICA",
        "equipe_sugerida": "Manutenção Mecânica",
        "regras_acionadas": [],
        "evidencias": {"urgencia": "vibração alta"},
        "requer_revisao_humana": False,
        "motivo_revisao": None,
        "confianca": 0.85,
        "campos_sem_suporte": [],
    }
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ollama(mocker):
    """Patcha ChatOllama em llm_only para evitar conexão com Ollama."""
    mock_classe = mocker.patch("src.approaches.llm_only.ChatOllama")
    return mock_classe.return_value


@pytest.fixture
def mock_kb(mocker, sample_knowledge_base):
    """Patcha load_knowledge_base para retornar KB de teste (sem leitura de YAML)."""
    mocker.patch(
        "src.approaches.llm_only.load_knowledge_base",
        return_value=sample_knowledge_base,
    )


@pytest.fixture(autouse=True)
def limpar_caches():
    """Limpa caches de funções cacheadas antes e após cada teste para isolamento."""
    from src.config.loader import get_settings
    from src.data.loader import load_categories, load_knowledge_base

    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    get_settings.cache_clear()
    yield
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def test_json_valido_completo_retorna_abordagem_llm(mock_ollama, mock_kb):
    """JSON válido do LLM deve retornar TriageResult com abordagem LLM."""
    mock_ollama.invoke.return_value = MagicMock(content=JSON_VALIDO)

    resultado = run_llm_only("BOMB-001 com vibração excessiva no Setor A")

    assert resultado.abordagem == ApproachType.LLM


def test_urgencia_invalida_mapeada_para_desconhecida(mock_ollama, mock_kb):
    """Urgência com valor fora do enum deve ser mapeada para DESCONHECIDA."""
    json_urgencia_invalida = json.dumps(
        {
            "urgencia": "EXTREMA",
            "prioridade": "P2",
            "categoria": "MECANICA",
            "equipe_sugerida": "Manutenção Mecânica",
            "regras_acionadas": [],
            "evidencias": {},
            "requer_revisao_humana": False,
            "motivo_revisao": None,
            "confianca": 0.5,
            "campos_sem_suporte": [],
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_urgencia_invalida)

    resultado = run_llm_only("relato de teste")

    assert resultado.urgencia == UrgencyLevel.DESCONHECIDA


def test_sem_equipe_retorna_revisao_manual(mock_ollama, mock_kb):
    """equipe_sugerida nula no JSON deve resultar em equipe 'Revisão Manual'."""
    json_sem_equipe = json.dumps(
        {
            "urgencia": "ALTA",
            "prioridade": "P2",
            "categoria": "MECANICA",
            "equipe_sugerida": None,
            "regras_acionadas": [],
            "evidencias": {},
            "requer_revisao_humana": False,
            "motivo_revisao": None,
            "confianca": 0.5,
            "campos_sem_suporte": [],
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_sem_equipe)

    resultado = run_llm_only("relato de teste")

    assert resultado.equipe_sugerida == "Revisão Manual"


def test_json_malformado_requer_revisao_humana_true(mock_ollama, mock_kb):
    """Resposta sem JSON válido deve retornar TriageResult com revisão humana obrigatória."""
    mock_ollama.invoke.return_value = MagicMock(content="texto inválido sem JSON nenhum")

    resultado = run_llm_only("relato qualquer")

    assert resultado.requer_revisao_humana is True
    assert resultado.motivo_revisao is not None


def test_connection_error_fallback_sem_excecao(mock_ollama, mock_kb):
    """ConnectionError no LLM deve retornar TriageResult válido sem propagar exceção."""
    mock_ollama.invoke.side_effect = ConnectionError("sem conexão com Ollama")

    resultado = run_llm_only("relato qualquer")

    assert isinstance(resultado, TriageResult)
    assert resultado.confianca == 0.0
    assert resultado.requer_revisao_humana is True


def test_regras_acionadas_sempre_lista_vazia(mock_ollama, mock_kb):
    """regras_acionadas deve ser sempre [] mesmo que o LLM retorne regras no JSON."""
    json_com_regras = json.dumps(
        {
            "urgencia": "ALTA",
            "prioridade": "P2",
            "categoria": "MECANICA",
            "equipe_sugerida": "Manutenção Mecânica",
            "regras_acionadas": ["RULE-001", "RULE-002"],  # LLM retorna regras
            "evidencias": {},
            "requer_revisao_humana": False,
            "motivo_revisao": None,
            "confianca": 0.85,
            "campos_sem_suporte": [],
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_com_regras)

    resultado = run_llm_only("relato qualquer")

    # Independente do que o LLM retornar, regras_acionadas é sempre []
    assert resultado.regras_acionadas == []


def test_latencia_ms_maior_que_zero(mock_ollama, mock_kb):
    """latencia_ms deve ser maior que zero após execução bem-sucedida."""
    mock_ollama.invoke.return_value = MagicMock(content=JSON_VALIDO)

    resultado = run_llm_only("BOMB-001 com vibração excessiva")

    assert resultado.latencia_ms > 0


def test_abordagem_sempre_llm_independente_do_json(mock_ollama, mock_kb):
    """abordagem deve ser sempre ApproachType.LLM independente do conteúdo do JSON."""
    mock_ollama.invoke.return_value = MagicMock(content=JSON_VALIDO)

    resultado = run_llm_only("qualquer relato de manutenção")

    assert resultado.abordagem == ApproachType.LLM


def test_prioridade_p1_minusculo_mapeada_para_P1(mock_ollama, mock_kb):
    """Prioridade 'p1' (minúsculo) deve ser mapeada para PriorityLevel.P1."""
    json_p1 = json.dumps(
        {
            "urgencia": "IMEDIATA",
            "prioridade": "p1",  # minúsculo — deve ser normalizado
            "categoria": "SEGURANCA",
            "equipe_sugerida": "Manutenção Mecânica",
            "regras_acionadas": [],
            "evidencias": {},
            "requer_revisao_humana": False,
            "motivo_revisao": None,
            "confianca": 0.9,
            "campos_sem_suporte": [],
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_p1)

    resultado = run_llm_only("risco de segurança imediato na linha")

    assert resultado.prioridade == PriorityLevel.P1


def test_contexto_ativos_equipes_presente_no_prompt(mock_ollama, mock_kb):
    """O prompt enviado ao LLM deve conter tags dos ativos e nomes das equipes da KB."""
    mock_ollama.invoke.return_value = MagicMock(content=JSON_VALIDO)

    run_llm_only("relato de teste para inspeção de prompt")

    # Inspecionar o argumento posicional passado para llm.invoke()
    call_args = mock_ollama.invoke.call_args
    prompt_text = call_args.args[0]

    # O prompt deve conter dados da KB de teste (BOMB-TEST ou Manutenção Mecânica)
    assert "BOMB-TEST" in prompt_text or "Manutenção Mecânica" in prompt_text


def test_requer_revisao_humana_true_tem_motivo_revisao(mock_ollama, mock_kb):
    """Quando requer_revisao_humana=True, motivo_revisao não deve ser None."""
    json_com_revisao = json.dumps(
        {
            "urgencia": "DESCONHECIDA",
            "prioridade": "DESCONHECIDA",
            "categoria": "DESCONHECIDA",
            "equipe_sugerida": "Manutenção Mecânica",
            "regras_acionadas": [],
            "evidencias": {},
            "requer_revisao_humana": True,
            "motivo_revisao": "situação incerta, verificar com técnico",
            "confianca": 0.3,
            "campos_sem_suporte": ["urgencia", "categoria"],
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_com_revisao)

    resultado = run_llm_only("relato ambíguo sem informações claras")

    assert resultado.requer_revisao_humana is True
    assert resultado.motivo_revisao is not None


def test_texto_vazio_retorna_triage_result_valido(mock_ollama, mock_kb):
    """Texto vazio não deve lançar exceção e deve retornar TriageResult válido."""
    mock_ollama.invoke.return_value = MagicMock(content=JSON_VALIDO)

    resultado = run_llm_only("")

    assert isinstance(resultado, TriageResult)
