"""
Testes do leitor defensivo de contagem de tokens (src.utils.tokens).

Cobrem os dois formatos de metadados do ChatOllama e o caso sem metadados.
"""

from types import SimpleNamespace

from src.utils.tokens import extrair_uso_tokens


def test_usage_metadata_padrao_langchain():
    """usage_metadata com input/output_tokens deve ser lido como (entrada, saida, total)."""
    resposta = SimpleNamespace(
        usage_metadata={"input_tokens": 120, "output_tokens": 45, "total_tokens": 165},
        response_metadata={},
    )
    assert extrair_uso_tokens(resposta) == (120, 45, 165)


def test_response_metadata_nativo_ollama():
    """Sem usage_metadata, deve recorrer a prompt_eval_count/eval_count do Ollama."""
    resposta = SimpleNamespace(
        usage_metadata=None,
        response_metadata={"prompt_eval_count": 200, "eval_count": 80},
    )
    assert extrair_uso_tokens(resposta) == (200, 80, 280)


def test_sem_metadados_retorna_zeros():
    """Objeto sem metadados de uso (ex.: mock, string) deve resultar em (0, 0, 0)."""
    assert extrair_uso_tokens("resposta em texto puro") == (0, 0, 0)
    assert extrair_uso_tokens(SimpleNamespace()) == (0, 0, 0)
