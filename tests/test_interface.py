"""
Testes automatizados para src/interface/session_manager.py.

AVISO: Este é um protótipo acadêmico. Os testes cobrem apenas o gerenciador
de sessões — não importam streamlit nem dependem de Ollama.

Todas as fixtures usam tmp_path e monkeypatch para isolar o sistema de arquivos
real e a configuração de produção.
"""

import json
from pathlib import Path

import pytest

from src.config.loader import Settings
from src.interface.session_manager import (
    clear_sessions,
    load_sessions,
    save_session,
)
from src.schemas.triage import TriageResult


# ---------------------------------------------------------------------------
# Fixture auxiliar: redireciona sessions_dir para pasta temporária
# ---------------------------------------------------------------------------

@pytest.fixture
def sessions_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Retorna Path de pasta de sessões temporária SEM criá-la.

    Aplica monkeypatch em get_settings para que session_manager use a pasta
    temporária em vez da pasta de produção configurada.
    """
    pasta = tmp_path / "sessions_test"
    # Pasta intencionalmente NÃO criada aqui — testa criação automática
    mock_settings = Settings(sessions_dir=str(pasta))
    monkeypatch.setattr(
        "src.interface.session_manager.get_settings",
        lambda: mock_settings,
    )
    return pasta


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_save_session_cria_json_na_pasta_correta(
    sessions_dir: Path, sample_triage_result: TriageResult
) -> None:
    """save_session deve criar exatamente 1 arquivo .json na pasta de sessões."""
    save_session({"hibrido": sample_triage_result}, "Bomba com vibração")

    arquivos = list(sessions_dir.glob("*.json"))
    assert sessions_dir.exists(), "Pasta de sessões deve existir após salvar"
    assert len(arquivos) == 1, "Deve existir exatamente 1 arquivo JSON"


def test_save_session_cria_pasta_se_nao_existir(
    sessions_dir: Path, sample_triage_result: TriageResult
) -> None:
    """save_session deve criar a pasta automaticamente se ela não existir."""
    assert not sessions_dir.exists(), "Pasta não deve existir antes do save"

    save_session({"hibrido": sample_triage_result}, "Relato de teste")

    assert sessions_dir.exists(), "Pasta deve ter sido criada por save_session"


def test_load_sessions_ordenado_por_timestamp_desc(
    sessions_dir: Path,
) -> None:
    """load_sessions deve retornar sessões com a mais recente primeiro."""
    sessions_dir.mkdir(parents=True)

    sessao_antiga = {
        "timestamp": "2024-01-01T10:00:00",
        "texto": "relato antigo",
        "results": {},
    }
    sessao_recente = {
        "timestamp": "2024-01-02T10:00:00",
        "texto": "relato recente",
        "results": {},
    }

    (sessions_dir / "antiga.json").write_text(
        json.dumps(sessao_antiga), encoding="utf-8"
    )
    (sessions_dir / "recente.json").write_text(
        json.dumps(sessao_recente), encoding="utf-8"
    )

    resultado = load_sessions()
    assert len(resultado) == 2
    assert resultado[0]["timestamp"] == "2024-01-02T10:00:00", (
        "Sessão mais recente deve aparecer primeiro"
    )


def test_load_sessions_vazio_quando_pasta_vazia(sessions_dir: Path) -> None:
    """load_sessions deve retornar lista vazia quando a pasta não tem JSONs."""
    sessions_dir.mkdir(parents=True)

    assert load_sessions() == []


def test_clear_sessions_remove_e_retorna_count(
    sessions_dir: Path, sample_triage_result: TriageResult
) -> None:
    """clear_sessions deve remover todos os JSONs e retornar a contagem correta."""
    # Salva 3 sessões
    for _ in range(3):
        save_session({"hibrido": sample_triage_result}, "Texto de teste")

    assert len(list(sessions_dir.glob("*.json"))) == 3

    count = clear_sessions()
    assert count == 3, "Deve retornar 3 arquivos removidos"
    assert load_sessions() == [], "Nenhuma sessão deve restar após clear"


def test_json_salvo_e_deserializavel_com_campos_esperados(
    sessions_dir: Path, sample_triage_result: TriageResult
) -> None:
    """O arquivo JSON salvo deve conter as chaves esperadas e urgência como str."""
    caminho = save_session({"hibrido": sample_triage_result}, "Vibração na bomba")

    with open(caminho, encoding="utf-8") as fh:
        dados = json.load(fh)

    assert "timestamp" in dados, "Chave 'timestamp' deve estar presente"
    assert "texto" in dados, "Chave 'texto' deve estar presente"
    assert "results" in dados, "Chave 'results' deve estar presente"
    # urgência deve estar serializada como string (mode='json' do Pydantic)
    assert isinstance(dados["results"]["hibrido"]["urgencia"], str), (
        "urgencia deve ser string no JSON serializado"
    )


def test_load_sessions_ignora_arquivos_nao_json(sessions_dir: Path) -> None:
    """load_sessions deve ignorar arquivos sem extensão .json na pasta."""
    sessions_dir.mkdir(parents=True)

    # Arquivo que não deve ser carregado
    (sessions_dir / "ignore.txt").write_text("não é json", encoding="utf-8")

    # Um arquivo JSON válido
    sessao_valida = {
        "timestamp": "2024-06-01T08:00:00",
        "texto": "relato válido",
        "results": {},
    }
    (sessions_dir / "valido.json").write_text(
        json.dumps(sessao_valida), encoding="utf-8"
    )

    resultado = load_sessions()
    assert len(resultado) == 1, "Apenas o arquivo JSON válido deve ser carregado"


def test_multiplas_sessoes_salvas_sao_todas_carregadas(
    sessions_dir: Path, sample_triage_result: TriageResult
) -> None:
    """Três sessões salvas sequencialmente devem ser todas retornadas por load_sessions."""
    for i in range(3):
        save_session({"hibrido": sample_triage_result}, f"Relato {i + 1}")

    resultado = load_sessions()
    assert len(resultado) == 3, "Todas as 3 sessões devem ser carregadas"
