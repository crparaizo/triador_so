"""
Módulo de carregamento e validação do dataset sintético de triagem de OS.

Fornece as classes DatasetCase e ExpectedOutput (schemas Pydantic v2) e a
função load_dataset() para carregar e validar o arquivo
datasets/synthetic_cases.json.

AVISO: Os dados são completamente sintéticos, gerados para fins acadêmicos.
Não representam eventos, equipamentos ou instalações reais.
Toda saída deve ser revisada por especialistas antes de qualquer uso operacional.
"""

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from src.schemas.triage import FailureCategory, PriorityLevel, UrgencyLevel

# ---------------------------------------------------------------------------
# Tipo literal para classificação do caso de teste
# ---------------------------------------------------------------------------

CaseType = Literal[
    "CANONICO",
    "PARAFRASES",
    "ABREVIACOES",
    "ERROS_ESCRITA",
    "MULTIPLOS_SINTOMAS",
    "INCOMPLETOS",
    "CONTRADITORIOS",
    "FORA_ESCOPO",
    "ALTA_CRITICIDADE",
    "REVISAO_HUMANA",
]

# ---------------------------------------------------------------------------
# Equipes válidas do dataset
# (6 equipes oficiais + DESCONHECIDA para gabarito incerto)
# ---------------------------------------------------------------------------

VALID_DATASET_TEAMS: frozenset[str] = frozenset({
    "Manutenção Mecânica",
    "Manutenção Elétrica",
    "Instrumentação e Controle",
    "Utilidades",
    "Infraestrutura e Facilities",
    "TI e Automação",
    "DESCONHECIDA",
})


# ---------------------------------------------------------------------------
# Schemas Pydantic v2
# ---------------------------------------------------------------------------


class ExpectedOutput(BaseModel):
    """Saída esperada (gabarito) para um caso de teste do dataset sintético."""

    model_config = ConfigDict(use_enum_values=False)

    urgencia: UrgencyLevel
    prioridade: PriorityLevel
    categoria: FailureCategory
    equipe: str = Field(..., min_length=1)
    requer_revisao_humana: bool


class DatasetCase(BaseModel):
    """
    Caso de teste anotado do dataset sintético de triagem de OS.

    Cada caso tem um tipo que classifica como foi gerado (canônico, paráfrase,
    abreviação, etc.) e um dicionário 'esperado' com o gabarito de avaliação.

    AVISO: Dados completamente sintéticos para fins acadêmicos.
    Não representam eventos ou equipamentos reais.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(..., min_length=1, description="Identificador único: CASE-NNN")
    tipo: CaseType = Field(..., description="Tipo/estilo do caso de teste")
    texto: str = Field(..., min_length=1, description="Relato da ocorrência em pt-BR")
    esperado: ExpectedOutput = Field(..., description="Gabarito de avaliação")
    referencia_caso_canonico: Optional[str] = Field(
        None,
        description="ID do caso CANONICO base (usado para tipo=PARAFRASES)",
    )
    notas: Optional[str] = Field(None, description="Observações sobre o caso")

    @model_validator(mode="after")
    def validar_restricoes_por_tipo(self) -> "DatasetCase":
        """
        Valida restrições cruzadas entre tipo e campos esperados:
        - ALTA_CRITICIDADE → urgencia=IMEDIATA, prioridade=P1, requer_revisao_humana=True
        - FORA_ESCOPO → categoria=FORA_DO_ESCOPO
        - REVISAO_HUMANA → requer_revisao_humana=True
        - equipe → valor de VALID_DATASET_TEAMS
        """
        e = self.esperado

        if self.tipo == "ALTA_CRITICIDADE":
            if e.urgencia != UrgencyLevel.IMEDIATA:
                raise ValueError(
                    f"Caso {self.id} (ALTA_CRITICIDADE): urgencia deve ser IMEDIATA, "
                    f"encontrado {e.urgencia}"
                )
            if e.prioridade != PriorityLevel.P1:
                raise ValueError(
                    f"Caso {self.id} (ALTA_CRITICIDADE): prioridade deve ser P1, "
                    f"encontrado {e.prioridade}"
                )
            if not e.requer_revisao_humana:
                raise ValueError(
                    f"Caso {self.id} (ALTA_CRITICIDADE): requer_revisao_humana deve ser True"
                )

        if self.tipo == "FORA_ESCOPO":
            if e.categoria != FailureCategory.FORA_DO_ESCOPO:
                raise ValueError(
                    f"Caso {self.id} (FORA_ESCOPO): categoria deve ser FORA_DO_ESCOPO, "
                    f"encontrado {e.categoria}"
                )

        if self.tipo == "REVISAO_HUMANA":
            if not e.requer_revisao_humana:
                raise ValueError(
                    f"Caso {self.id} (REVISAO_HUMANA): requer_revisao_humana deve ser True"
                )

        equipe_val = e.equipe.strip()
        if equipe_val not in VALID_DATASET_TEAMS:
            raise ValueError(
                f"Caso {self.id}: equipe '{equipe_val}' inválida. "
                f"Valores aceitos: {sorted(VALID_DATASET_TEAMS)}"
            )

        return self


# ---------------------------------------------------------------------------
# Função de carregamento
# ---------------------------------------------------------------------------


def load_dataset(path: str | None = None) -> list[DatasetCase]:
    """
    Carrega e valida o dataset sintético de casos de triagem.

    Caminho padrão: <raiz_projeto>/datasets/synthetic_cases.json
    A raiz é resolvida a partir do arquivo atual:
      src/data/dataset_loader.py → src/data/ → src/ → raiz

    Validações executadas:
      1. Arquivo existe e é JSON válido.
      2. JSON é uma lista (não dicionário).
      3. Cada item é um DatasetCase válido (Pydantic valida campos + tipo).
      4. IDs são únicos em todo o dataset.
      5. referencia_caso_canonico (quando preenchido) aponta para um ID existente
         de tipo CANONICO.

    Args:
        path: caminho absoluto ou relativo do arquivo JSON. None = padrão.

    Returns:
        list[DatasetCase] validado.

    Raises:
        FileNotFoundError: arquivo não encontrado.
        ValueError: estrutura inválida, IDs duplicados ou referência quebrada.
    """
    if path is None:
        # src/data/dataset_loader.py → src/data/ → src/ → raiz_projeto
        project_root = Path(__file__).resolve().parent.parent.parent
        resolved = project_root / "datasets" / "synthetic_cases.json"
    else:
        resolved = Path(path)

    if not resolved.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {resolved}. "
            "Verifique se o arquivo datasets/synthetic_cases.json existe na raiz do projeto."
        )

    with open(resolved, encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError(
            "Dataset inválido: esperado array JSON no nível raiz, "
            f"encontrado {type(raw).__name__}."
        )

    # Valida cada item e coleta todos os erros antes de levantar
    cases: list[DatasetCase] = []
    erros: list[str] = []
    for i, item in enumerate(raw):
        try:
            cases.append(DatasetCase(**item))
        except Exception as exc:
            erros.append(f"  Índice {i} (id={item.get('id', '?')}): {exc}")

    if erros:
        raise ValueError(
            f"Dataset com {len(erros)} caso(s) inválido(s):\n" + "\n".join(erros)
        )

    # Valida unicidade de IDs
    ids = [c.id for c in cases]
    duplicados = {i for i in ids if ids.count(i) > 1}
    if duplicados:
        raise ValueError(
            f"IDs duplicados no dataset: {sorted(duplicados)}"
        )

    # Valida referências de PARAFRASES contra IDs de tipo CANONICO
    ids_canonicos = {c.id for c in cases if c.tipo == "CANONICO"}
    for caso in cases:
        ref = caso.referencia_caso_canonico
        if ref is not None and ref not in ids_canonicos:
            raise ValueError(
                f"Caso {caso.id}: referencia_caso_canonico='{ref}' não encontrado "
                "entre os casos de tipo CANONICO."
            )

    return cases
