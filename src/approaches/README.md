# src/approaches/ — As três abordagens de triagem

Esta pasta contém os **três pipelines completos de triagem** que são comparados no trabalho. Cada arquivo implementa uma abordagem diferente, todas recebendo o mesmo texto como entrada e retornando um `TriageResult` como saída.

---

## Abordagens

### `rules_only.py` — Abordagem por regras puras

**Função principal:** `run_rules_only(texto: str) → TriageResult`

Usa **apenas** o extrator por palavras-chave e o motor de regras. Não faz nenhuma chamada ao LLM.

Fluxo:
1. Extrator de palavras-chave identifica sintomas, ativo, riscos e impacto
2. Enriquecimento de contexto busca o ativo na base local
3. Motor de regras classifica urgência, prioridade e equipe
4. Resultado montado com `abordagem=REGRAS`

**Ponto forte**: rápido, previsível, totalmente auditável  
**Ponto fraco**: limitado ao vocabulário das listas de palavras-chave; paráfrases e erros de escrita podem passar despercebidos

---

### `llm_only.py` — Abordagem por LLM puro

**Função principal:** `run_llm_only(texto: str) → TriageResult`

O LLM faz tudo em um **único prompt**: extração, classificação e encaminhamento. O prompt inclui a lista completa de ativos e equipes como contexto.

Fluxo:
1. Monta o prompt com contexto de ativos e equipes
2. Envia ao LLM (ChatOllama)
3. Parser defensivo extrai o JSON da resposta
4. Mapeia os valores para os enums do sistema
5. Resultado montado com `abordagem=LLM` e `regras_acionadas=[]` (sempre vazio)

**Ponto forte**: mais flexível com linguagem natural, paráfrases e variações de vocabulário  
**Ponto fraco**: mais lento, não-determinístico, pode "alucinar" (inventar campos sem evidência), decisões não são auditáveis por regras explícitas

---

### `hybrid.py` — Abordagem híbrida ⭐

**Função principal:** `run_hybrid(texto: str) → TriageResult`

A abordagem principal do trabalho: **o LLM extrai, as regras classificam**.

Fluxo:
1. **LLM extrai** informações estruturadas do texto (sem classificar urgência ou prioridade)
2. Se a extração LLM falhar → **fallback automático** para o extrator de palavras-chave (com flag de revisão humana)
3. Enriquecimento de contexto busca o ativo na base local
4. **Motor de regras classifica** urgência, prioridade e equipe com base nas informações extraídas
5. Pós-processamento: consolida campos sem suporte e sinaliza revisão humana se confiança baixa
6. Resultado montado com `abordagem=HIBRIDO`

O código usa comentários `# LLM extrai` e `# Regras classificam` para marcar visualmente a separação de responsabilidades.

**Ponto forte**: combina a flexibilidade do LLM na extração com a previsibilidade e auditabilidade das regras na classificação  
**Ponto fraco**: depende do LLM para extração; se o modelo não estiver disponível, cai para palavras-chave

---

## `__init__.py`
Marca a pasta como submódulo Python e exporta as três funções principais.

---

## Nota sobre tratamento de erros

Todas as três funções têm tratamento defensivo: **nunca lançam exceção para o chamador**. Em caso de qualquer falha interna, retornam um `TriageResult` com `requer_revisao_humana=True` e `motivo_revisao` descrevendo o problema. O erro é registrado nos logs, sem expor stack trace ao usuário.
