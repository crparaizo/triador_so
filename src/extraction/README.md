# src/extraction/ — Extração de informações do relato

Esta pasta contém os **extratores**: módulos que leem um texto livre de relato de ocorrência e identificam as informações estruturadas relevantes (qual ativo foi mencionado, quais sintomas foram descritos, se há risco de segurança, etc.).

Há dois extratores com abordagens diferentes:

---

## Arquivos

### `keyword_extractor.py` — Extrator por palavras-chave
Abordagem **determinística**: procura termos específicos no texto usando comparação de strings e listas de palavras-chave do `categories.yaml`.

**Como funciona:**
1. Normaliza o texto (remove acentos, converte para minúsculas) para um matching mais robusto
2. Varre o texto em busca de:
   - Tags de ativos (ex: "BOMB-001") e nomes (ex: "bomba de água")
   - Palavras de sintomas de cada categoria (ex: "vazamento", "vibração", "ruptura")
   - Palavras de impacto na produção (ex: "linha parada", "produção interrompida")
   - Palavras de risco de segurança (ex: "incêndio", "explosão", "choque")
   - Expressões de urgência (ex: "urgente", "imediato", "emergência")
3. Para cada campo identificado, registra o **trecho exato do texto** como evidência

**Vantagens**: rápido, previsível, sempre produz o mesmo resultado para a mesma entrada, não depende de conexão com serviço externo.  
**Limitações**: só reconhece termos da lista; não entende sinônimos fora do vocabulário, erros de escrita graves ou frases em contexto diferente.

Método adicional: `detect_category(texto)` — identifica a categoria de falha mais provável (Mecânica, Elétrica, etc.) com base nas palavras-chave encontradas.

### `llm_extractor.py` — Extrator via LLM
Abordagem **baseada em modelo de linguagem**: envia o texto para o Ollama com um prompt em português solicitando a extração em formato JSON.

**Como funciona:**
1. Monta um prompt que instrui o LLM a extrair apenas o que está no texto ("não invente dados")
2. Envia ao `ChatOllama` (modelo configurado no `.env`)
3. Recebe a resposta e tenta extrair o JSON com um **parser defensivo em três passos**:
   - Passo 1: `json.loads()` direto
   - Passo 2: regex para encontrar um bloco `{...}` caso o LLM tenha adicionado texto extra
   - Passo 3: fallback — retorna `ExtractedInfo` vazio com `erro_parse` preenchido
4. Em caso de falha de conexão: tenta novamente até `MAX_RETRIES_LLM` vezes

**Vantagens**: entende linguagem natural, sinônimos, paráfrases e contexto; mais tolerante a variações de escrita.  
**Limitações**: mais lento, pode variar entre execuções, pode "alucidar" (inventar campos), depende do Ollama estar em execução.

> **Importante**: o `LLMExtractor` instancia a conexão com o Ollama **somente dentro do método `extract()`**, nunca no `__init__`. Isso garante que importar o módulo não cause erros mesmo sem o Ollama rodando.

### `__init__.py`
Marca a pasta como submódulo Python.
