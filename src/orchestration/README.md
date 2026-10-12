# src/orchestration/ — Integração com LangChain

Esta pasta contém a integração dos três pipelines com o **LangChain**, o framework de orquestração usado no projeto.

---

## Para que serve?

O LangChain é uma biblioteca Python que oferece abstrações para construir pipelines com modelos de linguagem. Neste projeto, o código principal de cada abordagem vive em `src/approaches/`, e esta pasta simplesmente **envolve** cada pipeline numa estrutura LangChain chamada `RunnableSequence`.

Isso permite que as três abordagens sejam chamadas de forma uniforme:

```python
chain = build_hybrid_chain()
resultado = chain.invoke({"texto": "Relato de ocorrência..."})
```

---

## Arquivos

### `chains.py` — As três chains LangChain

Define três funções que retornam `Runnable` (a estrutura do LangChain):

| Função | Abordagem |
|--------|-----------|
| `build_rules_chain()` | Envolve `run_rules_only` |
| `build_llm_chain()` | Envolve `run_llm_only` |
| `build_hybrid_chain()` | Envolve `run_hybrid` |

Cada função usa `RunnableLambda` para transformar uma função Python num objeto LangChain. A entrada é sempre `{"texto": str}` e a saída é sempre `TriageResult`.

A lógica de negócio real fica em `src/approaches/` — aqui há apenas a "embalagem" LangChain.

### `__init__.py`
Marca a pasta como submódulo Python.

---

## Por que usar LangChain aqui?

O projeto foi construído com LangChain como requisito da monografia, para demonstrar integração com o ecossistema. Em cenários mais simples, chamar `run_hybrid(texto)` diretamente seria equivalente — o `RunnableLambda` é uma wrapper fina sem lógica adicional.
