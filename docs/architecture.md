# Arquitetura — Triador de Ordens de Serviço Industrial

> ⚠️ **Protótipo acadêmico** — monografia de especialização em Controle e Automação (IFSP).
> Não destinado a uso industrial real.

---

## Visão Geral

O sistema implementa três pipelines independentes que recebem o mesmo texto de entrada
e produzem um `TriageResult` estruturado. Os três pipelines compartilham os mesmos
dados de domínio (ativos, equipes, categorias e regras).

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ENTRADA                                       │
│              Texto livre em português                                │
│    "Bomba P-101 com vibração excessiva e parada de linha."           │
└────────────────────────┬────────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────────┐
          │              │                  │
          ▼              ▼                  ▼
  ┌──────────────┐ ┌───────────┐ ┌──────────────────┐
  │  [1] REGRAS  │ │[2] LLM    │ │  [3] HÍBRIDO     │
  └──────┬───────┘ └─────┬─────┘ └────────┬─────────┘
         │               │                │
         ▼               ▼                ▼
  ┌─────────────────────────────────────────────────────┐
  │                   TriageResult                       │
  │  urgencia · prioridade · categoria · equipe_sugerida │
  │  evidencias · regras_acionadas · confianca           │
  │  requer_revisao_humana · campos_sem_suporte          │
  └─────────────────────────────────────────────────────┘
```

---

## Orquestração LCEL (LangChain)

Cada pipeline é uma cadeia LCEL (LangChain Expression Language) de nós `Runnable`
nomeados que trocam um dicionário de estado. A topologia comum está em
`src/orchestration/triage_flow.py`; as funções de cada nó ficam em
`src/approaches/`. Os três fluxos começam com `preparacao_entrada` e envolvem o
núcleo em `triagem_com_falha_segura` (`RunnableWithFallbacks`): qualquer exceção
leva ao fallback `resultado_seguro`, que devolve um resultado com revisão humana
obrigatória.

**Os pipelines 1 e 3 usam a mesma estrutura de grafo** (mesma fábrica,
`compor_fluxo_triagem`) e diferem apenas no nó de extração. O motor de regras é um
único nó (`motor_regras_producao`); as regras continuam em `data/rules.yaml`.
Os grafos exportados do código estão em [`fluxos_langchain.md`](fluxos_langchain.md)
(regenerar com `python -m src.orchestration`).

---

## Pipeline 1 — Regras de Produção

**Módulo principal:** `src/approaches/rules_only.py` — `build_rules_flow()`

```
Texto livre
    │
    ▼
preparacao_entrada            (início da medição de latência)
    │
    ▼
carregamento_dados            (assets/teams, categories, rules — YAML cacheado)
    │
    ├──────────────────────────────┐   RunnableParallel
    ▼                              ▼
extracao_palavras_chave        deteccao_categoria
  KeywordExtractor.extract       KeywordExtractor.detect_category
  → ExtractedInfo                → FailureCategory
  (sem LLM)                      (ou categoria_ref no cenário-diagnóstico)
    │                              │
    └──────────────┬───────────────┘
                   ▼
enriquecimento_contexto       (enrich_context: ativo, criticidade, equipe)
                   │
                   ▼
motor_regras_producao         (apply_rules: avalia as 18 regras por prioridade_regra)
                   │
                   ▼
montagem_resultado → TriageResult (abordagem=REGRAS)
```

**Características:**
- Determinístico: mesmo texto sempre produz o mesmo resultado
- Rápido: sem chamada de rede (latência tipicamente < 50 ms)
- Rastreável: campo `regras_acionadas` lista cada regra disparada
- Limitado: cobre apenas os cenários modelados nas 18 regras

---

## Pipeline 2 — LLM Puro

**Módulo principal:** `src/approaches/llm_only.py` — `build_llm_flow()`

```
Texto livre
    │
    ▼
preparacao_entrada
    │
    ▼
preparacao_prompt             (prompt único com ativos e equipes da planta)
    │
    ▼
chamada_llm                   (ChatOllama instanciado em runtime; llm.invoke(prompt))
  → extrai E classifica (urgência, prioridade, categoria, equipe) num único passo
    │
    ▼
parser_defensivo              (json direto → regex → erro)
    │
    ▼
montagem_resultado → TriageResult (abordagem=LLM, regras_acionadas=[])
  → valores inválidos → DESCONHECIDA; JSON inválido → revisão humana
  → falha de conexão → resultado_seguro ("LLM indisponível: ...")
```

**Características:**
- Flexível: capaz de lidar com variações de linguagem naturalmente
- Não determinístico: resultados podem variar entre execuções
- Lento: latência depende do hardware (10 ms–60 s por chamada)
- Dependente do Ollama: falha se o servidor não estiver disponível
- Sem rastreabilidade de regras

---

## Pipeline 3 — Híbrido

**Módulo principal:** `src/approaches/hybrid.py` — `build_hybrid_flow()`

Mesmo grafo do Pipeline 1; muda apenas o nó de extração.

```
Texto livre
    │
    ▼
preparacao_entrada
    │
    ▼
carregamento_dados            (mesmos YAML + instância do LLMExtractor)
    │
    ├──────────────────────────────────────┐   RunnableParallel
    ▼                                      ▼
extracao_llm_com_fallback              deteccao_categoria
  (RunnableWithFallbacks)                KeywordExtractor.detect_category
  extracao_llm: LLMExtractor.extract
    → ExtractedInfo (sem urgência/prioridade)
  se erro_parse ou exceção:
    extracao_palavras_chave (KeywordExtractor)
    + evidência extracao_fallback + revisão obrigatória
    │                                      │
    └──────────────────┬───────────────────┘
                       ▼
enriquecimento_contexto
                       │
                       ▼
motor_regras_producao         (regras determinam urgência/prioridade/equipe)
                       │
                       ▼
montagem_resultado → TriageResult (abordagem=HIBRIDO, regras_acionadas=[...])
  (evidências LLM + ativo_encontrado + regras_classificacao;
   revisão se fallback ou confiança de extração < 0,4)
```

**Características:**
- Combina a flexibilidade do LLM na extração com a rastreabilidade das regras
- Decisões críticas controladas por regras explícitas (não pelo LLM)
- Mais robusto que LLM puro para casos que exigem regras de negócio estritas
- Ainda depende do Ollama para a fase de extração

---

## Módulos Principais

| Módulo | Arquivo | Responsabilidade |
|---|---|---|
| `schemas/triage` | `src/schemas/triage.py` | Enums e `TriageResult` (Pydantic v2) |
| `schemas/extraction` | `src/schemas/extraction.py` | `ExtractedInfo` (saída do extrator) |
| `schemas/assets` | `src/schemas/assets.py` | `Asset`, `Team`, `Category` (dados de domínio) |
| `config/loader` | `src/config/loader.py` | `Settings` via pydantic-settings; `get_settings()` |
| `data/loader` | `src/data/loader.py` | Carrega YAML de ativos, equipes e categorias |
| `data/context_enricher` | `src/data/context_enricher.py` | Enriquece `ExtractedInfo` com dados locais |
| `data/dataset_loader` | `src/data/dataset_loader.py` | Carrega e valida `datasets/synthetic_cases.json` |
| `extraction/keyword_extractor` | `src/extraction/keyword_extractor.py` | Extração por palavras-chave (sem LLM) |
| `extraction/llm_extractor` | `src/extraction/llm_extractor.py` | Extração estruturada via Ollama |
| `orchestration/triage_flow` | `src/orchestration/triage_flow.py` | Fábrica comum LCEL: nomes dos nós, envelope de falha segura, fallback da extração |
| `orchestration/chains` | `src/orchestration/chains.py` | Builders `build_*_chain()` dos três fluxos e exportação Mermaid dos grafos |
| `rules/definitions` | `src/rules/definitions.py` | Carrega e valida `data/rules.yaml` |
| `rules/engine` | `src/rules/engine.py` | Motor de regras: avalia condições e dispara ações |
| `approaches/*` | `src/approaches/` | Os três pipelines comparáveis |
| `evaluation/runner` | `src/evaluation/runner.py` | Executa abordagens sobre o dataset |
| `evaluation/metrics` | `src/evaluation/metrics.py` | Funções de métricas (F1, latência, etc.) |
| `evaluation/report` | `src/evaluation/report.py` | Gera e salva relatórios JSON/CSV |
| `interface/app` | `src/interface/app.py` | Interface Streamlit (3 páginas) |
| `interface/session_manager` | `src/interface/session_manager.py` | Persistência de sessões em JSON |

---

## Formato de Entrada

Texto livre em português descrevendo a ocorrência. Não há formato estruturado obrigatório.

**Exemplos válidos:**

```
Bomba centrífuga P-101 na área de utilidades apresentando vibração excessiva
e ruído anormal. Temperatura mancal acima de 80°C. Risco de parada de linha.
```

```
BOMB001 - vibração alta - prod parada
```

```
Não sei exatamente o que está errado, mas o equipamento está fazendo barulho.
```

O sistema deve lidar com abreviações, erros ortográficos, relatos incompletos e
contraditórios, sinalizando incerteza via `requer_revisao_humana=True` quando apropriado.

---

## Formato de Saída (TriageResult JSON)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-07-01T14:32:10.123456",
  "abordagem": "HIBRIDO",
  "texto_entrada": "Bomba BOMB-001 com vibração intensa. Linha parada.",
  "urgencia": "ALTA",
  "prioridade": "P1",
  "categoria": "MECANICA",
  "equipe_sugerida": "Manutenção Mecânica",
  "regras_acionadas": ["RULE-004", "RULE-011"],
  "evidencias": {
    "categoria": "vibração intensa",
    "impacto_producao": "Linha parada"
  },
  "requer_revisao_humana": false,
  "motivo_revisao": null,
  "confianca": 0.85,
  "latencia_ms": 1250.4,
  "campos_sem_suporte": []
}
```

---

## Como Adicionar uma Nova Regra

1. Abra `data/rules.yaml` em um editor de texto.

2. Adicione um novo bloco seguindo a estrutura existente. Escolha um ID sequencial
   (`RULE-019`, `RULE-020`, etc.) e defina `prioridade_regra` — maior valor significa
   maior precedência:

```yaml
- id: "RULE-019"
  descricao: "Descrição clara em português do que esta regra cobre"
  condicoes:
    categoria: "MECANICA"          # valor de FailureCategory (opcional)
    palavras_chave:                # lista OR — basta uma corresponder (opcional)
      - "termo1"
      - "termo2"
    risco_seguranca: true          # bool (opcional)
    impacto_producao: true         # bool (opcional)
    criticidade_ativo: "ALTA"      # "ALTA" | "MEDIA" | "BAIXA" (opcional)
    operador: "AND"                # "AND" (padrão) ou "OR" entre condições acima
  acoes:
    urgencia: "ALTA"               # valor de UrgencyLevel
    prioridade: "P2"               # valor de PriorityLevel
    equipe: "Manutenção Mecânica"  # nome da equipe (opcional)
    requer_revisao_humana: false
    confianca: 0.80                # float 0..1
  prioridade_regra: 45             # inteiro; maior = maior precedência
```

3. Valide carregando as regras:
```powershell
python -c "from src.rules.definitions import load_rules; r = load_rules(); print(f'{len(r)} regras OK')"
```

4. Execute os testes:
```powershell
pytest tests/test_rules_engine.py tests/test_rules_definitions.py -v
```

> **Nota sobre precedência:** o motor aplica a primeira regra (maior `prioridade_regra`)
> cujas condições são satisfeitas. Verifique se a nova regra não colide com regras
> existentes de prioridade próxima.

---

## Como Adicionar Novos Casos ao Dataset

1. Abra `datasets/synthetic_cases.json` em um editor de texto.

2. Acrescente um novo objeto JSON ao array seguindo a estrutura:

```json
{
  "id": "CASE-101",
  "tipo": "CANONICO",
  "texto": "Relato da ocorrência em português...",
  "esperado": {
    "urgencia": "ALTA",
    "prioridade": "P2",
    "categoria": "MECANICA",
    "equipe": "Manutenção Mecânica",
    "requer_revisao_humana": false
  },
  "referencia_caso_canonico": null,
  "notas": "Observação sobre o caso e regras esperadas."
}
```

   - `id`: padrão `CASE-NNN` com 3 dígitos; use o próximo número disponível
   - `tipo`: `CANONICO`, `PARAFRASES`, `ABREVIACOES`, `ERROS_ESCRITA`,
     `MULTIPLOS_SINTOMAS`, `INCOMPLETOS`, `CONTRADITORIOS`, `FORA_ESCOPO`,
     `ALTA_CRITICIDADE` ou `REVISAO_HUMANA`
   - Para tipo `PARAFRASES`, preencha `referencia_caso_canonico` com o ID do canônico base

3. Valide o arquivo:
```powershell
python -c "from src.data.dataset_loader import load_dataset; c = load_dataset(); print(f'{len(c)} casos OK')"
```

4. Execute os testes do dataset:
```powershell
pytest tests/test_dataset.py -v
```

---

## Definições das Métricas

Todas as métricas são calculadas em `src/evaluation/metrics.py` contra gabaritos
do dataset sintético. Nenhuma métrica usa LLM como avaliador de outro LLM.

### F1 ponderado por campo

**Definição:** F1-score weighted average (sklearn) para cada campo classificável
(urgência, prioridade, categoria, equipe). Pondera pelo suporte (número de amostras)
de cada classe.

**Limitação:** com classes desbalanceadas no dataset sintético, o F1 weighted
pode mascarar desempenho ruim em classes minoritárias. Consulte o relatório
`classification` completo para métricas por classe.

### Taxa de campos sem suporte (`unsupported_fields_rate`)

**Definição:** `Σ|campos_sem_suporte| / (n × 4)` — onde 4 é o número de campos
classificáveis (urgência, prioridade, categoria, equipe). Indica proporção de
inferências sem evidência textual direta.

**Limitação:** não distingue preenchimento legítimo por inferência contextual de
alucinação. Uso como indicador, não como prova de alucinação.

### Taxa de subestimação de casos críticos (`critical_underestimation_rate`)

**Definição:** proporção de casos críticos (urgência=IMEDIATA ou prioridade=P1 no
gabarito) classificados com urgência mais baixa (ALTA/MEDIA/BAIXA) ou prioridade
mais baixa (P2/P3/P4).

**Limitação:** definição conservadora — inclui casos onde apenas um dos critérios
foi subestimado. Taxas próximas de zero são desejáveis para segurança.

### Taxa de encaminhamento para revisão humana (`human_review_rate`)

**Definição:** proporção de resultados com `requer_revisao_humana=True`.

**Limitação:** inclui tanto verdadeiros positivos quanto falsos positivos. Taxas
altas podem indicar conservadorismo excessivo; taxas muito baixas podem indicar
sub-sinalização de casos ambíguos.

### Robustez em paráfrases (`robustness_score`)

**Definição:** para pares canônico/paráfrase anotados no dataset, mede a
consistência da classificação (predição idêntica nos dois textos). Score 1.0
indica classificação independente da formulação.

**Limitação:** depende dos 15 pares canônico/paráfrase disponíveis no dataset.
Amostra pequena limita a generalização.

### Latência (`latency_stats`)

**Definição:** estatísticas descritivas (média, desvio padrão, mínimo, máximo)
da latência de processamento em ms, medida dentro do fluxo LCEL, do nó
`preparacao_entrada` até a montagem do resultado.

**Limitação:** inclui o custo da orquestração LangChain (threads dos
`RunnableParallel`, callbacks), overhead de serialização Python e variações de carga do
sistema. Para abordagens LLM, a variância é alta e depende do hardware local.

---

## Dados de Domínio

| Arquivo | Conteúdo |
|---|---|
| `data/rules.yaml` | 18 regras de produção |
| `data/assets.yaml` | 18 ativos industriais sintéticos |
| `data/teams.yaml` | 6 equipes de manutenção |
| `data/categories.yaml` | 12 categorias de falha com palavras-chave |

Todos os dados são sintéticos e genéricos. Para uso em uma planta real, estes arquivos
deveriam ser substituídos por dados reais validados por especialistas do domínio.
