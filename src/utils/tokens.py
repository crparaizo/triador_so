"""
Leitura defensiva da contagem de tokens de uma resposta de LLM (ChatOllama).

O objeto AIMessage devolvido pelo ChatOllama expõe o uso de tokens em dois
lugares possíveis, conforme a versão do LangChain:
  1. usage_metadata (padrão LangChain): {'input_tokens', 'output_tokens', ...}
  2. response_metadata (nativo do Ollama): {'prompt_eval_count', 'eval_count'}

A função tenta o formato padrão primeiro e, se ausente, recorre ao nativo.
Qualquer objeto sem esses metadados (string, mock de teste) resulta em (0, 0, 0),
sem lançar exceção — a ausência de contagem nunca interrompe a triagem.
"""

from __future__ import annotations

from typing import Any


def extrair_uso_tokens(resposta: Any) -> tuple[int, int, int]:
    """
    Extrai (tokens_entrada, tokens_saida, tokens_total) de uma resposta de LLM.

    Args:
        resposta: objeto retornado por ChatOllama.invoke (AIMessage) ou similar.

    Returns:
        Tupla (entrada, saida, total) em inteiros. (0, 0, 0) quando a contagem
        não está disponível no objeto.
    """
    # Formato padrão do LangChain: usage_metadata
    usage = getattr(resposta, "usage_metadata", None)
    if isinstance(usage, dict):
        entrada = usage.get("input_tokens")
        saida = usage.get("output_tokens")
        if isinstance(entrada, int) and isinstance(saida, int):
            return entrada, saida, entrada + saida

    # Formato nativo do Ollama: response_metadata
    meta = getattr(resposta, "response_metadata", None)
    if isinstance(meta, dict):
        entrada = meta.get("prompt_eval_count", 0) or 0
        saida = meta.get("eval_count", 0) or 0
        if isinstance(entrada, int) and isinstance(saida, int):
            return entrada, saida, entrada + saida

    # Sem metadados de uso — resposta de tipo inesperado ou mock de teste
    return 0, 0, 0
