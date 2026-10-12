# -*- coding: utf-8 -*-
"""
Extrai os números de um relatório de avaliação (evaluation_summary_<ts>.json)
e os imprime já formatados em pt-BR (vírgula decimal), prontos para colar nas
tabelas da monografia (Tabela 2, 3, 4, 5 e Quadro B.1).

Uso:
    python extrair_resultados_monografia.py
        -> usa o evaluation_summary_*.json mais recente em results/

    python extrair_resultados_monografia.py caminho/para/evaluation_summary_XXXX.json
        -> usa o arquivo informado

Também aceita o evaluation_raw_*.json ou o datasets/sample_report.json,
desde que tenham a estrutura {abordagem: metricas}.
"""
import glob
import json
import os
import sys

ORDEM_ABORDAGENS = ["regras", "llm", "hibrido"]
ROTULO_ABORDAGEM = {"regras": "Regras", "llm": "LLM puro", "hibrido": "Híbrido"}
ORDEM_URGENCIA = ["IMEDIATA", "ALTA", "MEDIA", "BAIXA", "DESCONHECIDA"]


def achar_arquivo():
    if len(sys.argv) > 1:
        return sys.argv[1]
    base = os.path.dirname(os.path.abspath(__file__))
    padrao = os.path.join(base, "results", "evaluation_summary_*.json")
    candidatos = sorted(glob.glob(padrao))
    if not candidatos:
        print("Nenhum evaluation_summary_*.json encontrado em results/.")
        print("Rode primeiro: python -m src.evaluation")
        print("Ou informe o caminho: python extrair_resultados_monografia.py <arquivo.json>")
        sys.exit(1)
    return candidatos[-1]  # mais recente (ordenação por timestamp no nome)


def num(x, casas=2):
    """Formata número com vírgula decimal (pt-BR), sem separador de milhar."""
    try:
        return f"{float(x):.{casas}f}".replace(".", ",")
    except (TypeError, ValueError):
        return "-"


def ms(x):
    """Formata milissegundos com separador de milhar '.' e decimal ','."""
    try:
        s = f"{float(x):,.1f}"  # ex.: 16,830.7
        return s.replace(",", "§").replace(".", ",").replace("§", ".")
    except (TypeError, ValueError):
        return "-"


def get_aprox(dados, chave):
    """Busca a abordagem tolerando variações de caixa (regras/REGRAS...)."""
    for k, v in dados.items():
        if k.lower() == chave:
            return v
    return {}


def sep(t=""):
    print("\n" + "=" * 70)
    if t:
        print(t)
        print("-" * 70)


def tabela2(dados):
    sep("TABELA 2 — F1 ponderado por dimensão e abordagem")
    print(f"{'Dimensão':<12} {'Regras':>8} {'LLM puro':>10} {'Híbrido':>9}")
    campos = [("Urgência", "f1_urgencia"), ("Prioridade", "f1_prioridade"),
              ("Categoria", "f1_categoria"), ("Equipe", "f1_equipe")]
    for rotulo, chave in campos:
        r = get_aprox(dados, "regras").get(chave, 0.0)
        l = get_aprox(dados, "llm").get(chave, 0.0)
        h = get_aprox(dados, "hibrido").get(chave, 0.0)
        print(f"{rotulo:<12} {num(r):>8} {num(l):>10} {num(h):>9}")


def tabela3(dados, abordagem="hibrido"):
    sep(f"TABELA 3 — Métricas por classe de urgência ({ROTULO_ABORDAGEM.get(abordagem)})")
    cls = get_aprox(dados, abordagem).get("classification", {}).get("urgencia", {})
    if not cls:
        print("(sem dados de classificação de urgência)")
        return
    print(f"{'Classe':<14} {'Precisão':>9} {'Revocação':>10} {'F1':>6} {'Suporte':>8}")
    for c in ORDEM_URGENCIA:
        if c in cls:
            d = cls[c]
            print(f"{c:<14} {num(d.get('precision')):>9} {num(d.get('recall')):>10} "
                  f"{num(d.get('f1-score')):>6} {int(d.get('support', 0)):>8}")
    wa = cls.get("weighted avg", {})
    if wa:
        print(f"{'Média pond.':<14} {num(wa.get('precision')):>9} {num(wa.get('recall')):>10} "
              f"{num(wa.get('f1-score')):>6} {int(wa.get('support', 0)):>8}")


def tabela4(dados, abordagem="hibrido"):
    sep(f"TABELA 4 — Matriz de confusão de urgência ({ROTULO_ABORDAGEM.get(abordagem)})")
    cm = get_aprox(dados, abordagem).get("confusion_matrices", {}).get("urgencia", {})
    labels = cm.get("labels", [])
    matrix = cm.get("matrix", [])
    if not matrix:
        print("(sem matriz de confusão)")
        return
    curtos = {"IMEDIATA": "IMED.", "DESCONHECIDA": "DESCON."}
    cab = [curtos.get(x, x.capitalize()) for x in labels]
    print("Ref \\ Prev".ljust(12) + "".join(f"{c:>9}" for c in cab) + f"{'Total':>9}")
    col_tot = [0] * len(labels)
    for i, lin in enumerate(matrix):
        rot = curtos.get(labels[i], labels[i].capitalize())
        print(rot.ljust(12) + "".join(f"{v:>9}" for v in lin) + f"{sum(lin):>9}")
        for j, v in enumerate(lin):
            col_tot[j] += v
    print("Total".ljust(12) + "".join(f"{v:>9}" for v in col_tot) + f"{sum(col_tot):>9}")


def tabela5(dados):
    sep("TABELA 5 / QUADRO B.1 — Métricas complementares por abordagem")
    linhas = [
        ("Taxa de campos sem suporte", "unsupported_fields_rate", None),
        ("Subestimação de casos críticos", "critical_underestimation_rate", None),
        ("Taxa de revisão humana", "human_review_rate", None),
        ("Robustez — urgência", ("robustness", "urgencia"), None),
        ("Robustez — prioridade", ("robustness", "prioridade"), None),
        ("Robustez — categoria", ("robustness", "categoria"), None),
    ]
    print(f"{'Métrica':<34} {'Regras':>9} {'LLM puro':>10} {'Híbrido':>9}")

    def val(ap, chave):
        d = get_aprox(dados, ap)
        if isinstance(chave, tuple):
            return d.get(chave[0], {}).get(chave[1], 0.0)
        return d.get(chave, 0.0)

    for rotulo, chave, _ in linhas:
        r, l, h = val("regras", chave), val("llm", chave), val("hibrido", chave)
        print(f"{rotulo:<34} {num(r):>9} {num(l):>10} {num(h):>9}")

    # Latência média (ms)
    r = get_aprox(dados, "regras").get("latency", {}).get("media", 0.0)
    l = get_aprox(dados, "llm").get("latency", {}).get("media", 0.0)
    h = get_aprox(dados, "hibrido").get("latency", {}).get("media", 0.0)
    print(f"{'Latência média (ms)':<34} {ms(r):>9} {ms(l):>10} {ms(h):>9}")

    # Casos / erros
    def ce(ap):
        d = get_aprox(dados, ap)
        return f"{int(d.get('total_cases', 0))} / {int(d.get('total_errors', 0))}"
    print(f"{'Casos avaliados / erros':<34} {ce('regras'):>9} {ce('llm'):>10} {ce('hibrido'):>9}")


def main():
    arquivo = achar_arquivo()
    print(f"Lendo: {arquivo}")
    with open(arquivo, encoding="utf-8") as f:
        dados = json.load(f)
    # tolera arquivos com chave extra "_aviso" (como o sample_report.json)
    dados = {k: v for k, v in dados.items() if isinstance(v, dict) and "f1_urgencia" in v}
    if not dados:
        print("Estrutura inesperada: nenhuma abordagem com 'f1_urgencia' encontrada.")
        sys.exit(1)
    tabela2(dados)
    tabela3(dados, "hibrido")
    tabela4(dados, "hibrido")
    tabela5(dados)
    print("\n" + "=" * 70)
    print("Copie os valores acima para as tabelas correspondentes da monografia.")
    print("Lembre-se de substituir também os números citados no texto (Resumo,")
    print("Abstract, Seções 5.2 a 5.6) e de refazer as Figuras 2 e 3 com estes dados.")


if __name__ == "__main__":
    main()
