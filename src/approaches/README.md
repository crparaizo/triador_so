# src/approaches/ — As três abordagens de triagem

Esta pasta contém os **três pipelines completos de triagem** que são comparados no trabalho. Cada arquivo implementa uma abordagem diferente, todas recebendo o mesmo texto como entrada e retornando um `TriageResult` como saída.

Cada pipeline é um **fluxo LCEL** (LangChain Expression Language): uma cadeia de nós `Runnable` com nomes próprios, montada por `build_*_flow()`. As funções `run_*` apenas chamam `build_*_flow().invoke(...)`. A estrutura comum dos fluxos (envelope de falha segura, paralelismo entre extração e categoria) é definida em `src/orchestration/triage_flow.py`; as funções que executam cada nó ficam aqui. Ver `src/orchestration/README.md` e os diagramas gerados por `python -m src.orchestration` (`docs/fluxos_langchain.md`).

---

## Abordagens

### `rules_only.py` — Abordagem por regras puras

**Função principal:** `run_rules_only(texto: str, categoria_ref: str | None = None) → TriageResult`
**Fluxo LCEL:** `build_rules_flow()` (`fluxo_regras`). Quando `categoria_ref` é informada, `run_rules_only` usa `build_rules_flow(usar_categoria_ref=True)` (`fluxo_regras_categoria_ref`), de modo que o nome no trace corresponde ao cenário executado.

Usa **apenas** o extrator por palavras-chave e o motor de regras. Não faz nenhuma chamada ao LLM.

Nós:
1. `preparacao_entrada` — marca o início da medição de latência
2. `carregamento_dados` — base de ativos/equipes, categorias e regras
3. `extracao_palavras_chave` ∥ `deteccao_categoria` — em paralelo: o extrator identifica sintomas, ativo, riscos e impacto; a categoria é detectada por palavras-chave (ou fixada por `categoria_ref` no cenário-diagnóstico)
4. `enriquecimento_contexto` — busca o ativo e a equipe na base local
5. `motor_regras_producao` — o motor de regras inteiro, um único nó, classifica urgência, prioridade e equipe
6. `montagem_resultado` — `TriageResult` com `abordagem=REGRAS`

**Ponto forte**: rápido, previsível, totalmente auditável  
**Ponto fraco**: limitado ao vocabulário das listas de palavras-chave; paráfrases e erros de escrita podem passar despercebidos

---

### `llm_only.py` — Abordagem por LLM puro

**Função principal:** `run_llm_only(texto: str) → TriageResult`
**Fluxo LCEL:** `build_llm_flow()`

O LLM faz tudo em um **único prompt**: extração, classificação e encaminhamento. O prompt inclui a lista completa de ativos e equipes como contexto.

Nós:
1. `preparacao_entrada` — marca o início e trata relato vazio
2. `preparacao_prompt` — monta o prompt com contexto de ativos e equipes e a lista exata de nomes de equipe que o modelo deve copiar em `equipe_sugerida`
3. `chamada_llm` — instancia o `ChatOllama` em tempo de execução, com `format="json"` (o Ollama restringe a geração a JSON válido, necessário para modelos pequenos como o `qwen3:0.6b`), e envia o prompt
4. `parser_defensivo` — extrai o JSON da resposta (json direto → regex → erro)
5. `montagem_resultado` — mapeia os valores para os enums do sistema; `abordagem=LLM` e `regras_acionadas=[]` (sempre vazio). `evidencias` que não sejam objeto são descartadas. JSON inválido gera resultado de revisão com motivo "Falha na classificação: ..."

**Validação da equipe (`_mapear_equipe_valida`):** o nome retornado pelo modelo só é aceito se coincidir com uma equipe cadastrada (comparação sem acentos e sem diferenciar maiúsculas) ou se contiver o nome completo de exatamente uma equipe, como palavras inteiras (ex.: "Manutenção Mecânica Turno A" → "Manutenção Mecânica"). Fragmentos ("TI", "MECANICA"), tags de ativos e valores com duas equipes resultam em "Revisão Manual".

**Ponto forte**: mais flexível com linguagem natural, paráfrases e variações de vocabulário  
**Ponto fraco**: mais lento, não-determinístico, pode "alucinar" (inventar campos sem evidência), decisões não são auditáveis por regras explícitas

---

### `hybrid.py` — Abordagem híbrida ⭐

**Função principal:** `run_hybrid(texto: str) → TriageResult`
**Fluxo LCEL:** `build_hybrid_flow()`

A abordagem principal do trabalho: **o LLM extrai, as regras classificam**. O grafo é o mesmo do fluxo por regras; muda apenas o nó de extração.

Nós:
1. `preparacao_entrada` — marca o início e trata relato vazio
2. `carregamento_dados` — base local, categorias, regras e instância do `LLMExtractor`
3. `extracao_llm_com_fallback` ∥ `deteccao_categoria` — em paralelo:
   - **LLM extrai** informações estruturadas do texto (nó `extracao_llm`, sem classificar urgência ou prioridade)
   - se a extração falhar (`erro_parse` ou exceção), o **fallback nativo do LangChain** (`RunnableWithFallbacks`) aciona `extracao_palavras_chave`, registra a evidência `extracao_fallback` e torna a revisão humana obrigatória
   - a categoria é detectada de forma determinística por palavras-chave
4. `enriquecimento_contexto` — busca o ativo na base local
5. `motor_regras_producao` — **regras classificam** urgência, prioridade e equipe
6. `montagem_resultado` — consolida evidências (LLM + `ativo_encontrado` + `regras_classificacao`), campos sem suporte e revisão humana (fallback ou confiança de extração < 0,4); `abordagem=HIBRIDO`

O código usa comentários `# LLM extrai` e `# Regras classificam` para marcar visualmente a separação de responsabilidades.

**Ponto forte**: combina a flexibilidade do LLM na extração com a previsibilidade e auditabilidade das regras na classificação  
**Ponto fraco**: depende do LLM para extração; se o modelo não estiver disponível, cai para palavras-chave

---

## `__init__.py`
Marca a pasta como submódulo Python e exporta as três funções principais.

---

## Nota sobre tratamento de erros

As três abordagens têm tratamento defensivo: **nunca lançam exceção para o chamador**. O núcleo de cada fluxo fica dentro do envelope `triagem_com_falha_segura` (`RunnableWithFallbacks`); se qualquer nó lançar exceção, o fallback `resultado_seguro` devolve um `TriageResult` com `requer_revisao_humana=True` e `motivo_revisao` com o nome da exceção ("Erro interno no processamento (...)" nas regras e no híbrido; "LLM indisponível: ..." no LLM puro). O erro é registrado nos logs, sem expor stack trace ao usuário.

Exceção pré-existente: `run_rules_only("")` não sanitiza o texto e o schema rejeita `texto_entrada` vazio; a interface impede a entrada vazia.
