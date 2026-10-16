# Métricas de Avaliação

> Protótipo acadêmico — monografia de especialização em Controle e Automação (IFSP).
> As métricas abaixo são calculadas sobre um dataset sintético de 100 casos.
> **Não extrair conclusões estatísticas robustas** sem considerar as limitações
> documentadas aqui e em [`datasets/DATASET_README.md`](../datasets/DATASET_README.md).

Este documento define cada métrica coletada pelo módulo
[`src/evaluation/metrics.py`](../src/evaluation/metrics.py), como é calculada e
quais são suas limitações. Nenhuma métrica usa um LLM para avaliar a saída de
outro LLM: **toda comparação é feita contra o gabarito** (`esperado`) de cada caso.

## Princípios

- **Comparação contra gabarito.** Predição versus `ExpectedOutput` anotado no
  dataset. O gabarito foi definido por regras de anotação e julgamento editorial
  (não por especialistas de manutenção reais) — ver limitação no DATASET_README.
- **Execução reprodutível.** O LLM roda com `temperature=0` e `seed` fixo
  (ver [`src/config/loader.py`](../src/config/loader.py)), tornando a saída
  quase determinística. Cada caso é avaliado uma vez; a variância entre execuções
  repetidas não é medida — é uma limitação assumida do desenho.

## Métricas de assertividade (acurácia do roteamento)

| Métrica | Como é calculada | Função |
|---|---|---|
| F1 por campo (urgência, prioridade, categoria, equipe) | `sklearn.metrics.classification_report` (média *weighted*, `zero_division=0`), predição × gabarito | `classification_report_dict`, `per_approach_summary` |
| Matriz de confusão (urgência, prioridade, categoria) | `sklearn.metrics.confusion_matrix` sobre os rótulos de cada enum | `confusion_matrix_dict` |

O F1 *weighted* foi escolhido por ponderar as classes pela frequência, adequado
ao dataset desbalanceado (ver distribuição por categoria no DATASET_README).

## Métricas de segurança operacional

| Métrica | Definição | Função |
|---|---|---|
| Taxa de subestimação de casos críticos | Entre os casos críticos (urgência verdadeira `IMEDIATA` **ou** prioridade verdadeira `P1`), fração classificada abaixo do crítico. Definição conservadora: conta subestimação em urgência **ou** prioridade. | `critical_underestimation_rate` |
| Taxa de revisão humana | Fração de casos sinalizados com `requer_revisao_humana=True` (inclui falsos positivos). Taxa alta sugere conservadorismo; muito baixa, sub-sinalização. | `human_review_rate` |
| Taxa de campos sem suporte | `Σ campos_sem_suporte / (n × 4)`, proxy de preenchimento sem evidência textual (possível alucinação). | `unsupported_fields_rate` |

> **Limitação de comparabilidade.** A semântica de `campos_sem_suporte` difere por
> abordagem: em `regras` e `hibrido` lista campos de **extração** sem evidência;
> em `llm` lista campos de **classificação** que o próprio modelo declarou sem
> suporte. Portanto a taxa é um indicador **por abordagem**, não diretamente
> equivalente entre as três. O indicador também não separa inferência contextual
> legítima de alucinação.

## Métricas de robustez

| Métrica | Definição | Função |
|---|---|---|
| Consistência canônico × paráfrase | Para cada par (caso `CANONICO`, sua `PARAFRASES`), fração de predições iguais em urgência, prioridade e categoria. 1.0 = classificação invariante à formulação do relato. | `robustness_score` |

Depende da existência de pares anotados (`referencia_caso_canonico`) no dataset.
A comparação usa as **predições**, não o gabarito.

## Métricas de custo computacional

| Métrica | Definição | Função |
|---|---|---|
| Latência (média, desvio, mín, máx) | Tempo do fluxo em milissegundos, de `preparacao_entrada` a `montagem_resultado`, via `time.perf_counter()`. Inclui serialização e *overhead* do Python. | `latency_stats` |
| Tokens (entrada média, saída média, total médio, total soma) | Tokens consumidos por chamada ao LLM, lidos dos metadados do Ollama (`usage_metadata` ou `prompt_eval_count`/`eval_count`). | `token_stats` |

> **Interpretação dos tokens por abordagem.** Regras puras consomem **0 tokens**
> (nenhuma chamada a LLM); o híbrido consome apenas os tokens da **extração**; o
> LLM puro consome extração + classificação + roteamento num único *prompt*. O
> token é o indicador direto de custo computacional desta comparação — como a
> inferência é **local** (Ollama), não há custo monetário por token. Quando os
> metadados de uso não estão disponíveis, a contagem vale 0 e **não** deve ser
> confundida com ausência de chamada ao modelo.

## Arquivos de saída

O módulo [`src/evaluation/report.py`](../src/evaluation/report.py) gera, por
execução (com *timestamp*):

1. `evaluation_raw_<ts>.json` — dados brutos completos.
2. `evaluation_per_case_<ts>.csv` — predição × gabarito por caso (inclui `latencia_ms` e `tokens_total`).
3. `evaluation_summary_<ts>.json` — métricas agregadas por abordagem.
4. `evaluation_summary_<ts>.csv` — resumo tabular por abordagem (inclui `latencia_media_ms`, `tokens_total_medio`, `tokens_total_soma`).
