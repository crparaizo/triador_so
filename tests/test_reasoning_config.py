"""
Testes da opção OLLAMA_REASONING (variante sem o modo de raciocínio do qwen3).

O padrão (None) mantém a configuração da execução de referência; False desativa
o raciocínio no LLM puro e na extração da híbrida. Nenhum teste requer Ollama.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import pytest

from src.config.loader import Settings, get_settings
from src.evaluation.runner import _config_llm
from src.extraction.llm_extractor import LLMExtractor


@pytest.fixture(autouse=True)
def limpar_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_padrao_mantem_a_configuracao_de_referencia(monkeypatch):
    """Sem a variável de ambiente, o raciocínio fica no padrão do modelo (None)."""
    monkeypatch.delenv("OLLAMA_REASONING", raising=False)
    assert Settings(_env_file=None).ollama_reasoning is None


def test_variavel_de_ambiente_desativa_o_raciocinio(monkeypatch):
    """OLLAMA_REASONING=false chega ao extrator da híbrida e ao registro da execução."""
    monkeypatch.setenv("OLLAMA_REASONING", "false")
    assert get_settings().ollama_reasoning is False
    assert LLMExtractor()._criar_llm().reasoning is False
    assert _config_llm()["raciocinio"] is False


def test_variavel_vazia_equivale_ao_padrao(monkeypatch):
    """OLLAMA_REASONING vazio não quebra a configuração e mantém o padrão do modelo."""
    monkeypatch.setenv("OLLAMA_REASONING", "")
    assert get_settings().ollama_reasoning is None
