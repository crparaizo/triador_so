# src/data/ — Acesso e carregamento dos dados

Esta pasta contém o código que **lê, valida e disponibiliza** os dados do sistema para os demais módulos. Ela faz a ponte entre os arquivos YAML da pasta `data/` (na raiz) e o restante do código.

---

## Arquivos

### `loader.py` — Carregador dos dados de referência
Funções que leem os arquivos YAML e os transformam em objetos Pydantic validados:

- `load_knowledge_base()` → lê `assets.yaml` e `teams.yaml`, retorna um objeto `KnowledgeBase` com os 18 ativos e 6 equipes
- `load_categories()` → lê `categories.yaml`, retorna um dicionário com as categorias de falha e suas palavras-chave

Ambas usam **cache** (`lru_cache`): os arquivos são lidos do disco apenas uma vez por execução. Chamadas subsequentes retornam o mesmo objeto já carregado, sem re-ler o arquivo.

Se um arquivo YAML estiver malformado ou faltando campos obrigatórios, um erro descritivo é lançado imediatamente (não silenciosamente).

### `dataset_loader.py` — Carregador do dataset de avaliação
Carrega e valida o dataset sintético de 100 casos (`datasets/synthetic_cases.json`):

- `DatasetCase`: modelo Pydantic que valida cada caso (campos obrigatórios, valores válidos de enums, restrições por tipo)
- `load_dataset(path=None)` → lê o JSON, valida todos os casos e retorna uma lista de `DatasetCase`

Validações realizadas:
- IDs únicos (sem duplicatas)
- Valores de urgência, prioridade e categoria dentro dos enums válidos
- Casos `ALTA_CRITICIDADE` têm obrigatoriamente `urgencia=IMEDIATA` e `requer_revisao_humana=True`
- Referências de paráfrases apontam para IDs existentes

### `context_enricher.py` — Enriquecedor de contexto
Recebe o resultado da extração (quais informações foram identificadas no relato) e busca informações complementares na base de conhecimento local:

- `enrich_context(extracted, kb, cats, categoria)` → tenta encontrar o ativo mencionado por:
  1. Tag exata (ex: "BOMB-001")
  2. Substring do nome (ex: "bomba de água")
  3. Localização (ex: "Setor A")
- Monta a lista de equipes candidatas (equipe responsável pelo ativo + equipe padrão da categoria)
- Retorna um `ContextData` com o ativo encontrado (ou `None`) e a fonte do enriquecimento

Este módulo é usado tanto pelo pipeline híbrido quanto pelo pipeline de regras puras — evitando duplicação de código.

### `__init__.py`
Marca a pasta como submódulo Python.
