"""
Adaptador de alarmes de um supervisório (SCADA) simulado para ordens de serviço.

Um evento de alarme estruturado (tag, variável, valor, limite) é convertido no
texto de uma OS, que segue sem alteração para as três abordagens de triagem.
O valor medido fica escrito no texto, de onde o motor de regras o lê de forma
determinística (src/extraction/medicoes.py) para comparar com a PMTA cadastrada.

AVISO: Os eventos são sintéticos e o supervisório é simulado. Não há conexão
com equipamentos ou sistemas reais.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.schemas.assets import KnowledgeBase

# Nome da variável no texto da OS e concordância do adjetivo do alarme
_VARIAVEIS = {
    "pressao": ("pressão", "a"),
    "temperatura": ("temperatura", "a"),
    "vibracao": ("vibração", "a"),
    "corrente": ("corrente", "a"),
    "nivel": ("nível", "o"),
}


class AlarmEvent(BaseModel):
    """Evento de alarme do supervisório simulado."""

    id: str = Field(..., description="Identificador do evento (ex: ALM-001)")
    tag: Optional[str] = Field(None, description="Tag do ativo cadastrado, quando houver")
    local: Optional[str] = Field(None, description="Local do alarme quando não há ativo cadastrado")
    variavel: Optional[str] = Field(None, description="Chave de _VARIAVEIS para alarmes analógicos")
    sentido: Optional[Literal["alto", "baixo"]] = None
    valor: Optional[float] = None
    limite: Optional[float] = None
    unidade: Optional[str] = None
    descricao: Optional[str] = Field(None, description="Texto do alarme discreto (ex: falha de comunicação)")


def _numero(v: float) -> str:
    """Formata no padrão brasileiro: 1080 → '1.080'; 1.04 → '1,04'; 11.2 → '11,2'."""
    if float(v).is_integer():
        return f"{int(v):,}".replace(",", ".")
    inteiro, decimal = f"{v:.3f}".rstrip("0").split(".")
    return f"{int(inteiro):,}".replace(",", ".") + "," + decimal


def alarme_para_relato(evento: AlarmEvent, kb: KnowledgeBase) -> str:
    """Texto da OS correspondente ao evento de alarme."""
    ativo = kb.get_asset_by_tag(evento.tag) if evento.tag else None
    onde = f"{ativo.nome} ({ativo.tag})" if ativo else (evento.local or evento.tag or "local não informado")

    if evento.variavel is None:
        return f"Alarme de {evento.descricao} gerado pelo supervisório, local: {onde}."

    nome, genero = _VARIAVEIS[evento.variavel]
    adjetivo = ("alt" if evento.sentido == "alto" else "baix") + genero
    relacao = "acima" if evento.sentido == "alto" else "abaixo"
    return (
        f"Alarme de {nome} {adjetivo} em {onde}, gerado pelo supervisório: "
        f"{_numero(evento.valor)} {evento.unidade}, {relacao} do limite de alarme de "
        f"{_numero(evento.limite)} {evento.unidade}."
    )
