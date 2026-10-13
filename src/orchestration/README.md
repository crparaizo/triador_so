# src/orchestration/ — Orquestração com LangChain (LCEL)

Esta pasta define como os três pipelines de triagem são compostos com o **LangChain Expression Language (LCEL)**, a forma declarativa do LangChain de encadear componentes executáveis (`Runnable`). Cada etapa do pipeline é um nó com nome próprio, e os nós são ligados com o operador `|` (sequência), `RunnablePassthrough.assign` (acrescenta uma chave ao estado) e `RunnableParallel` (executa ramos independentes ao mesmo tempo).

> Protótipo acadêmico. Não usar em ambiente industrial real sem validação por especialistas.

---

## Uso

A interface pública é a mesma para as três abordagens:

```python
from src.orchestration.chains import build_hybrid_chain

chain = build_hybrid_chain()
resultado = chain.invoke({"texto": "Relato de ocorrência..."})  # → TriageResult
```

`run_rules_only(texto, categoria_ref=None)`, `run_llm_only(texto)` e `run_hybrid(texto)` (em `src/approaches/`) continuam disponíveis e apenas chamam `invoke` no fluxo correspondente.

| Builder | Fluxo (nome do Runnable) | Entrada |
|---------|--------------------------|---------|
| `build_rules_chain()` | `fluxo_regras` | `{"texto"}` (ignora `categoria_ref`) |
| `build_rules_catref_chain()` | `fluxo_regras_categoria_ref` | `{"texto", "categoria_ref"}` |
| `build_llm_chain()` | `fluxo_llm` | `{"texto"}` |
| `build_hybrid_chain()` | `fluxo_hibrido` | `{"texto"}` |

Construir qualquer fluxo não abre conexão com o Ollama; a conexão só ocorre quando o nó que chama o modelo executa.

---

## Arquivos

### `triage_flow.py` — Fábrica comum dos fluxos

Define a **topologia** dos fluxos e os nomes dos nós. Não contém lógica de triagem: as funções de cada etapa ficam nos módulos de `src/approaches/` e são passadas para a fábrica. Isso mantém os loaders e extratores resolvidos pelos nomes globais de cada módulo, o que permite substituí-los nos testes com `mocker.patch("src.approaches.hybrid.LLMExtractor")`, por exemplo.

Principais elementos:

- `compor_fluxo_triagem(...)`: monta o fluxo usado **tanto pelas regras quanto pelo híbrido**. Os dois fluxos têm o mesmo grafo e diferem apenas no nó de extração.
- `envolver_com_falha_segura(...)`: acrescenta o envelope de falha segura (usado pelos três fluxos).
- `extracao_com_fallback(primaria, fallback)`: nó de extração do híbrido com fallback nativo.
- `FalhaExtracaoLLM`: exceção que converte o `erro_parse` do `LLMExtractor` em falha visível para o LangChain.
- `obter_nucleo(fluxo)`: devolve o núcleo de um fluxo, usado para exportar o grafo.

### `chains.py` — Builders públicos e exportação do grafo

Os quatro `build_*_chain()` acima, mais:

- `gerar_diagramas_mermaid()` → `{"regras", "hibrido", "llm"}` com o texto Mermaid de cada núcleo (`get_graph().draw_mermaid()`).
- `salvar_diagramas_mermaid(caminho=None)` → grava `docs/fluxos_langchain.md`.

### `__main__.py`

Permite regenerar os diagramas pela linha de comando:

```bash
python -m src.orchestration
```

O arquivo `docs/fluxos_langchain.md` é gerado; não deve ser editado à mão. Um teste (`tests/test_orchestration.py`) falha se o arquivo estiver desatualizado em relação ao código. A exportação usa apenas `langchain_core`; nenhuma dependência foi adicionada ao `requirements.txt`.

### `__init__.py`

Expõe os builders com importação sob demanda (evita importação circular entre `orchestration` e `approaches`).

---

## Composição dos fluxos

O estado é um dicionário que passa de nó em nó. Cada `assign` acrescenta uma chave sem apagar as anteriores: `dados` (base de conhecimento, categorias e regras), `extracao`, `categoria`, `contexto`, `regras`. O contrato completo está na docstring de `triage_flow.py`.

**Regras e híbrido (mesma estrutura):**

```
preparacao_entrada
| triagem_com_falha_segura(                                   ← RunnableWithFallbacks
      carregamento_dados
    | <extrator>  ∥  deteccao_categoria                       ← RunnableParallel
    | enriquecimento_contexto
    | motor_regras_producao                                   ← apply_rules, um único nó
    | montagem_resultado
  , fallback = resultado_seguro)

<extrator> nas regras:  extracao_palavras_chave
<extrator> no híbrido:  extracao_llm_com_fallback
                        = extracao_llm, com fallback para extracao_palavras_chave
```

**LLM puro:**

```
preparacao_entrada
| triagem_com_falha_segura(
      preparacao_prompt → chamada_llm → parser_defensivo → montagem_resultado
  , fallback = resultado_seguro)
```

O nó `chamada_llm` instancia o `ChatOllama` em tempo de execução e envia o prompt como texto. Ele não é ligado diretamente com `| ChatOllama(...)` porque o runner de avaliação constrói os fluxos na importação, e os testes substituem a classe `ChatOllama` por um mock.

### Por que o motor de regras é um único nó

As 18 regras de produção continuam declaradas em `data/rules.yaml` e são avaliadas por `apply_rules` (`src/rules/engine.py`), que trata prioridade entre regras e resolução de conflitos. Transformar cada regra em um `Runnable` espalharia essa lógica pelo grafo e tiraria do especialista a possibilidade de editar as regras em um arquivo legível. O LCEL organiza as etapas; o conhecimento simbólico permanece no YAML.

### Fallbacks

Os dois níveis de tratamento de falha usam `RunnableWithFallbacks` do LangChain:

| Nível | Onde | Quando aciona | Efeito |
|-------|------|---------------|--------|
| Extração | `extracao_llm_com_fallback` (híbrido) | `LLMExtractor` retorna `erro_parse` (convertido em `FalhaExtracaoLLM`) ou lança exceção | `KeywordExtractor` assume; evidência `extracao_fallback`; revisão humana obrigatória com motivo "Falha na extração LLM — resultado baseado em extrator por palavras-chave. Revisar manualmente." |
| Fluxo | `triagem_com_falha_segura` (todos) | Qualquer exceção no núcleo | `resultado_seguro`: urgência, prioridade e categoria `DESCONHECIDA`, confiança 0,0, revisão humana com o nome da exceção no motivo |

A latência (`latencia_ms`) é medida a partir do nó `preparacao_entrada` até a montagem do resultado (ou do resultado seguro), portanto inclui o custo da própria orquestração LCEL.

### Limitações conhecidas

- No híbrido, extração e detecção de categoria rodam em threads paralelas; a ordem das linhas de log pode se intercalar.
- Se a extração LLM e o fallback por palavras-chave falharem ao mesmo tempo, o resultado seguro mostra a classe do erro do LLM (o LangChain relança o primeiro erro).
- A orquestração LCEL tem custo próprio (criação de threads dos `RunnableParallel` e gerenciamento de callbacks). Na avaliação do fluxo por regras (100 casos, Windows, Python 3.14), a mediana de `latencia_ms` passou de 2,2 ms (função única) para 19,2 ms (fluxo LCEL), sem nenhuma mudança nas classificações. Esse acréscimo é pequeno frente aos dezenas de segundos de uma chamada ao LLM local, mas deve ser considerado ao comparar latências entre versões.
