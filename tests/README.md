# tests/ — Testes automatizados

Esta pasta contém os **testes automatizados** do projeto. Eles verificam que cada parte do sistema funciona corretamente e garantem que uma mudança no código não quebra algo que funcionava antes.

> **Importante**: todos os testes rodam **sem precisar do Ollama**. O modelo de linguagem é simulado (mockado) nos testes — você pode verificar a integridade do código mesmo sem GPU ou conexão com o modelo.

---

## Como executar

```bash
# Rodar todos os testes
pytest tests/ -v

# Rodar apenas um arquivo de testes
pytest tests/test_rules_engine.py -v

# Ver só os testes que falharam
pytest tests/ -v --tb=short
```

O resultado esperado é `183 passed` em aproximadamente 7 segundos.

---

## Arquivos

### `conftest.py` — Dados compartilhados pelos testes
Define **fixtures** (objetos de exemplo reutilizáveis) que todos os arquivos de teste podem usar: um `TriageResult` de exemplo, um `Asset`, uma `KnowledgeBase` pequena, etc. Evita repetição de código nos testes.

---

### Testes por módulo

| Arquivo | O que testa |
|---------|------------|
| `test_schemas.py` | Validação dos modelos de dados Pydantic (TriageResult, Asset, Team, etc.) |
| `test_data_loader.py` | Carregamento e validação dos YAMLs de ativos, equipes e categorias |
| `test_dataset.py` | Integridade do dataset sintético (100 casos, distribuição, campos válidos) |
| `test_rules_definitions.py` | Carregamento das regras de `rules.yaml` e validação de sua estrutura |
| `test_keyword_extractor.py` | Extração por palavras-chave: detecção de ativos, sintomas, risco, impacto |
| `test_rules_engine.py` | Motor de regras: quais regras disparam, precedência, resultado final |
| `test_llm_extractor.py` | Extrator LLM: parser defensivo, tratamento de JSON malformado, fallbacks |
| `test_llm_only.py` | Pipeline LLM puro: mapeamento de enums, fallback para Ollama indisponível |
| `test_context_enricher.py` | Enriquecimento de contexto: busca de ativos por tag, nome e localização |
| `test_hybrid.py` | Pipeline híbrido: fluxo completo, fallback LLM → palavras-chave |
| `test_evaluation.py` | Módulo de avaliação: métricas, runner, geração de relatórios |
| `test_interface.py` | Gerenciador de sessões: salvar, carregar e limpar histórico |

---

## Por que os testes usam "mocks"?

Nos testes do LLM (`test_llm_extractor.py`, `test_llm_only.py`, `test_hybrid.py`), o modelo de linguagem real é substituído por um objeto simulado que retorna respostas pré-definidas. Isso serve para:

1. **Velocidade**: um teste real com LLM demora segundos; com mock, milissegundos
2. **Reprodutibilidade**: o mock sempre retorna a mesma resposta, o LLM real pode variar
3. **Independência**: os testes funcionam sem Ollama instalado

Os mocks não testam a qualidade das respostas do LLM — apenas que o sistema processa corretamente qualquer resposta que o LLM possa dar (inclusive respostas malformadas ou erros de conexão).
