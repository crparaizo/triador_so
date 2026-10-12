"""
Testes automatizados para o módulo src/data/dataset_loader.py.

Cobre: carregamento do dataset sintético, validação de estrutura,
invariantes por tipo, unicidade de IDs, referências de paráfrases e
comportamento com entradas inválidas.

Nenhum teste depende de Ollama. Os testes 1–14 lêem o arquivo real
datasets/synthetic_cases.json. Os testes 15–17 usam tmp_path ou
constroem DatasetCase diretamente.

AVISO: O dataset é completamente sintético — gerado para fins acadêmicos.
"""

import json
import re
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from src.data.dataset_loader import (
    CaseType,
    DatasetCase,
    VALID_DATASET_TEAMS,
    load_dataset,
)
from src.schemas.triage import FailureCategory, PriorityLevel, UrgencyLevel


# ---------------------------------------------------------------------------
# Fixture de módulo — carrega o dataset uma única vez para todos os testes
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dataset() -> list[DatasetCase]:
    """Carrega o dataset sintético real uma vez por módulo de teste."""
    return load_dataset()


# ---------------------------------------------------------------------------
# Testes 1–14: validação do dataset real
# ---------------------------------------------------------------------------


def test_load_dataset_retorna_lista(dataset: list[DatasetCase]):
    """load_dataset deve retornar uma instância de list."""
    assert isinstance(dataset, list)


def test_load_dataset_100_casos(dataset: list[DatasetCase]):
    """O dataset deve conter exatamente 100 casos."""
    assert len(dataset) == 100, f"Esperado 100 casos, encontrado {len(dataset)}"


def test_todos_ids_unicos(dataset: list[DatasetCase]):
    """Todos os IDs do dataset devem ser únicos."""
    ids = {c.id for c in dataset}
    assert len(ids) == 100, f"IDs únicos: {len(ids)}, esperado 100"


def test_ids_formato_case_nnn(dataset: list[DatasetCase]):
    """Todos os IDs devem seguir o padrão CASE-NNN (3 dígitos)."""
    invalidos = [c.id for c in dataset if not re.match(r"^CASE-\d{3}$", c.id)]
    assert invalidos == [], f"IDs com formato inválido: {invalidos}"


def test_todos_textos_nao_vazios(dataset: list[DatasetCase]):
    """Nenhum caso deve ter texto vazio após strip."""
    vazios = [c.id for c in dataset if len(c.texto.strip()) == 0]
    assert vazios == [], f"Casos com texto vazio: {vazios}"


def test_todos_tipos_validos(dataset: list[DatasetCase]):
    """Todos os valores de 'tipo' devem ser membros válidos de CaseType."""
    tipos_validos = set(get_args(CaseType))
    invalidos = [c.id for c in dataset if c.tipo not in tipos_validos]
    assert invalidos == [], f"Casos com tipo inválido: {invalidos}"


def test_urgencia_valores_validos(dataset: list[DatasetCase]):
    """Todos os valores de esperado.urgencia devem ser instâncias de UrgencyLevel."""
    invalidos = [c.id for c in dataset if not isinstance(c.esperado.urgencia, UrgencyLevel)]
    assert invalidos == [], f"Casos com urgencia inválida: {invalidos}"


def test_prioridade_valores_validos(dataset: list[DatasetCase]):
    """Todos os valores de esperado.prioridade devem ser instâncias de PriorityLevel."""
    invalidos = [c.id for c in dataset if not isinstance(c.esperado.prioridade, PriorityLevel)]
    assert invalidos == [], f"Casos com prioridade inválida: {invalidos}"


def test_categoria_valores_validos(dataset: list[DatasetCase]):
    """Todos os valores de esperado.categoria devem ser instâncias de FailureCategory."""
    invalidos = [c.id for c in dataset if not isinstance(c.esperado.categoria, FailureCategory)]
    assert invalidos == [], f"Casos com categoria inválida: {invalidos}"


def test_equipe_valores_validos(dataset: list[DatasetCase]):
    """Todos os valores de esperado.equipe devem estar em VALID_DATASET_TEAMS."""
    invalidos = [c.id for c in dataset if c.esperado.equipe not in VALID_DATASET_TEAMS]
    assert invalidos == [], f"Casos com equipe inválida: {invalidos}"


def test_alta_criticidade_restricoes(dataset: list[DatasetCase]):
    """Casos ALTA_CRITICIDADE devem ter urgencia=IMEDIATA, prioridade=P1 e revisao=True."""
    casos_ac = [c for c in dataset if c.tipo == "ALTA_CRITICIDADE"]
    assert len(casos_ac) > 0, "Nenhum caso ALTA_CRITICIDADE encontrado no dataset"
    for caso in casos_ac:
        assert caso.esperado.urgencia == UrgencyLevel.IMEDIATA, (
            f"{caso.id}: urgencia deveria ser IMEDIATA, encontrado {caso.esperado.urgencia}"
        )
        assert caso.esperado.prioridade == PriorityLevel.P1, (
            f"{caso.id}: prioridade deveria ser P1, encontrado {caso.esperado.prioridade}"
        )
        assert caso.esperado.requer_revisao_humana is True, (
            f"{caso.id}: requer_revisao_humana deveria ser True"
        )


def test_fora_escopo_categoria(dataset: list[DatasetCase]):
    """Todos os casos FORA_ESCOPO devem ter categoria=FORA_DO_ESCOPO."""
    casos_fora = [c for c in dataset if c.tipo == "FORA_ESCOPO"]
    assert len(casos_fora) > 0, "Nenhum caso FORA_ESCOPO encontrado no dataset"
    for caso in casos_fora:
        assert caso.esperado.categoria == FailureCategory.FORA_DO_ESCOPO, (
            f"{caso.id}: categoria deveria ser FORA_DO_ESCOPO, encontrado {caso.esperado.categoria}"
        )


def test_revisao_humana_revisao_true(dataset: list[DatasetCase]):
    """Todos os casos REVISAO_HUMANA devem ter requer_revisao_humana=True."""
    casos_rev = [c for c in dataset if c.tipo == "REVISAO_HUMANA"]
    assert len(casos_rev) > 0, "Nenhum caso REVISAO_HUMANA encontrado no dataset"
    for caso in casos_rev:
        assert caso.esperado.requer_revisao_humana is True, (
            f"{caso.id}: requer_revisao_humana deveria ser True"
        )


def test_parafrases_referencia_valida(dataset: list[DatasetCase]):
    """Casos PARAFRASES devem ter referencia_caso_canonico apontando para um CANONICO existente."""
    ids_canonicos = {c.id for c in dataset if c.tipo == "CANONICO"}
    casos_paraf = [c for c in dataset if c.tipo == "PARAFRASES"]
    assert len(casos_paraf) > 0, "Nenhum caso PARAFRASES encontrado no dataset"
    invalidos = [
        c.id for c in casos_paraf
        if c.referencia_caso_canonico is None or c.referencia_caso_canonico not in ids_canonicos
    ]
    assert invalidos == [], (
        f"Paráfrases com referência inválida ou ausente: {invalidos}"
    )


# ---------------------------------------------------------------------------
# Testes 15–17: comportamento com entradas inválidas
# ---------------------------------------------------------------------------


def test_arquivo_inexistente_levanta_error():
    """load_dataset com caminho inexistente deve levantar FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_dataset("/caminho/que/nao/existe/dataset_invalido_xyz.json")


def test_dataset_case_invalido_alta_criticidade_sem_imediata():
    """DatasetCase ALTA_CRITICIDADE com urgencia != IMEDIATA deve levantar ValidationError."""
    with pytest.raises(ValidationError):
        DatasetCase(
            id="CASE-TST",
            tipo="ALTA_CRITICIDADE",
            texto="Caso de teste com urgência incorreta para tipo ALTA_CRITICIDADE.",
            esperado={
                "urgencia": "ALTA",       # deveria ser IMEDIATA
                "prioridade": "P1",
                "categoria": "MECANICA",
                "equipe": "Manutenção Mecânica",
                "requer_revisao_humana": True,
            },
        )


def test_distribuicao_todos_tipos_presentes(dataset: list[DatasetCase]):
    """Todos os 10 tipos definidos em CaseType devem estar presentes no dataset."""
    tipos_no_dataset = {c.tipo for c in dataset}
    todos_tipos = set(get_args(CaseType))
    ausentes = todos_tipos - tipos_no_dataset
    assert ausentes == set(), f"Tipos ausentes no dataset: {ausentes}"
