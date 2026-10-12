"""
Testes de integração leve para src/extraction/keyword_extractor.py.

Usa dados reais dos YAMLs (sem Ollama). Verifica extração de tag de ativo,
sintomas, localização, impacto na produção, risco de segurança, urgência
mencionada, evidências, campos_sem_suporte e detect_category().

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import pytest

from src.data.loader import load_categories, load_knowledge_base
from src.extraction.keyword_extractor import KeywordExtractor
from src.schemas.triage import FailureCategory


# ---------------------------------------------------------------------------
# Fixture autouse: limpar cache antes e depois de cada teste
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def limpar_caches():
    """Garante isolamento dos testes limpando o cache dos loaders."""
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    yield
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()


# ---------------------------------------------------------------------------
# Fixture de conveniência: extrator com dados reais
# ---------------------------------------------------------------------------


@pytest.fixture
def extractor() -> KeywordExtractor:
    """Instância de KeywordExtractor com dados reais dos YAMLs."""
    kb = load_knowledge_base()
    cats = load_categories()
    return KeywordExtractor(kb, cats)


# ---------------------------------------------------------------------------
# Testes de extração de ativo
# ---------------------------------------------------------------------------


def test_extrai_tag_ativo_explicito(extractor):
    """Tag explícito no texto deve ser extraído como ativo_mencionado."""
    result = extractor.extract("bomba BOMB-001 com vazamento de óleo")

    assert result.ativo_mencionado == "BOMB-001", (
        f"Esperado 'BOMB-001', obtido: {result.ativo_mencionado}"
    )


def test_extrai_tag_ativo_case_insensitive(extractor):
    """Tag em minúsculas deve ser normalizado para maiúsculas."""
    result = extractor.extract("bomb-001 apresenta falha")

    assert result.ativo_mencionado == "BOMB-001", (
        f"Esperado 'BOMB-001', obtido: {result.ativo_mencionado}"
    )


def test_extrai_ativo_por_nome(extractor):
    """Quando não há tag, o ativo deve ser identificado pelo nome na base."""
    result = extractor.extract("bomba centrífuga de resfriamento parou de funcionar")

    assert result.ativo_mencionado is not None, (
        "Ativo deve ser identificado pelo nome 'Bomba Centrífuga de Resfriamento'"
    )
    assert result.ativo_mencionado == "BOMB-001"


# ---------------------------------------------------------------------------
# Testes de sintomas
# ---------------------------------------------------------------------------


def test_extrai_sintomas_mecanicos(extractor):
    """Palavras-chave de falha mecânica devem aparecer nos sintomas."""
    result = extractor.extract("vibração excessiva no rolamento")

    assert len(result.sintomas) > 0, "Deve detectar ao menos um sintoma mecânico"
    sintomas_norm = [s.lower() for s in result.sintomas]
    assert any("vibra" in s for s in sintomas_norm), (
        f"Esperado sintoma com 'vibra', sintomas: {result.sintomas}"
    )


def test_extrai_sintomas_eletricos(extractor):
    """Palavras-chave de falha elétrica devem aparecer nos sintomas."""
    result = extractor.extract("curto no quadro elétrico com cheiro de queimado")

    assert len(result.sintomas) > 0, "Deve detectar sintomas elétricos"
    sintomas_lower = [s.lower() for s in result.sintomas]
    assert any("curto" in s or "queimado" in s for s in sintomas_lower), (
        f"Esperado 'curto' ou 'queimado' nos sintomas, obtido: {result.sintomas}"
    )


# ---------------------------------------------------------------------------
# Testes de localização
# ---------------------------------------------------------------------------


def test_extrai_localizacao_do_ativo(extractor):
    """Localização mencionada no texto deve ser identificada via ativos cadastrados."""
    result = extractor.extract("falha no equipamento do Setor A")

    assert result.localizacao is not None, (
        "Localização 'Setor A' deve ser detectada via ativos do Setor A"
    )


# ---------------------------------------------------------------------------
# Testes de impacto na produção
# ---------------------------------------------------------------------------


def test_detecta_impacto_producao_true(extractor):
    """Texto com linha de produção parada deve setar impacto_producao=True."""
    result = extractor.extract(
        "linha de produção parada por falha no equipamento"
    )

    assert result.impacto_producao is True, (
        "Esperado impacto_producao=True para 'linha de produção parada'"
    )


# ---------------------------------------------------------------------------
# Testes de risco de segurança
# ---------------------------------------------------------------------------


def test_detecta_risco_seguranca_true(extractor):
    """Texto com risco de explosão deve setar risco_seguranca=True."""
    result = extractor.extract("risco de explosão detectado na área")

    assert result.risco_seguranca is True, (
        "Esperado risco_seguranca=True para 'risco de explosão'"
    )


# ---------------------------------------------------------------------------
# Testes de urgência mencionada
# ---------------------------------------------------------------------------


def test_detecta_urgencia_mencionada(extractor):
    """Texto com 'urgente' deve preencher urgencia_mencionada."""
    result = extractor.extract("urgente: bomba parou completamente")

    assert result.urgencia_mencionada is not None, (
        "urgencia_mencionada deve ser preenchida quando 'urgente' aparece no texto"
    )


# ---------------------------------------------------------------------------
# Testes de evidências
# ---------------------------------------------------------------------------


def test_evidencias_mapeadas_para_texto_original(extractor):
    """Texto com múltiplos campos detectáveis deve gerar evidencias não vazia."""
    result = extractor.extract(
        "BOMB-001 com vibração excessiva no Setor A — linha de produção parada"
    )

    assert len(result.evidencias) > 0, (
        "Evidências devem ser preenchidas quando campos são detectados"
    )
    # Pelo menos ativo e sintomas devem ter evidência
    assert "ativo" in result.evidencias or "sintomas" in result.evidencias


# ---------------------------------------------------------------------------
# Testes de texto vago
# ---------------------------------------------------------------------------


def test_texto_vago_retorna_campos_vazios(extractor):
    """Texto genérico sem palavras-chave específicas deve ter poucos campos preenchidos."""
    result = extractor.extract("problema geral")

    # Confiança baixa — poucos campos com suporte
    assert result.confianca_extracao < 0.5, (
        f"Esperado confiança < 0.5 para texto vago, obtido: {result.confianca_extracao}"
    )


# ---------------------------------------------------------------------------
# Testes de normalização
# ---------------------------------------------------------------------------


def test_normalizacao_sem_acentos(extractor):
    """Palavras com acento no texto devem ser detectadas via normalização."""
    result = extractor.extract("vibração excessiva no equipamento")

    assert len(result.sintomas) > 0, (
        "Sintoma 'vibração' (com acento) deve ser detectado após normalização"
    )


# ---------------------------------------------------------------------------
# Testes de campos_sem_suporte
# ---------------------------------------------------------------------------


def test_campos_sem_suporte_populados(extractor):
    """Campos não detectados no texto devem aparecer em campos_sem_suporte."""
    result = extractor.extract("problema na máquina sem identificação do equipamento")

    assert "ativo_mencionado" in result.campos_sem_suporte, (
        "ativo_mencionado deve estar em campos_sem_suporte quando não detectado"
    )


# ---------------------------------------------------------------------------
# Testes de detect_category
# ---------------------------------------------------------------------------


def test_detect_category_mecanica(extractor):
    """Texto com múltiplas palavras mecânicas deve retornar FailureCategory.MECANICA."""
    categoria = extractor.detect_category(
        "bomba com vazamento de óleo e vibração excessiva"
    )

    assert categoria == FailureCategory.MECANICA, (
        f"Esperado FailureCategory.MECANICA, obtido: {categoria}"
    )


def test_detect_category_desconhecida(extractor):
    """Texto sem palavras-chave de categoria deve retornar FailureCategory.DESCONHECIDA."""
    categoria = extractor.detect_category("algo aconteceu na fábrica")

    assert categoria == FailureCategory.DESCONHECIDA, (
        f"Esperado FailureCategory.DESCONHECIDA, obtido: {categoria}"
    )
