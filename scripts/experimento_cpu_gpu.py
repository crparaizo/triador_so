"""
Miniexperimento de hardware: execução do LLM em GPU e em CPU.

Mede, para os modelos qwen3 de 0.6b, 1.7b e 4b, o tempo das duas fases da
inferência (processamento do prompt e geração de tokens) com o modelo carregado
pelo padrão do Ollama (GPU, com transbordo para a memória do sistema quando a
VRAM não comporta o modelo) e com o modelo forçado na CPU (num_gpu = 0).

Usa o mesmo prompt de extração da abordagem híbrida, temperatura zero,
semente 42 e limite de 1.024 tokens, sobre alguns relatos do conjunto de dados.
Não altera o experimento principal: é uma medição à parte, salva em results/.

Uso (com o Ollama em execução):
    python scripts/experimento_cpu_gpu.py --casos 3

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import httpx

from src.data.dataset_loader import load_dataset
from src.extraction.llm_extractor import _PROMPT_TEMPLATE

URL = "http://localhost:11434"
MODELOS = ["qwen3:0.6b", "qwen3:1.7b", "qwen3:4b"]
MODOS = {"padrao": {}, "cpu": {"num_gpu": 0}}


def _descarregar(cliente: httpx.Client, modelo: str) -> None:
    cliente.post(f"{URL}/api/generate", json={"model": modelo, "keep_alive": 0})


def _alocacao(cliente: httpx.Client, modelo: str) -> tuple[int, int]:
    """Tamanho total do modelo carregado e parte dele na VRAM (bytes), via /api/ps."""
    for m in cliente.get(f"{URL}/api/ps").json().get("models", []):
        if m.get("name") == modelo or m.get("model") == modelo:
            return int(m.get("size", 0)), int(m.get("size_vram", 0))
    return 0, 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--casos", type=int, default=3, help="número de relatos por configuração")
    args = parser.parse_args()

    relatos = [c.texto for c in load_dataset()[: args.casos]]
    linhas = []
    with httpx.Client(timeout=900) as cliente:
        for modelo in MODELOS:
            for modo, extra in MODOS.items():
                _descarregar(cliente, modelo)
                for i, texto in enumerate(relatos):
                    opcoes = {"temperature": 0, "seed": 42, "num_predict": 1024, **extra}
                    inicio = time.perf_counter()
                    r = cliente.post(f"{URL}/api/generate", json={
                        "model": modelo, "prompt": _PROMPT_TEMPLATE.format(texto=texto),
                        "format": "json", "stream": False, "options": opcoes,
                    }).json()
                    parede = time.perf_counter() - inicio
                    total, vram = _alocacao(cliente, modelo)
                    linha = {
                        "modelo": modelo, "modo": modo, "caso": i,
                        "tamanho_carregado_mb": round(total / 2**20),
                        "fracao_vram": round(vram / total, 3) if total else None,
                        "load_s": round(r.get("load_duration", 0) / 1e9, 2),
                        "prompt_tokens": r.get("prompt_eval_count"),
                        "prompt_s": round(r.get("prompt_eval_duration", 0) / 1e9, 2),
                        "gerados_tokens": r.get("eval_count"),
                        "geracao_s": round(r.get("eval_duration", 0) / 1e9, 2),
                        "total_s": round(parede, 2),
                    }
                    linha["prompt_tok_s"] = round(linha["prompt_tokens"] / linha["prompt_s"], 1) if linha["prompt_s"] else None
                    linha["geracao_tok_s"] = round(linha["gerados_tokens"] / linha["geracao_s"], 1) if linha["geracao_s"] else None
                    linhas.append(linha)
                    print(json.dumps(linha, ensure_ascii=False), flush=True)
                _descarregar(cliente, modelo)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saida = Path("results") / f"experimento_cpu_gpu_{ts}.csv"
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()
