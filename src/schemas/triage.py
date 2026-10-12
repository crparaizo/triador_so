"""
Schemas Pydantic v2 para o resultado de triagem de ordens de serviço industriais.

Define os enums de urgência, prioridade, categoria de falha e abordagem, além
do modelo TriageResult com validação cruzada de campos.

AVISO: Protótipo acadêmico. Toda saída deve ser revisada por especialistas antes
de qualquer uso operacional.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UrgencyLevel(str, Enum):
    """Nível de urgência para atendimento da ordem de serviço."""

    IMEDIATA = "IMEDIATA"
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"
    DESCONHECIDA = "DESCONHECIDA"


class PriorityLevel(str, Enum):
    """Nível de prioridade de execução da ordem de serviço."""

    P1 = "P1"  # Crítico
    P2 = "P2"  # Alto
    P3 = "P3"  # Médio
    P4 = "P4"  # Baixo
    DESCONHECIDA = "DESCONHECIDA"


class ApproachType(str, Enum):
    """Abordagem de triagem utilizada."""

    REGRAS = "REGRAS"
    LLM = "LLM"
    HIBRIDO = "HIBRIDO"


class FailureCategory(str, Enum):
    """Categoria da falha identificada no relato."""

    MECANICA = "MECANICA"
    ELETRICA = "ELETRICA"
    INSTRUMENTACAO = "INSTRUMENTACAO"
    UTILIDADES = "UTILIDADES"
    SEGURANCA = "SEGURANCA"
    QUALIDADE = "QUALIDADE"
    PROCESSO = "PROCESSO"
    INFRAESTRUTURA = "INFRAESTRUTURA"
    TI_AUTOMACAO = "TI_AUTOMACAO"
    OUTROS = "OUTROS"
    FORA_DO_ESCOPO = "FORA_DO_ESCOPO"
    DESCONHECIDA = "DESCONHECIDA"


class TriageResult(BaseModel):
    """
    Resultado completo de uma triagem de ordem de serviço.

    Agrupa todos os campos produzidos pelas três abordagens (regras, LLM,
    híbrido) em um formato único e validado. O campo 'requer_revisao_humana'
    exige 'motivo_revisao' preenchido quando True.
    """

    model_config = ConfigDict(use_enum_values=False)

    # Metadados do resultado
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="UUID único do resultado",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Momento da triagem",
    )
    abordagem: ApproachType = Field(..., description="Abordagem usada na triagem")
    texto_entrada: str = Field(
        ..., min_length=1, description="Relato original da ocorrência"
    )

    # Classificação
    urgencia: UrgencyLevel = Field(..., description="Nível de urgência determinado")
    prioridade: PriorityLevel = Field(..., description="Nível de prioridade determinado")
    categoria: FailureCategory = Field(..., description="Categoria da falha identificada")
    equipe_sugerida: str = Field(
        ..., min_length=1, description="Equipe recomendada para atendimento"
    )

    # Rastreabilidade
    regras_acionadas: list[str] = Field(
        default_factory=list,
        description="Regras de produção disparadas (vazio para abordagem LLM puro)",
    )
    evidencias: dict[str, str] = Field(
        default_factory=dict,
        description="Evidências textuais por campo classificado",
    )

    # Controle de qualidade
    requer_revisao_humana: bool = Field(
        ..., description="Sinaliza necessidade de revisão humana obrigatória"
    )
    motivo_revisao: Optional[str] = Field(
        None,
        description="Justificativa para revisão humana (obrigatório quando requer_revisao_humana=True)",
    )
    confianca: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confiança da classificação — valor entre 0 (nenhuma) e 1 (total)",
    )
    latencia_ms: float = Field(
        ..., ge=0.0, description="Latência de processamento em milissegundos"
    )
    campos_sem_suporte: list[str] = Field(
        default_factory=list,
        description="Campos inferidos sem evidência direta no texto (indicador de possível alucinação)",
    )

    @model_validator(mode="after")
    def validar_motivo_revisao(self) -> "TriageResult":
        """Exige motivo_revisao preenchido quando requer_revisao_humana for True."""
        if self.requer_revisao_humana and not self.motivo_revisao:
            raise ValueError(
                "motivo_revisao é obrigatório quando requer_revisao_humana=True"
            )
        return self
