"""
Testes unitários para src/data/context_enricher.py.

Verifica a função enrich_context em cenários de busca por tag, nome substring
e localização, além da montagem de equipes candidatas. Nenhum teste depende
de Ollama nem de arquivos YAML — a KnowledgeBase é injetada diretamente.

Dataset sintético criado para fins acadêmicos.
"""

import pytest

from src.config.loader import get_settings
from src.data.context_enricher import enrich_context
from src.data.loader import load_categories, load_knowledge_base
from src.rules.definitions import load_rules
from src.schemas.assets import Asset, KnowledgeBase, Team
from src.schemas.extraction import ExtractedInfo


@pytest.fixture(autouse=True)
def limpar_caches():
    """Limpa caches lru_cache antes de cada teste para evitar estado compartilhado."""
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    load_rules.cache_clear()
    get_settings.cache_clear()
    yield


# ---------------------------------------------------------------------------
# Testes de busca de ativo
# ---------------------------------------------------------------------------


def test_busca_por_tag_exata_encontra_ativo(sample_knowledge_base):
    """Ativo encontrado pela tag exata → ativo_encontrado.tag correto e fonte 'assets.yaml'."""
    extracted = ExtractedInfo(ativo_mencionado="BOMB-TEST")
    context = enrich_context(extracted, sample_knowledge_base)

    assert context.ativo_encontrado is not None
    assert context.ativo_encontrado.tag == "BOMB-TEST"
    assert context.fonte_enriquecimento == "assets.yaml"


def test_busca_por_tag_case_insensitive(sample_knowledge_base):
    """Tag em minúsculas deve encontrar o ativo (busca case-insensitive)."""
    extracted = ExtractedInfo(ativo_mencionado="bomb-test")
    context = enrich_context(extracted, sample_knowledge_base)

    assert context.ativo_encontrado is not None
    assert context.ativo_encontrado.tag == "BOMB-TEST"


def test_busca_por_nome_substring_case_insensitive(sample_knowledge_base):
    """Substring do nome encontra o ativo quando a busca por tag falha.

    BOMB-TEST tem nome 'Bomba Centrífuga Teste'; 'Bomba Centrífuga' é substring.
    """
    extracted = ExtractedInfo(ativo_mencionado="Bomba Centrífuga")
    context = enrich_context(extracted, sample_knowledge_base)

    assert context.ativo_encontrado is not None
    assert context.ativo_encontrado.tag == "BOMB-TEST"


def test_ativo_nao_encontrado_retorna_none(sample_knowledge_base):
    """Tag inexistente → ativo_encontrado None e fonte 'não encontrado'."""
    extracted = ExtractedInfo(ativo_mencionado="INEXISTENTE-999")
    context = enrich_context(extracted, sample_knowledge_base)

    assert context.ativo_encontrado is None
    assert context.fonte_enriquecimento == "não encontrado"


def test_fallback_por_localizacao_quando_ativo_mencionado_none(sample_knowledge_base):
    """Sem ativo_mencionado, busca por localização encontra BOMB-TEST no Setor A."""
    # BOMB-TEST está em "Setor A - Linha 1" que contém a substring "Setor A"
    extracted = ExtractedInfo(ativo_mencionado=None, localizacao="Setor A")
    context = enrich_context(extracted, sample_knowledge_base)

    assert context.ativo_encontrado is not None
    assert context.ativo_encontrado.tag == "BOMB-TEST"


# ---------------------------------------------------------------------------
# Testes de equipes candidatas
# ---------------------------------------------------------------------------


def test_equipe_candidata_adicionada_quando_ativo_encontrado(sample_knowledge_base):
    """Ativo BOMB-TEST encontrado → equipe 'Manutenção Mecânica' está em equipes_candidatas."""
    extracted = ExtractedInfo(ativo_mencionado="BOMB-TEST")
    context = enrich_context(extracted, sample_knowledge_base)

    nomes = [e.nome for e in context.equipes_candidatas]
    assert "Manutenção Mecânica" in nomes


def test_equipes_candidatas_vazia_sem_ativo(sample_knowledge_base):
    """Quando nenhum ativo é encontrado, equipes_candidatas deve ser lista vazia."""
    extracted = ExtractedInfo(ativo_mencionado="INEXISTENTE-999")
    context = enrich_context(extracted, sample_knowledge_base)

    assert context.equipes_candidatas == []


def test_categoria_padrao_adicionada_quando_categorias_fornecido(sample_knowledge_base):
    """equipe_padrao da categoria detectada é incluída em equipes_candidatas."""
    # Ativo inexistente para garantir que a equipe vem apenas da categoria
    extracted = ExtractedInfo(ativo_mencionado="INEXISTENTE-999")
    categorias = {"MECANICA": {"equipe_padrao": "Manutenção Mecânica"}}

    context = enrich_context(
        extracted,
        sample_knowledge_base,
        categorias=categorias,
        categoria_detectada="MECANICA",
    )

    nomes = [e.nome for e in context.equipes_candidatas]
    assert "Manutenção Mecânica" in nomes


def test_equipe_responsavel_nao_existe_no_kb_candidatas_vazia():
    """Ativo encontrado mas equipe_responsavel não existe na KB → equipes_candidatas vazia."""
    ativo_sem_equipe = Asset(
        id="test-999",
        nome="Ativo Sem Equipe",
        tag="SEM-EQUIPE",
        tipo="Mecânico",
        localizacao="Setor X",
        equipe_responsavel="Equipe Inexistente",
        criticidade="BAIXA",
    )
    kb = KnowledgeBase(assets=[ativo_sem_equipe], teams=[])

    extracted = ExtractedInfo(ativo_mencionado="SEM-EQUIPE")
    context = enrich_context(extracted, kb)

    # Ativo é encontrado, mas a equipe não existe na KB
    assert context.ativo_encontrado is not None
    assert context.equipes_candidatas == []
