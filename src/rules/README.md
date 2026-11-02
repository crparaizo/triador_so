# src/rules/ — Motor de regras de produção

Esta pasta implementa o **motor de regras determinístico** do sistema: o módulo que pega as informações extraídas do relato e decide, de forma explícita e auditável, qual é a urgência, a prioridade e a equipe responsável.

> Diferente do LLM (que "decide" de forma opaca), o motor de regras **sempre explica por que chegou a uma conclusão** — os IDs das regras acionadas ficam registrados no resultado.

---

## Arquivos

### `definitions.py` — Estrutura de uma regra
Define o formato de uma regra de produção em Python (Pydantic):

- `RuleCondition`: as condições que devem ser satisfeitas. Campos opcionais:
  - `categoria`: tipo de falha detectado (ex: `MECANICA`)
  - `risco_seguranca`: se a extração identificou risco
  - `impacto_producao`: se a extração identificou impacto produtivo
  - `criticidade_ativo`: criticidade do ativo na base de dados (`ALTA`, `MEDIA`, `BAIXA`)
  - `palavras_chave`: lista de termos — basta **um** estar presente para satisfazer esta condição (abreviações de até 3 letras, como `pm` e `rh`, só casam como palavra inteira)
  - `palavras_chave_condicao`: segundo grupo de termos, avaliado como condição própria (ex.: equipamento **e** dispositivo de segurança)
  - `norma_ativo`: norma do campo `normas_aplicaveis` do ativo encontrado (ex.: `NR-13`); junto com `palavras_chave`, forma uma única condição OR
  - `pressao_acima_pmta`: pressão escrita no relato (kPa ou MPa, lida por `src/extraction/medicoes.py`) acima da PMTA cadastrada do ativo encontrado (RULE-021)
  - `urgencia_mencionada`: expressão de urgência detectada no texto
  - `operador`: `AND` (todas as condições devem ser verdadeiras) ou `OR` (basta uma)
- `RuleAction`: o que fazer quando a regra dispara (urgência, prioridade, equipe, revisão humana)
- `Rule`: a regra completa = condição + ação + prioridade_regra (número de precedência) + `fundamentacao` (norma e item, ou "Critério da autora")
- `load_rules()`: lê o arquivo `data/rules.yaml` e retorna a lista de regras validadas

### `engine.py` — Avaliação das regras
Implementa a função principal `apply_rules(extracted, context, rules, texto_original, categoria_detectada)`:

**Como funciona:**
1. Para cada regra, avalia se as condições são satisfeitas com base nas informações extraídas e no contexto enriquecido
2. Coleta todas as regras que "disparam" (condições satisfeitas)
3. Ordena por `prioridade_regra` (maior número = maior precedência)
4. Faz o **merge das ações**: para cada campo (urgência, prioridade, equipe, confiança), o valor da regra de maior prioridade prevalece. A revisão humana é a exceção: basta **uma** regra disparada exigi-la (disjunção), e os motivos são combinados
5. Se nenhuma regra disparar: retorna `DESCONHECIDA` + `requer_revisao_humana=True`
6. Retorna um dicionário com o resultado consolidado, a lista de IDs das regras acionadas e o `rastro` (campo → regra que definiu o valor). `descrever_regras()` transforma esse rastro no texto da evidência `regras_classificacao` (ex.: `urgência ← RULE-019; revisão ← RULE-019, RULE-001`)

**Garantias:**
- Mesma entrada → sempre mesmo resultado (comportamento determinístico)
- Nenhuma chamada externa (sem LLM, sem internet)
- Decisões rastreáveis: o campo `regras_acionadas` lista exatamente quais regras contribuíram

### `__init__.py`
Marca a pasta como submódulo Python.
