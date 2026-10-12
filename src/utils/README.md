# src/utils/ — Utilitários compartilhados

Esta pasta contém funções auxiliares **usadas por mais de um módulo** do sistema. O objetivo é evitar duplicação de código — ao invés de cada módulo ter sua própria versão da mesma função, todos importam daqui.

---

## Arquivos

### `parsers.py` — Parser defensivo de JSON de LLMs
Contém a função `parsear_json_llm(texto_resposta: str)`, usada tanto pelo `LLMExtractor` (extração) quanto pelo `run_llm_only` (classificação).

**O problema que resolve:** modelos de linguagem nem sempre retornam JSON limpo. Às vezes envolvem a resposta em blocos de markdown (` ```json ... ``` `), às vezes adicionam texto explicativo antes ou depois, e às vezes o JSON está mal formado.

**Como funciona — três tentativas em ordem:**
1. `json.loads()` direto — funciona quando o LLM respeitou a instrução de retornar JSON puro
2. Regex `{.*}` com busca em todo o texto — extrai o bloco JSON mesmo que haja texto ao redor
3. Retorna erro descritivo — nunca lança exceção; o chamador recebe `(None, "mensagem de erro")`

**Retorno:** tupla `(dict, None)` em caso de sucesso, ou `(None, "mensagem de erro")` em caso de falha.

A função nunca interrompe o fluxo do programa com uma exceção — o tratamento de erro fica a cargo do módulo que a chama.

### `__init__.py`
Marca a pasta como submódulo Python.
