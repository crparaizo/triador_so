"""
Schemas Pydantic v2 para ativos industriais, equipes de manutenção e base de conhecimento.

Define Asset (ativo industrial), Team (equipe de manutenção) e KnowledgeBase
(repositório local com métodos de busca). Usado por todas as abordagens de
triagem para enriquecer o contexto com dados locais.

AVISO: Protótipo acadêmico com dados sintéticos. Não reflete instalação industrial real.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Asset(BaseModel):
    """Representa um ativo industrial cadastrado na base local."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(..., description="Identificador único do ativo")
    nome: str = Field(..., description="Nome descritivo do ativo")
    tag: str = Field(..., description="Tag de identificação do ativo (ex: BOMB-001)")
    tipo: str = Field(..., description="Tipo do ativo (ex: Mecânico, Elétrico)")
    localizacao: str = Field(..., description="Localização física do ativo na planta")
    equipe_responsavel: str = Field(
        ..., description="Equipe responsável pela manutenção do ativo"
    )
    criticidade: Literal["ALTA", "MEDIA", "BAIXA"] = Field(
        ..., description="Criticidade do ativo para a produção"
    )
    observacoes: str = Field(
        default="", description="Observações adicionais sobre o ativo"
    )


class Team(BaseModel):
    """Representa uma equipe de manutenção disponível na planta."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(..., description="Identificador único da equipe")
    nome: str = Field(..., description="Nome da equipe de manutenção")
    especialidades: list[str] = Field(
        ..., description="Lista de especialidades técnicas da equipe"
    )
    contato: str = Field(..., description="Contato da equipe (e-mail ou ramal)")
    disponivel: bool = Field(
        default=True, description="Indica se a equipe está disponível para atendimento"
    )


class KnowledgeBase(BaseModel):
    """
    Base de conhecimento local com ativos e equipes da planta industrial.

    Oferece métodos de busca utilizados pelas abordagens de triagem para
    enriquecer o contexto extraído do relato com dados reais da instalação.
    """

    assets: list[Asset] = Field(
        default_factory=list, description="Lista de ativos industriais cadastrados"
    )
    teams: list[Team] = Field(
        default_factory=list, description="Lista de equipes de manutenção cadastradas"
    )

    def get_asset_by_tag(self, tag: str) -> Optional[Asset]:
        """
        Retorna ativo pelo tag (busca exata, case-insensitive).

        Retorna None se nenhum ativo for encontrado com o tag informado.
        """
        tag_upper = tag.upper()
        return next((a for a in self.assets if a.tag.upper() == tag_upper), None)

    def get_team_by_name(self, name: str) -> Optional[Team]:
        """
        Retorna equipe pelo nome (busca parcial, case-insensitive).

        Retorna None se nenhuma equipe contiver o nome informado.
        """
        name_lower = name.lower()
        return next(
            (t for t in self.teams if name_lower in t.nome.lower()), None
        )

    def find_assets_by_location(self, location: str) -> list[Asset]:
        """
        Retorna lista de ativos que contêm a localização informada (busca parcial, case-insensitive).

        Retorna lista vazia se nenhum ativo corresponder.
        """
        location_lower = location.lower()
        return [a for a in self.assets if location_lower in a.localizacao.lower()]
