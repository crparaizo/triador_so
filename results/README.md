# results/ — Relatórios de avaliação gerados

Esta pasta é criada automaticamente pelo sistema e armazena os **resultados das avaliações comparativas** entre as três abordagens de triagem.

> Os arquivos nesta pasta são gerados em tempo de execução por `python -m src.evaluation`. Esta pasta **contém as execuções realizadas durante o desenvolvimento e a execução de referência da monografia** (ver a seção abaixo); novas execuções são acrescentadas sem sobrescrever as anteriores.

---

## Como os arquivos são gerados?

Ao executar o comando de avaliação:

```bash
python -m src.evaluation
```

O sistema cria automaticamente 4 arquivos com o mesmo timestamp no nome, para que execuções consecutivas não se sobrescrevam:

---

## Estrutura dos arquivos gerados

Para cada execução de avaliação, são criados quatro arquivos com timestamp `YYYYMMDD_HHMMSS`:

### `evaluation_raw_<timestamp>.json`
Dados brutos completos de todas as execuções — cada caso, cada abordagem, cada resultado. Arquivo grande, útil para análises detalhadas ou reprocessamento.

### `evaluation_per_case_<timestamp>.csv`
Tabela com uma linha para cada combinação de (caso × abordagem). Colunas incluem o texto do relato, a resposta esperada (gabarito), a resposta predita e se cada campo foi acertado. Fácil de abrir no Excel ou Google Sheets para análise manual.

### `evaluation_summary_<timestamp>.json`
Resumo das métricas agregadas por abordagem: F1 de urgência, prioridade, categoria e equipe; taxa de subestimação de casos críticos; taxa de encaminhamento para revisão humana; latência média; e mais. Este é o arquivo principal para comparação entre abordagens.

### `evaluation_summary_<timestamp>.csv`
Versão tabular do resumo — uma linha por abordagem, uma coluna por métrica. Ideal para incluir diretamente em tabelas da monografia.

---

## Por que o timestamp no nome?

Para preservar o histórico. Cada vez que você rodar a avaliação (com o LLM aquecido, com modelo diferente, com dataset ampliado), os resultados anteriores não são perdidos.

---

## Execução de referência da monografia

Os números do Capítulo 4 e do Apêndice D da monografia vêm da execução **`20261103_014254`** (`evaluation_raw_`, `evaluation_per_case_` e `evaluation_summary_` com esse timestamp; análise em `analise_estatistica_20261103_014254.json`): 3 abordagens, 100 casos, `qwen3:0.6b`, temperatura 0, semente 42, janela de contexto de 4.096 tokens (`num_ctx`), raciocínio ativado de forma explícita e saída restrita a um esquema JSON, com a base de 21 regras, a revisão humana combinada por disjunção e o casamento por palavra inteira dos termos de até 3 letras. Cada resultado grava a resposta completa do modelo (`resposta_llm_bruta`) e o texto do raciocínio (`raciocinio_llm`).

A execução de referência **anterior às correções do formato de saída** é a **`20261028_115033`** (base de 20 regras, `format="json"`, contexto no padrão do Ollama, resposta gravada só nas falhas), usada na Tabela 13 da monografia para medir o efeito das correções.

A **primeira execução**, com a versão inicial da base de regras (18 regras, revisão combinada por prioridade), é a **`20261016_100014`**, citada na monografia para comparação. As execuções completas `20261017_023149`, `20261017_023150` (arquivos duplicados, gravados com 1 s de diferença) e `20261018_203650` foram feitas nas mesmas condições dela e reproduzem exatamente as classificações e o consumo de tokens; só a latência varia (a das regras, por exemplo, ficou entre 7,4 e 28,0 ms). A execução `20261028_115033` reproduziu, caso a caso, as classificações do LLM puro e o consumo de tokens das duas abordagens com modelo obtidos na `20261016_100014`.

O experimento complementar de hardware (Tabela 7 da monografia) está em `experimento_cpu_gpu_20261102_023354.csv` (dez relatos), gerado por `scripts/experimento_cpu_gpu.py`; `experimento_cpu_gpu_20261028_103424.csv` é a rodada preliminar com três relatos.

Execuções complementares de 01 a 03/11/2026 (todas com 21 regras, incluindo a RULE-021 da PMTA). O arquivo bruto de cada uma registra a configuração do modelo em `config_llm`. As de 03/11 usam a configuração corrigida (esquema JSON, `num_ctx` e registro das respostas); as de 02/11, a anterior:

| Execução | O que é |
|---|---|
| `20261101_231417` | Só regras, 100 casos: confirma que a RULE-021 não altera o conjunto principal (saídas idênticas às da `20261028_115033`) |
| `20261101_231430` | Só regras, 10 alarmes simulados (`datasets/alarm_cases.json`), conferência antes da rodada noturna |
| `20261102_002222` | Alarmes simulados, três abordagens, configuração anterior |
| `20261102_004216` | 100 casos, LLM puro e híbrida sem o modo de raciocínio, configuração anterior |
| `20261102_004434` | Alarmes simulados, LLM puro e híbrida sem o modo de raciocínio, configuração anterior |
| `20261102_065123` | Conjunto de validação, três abordagens, configuração anterior; análise em `analise_estatistica_20261102_065123.json` |
| `20261103_014254` | **Execução de referência** (Capítulo 4) |
| `20261103_025551` | Conjunto de validação (`datasets/holdout_cases.json`), 100 casos novos, três abordagens (Tabela 5); análise em `analise_estatistica_20261103_025551.json` |
| `20261103_030330` | Alarmes simulados, três abordagens (Tabela 14) |
| `20261103_032922` | 100 casos, três abordagens sem o modo de raciocínio, `OLLAMA_REASONING=false` (Tabela 8) |
| `20261103_033209` | Alarmes simulados, três abordagens sem o modo de raciocínio (Tabela 14) |

A rodada de 02/11 foi executada por `scripts/rodada_noturna.ps1`, com registro em `rodada_noturna.log`; a de 03/11, por um único comando que encadeou as cinco execuções. Nas três execuções de 03/11 com 100 casos ou com os alarmes, a abordagem por regras reproduziu exatamente os resultados das execuções correspondentes de 02/11 e de 28/10.

As demais execuções são anteriores ou parciais e **não** devem ser usadas para comparação:

| Execuções | O que são |
|---|---|
| `20261012_*`, `20261013_*` (exceto abaixo) | Testes durante o desenvolvimento, com 20, 50 ou 100 casos e com apenas uma ou duas abordagens |
| `20261013_013520`, `20261013_022829` | Três abordagens, 100 casos, mas com versão anterior do código (F1 do LLM puro diferente) |
| `20261013_111110` | Classificação igual à final, porém sem registro de tokens |
| `20261016_030318` | Classificação e tokens iguais à referência; latência ligeiramente diferente |
| `20261017_012121`, `20261017_015851` | Execuções interrompidas: só regras, e regras + LLM puro (sem a híbrida) |
| `20261016_2316*`, `20261016_2324*`, `20261016_2330*`, `20261018_185715`, `20261018_190055`, `20261018_190353` | Execuções parciais de verificação (10 ou 20 casos) |
| `20261027_*` | Testes com 5 casos e uma execução completa (`20261027_152450`) anterior aos ajustes finais da base de regras |
| `20261028_094847`, `20261028_103605` | Prévias só da abordagem por regras durante os ajustes da base de regras |

### Reproduzir as tabelas estatísticas da monografia

```bash
python scripts/analise_estatistica.py results/evaluation_raw_20261103_014254.json
# opcional: gravar o resultado em JSON
python scripts/analise_estatistica.py results/evaluation_raw_20261103_014254.json --saida results/analise_estatistica_20261103_014254.json
# conjunto de validação
python scripts/analise_estatistica.py results/evaluation_raw_20261103_025551.json --dataset datasets/holdout_cases.json
```

O script calcula F1 ponderado com IC 95% por *bootstrap* (10.000 amostras, semente 42), diferenças pareadas com teste exato de McNemar (com ajuste de Holm sobre os 15 testes da Tabela 3), subestimação de casos críticos com IC de Clopper-Pearson, métricas de revisão humana, sensibilidade do rótulo de equipe e verificabilidade das evidências (Tabelas 2, 3, 6, 9 e 11 da monografia; com `--dataset datasets/holdout_cases.json`, os dados do conjunto de validação da Tabela 5). Requer `scipy` (já em `requirements.txt`).

---

## Aviso sobre interpretação dos resultados

Os relatórios incluem um aviso: as métricas foram calculadas em um dataset sintético de 100 casos. Não extrair conclusões operacionais sem considerar as limitações documentadas em `datasets/README.md`.
