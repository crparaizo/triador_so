"""
Módulo de extração de informações do texto de relatos de ocorrência.

Expõe:
    KeywordExtractor — extração determinística por palavras-chave (sem LLM)

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from src.extraction.keyword_extractor import KeywordExtractor

__all__ = [
    "KeywordExtractor",
]
