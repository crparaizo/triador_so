"""
Gera datasets/alarm_cases.json a partir dos eventos de datasets/alarm_events.json.

Cada evento do supervisório simulado vira o texto de uma OS (src/alarms) e um
caso no formato do conjunto de dados (tipo ALARME), com o gabarito anotado no
próprio arquivo de eventos. Os casos podem então ser avaliados como o
conjunto principal:

    python scripts/gerar_casos_alarme.py
    python -m src.evaluation --dataset datasets/alarm_cases.json

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import json
from pathlib import Path

from src.alarms import AlarmEvent, alarme_para_relato
from src.data.dataset_loader import load_dataset
from src.data.loader import load_knowledge_base

RAIZ = Path(__file__).resolve().parents[1]
ORIGEM = RAIZ / "datasets" / "alarm_events.json"
DESTINO = RAIZ / "datasets" / "alarm_cases.json"


def main() -> None:
    kb = load_knowledge_base()
    casos = []
    for item in json.loads(ORIGEM.read_text(encoding="utf-8")):
        evento = AlarmEvent(**item["evento"])
        casos.append({
            "id": evento.id,
            "tipo": "ALARME",
            "texto": alarme_para_relato(evento, kb),
            "esperado": item["esperado"],
            "referencia_caso_canonico": None,
            "notas": item["notas"],
        })
    DESTINO.write_text(json.dumps(casos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(load_dataset(str(DESTINO)))} casos de alarme gravados em {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
