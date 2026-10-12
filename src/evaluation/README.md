# src/evaluation/ — Avaliação e métricas comparativas

Esta pasta contém o código que **avalia quantitativamente** as três abordagens de triagem sobre o dataset sintético de 100 casos.

---

## Como usar

```bash
# Avaliar as três abordagens (pode demorar vários minutos por causa do LLM)
python -m src.evaluation

# Avaliar só a abordagem de regras (rápido, não precisa do Ollama)
python -m src.evaluation --approaches regras

# Ver todas as opções
python -m src.evaluation --help
```

Os arquivos de resultado são salvos automaticamente em `results/`.

---

## Arquivos

### `metrics.py` — Cálculo das métricas
Funções que calculam as métricas de desempenho, usando `scikit-learn` internamente.

Cada função tem uma docstring explicando sua definição e limitações:

| Função | O que mede |
|--------|-----------|
| `classification_report_dict` | Precisão, revocação e F1 por classe (urgência, prioridade, etc.) |
| `confusion_matrix_dict` | Matriz de confusão — quais valores foram confundidos com quais |
| `unsupported_fields_rate` | Taxa de campos preenchidos sem evidência direta no texto (proxy de alucinação) |
| `critical_underestimation_rate` | % de casos P1/IMEDIATA classificados como menos urgentes |
| `human_review_rate` | % de casos sinalizados para revisão humana |
| `robustness_score` | Consistência entre casos canônicos e suas paráfrases |
| `latency_stats` | Média, desvio padrão, mínimo e máximo de latência |
| `per_approach_summary` | Consolida todas as métricas acima para uma abordagem |

> As métricas são calculadas comparando contra o **gabarito** do dataset — nenhum LLM é usado para avaliar o outro.

### `runner.py` — Executor da avaliação
Responsável por **rodar** os três pipelines sobre os 100 casos do dataset:

- `evaluate_approach(abordagem, casos)` → executa um único pipeline em todos os casos, com timeout por caso
- `run_evaluation(abordagens, dataset_path)` → executa todas as abordagens selecionadas e retorna os resultados consolidados

Em caso de timeout ou erro num caso específico, registra o erro e continua com os demais — a avaliação não para por falha individual.

### `report.py` — Geração dos relatórios
Transforma os resultados brutos em arquivos legíveis:

- `save_evaluation_report(eval_data)` → gera os 4 arquivos em `results/` (JSON bruto, CSV por caso, JSON de resumo, CSV de resumo)
- `print_summary_table(summary)` → exibe uma tabela formatada no terminal com as métricas principais e um aviso sobre as limitações do dataset sintético

### `__main__.py` — Ponto de entrada da CLI
Permite executar o módulo diretamente com `python -m src.evaluation`. Aceita argumentos de linha de comando:
- `--approaches regras llm hibrido` — escolher quais abordagens avaliar
- `--dataset <caminho>` — usar um dataset diferente do padrão

Em caso de erro de Ollama, exibe mensagem amigável (sem stack trace técnico).

### `__init__.py`
Exporta as funções principais do módulo.
