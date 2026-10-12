"""
Extrator de informações por palavras-chave para triagem de ordens de serviço.

Implementa a abordagem determinística de extração: varredura de texto livre
por padrões de tag de ativo, palavras-chave de categoria, localização e
indicadores de urgência/impacto/risco.

Não usa LLM — toda extração é feita por correspondência de substrings
normalizadas (sem acentos, minúsculas).

AVISO: Protótipo acadêmico. A extração por palavras-chave tem limitações — não
captura expressões idiomáticas, erros de grafia graves ou contextos implícitos.
Revisar resultados antes de uso operacional.
"""

import re
import unicodedata
from typing import Optional

from src.schemas.assets import KnowledgeBase
from src.schemas.extraction import ExtractedInfo
from src.schemas.triage import FailureCategory


def _normalize(texto: str) -> str:
    """
    Normaliza texto para matching insensível a acentos e maiúsculas.

    Remove acentos via decomposição NFD e converte para minúsculas.
    """
    nfd = unicodedata.normalize("NFD", texto.lower())
    return nfd.encode("ascii", "ignore").decode()


class KeywordExtractor:
    """
    Extrator de informações por palavras-chave a partir de texto livre.

    Usa correspondência de substrings normalizadas para detectar: tag de ativo,
    localização, sintomas, impacto na produção, risco de segurança e urgência.
    Não inventa valores — campos sem evidência ficam como None.
    """

    # Palavras-chave normalizadas para detecção de impacto na produção
    _IMPACTO_KEYWORDS = [
        "producao parada",
        "linha parada",
        "impacto na producao",
        "parada de producao",
        "linha de producao parada",
        "parou a producao",
        "producao parou",
    ]

    # Palavras-chave normalizadas para detecção de risco de segurança
    _RISCO_KEYWORDS = [
        "risco",
        "perigo",
        "incendio",
        "explosao",
        "fogo",
        "acidente",
        "emergencia",
        "evacuacao",
        "choque eletrico",
        "vazamento de gas",
        "gas",
        "parada de emergencia",
    ]

    # Palavras-chave normalizadas para detecção de urgência explícita
    _URGENCIA_KEYWORDS = [
        "urgente",
        "imediato",
        "emergencia",
        "critico",
        "agora",
        "rapidamente",
    ]

    def __init__(self, knowledge_base: KnowledgeBase, categories: dict) -> None:
        """
        Inicializa o extrator com base de conhecimento e mapa de categorias.

        Args:
            knowledge_base: instância de KnowledgeBase com ativos e equipes.
            categories: dict retornado por load_categories() — chaves são nomes
                de categoria (ex: 'MECANICA'), valores contêm 'palavras_chave'.
        """
        self.knowledge_base = knowledge_base
        self.categories = categories

    def extract(self, texto: str) -> ExtractedInfo:
        """
        Extrai informações estruturadas do texto livre por palavras-chave.

        Passos em ordem:
        1. Normalizar texto.
        2. Detectar tag de ativo por regex.
        3. Detectar ativo por nome se tag não encontrado.
        4. Coletar sintomas das palavras-chave de categorias.
        5. Detectar localização pelos ativos cadastrados.
        6. Detectar impacto na produção.
        7. Detectar risco de segurança.
        8. Detectar urgência mencionada explicitamente.
        9. Calcular campos_sem_suporte e confianca_extracao.

        Args:
            texto: relato livre da ocorrência.

        Returns:
            ExtractedInfo com campos preenchidos apenas quando há evidência no texto.
        """
        texto_norm = _normalize(texto)
        evidencias: dict[str, str] = {}

        # --- Passo 2: detectar tag de ativo (padrão LETRAS-dígitos, ex: BOMB-001) ---
        ativo_mencionado: Optional[str] = None
        match_tag = re.search(r"[A-Za-z]+-\d+", texto)
        if match_tag:
            ativo_mencionado = match_tag.group().upper()
            evidencias["ativo"] = match_tag.group()  # preservar caixa original

        # --- Passo 3: detectar ativo por nome (apenas se tag não encontrado) ---
        if ativo_mencionado is None:
            for asset in self.knowledge_base.assets:
                nome_norm = _normalize(asset.nome)
                if nome_norm in texto_norm:
                    ativo_mencionado = asset.tag
                    evidencias["ativo"] = asset.nome
                    break

        # --- Passo 4: coletar sintomas por palavras-chave de categorias ---
        sintomas_vistos: set[str] = set()
        sintomas: list[str] = []
        for _cat_nome, cat_data in self.categories.items():
            palavras = cat_data.get("palavras_chave", [])
            for palavra in palavras:
                palavra_norm = _normalize(palavra)
                if palavra_norm in texto_norm and palavra not in sintomas_vistos:
                    sintomas_vistos.add(palavra)
                    sintomas.append(palavra)

        if sintomas:
            evidencias["sintomas"] = ", ".join(sintomas[:3])

        # --- Passo 5: detectar localização pelos ativos cadastrados ---
        localizacao: Optional[str] = None
        for asset in self.knowledge_base.assets:
            loc_norm = _normalize(asset.localizacao)
            # Verificação direta ou por partes separadas por " - "
            partes = [p.strip() for p in loc_norm.split(" - ") if len(p.strip()) > 2]
            if loc_norm in texto_norm or any(parte in texto_norm for parte in partes):
                localizacao = asset.localizacao
                evidencias["localizacao"] = asset.localizacao
                break

        # --- Passo 6: detectar impacto na produção ---
        impacto_producao: Optional[bool] = None
        for kw in self._IMPACTO_KEYWORDS:
            if kw in texto_norm:
                impacto_producao = True
                # Buscar trecho correspondente no texto original (sem acento)
                evidencias["impacto_producao"] = kw
                break

        # --- Passo 7: detectar risco de segurança ---
        risco_seguranca: Optional[bool] = None
        for kw in self._RISCO_KEYWORDS:
            if kw in texto_norm:
                risco_seguranca = True
                evidencias["risco_seguranca"] = kw
                break

        # --- Passo 8: detectar urgência mencionada ---
        urgencia_mencionada: Optional[str] = None
        for kw in self._URGENCIA_KEYWORDS:
            if kw in texto_norm:
                # Recuperar forma original do texto (preservar acentuação e caixa)
                m = re.search(re.escape(kw), texto, re.IGNORECASE)
                urgencia_mencionada = m.group() if m else kw
                evidencias["urgencia_mencionada"] = urgencia_mencionada
                break

        # --- Passo 9: campos sem suporte e confiança ---
        campos_sem_suporte: list[str] = []
        if ativo_mencionado is None:
            campos_sem_suporte.append("ativo_mencionado")
        if localizacao is None:
            campos_sem_suporte.append("localizacao")
        if impacto_producao is None:
            campos_sem_suporte.append("impacto_producao")
        if risco_seguranca is None:
            campos_sem_suporte.append("risco_seguranca")
        if urgencia_mencionada is None:
            campos_sem_suporte.append("urgencia_mencionada")

        confianca_extracao = (5 - len(campos_sem_suporte)) / 5.0

        return ExtractedInfo(
            ativo_mencionado=ativo_mencionado,
            sintomas=sintomas,
            localizacao=localizacao,
            impacto_producao=impacto_producao,
            risco_seguranca=risco_seguranca,
            urgencia_mencionada=urgencia_mencionada,
            evidencias=evidencias,
            confianca_extracao=confianca_extracao,
            campos_sem_suporte=campos_sem_suporte,
            erro_parse=None,
        )

    def detect_category(self, texto: str) -> FailureCategory:
        """
        Detecta a categoria de falha com maior correspondência de palavras-chave.

        Conta quantas palavras-chave (normalizadas) de cada categoria aparecem
        no texto normalizado. Retorna a categoria com maior contagem, ou
        FailureCategory.DESCONHECIDA se nenhuma palavra-chave corresponder.

        Args:
            texto: relato livre da ocorrência.

        Returns:
            FailureCategory enum — nunca retorna string.
        """
        texto_norm = _normalize(texto)
        max_contagem = 0
        melhor_categoria: Optional[str] = None

        for categoria_nome, cat_data in self.categories.items():
            palavras = cat_data.get("palavras_chave", [])
            contagem = sum(
                1 for p in palavras if _normalize(p) in texto_norm
            )
            if contagem > max_contagem:
                max_contagem = contagem
                melhor_categoria = categoria_nome

        if max_contagem > 0 and melhor_categoria is not None:
            try:
                return FailureCategory[melhor_categoria]
            except KeyError:
                return FailureCategory.DESCONHECIDA

        return FailureCategory.DESCONHECIDA
