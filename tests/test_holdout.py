"""
Testes do conjunto de validação (datasets/holdout_cases.json).

Verificam que o conjunto é válido, que reproduz a distribuição por tipo do
conjunto principal e que nenhum relato repete um relato do conjunto principal.
Nenhum teste requer Ollama rodando.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from collections import Counter
from pathlib import Path

from src.data.dataset_loader import load_dataset

RAIZ = Path(__file__).resolve().parents[1]
VALIDACAO = load_dataset(str(RAIZ / "datasets" / "holdout_cases.json"))
PRINCIPAL = load_dataset(str(RAIZ / "datasets" / "synthetic_cases.json"))


def test_cem_casos_com_ids_sequenciais():
    assert [c.id for c in VALIDACAO] == [f"VAL-{i:03d}" for i in range(1, 101)]


def test_mesma_distribuicao_por_tipo_do_conjunto_principal():
    assert Counter(c.tipo for c in VALIDACAO) == Counter(c.tipo for c in PRINCIPAL)


def test_nenhum_relato_repete_o_conjunto_principal():
    principais = {c.texto.strip().lower() for c in PRINCIPAL}
    assert not [c.id for c in VALIDACAO if c.texto.strip().lower() in principais]


def test_parafrases_apontam_para_canonicos_do_proprio_conjunto():
    canonicos = {c.id for c in VALIDACAO if c.tipo == "CANONICO"}
    assert all(c.referencia_caso_canonico in canonicos for c in VALIDACAO if c.tipo == "PARAFRASES")
