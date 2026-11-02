"""
Leitura determinística de valores de pressão escritos no relato.

Reconhece valores em kPa e MPa no formato brasileiro (ponto como separador de
milhar e vírgula como separador decimal, ex.: "1.080 kPa", "1,04 MPa") e os
devolve em kPa. Usado pelo motor de regras para comparar a pressão relatada com
a PMTA cadastrada do ativo (condição pressao_acima_pmta).

Só considera unidades com prefixo do SI sobre o pascal, sem conversões de
outras unidades (bar, psi, kgf/cm²), que não aparecem nos relatos do protótipo.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import re

_FATOR_KPA = {"kpa": 1.0, "mpa": 1000.0}

_PADRAO = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?\s*(kPa|MPa)\b",
    re.IGNORECASE,
)


def pressoes_kpa(texto: str) -> list[float]:
    """Valores de pressão do texto, convertidos para kPa, na ordem em que aparecem."""
    valores = []
    for inteiro, decimal, unidade in _PADRAO.findall(texto or ""):
        numero = float(inteiro.replace(".", "") + ("." + decimal if decimal else ""))
        valores.append(numero * _FATOR_KPA[unidade.lower()])
    return valores
