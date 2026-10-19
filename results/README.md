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

Os números do Capítulo 4 e do Apêndice D da monografia vêm da execução **`20261016_100014`** (`evaluation_raw_`, `evaluation_per_case_` e `evaluation_summary_` com esse timestamp): 3 abordagens, 100 casos, `qwen3:0.6b`, temperatura 0 e semente 42.

As execuções completas `20261017_023149`, `20261017_023150` (arquivos duplicados, gravados com 1 s de diferença) e `20261018_203650` foram feitas nas mesmas condições e reproduzem exatamente as classificações e o consumo de tokens; só a latência varia (a das regras, por exemplo, ficou entre 7,4 e 28,0 ms).

As demais execuções são anteriores ou parciais e **não** devem ser usadas para comparação:

| Execuções | O que são |
|---|---|
| `20261012_*`, `20261013_*` (exceto abaixo) | Testes durante o desenvolvimento, com 20, 50 ou 100 casos e com apenas uma ou duas abordagens |
| `20261013_013520`, `20261013_022829` | Três abordagens, 100 casos, mas com versão anterior do código (F1 do LLM puro diferente) |
| `20261013_111110` | Classificação igual à final, porém sem registro de tokens |
| `20261016_030318` | Classificação e tokens iguais à referência; latência ligeiramente diferente |
| `20261017_012121`, `20261017_015851` | Execuções interrompidas: só regras, e regras + LLM puro (sem a híbrida) |
| `20261016_2316*`, `20261016_2324*`, `20261016_2330*`, `20261018_185715`, `20261018_190055`, `20261018_190353` | Execuções parciais de verificação (10 ou 20 casos) |

### Reproduzir as tabelas estatísticas da monografia

```bash
python scripts/analise_estatistica.py results/evaluation_raw_20261016_100014.json
# opcional: gravar o resultado em JSON
python scripts/analise_estatistica.py results/evaluation_raw_20261016_100014.json --saida results/analise_20261016_100014.json
```

O script calcula F1 ponderado com IC 95% por *bootstrap* (10.000 amostras, semente 42), diferenças pareadas com teste exato de McNemar, subestimação de casos críticos com IC de Clopper-Pearson, métricas de revisão humana (com e sem disjunção), sensibilidade do rótulo de equipe e verificabilidade das evidências (Tabelas 2, 3, 5, 6 e 8 da monografia). Requer `scipy` (já em `requirements.txt`).

---

## Aviso sobre interpretação dos resultados

Os relatórios incluem um aviso: as métricas foram calculadas em um dataset sintético de 100 casos. Não extrair conclusões operacionais sem considerar as limitações documentadas em `datasets/README.md`.
