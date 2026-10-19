# -*- coding: utf-8 -*-
"""
Análise estatística e de auditabilidade da monografia.

Reproduz, a partir de um arquivo evaluation_raw_<timestamp>.json e do dataset
sintético, os números dos Capítulos 3 e 4: F1 ponderado com IC 95% por
bootstrap (Tabela 2), diferenças pareadas com teste exato de McNemar
(Tabela 3), subestimação de casos críticos com IC de Clopper-Pearson,
métricas de revisão humana com e sem disjunção (Tabela 8), análise de
sensibilidade do rótulo de equipe e verificabilidade das evidências
(Tabela 6 e Seção 4.3).

Uso:
    python scripts/analise_estatistica.py results/evaluation_raw_20261016_100014.json
    python scripts/analise_estatistica.py <raw.json> --saida results/analise.json

Dependências: numpy, scipy, pyyaml (scipy não consta em requirements.txt:
pip install scipy).
Parâmetros fixos: 10.000 amostras bootstrap, semente 42
(numpy.random.default_rng).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import beta, binomtest

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS = ["urgencia", "prioridade", "categoria", "equipe"]
ABORDAGENS = ["regras", "llm", "hibrido"]
ROTULO_SEM_EQUIPE = {"Revisão necessária", "Revisão Manual", "DESCONHECIDA"}
N_BOOT, SEMENTE = 10_000, 42


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def norm(s) -> str:
    """Minúsculas, sem acentos e sem pontuação (comparação de evidências)."""
    s = "".join(c for c in unicodedata.normalize("NFD", str(s).lower())
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def f1_ponderado(y: np.ndarray, p: np.ndarray, k: int) -> np.ndarray:
    """F1 ponderado (média por suporte) para cada linha de y/p (B x n)."""
    saida = np.zeros(y.shape[0])
    for c in range(k):
        yk, pk = (y == c), (p == c)
        tp = (yk & pk).sum(1)
        denom = 2 * tp + (~yk & pk).sum(1) + (yk & ~pk).sum(1)
        f = np.where(denom > 0, 2 * tp / np.maximum(denom, 1), 0.0)
        saida += f * yk.sum(1)
    return saida / y.shape[1]


def mcnemar_exato(b: int, c: int) -> float:
    return 1.0 if b + c == 0 else float(binomtest(min(b, c), b + c, 0.5).pvalue)


def clopper_pearson(k: int, n: int, alfa: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else beta.ppf(alfa / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alfa / 2, k + 1, n - k)
    return float(lo), float(hi)


# ----------------------------------------------------------------------------
# Carga
# ----------------------------------------------------------------------------
def carregar(raw_path: Path):
    raw = json.loads(raw_path.read_text(encoding="utf-8"))["approaches"]
    casos = json.loads((RAIZ / "datasets" / "synthetic_cases.json").read_text(encoding="utf-8"))
    regras = {r["id"]: r for r in yaml.safe_load(
        (RAIZ / "data" / "rules.yaml").read_text(encoding="utf-8"))["regras"]}
    res = {}
    for a in ABORDAGENS:
        lista = raw[a]["results"]
        assert len(lista) == len(casos), f"{a}: {len(lista)} resultados"
        assert all(r["texto_entrada"] == c["texto"] for r, c in zip(lista, casos)), \
            f"{a}: resultados desalinhados do dataset"
        res[a] = lista
    return res, casos, regras


def pred(r: dict, campo: str) -> str:
    return r["equipe_sugerida"] if campo == "equipe" else r[campo]


# ----------------------------------------------------------------------------
# Análises
# ----------------------------------------------------------------------------
def assertividade(res, casos):
    out, n = {}, len(casos)
    cod = {}
    for f in CAMPOS:
        esp = [c["esperado"][f] for c in casos]
        rot = sorted(set(esp) | {pred(r, f) for a in ABORDAGENS for r in res[a]})
        m = {v: i for i, v in enumerate(rot)}
        cod[f] = (len(rot), np.array([m[v] for v in esp]),
                  {a: np.array([m[pred(r, f)] for r in res[a]]) for a in ABORDAGENS})
    idx = np.random.default_rng(SEMENTE).integers(0, n, (N_BOOT, n))
    for f in CAMPOS:
        k, y, P = cod[f]
        boot = {a: f1_ponderado(y[idx], P[a][idx], k) for a in ABORDAGENS}
        pt = {a: float(f1_ponderado(y[None], P[a][None], k)[0]) for a in ABORDAGENS}
        out[f] = {"f1": {}, "dif": {}, "mcnemar": {}}
        for a in ABORDAGENS:
            lo, hi = np.percentile(boot[a], [2.5, 97.5])
            out[f]["f1"][a] = {"f1": round(pt[a], 3),
                               "ic95": [round(float(lo), 3), round(float(hi), 3)],
                               "acuracia": round(float((P[a] == y).mean()), 2)}
        for a, b in [("hibrido", "regras"), ("hibrido", "llm"), ("regras", "llm")]:
            d = boot[a] - boot[b]
            oa, ob = P[a] == y, P[b] == y
            x1, x2 = int((oa & ~ob).sum()), int((ob & ~oa).sum())
            out[f]["dif"][f"{a}-{b}"] = {
                "delta_f1": round(pt[a] - pt[b], 3),
                "ic95": [round(float(np.percentile(d, 2.5)), 3),
                         round(float(np.percentile(d, 97.5)), 3)]}
            out[f]["mcnemar"][f"{a}-{b}"] = {"a_favor_1o": x1, "a_favor_2o": x2,
                                             "p": round(mcnemar_exato(x1, x2), 3)}
    # urgência e prioridade simultâneas
    ok = {a: (cod["urgencia"][2][a] == cod["urgencia"][1]) &
             (cod["prioridade"][2][a] == cod["prioridade"][1]) for a in ABORDAGENS}
    up = {"acertos": {a: int(ok[a].sum()) for a in ABORDAGENS}}
    for a, b in [("hibrido", "regras"), ("hibrido", "llm"), ("regras", "llm")]:
        x1, x2 = int((ok[a] & ~ok[b]).sum()), int((ok[b] & ~ok[a]).sum())
        up[f"{a}-{b}"] = {"a_favor_1o": x1, "a_favor_2o": x2, "p": round(mcnemar_exato(x1, x2), 3)}
    out["urgencia_e_prioridade"] = up
    return out


def criticos(res, casos):
    ids = [i for i, c in enumerate(casos)
           if c["esperado"]["urgencia"] == "IMEDIATA" or c["esperado"]["prioridade"] == "P1"]
    out = {"n_criticos": len(ids), "abordagens": {}}
    sub = {}
    for a in ABORDAGENS:
        flags = []
        for i in ids:
            e, r = casos[i]["esperado"], res[a][i]
            flags.append((e["urgencia"] == "IMEDIATA" and r["urgencia"] in {"ALTA", "MEDIA", "BAIXA"}) or
                         (e["prioridade"] == "P1" and r["prioridade"] in {"P2", "P3", "P4"}))
        sub[a] = np.array(flags)
        k = int(sub[a].sum())
        lo, hi = clopper_pearson(k, len(ids))
        desc = sum(1 for i in ids if res[a][i]["urgencia"] == "DESCONHECIDA"
                   or res[a][i]["prioridade"] == "DESCONHECIDA")
        out["abordagens"][a] = {"subestimados": k, "taxa": round(k / len(ids), 3),
                                "ic_clopper_pearson": [round(lo, 3), round(hi, 3)],
                                "criticos_com_DESCONHECIDA_nao_contados": desc}
    x1 = int((sub["hibrido"] & ~sub["llm"]).sum())
    x2 = int((sub["llm"] & ~sub["hibrido"]).sum())
    out["mcnemar_hibrido_vs_llm"] = {"so_hibrido": x1, "so_llm": x2, "p": round(mcnemar_exato(x1, x2), 3)}
    return out


def revisao(res, casos, regras):
    esp = np.array([c["esperado"]["requer_revisao_humana"] for c in casos])
    crit = np.array([c["esperado"]["urgencia"] == "IMEDIATA" or c["esperado"]["prioridade"] == "P1"
                     for c in casos])
    out, flags = {}, {}

    def linha(nome, p):
        vp, n = int((p & esp).sum()), int(p.sum())
        pr, rc = vp / n, vp / int(esp.sum())
        out[nome] = {"encaminhados": n, "taxa": round(n / len(casos), 3), "vp": vp,
                     "precisao": round(pr, 3), "revocacao": round(rc, 3),
                     "f1": round(2 * pr * rc / (pr + rc), 3),
                     "criticos_revisados": int((p & esp & crit).sum()),
                     "criticos_que_exigem_revisao": int((esp & crit).sum())}
        flags[nome] = p

    for a in ABORDAGENS:
        linha(a, np.array([bool(r["requer_revisao_humana"]) for r in res[a]]))
    for a in ["regras", "hibrido"]:   # disjunção: basta uma regra acionada exigir revisão
        linha(f"{a}_disjuncao", np.array([
            bool(r["requer_revisao_humana"]) or
            any(regras[x]["acoes"].get("requer_revisao_humana") for x in r["regras_acionadas"])
            for r in res[a]]))
    x1 = int((flags["hibrido"] & esp & ~flags["regras"]).sum())
    x2 = int((flags["regras"] & esp & ~flags["hibrido"]).sum())
    out["mcnemar_revocacao_hibrido_vs_regras"] = {"so_hibrido": x1, "so_regras": x2,
                                                  "p": round(mcnemar_exato(x1, x2), 3)}
    out["n_exigem_revisao"] = int(esp.sum())
    return out


def sensibilidade_equipe(res, casos):
    """Trata 'Revisão necessária' / 'Revisão Manual' como equivalentes a DESCONHECIDA."""
    esp = [c["esperado"]["equipe"] for c in casos]
    out = {}
    for a in ABORDAGENS:
        p = [pred(r, "equipe") for r in res[a]]
        p2 = ["DESCONHECIDA" if x in ROTULO_SEM_EQUIPE else x for x in p]
        rot = sorted(set(esp) | set(p2))
        m = {v: i for i, v in enumerate(rot)}
        y, q = np.array([m[v] for v in esp])[None], np.array([m[v] for v in p2])[None]
        out[a] = {"acuracia_original": round(float(np.mean([x == y_ for x, y_ in zip(p, esp)])), 2),
                  "acuracia_harmonizada": round(float(np.mean([x == y_ for x, y_ in zip(p2, esp)])), 2),
                  "f1_ponderado_harmonizado": round(float(f1_ponderado(y, q, len(rot))[0]), 3)}
    return out


def evidencias(res):
    """
    Verificabilidade das evidências extraídas do relato (Seções 3.6.1 e 4.3).

    Campos considerados: ativo, ativo_mencionado, sintomas, risco_seguranca,
    impacto_producao, urgencia_mencionada. Excluídos: localização (vem do
    cadastro), ativo_encontrado, regras_classificacao e registros de falha.
    Evidência verificável: trecho localizado no relato após remover acentos,
    caixa e pontuação. Na abordagem por regras, 'sintomas' é uma lista de
    palavras-chave separadas por vírgula e cada termo é verificado
    isoladamente; na híbrida, 'sintomas' é a frase devolvida pelo modelo (ou
    uma lista literal) e cada item é verificado como um todo.
    """
    campos = ["ativo", "ativo_mencionado", "sintomas", "risco_seguranca",
              "impacto_producao", "urgencia_mencionada"]
    out = {}
    for a in ABORDAGENS:
        com_ev = todas = com_regra = regra_todas = 0
        tot, ok = Counter(), Counter()
        urg_ausente = []
        for r in res[a]:
            texto, ev = norm(r["texto_entrada"]), r.get("evidencias") or {}
            itens = []
            for k in campos:
                v = ev.get(k)
                if v in (None, "", "[]", "None", "null"):
                    continue
                if a == "regras" and k == "sintomas":
                    partes = str(v).split(",")
                else:
                    if isinstance(v, str) and v.startswith("["):
                        try:
                            v = ast.literal_eval(v)
                        except (ValueError, SyntaxError):
                            pass
                    partes = v if isinstance(v, list) else [v]
                itens += [(k, str(p).strip()) for p in partes if str(p).strip()]
            todas_ok = True
            for k, p in itens:
                tot[k] += 1
                if norm(p) in texto:
                    ok[k] += 1
                else:
                    todas_ok = False
                    if k == "urgencia_mencionada":
                        urg_ausente.append(p)
            if itens:
                com_ev += 1
                todas += todas_ok
            if r["regras_acionadas"]:
                com_regra += 1
                regra_todas += bool(itens and todas_ok)
        n = len(res[a])
        out[a] = {"casos_com_regra_acionada_pct": round(100 * com_regra / n),
                  "casos_com_evidencia": com_ev,
                  "casos_com_evidencia_pct": round(100 * com_ev / n),
                  "casos_evidencias_todas_verificaveis": todas,
                  "casos_regra_e_todas_verificaveis_pct": round(100 * regra_todas / n),
                  "evidencias_verificaveis": f"{sum(ok.values())}/{sum(tot.values())}",
                  "por_campo": {k: f"{ok[k]}/{tot[k]}" for k in tot},
                  "urgencia_mencionada_ausente_no_relato": dict(Counter(urg_ausente).most_common(5))}
    return out


def custo(res):
    out = {}
    for a in ABORDAGENS:
        lat = np.array([r["latencia_ms"] for r in res[a]])
        out[a] = {"lat_media_ms": round(float(lat.mean()), 1), "lat_dp_ms": round(float(lat.std(ddof=0)), 1),
                  "lat_min_ms": round(float(lat.min()), 1), "lat_max_ms": round(float(lat.max()), 1),
                  "tokens_entrada_medio": round(float(np.mean([r.get("tokens_entrada", 0) for r in res[a]])), 1),
                  "tokens_saida_medio": round(float(np.mean([r.get("tokens_saida", 0) for r in res[a]])), 1),
                  "tokens_total_medio": round(float(np.mean([r.get("tokens_total", 0) for r in res[a]])), 1),
                  "tokens_total_soma": int(sum(r.get("tokens_total", 0) for r in res[a]))}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", type=Path, help="results/evaluation_raw_<timestamp>.json")
    ap.add_argument("--saida", type=Path, help="grava o resultado também em JSON")
    args = ap.parse_args()
    res, casos, regras = carregar(args.raw)
    resultado = {
        "arquivo": args.raw.name,
        "assertividade": assertividade(res, casos),
        "criticos": criticos(res, casos),
        "revisao_humana": revisao(res, casos, regras),
        "sensibilidade_equipe": sensibilidade_equipe(res, casos),
        "evidencias": evidencias(res),
        "custo": custo(res),
    }
    texto = json.dumps(resultado, ensure_ascii=False, indent=2)
    print(texto)
    if args.saida:
        args.saida.write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
