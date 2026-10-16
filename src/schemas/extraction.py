"""
Schemas Pydantic v2 para dados extraídos do relato e dados de contexto enriquecido.

ExtractedInfo: saída da etapa de extração (LLM ou regras) sobre o texto livre.
ContextData: resultado do enriquecimento com dados locais de ativos e equipes.

Separar informação observada no relato (ExtractedInfo) de informação recuperada
dos dados locais (ContextData) é requisito explícito de rastreabilidade do sistema.

AVISO: Protótipo acadêmico. ExtractedInfo não deve inventar valores ausentes no texto.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Importação direta é segura — não há ciclo entre extraction.py e assets.py
from src.schemas.assets import Asset, Team


class ExtractedInfo(BaseModel):
    """
    Informações extraídas diretamente do texto livre do relato.

    Todos os campos opcionais refletem a ausência de informação no texto,
    não a ausência de dados na base local. O LLM não deve preencher campos
    sem evidência textual — campos sem suporte devem ser listados em
    'campos_sem_suporte'.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    ativo_mencionado: Optional[str] = Field(
        None, description="Tag ou nome do ativo explicitamente mencionado no relato"
    )
    sintomas: list[str] = Field(
        default_factory=list,
        description="Lista de sintomas identificados no texto do relato",
    )
    localizacao: Optional[str] = Field(
        None, description="Localização mencionada no relato"
    )
    impacto_producao: Optional[bool] = Field(
        None, description="Indica se o relato menciona impacto na produção"
    )
    risco_seguranca: Optional[bool] = Field(
        None, description="Indica se o relato menciona risco de segurança"
    )
    urgencia_mencionada: Optional[str] = Field(
        None,
        description="Urgência explicitamente mencionada no relato (valor bruto, não normalizado)",
    )
    evidencias: dict[str, str] = Field(
        default_factory=dict,
        description="Trechos do texto que evidenciam cada campo extraído",
    )
    confianca_extracao: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confiança geral da extração — 0 (nenhuma) a 1 (total)",
    )
    campos_sem_suporte: list[str] = Field(
        default_factory=list,
        description="Campos preenchidos sem evidência no texto original (indica possível alucinação)",
    )
    erro_parse: Optional[str] = Field(
        None,
        description="Mensagem de erro quando a extração falhou (ex: resposta malformada do LLM)",
    )
    tokens_entrada: int = Field(
        default=0,
        ge=0,
        description="Tokens de entrada da chamada LLM de extração. 0 no extrator por palavras-chave.",
    )
    tokens_saida: int = Field(
        default=0,
        ge=0,
        description="Tokens de saída da chamada LLM de extração. 0 no extrator por palavras-chave.",
    )
    tokens_total: int = Field(
        default=0,
        ge=0,
        description="Soma de tokens de entrada e saída da extração LLM. 0 no extrator por palavras-chave.",
    )


class ContextData(BaseModel):
    """
    Dados de contexto recuperados da base local para enriquecer a triagem.

    Representa o resultado do cruzamento entre as informações extraídas do
    relato (ExtractedInfo) e os dados cadastrados na KnowledgeBase. Deve
    ser mantido separado de ExtractedInfo para rastreabilidade.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ativo_encontrado: Optional[Asset] = Field(
        None,
        description="Ativo encontrado na base local ao cruzar com o relato",
    )
    equipes_candidatas: list[Team] = Field(
        default_factory=list,
        description="Equipes candidatas para atendimento conforme especialidades e ativo",
    )
    historico_notas: list[str] = Field(
        default_factory=list,
        description="Notas históricas relevantes sobre o ativo (quando disponíveis)",
    )
    fonte_enriquecimento: str = Field(
        default="",
        description="Fonte dos dados de enriquecimento (ex: 'base_local', 'sem_dados')",
    )
