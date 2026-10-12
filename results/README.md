# results/ — Relatórios de avaliação gerados

Esta pasta é criada automaticamente pelo sistema e armazena os **resultados das avaliações comparativas** entre as três abordagens de triagem.

> Os arquivos nesta pasta são gerados em tempo de execução. A pasta está vazia no repositório — os relatórios surgem ao rodar `python -m src.evaluation`.

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

## Aviso sobre interpretação dos resultados

Os relatórios incluem um aviso: as métricas foram calculadas em um dataset sintético de 100 casos. Não extrair conclusões operacionais sem considerar as limitações documentadas em `datasets/README.md`.
