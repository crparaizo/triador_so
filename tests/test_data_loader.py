"""
Testes automatizados para o módulo src/data/loader.py.

Cobre: carregamento da KnowledgeBase, métodos de busca, carregamento de
categorias, tratamento de arquivos inválidos e comportamento de cache.

Nenhum teste depende de Ollama. Os testes lêem os arquivos YAML reais de
data/ para validar a integridade dos dados de domínio.
"""

import pytest

from src.data.loader import load_categories, load_knowledge_base
from src.schemas.triage import FailureCategory


# ---------------------------------------------------------------------------
# Fixture autouse — garante limpeza de cache entre todos os testes
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def limpar_caches():
    """Limpa cache das funções de loader antes e depois de cada teste."""
    from src.data import loader as _loader

    _loader.load_knowledge_base.cache_clear()
    _loader.load_categories.cache_clear()
    yield
    _loader.load_knowledge_base.cache_clear()
    _loader.load_categories.cache_clear()


# ---------------------------------------------------------------------------
# Testes de load_knowledge_base
# ---------------------------------------------------------------------------


def test_load_knowledge_base_retorna_knowledge_base():
    """load_knowledge_base deve retornar instância de KnowledgeBase."""
    from src.schemas.assets import KnowledgeBase

    kb = load_knowledge_base()
    assert kb is not None
    assert isinstance(kb, KnowledgeBase)


def test_load_knowledge_base_tem_ativos():
    """Base de conhecimento deve conter pelo menos 18 ativos cadastrados."""
    kb = load_knowledge_base()
    assert len(kb.assets) >= 18, f"Esperado 18 ativos, encontrado {len(kb.assets)}"


def test_load_knowledge_base_tem_equipes():
    """Base de conhecimento deve conter pelo menos 6 equipes cadastradas."""
    kb = load_knowledge_base()
    assert len(kb.teams) >= 6, f"Esperado 6 equipes, encontrado {len(kb.teams)}"


def test_get_asset_by_tag_bomb001():
    """get_asset_by_tag deve encontrar o ativo BOMB-001 pelo tag exato."""
    kb = load_knowledge_base()
    asset = kb.get_asset_by_tag("BOMB-001")
    assert asset is not None
    assert asset.tag == "BOMB-001"


def test_get_asset_by_tag_nao_existe():
    """get_asset_by_tag deve retornar None para tag inexistente."""
    kb = load_knowledge_base()
    result = kb.get_asset_by_tag("NAO-EXISTE-999")
    assert result is None


def test_get_asset_by_tag_case_insensitive():
    """get_asset_by_tag deve funcionar independente de maiúsculas/minúsculas."""
    kb = load_knowledge_base()
    result = kb.get_asset_by_tag("bomb-001")
    assert result is not None
    assert result.tag == "BOMB-001"


def test_find_assets_by_location_setor_a():
    """find_assets_by_location deve retornar ao menos um ativo no Setor A."""
    kb = load_knowledge_base()
    assets = kb.find_assets_by_location("Setor A")
    assert len(assets) >= 1, "Deve existir ao menos um ativo no Setor A"


def test_find_assets_by_location_inexistente():
    """find_assets_by_location deve retornar lista vazia para local inexistente."""
    kb = load_knowledge_base()
    assets = kb.find_assets_by_location("Local Que Nao Existe XYZ999")
    assert assets == []


def test_yaml_invalido_assets_levanta_erro_descritivo(tmp_path, monkeypatch):
    """load_knowledge_base com YAML inválido deve levantar erro descritivo."""
    from src.data import loader as _loader

    # Cria assets.yaml inválido — campo obrigatório 'id' ausente
    (tmp_path / "assets.yaml").write_text(
        "assets:\n  - nome: apenas nome sem id\n", encoding="utf-8"
    )
    (tmp_path / "teams.yaml").write_text("teams: []\n", encoding="utf-8")
    (tmp_path / "categories.yaml").write_text("categorias: {}\n", encoding="utf-8")

    # Configura settings mock apontando para tmp_path
    class FakeSettings:
        data_dir = str(tmp_path)
        ollama_model = "test"
        ollama_base_url = "http://localhost:11434"
        log_level = "INFO"
        sessions_dir = "sessions"
        results_dir = "results"
        max_retries_llm = 3
        llm_timeout_seconds = 60

    monkeypatch.setattr(_loader, "get_settings", lambda: FakeSettings())
    _loader.load_knowledge_base.cache_clear()

    with pytest.raises((ValueError, Exception)) as exc_info:
        _loader.load_knowledge_base()

    # Mensagem de erro deve ser descritiva (mais que apenas 'Exception')
    assert len(str(exc_info.value)) > 10


# ---------------------------------------------------------------------------
# Testes de load_categories
# ---------------------------------------------------------------------------


def test_load_categories_retorna_dict():
    """load_categories deve retornar um dict com pelo menos 9 categorias."""
    cats = load_categories()
    assert isinstance(cats, dict)
    assert len(cats) >= 9


def test_load_categories_contem_mecanica():
    """Categoria MECANICA deve estar presente no dicionário de categorias."""
    cats = load_categories()
    assert "MECANICA" in cats


def test_load_categories_contem_todas_obrigatorias():
    """Todas as 9 categorias obrigatórias devem estar presentes."""
    cats = load_categories()
    obrigatorias = [
        "MECANICA",
        "ELETRICA",
        "INSTRUMENTACAO",
        "UTILIDADES",
        "SEGURANCA",
        "QUALIDADE",
        "PROCESSO",
        "INFRAESTRUTURA",
        "TI_AUTOMACAO",
    ]
    for cat in obrigatorias:
        assert cat in cats, f"Categoria obrigatória ausente: {cat}"


def test_load_categories_tem_palavras_chave():
    """Categoria MECANICA deve ter pelo menos 20 palavras-chave."""
    cats = load_categories()
    mecanica = cats["MECANICA"]
    assert "palavras_chave" in mecanica
    assert len(mecanica["palavras_chave"]) >= 20


def test_load_categories_tem_equipe_padrao():
    """Categoria MECANICA deve ter equipe_padrao igual a 'Manutenção Mecânica'."""
    cats = load_categories()
    mecanica = cats["MECANICA"]
    assert "equipe_padrao" in mecanica
    assert mecanica["equipe_padrao"] == "Manutenção Mecânica"
