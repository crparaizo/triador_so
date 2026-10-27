# Comparação de Arquiteturas de Orquestração (Regras, LLM e Híbrida) — Protótipo Acadêmico

> ⚠️ **PROTÓTIPO ACADÊMICO** — desenvolvido como parte de monografia de especialização em
> Controle e Automação (IFSP). **Não destinado a uso industrial real.**
> Toda classificação gerada deve ser revisada por especialistas habilitados em manutenção
> e segurança industrial antes de qualquer ação operacional.
> Decisões críticas em ambiente industrial exigem revisão humana obrigatória.

---

## Sobre o Projeto

Este projeto é um estudo comparativo de três arquiteturas de orquestração de fluxos para
sistemas de apoio à decisão: determinística (regras de produção), não determinística (modelo
de linguagem) e híbrida (neurossimbólica). O objeto de estudo é a **arquitetura de software**.

Como caso de uso, o protótipo implementa a triagem de ordens de serviço industriais: recebe um
relato em texto livre, enriquece o caso com dados locais de ativos e equipes, classifica urgência
e prioridade, recomenda uma equipe responsável e apresenta a justificativa com evidências textuais.
A triagem é o cenário de validação, não o foco do estudo.

As três abordagens são comparadas sobre os mesmos casos de teste e dados de contexto:

| Abordagem | Descrição |
|---|---|
| **Regras** | Classificação determinística por 18 regras de produção explícitas e documentadas |
| **LLM puro** | Extração e classificação inteiramente via modelo de linguagem local (Ollama) |
| **Híbrido** | LLM extrai informações estruturadas do texto; regras de produção classificam e encaminham |

**Contexto acadêmico:** este protótipo foi desenvolvido para comparar empiricamente as três
arquiteturas de orquestração, usando a triagem automática como caso de uso. Os dados de domínio
(ativos, equipes, categorias) são sintéticos e genéricos. O sistema não está conectado a sistemas
reais nem executa ações externas.

---

## Pré-requisitos

- **Python 3.10 ou superior** (testado com Python 3.14 no Windows x64)
- **[Ollama](https://ollama.ai/download)** instalado e rodando (necessário apenas para as abordagens LLM e híbrida)
- **Git**

---

## Instalação

### 1. Clone o repositório

```powershell
# PowerShell (Windows)
git clone https://github.com/crparaizo/triador_so
cd triador_so
```

```bash
# Bash (Linux / macOS)
git clone https://github.com/crparaizo/triador_so
cd triador_so
```

### 2. Crie e ative o ambiente virtual

```powershell
# PowerShell (Windows)
python -m venv .venv
.venv\Scripts\activate
```

```bash
# Bash (Linux / macOS)
python -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências

```powershell
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```powershell
# PowerShell (Windows)
copy .env.example .env
```

```bash
# Bash (Linux / macOS)
cp .env.example .env
```

Abra o arquivo `.env` e ajuste conforme necessário. Consulte a seção
[Variáveis de Ambiente](#variáveis-de-ambiente) abaixo para a descrição de cada variável.

---

## Variáveis de Ambiente

O arquivo `.env` (criado a partir de `.env.example`) controla o comportamento do sistema.
Todos os campos têm valores padrão funcionais — o sistema roda sem `.env` configurado.

| Variável | Padrão | Descrição |
|---|---|---|
| `OLLAMA_MODEL` | `qwen3:0.6b` | Nome do modelo Ollama. Deve estar baixado localmente (`ollama pull <modelo>`). |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL base do servidor Ollama. Alterar se a porta 11434 estiver em uso. |
| `DATA_DIR` | `data` | Diretório com os arquivos YAML de ativos, equipes e categorias. |
| `RESULTS_DIR` | `results` | Diretório onde os relatórios de avaliação são salvos. |
| `SESSIONS_DIR` | `sessions` | Diretório onde as sessões da interface são persistidas. |
| `LOG_LEVEL` | `INFO` | Nível de log: `DEBUG`, `INFO`, `WARNING` ou `ERROR`. |
| `MAX_RETRIES_LLM` | `3` | Número máximo de tentativas para chamadas ao LLM em caso de erro. |
| `LLM_TIMEOUT_SECONDS` | `60` | Base do timeout por caso na avaliação (o runner aguarda 2× este valor). Não é repassado ao cliente HTTP do Ollama. |
| `OLLAMA_NUM_PREDICT` | `1024` | Limite de tokens gerados por chamada ao LLM (inclui o raciocínio do qwen3). Evita que o modelo entre em laço com `format="json"`; resposta truncada vai para revisão humana. |

---

## Configuração do Ollama

### Instalar o Ollama

Acesse [https://ollama.ai/download](https://ollama.ai/download) e siga as instruções
para o seu sistema operacional. No Windows, o instalador adiciona o Ollama ao PATH automaticamente.

### Iniciar o servidor

```powershell
ollama serve
```

Mantenha este terminal aberto. O servidor roda na porta 11434 por padrão.

### Baixar o modelo padrão

```powershell
ollama pull qwen3:0.6b
```

O download pode levar alguns minutos dependendo da conexão (o modelo tem aproximadamente 500 MB).

> **Nota sobre escolha de modelo:** `qwen3:0.6b` é o modelo padrão deste protótipo por rodar inteiramente em GPU mesmo com VRAM limitada (~1 GB disponível). Se a sua máquina tiver GPU com 4 GB ou mais de VRAM, você pode usar modelos maiores para melhor qualidade de extração:
>
> ```powershell
> ollama pull qwen3:4b   # requer ~2.7 GB de VRAM para rodar 100% em GPU
> ollama pull qwen3:1.7b # requer ~1.5 GB de VRAM
> ```
>
> Altere `OLLAMA_MODEL` no `.env` após baixar. Verifique qual percentual está rodando em GPU com `ollama ps` — quanto maior a fração GPU, menor a latência.

### Verificar modelos disponíveis

```powershell
ollama list
```

### Trocar o modelo

Para usar um modelo diferente, altere `OLLAMA_MODEL` no arquivo `.env`:

```env
OLLAMA_MODEL=llama3.2:3b
```

O modelo deve estar baixado localmente. Modelos muito pequenos podem não produzir JSON
estruturado consistente — consulte a seção [Solução de Problemas](#solução-de-problemas)
para mais detalhes.

---

## Executar a Aplicação

### Interface gráfica (Streamlit) — recomendado

```powershell
python -m streamlit run src/interface/app.py
```

Acesse **http://localhost:8501** no navegador. A interface possui três páginas
navegáveis pela barra lateral:

| Página | Descrição |
|---|---|
| **Triagem** | Insira um relato de ocorrência e execute as três abordagens comparáveis. Exibe resultados em abas (Regras / LLM Puro / Híbrido / Comparação). |
| **Avaliação** | Execute a avaliação completa sobre o dataset sintético com seleção de abordagens, barra de progresso e download dos relatórios. |
| **Histórico** | Exibe sessões salvas com detalhes por abordagem. Permite limpar o histórico. |

> Em telas estreitas (< 768 px), os resultados são exibidos em abas separadas para
> manter a legibilidade.

### Execução alternativa (IDEs sem suporte a `streamlit`)

```powershell
python run_app.py
```

---

## Executar a Avaliação Comparativa

O comando de avaliação executa as abordagens selecionadas sobre o dataset sintético
de 100 casos e salva relatórios com timestamp em `results/`.

```powershell
# Avaliar as três abordagens (requer Ollama rodando)
python -m src.evaluation

# Avaliar apenas por regras (sem necessidade do Ollama)
python -m src.evaluation --approaches regras

# Avaliar LLM puro e híbrido
python -m src.evaluation --approaches llm hibrido

# Especificar um dataset alternativo
python -m src.evaluation --dataset datasets/synthetic_cases.json

# Ver todas as opções
python -m src.evaluation --help
```

### Arquivos gerados em `results/`

Cada execução cria 4 arquivos com timestamp (`YYYYMMDD_HHMMSS`) para evitar sobrescrita:

| Arquivo | Conteúdo |
|---|---|
| `evaluation_raw_<ts>.json` | Dados brutos completos de todas as execuções |
| `evaluation_per_case_<ts>.csv` | Comparativo predição vs. gabarito por caso |
| `evaluation_summary_<ts>.json` | Métricas agregadas por abordagem (F1, latência, etc.) |
| `evaluation_summary_<ts>.csv` | Resumo tabular por abordagem |

Um exemplo de relatório de avaliação sintético está disponível em
`datasets/sample_report.json` para referência de formato.

### Análise estatística da monografia

A execução de referência da monografia (`results/evaluation_*_20261016_100014`) pode ser reanalisada com:

```powershell
python scripts/analise_estatistica.py results/evaluation_raw_20261016_100014.json
```

O script reproduz as Tabelas 2, 3, 5, 6 e 8 (IC 95% por *bootstrap*, teste de McNemar, Clopper-Pearson, métricas de revisão humana e verificabilidade das evidências). Detalhes e a lista das execuções em `results/README.md`.

---

## Executar os Testes Automatizados

```powershell
pytest tests/ -v
```

Resultado esperado: **232 testes aprovados, 0 falhas.**

> Os testes **não dependem do Ollama**. Chamadas ao LLM são simuladas por mocks.
> Execute os testes mesmo sem o Ollama instalado.

Para executar um módulo específico:

```powershell
pytest tests/test_schemas.py -v
pytest tests/test_rules_engine.py -v
pytest tests/test_evaluation.py -v
pytest tests/test_dataset.py -v
```

---

## Estrutura do Projeto

```
hibrido/
├── src/
│   ├── approaches/          # Três abordagens comparáveis
│   │   ├── rules_only.py    # Pipeline somente por regras de produção
│   │   ├── llm_only.py      # Pipeline somente por LLM
│   │   └── hybrid.py        # Pipeline híbrido (LLM extrai, regras classificam)
│   ├── config/
│   │   └── loader.py        # Carregamento de configurações via pydantic-settings
│   ├── data/
│   │   ├── loader.py        # Carregamento de ativos, equipes e categorias (YAML)
│   │   ├── context_enricher.py  # Enriquecimento do caso com dados locais
│   │   └── dataset_loader.py    # Carregamento e validação do dataset sintético
│   ├── evaluation/
│   │   ├── __main__.py      # CLI de avaliação (python -m src.evaluation)
│   │   ├── runner.py        # Execução das abordagens sobre o dataset
│   │   ├── metrics.py       # Funções de métricas (F1, latência, taxa de revisão…)
│   │   └── report.py        # Geração e persistência de relatórios (JSON/CSV)
│   ├── extraction/
│   │   ├── keyword_extractor.py  # Extração baseada em palavras-chave (sem LLM)
│   │   └── llm_extractor.py      # Extração estruturada via LLM (Ollama)
│   ├── interface/
│   │   ├── app.py               # Interface Streamlit (Triagem / Avaliação / Histórico)
│   │   └── session_manager.py   # Persistência de sessões em JSON
│   ├── orchestration/
│   │   ├── triage_flow.py       # Fábrica comum LCEL: nós, fallbacks, falha segura
│   │   ├── chains.py            # build_*_chain() dos três fluxos + exportação Mermaid
│   │   └── __main__.py          # Gera docs/fluxos_langchain.md (python -m src.orchestration)
│   ├── rules/
│   │   ├── engine.py            # Motor de regras de produção
│   │   └── definitions.py       # Carregamento e validação das regras do YAML
│   └── schemas/
│       ├── triage.py            # TriageResult e enums (UrgencyLevel, etc.)
│       ├── extraction.py        # ExtractedInfo (saída do extrator LLM)
│       └── assets.py            # Asset, Team, Category (dados de domínio)
├── data/
│   ├── rules.yaml           # 18 regras de produção com condições e ações
│   ├── assets.yaml          # Ativos industriais sintéticos (tag, criticidade, equipe)
│   ├── teams.yaml           # 6 equipes com especialidades
│   └── categories.yaml      # 12 categorias de falha com palavras-chave
├── datasets/
│   ├── synthetic_cases.json # 100 casos sintéticos para avaliação
│   ├── DATASET_README.md    # Documentação e limitações do dataset
│   └── sample_report.json   # Exemplo pré-computado de relatório de avaliação
├── docs/
│   ├── architecture.md      # Arquitetura detalhada e diagramas
│   └── fluxos_langchain.md  # Grafos LCEL (Mermaid) gerados a partir do código
├── tests/                   # Testes automatizados (pytest)
│   ├── conftest.py
│   ├── test_schemas.py
│   ├── test_rules_engine.py
│   ├── test_evaluation.py
│   ├── test_dataset.py
│   ├── test_orchestration.py  # Estrutura dos grafos LCEL e fallbacks
│   └── ...
├── results/                 # Relatórios gerados (*.json, *.csv — não versionados)
│   └── .gitkeep
├── sessions/                # Sessões da interface (*.json — não versionadas)
│   └── .gitkeep
├── run_app.py               # Ponto de entrada alternativo para IDEs
├── .env.example             # Modelo de variáveis de ambiente (sem segredos)
├── requirements.txt         # Dependências com versões fixadas
└── pyproject.toml           # Metadados do projeto
```

---

## Arquitetura

Consulte [`docs/architecture.md`](docs/architecture.md) para diagramas ASCII e descrição
detalhada dos módulos. Esta seção apresenta um resumo.

### Três pipelines comparáveis

Os três pipelines são cadeias LCEL (LangChain Expression Language) de nós `Runnable`
nomeados, definidas em `src/orchestration/` e `src/approaches/`. Todos começam em
`preparacao_entrada` e ficam dentro do envelope `triagem_com_falha_segura`
(`RunnableWithFallbacks`): qualquer exceção leva ao nó `resultado_seguro`, que exige
revisão humana. **Regras e híbrido usam a mesma estrutura de grafo e diferem apenas no
nó de extração.**

```
Texto livre
    │
    ├─── [1] REGRAS ─────────────────────────────────────────────────────────┐
    │    carregamento_dados                                                   │
    │    extracao_palavras_chave  ∥  deteccao_categoria   (RunnableParallel)  │
    │    enriquecimento_contexto  (dados de ativos/equipes)                   │
    │    motor_regras_producao    (apply_rules: um nó, regras em rules.yaml)  │
    │    montagem_resultado ─────────────────────────────────────────→ TriageResult
    │
    ├─── [2] LLM PURO ───────────────────────────────────────────────────────┐
    │    preparacao_prompt        (ativos + equipes + relato)                 │
    │    chamada_llm              (ChatOllama — extrai E classifica)          │
    │    parser_defensivo         (JSON direto → regex → erro)                │
    │    montagem_resultado ─────────────────────────────────────────→ TriageResult
    │
    └─── [3] HÍBRIDO (mesmo grafo de [1]) ───────────────────────────────────┐
         carregamento_dados       (+ LLMExtractor)                            │
         extracao_llm_com_fallback  ∥  deteccao_categoria                     │
           └ extracao_llm (Ollama, só extração)                               │
             → se falhar: extracao_palavras_chave + revisão obrigatória       │
         enriquecimento_contexto                                              │
         motor_regras_producao    (regras determinam urgência/prioridade/equipe)
         montagem_resultado ─────────────────────────────────────────→ TriageResult
```

Os grafos exatos, exportados do código com `get_graph().draw_mermaid()`, estão em
[`docs/fluxos_langchain.md`](docs/fluxos_langchain.md). Para regenerá-los:

```powershell
python -m src.orchestration
```

### Separação entre informação observada e inferida

O sistema diferencia:
- **Informação observada**: extraída diretamente do texto do relato (campo `evidencias`)
- **Informação recuperada**: obtida dos dados locais de ativos/equipes (context_enricher)
- **Campos sem suporte**: inferidos sem evidência direta (`campos_sem_suporte` — indicador de possível alucinação)

---

## Dados Sintéticos

> ⚠️ **ATENÇÃO: Os 100 casos do dataset são completamente sintéticos.**
> Foram criados com auxílio de IA Generativa para fins acadêmicos e **não representam incidentes,
> equipamentos ou instalações reais.**

### Distribuição por tipo

| Tipo | Qtd | Descrição |
|---|:---:|---|
| CANONICO | 15 | Casos de referência com texto direto e preciso |
| PARAFRASES | 15 | Reescrita dos canônicos com linguagem diferente (teste de robustez) |
| ABREVIACOES | 8 | Relatos com abreviações industriais comuns |
| ERROS_ESCRITA | 8 | Relatos com 1–3 erros ortográficos ou de digitação |
| MULTIPLOS_SINTOMAS | 8 | Relatos com 3+ sintomas de subcategorias diferentes |
| INCOMPLETOS | 8 | Relatos vagos sem tag de ativo ou sintoma específico |
| CONTRADITORIOS | 8 | Relatos com contradição interna |
| FORA_ESCOPO | 8 | Solicitações fora do escopo de manutenção industrial |
| ALTA_CRITICIDADE | 11 | Emergências de criticidade máxima (urgência IMEDIATA/P1) |
| REVISAO_HUMANA | 11 | Cenários que exigem revisão humana por incerteza |
| **Total** | **100** | |

### Limitações do dataset

- Gerado com auxílio de IA Generativa — não cobre a diversidade real de relatos de campo
- Sem dados temporais (turno, histórico de falhas, sazonalidade)
- Gabarito anotado com base nas regras do sistema e julgamento editorial, não por especialistas
- Tamanho insuficiente para conclusões estatísticas robustas (apenas demonstração)
- Consulte `datasets/DATASET_README.md` para documentação completa

---

## Formato de Saída (TriageResult)

Todas as abordagens produzem um objeto `TriageResult` com os seguintes campos:

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | `str` (UUID) | Identificador único do resultado |
| `timestamp` | `datetime` | Momento em que a triagem foi executada |
| `abordagem` | `ApproachType` | Abordagem utilizada: `REGRAS`, `LLM` ou `HIBRIDO` |
| `texto_entrada` | `str` | Relato original da ocorrência (mínimo 1 caractere) |
| `urgencia` | `UrgencyLevel` | `IMEDIATA` / `ALTA` / `MEDIA` / `BAIXA` / `DESCONHECIDA` |
| `prioridade` | `PriorityLevel` | `P1` (Crítico) / `P2` / `P3` / `P4` / `DESCONHECIDA` |
| `categoria` | `FailureCategory` | Categoria da falha — ver tabela abaixo |
| `equipe_sugerida` | `str` | Nome da equipe recomendada para atendimento |
| `regras_acionadas` | `list[str]` | IDs das regras disparadas (vazio para LLM puro) |
| `evidencias` | `dict[str, str]` | Evidências textuais por campo classificado |
| `requer_revisao_humana` | `bool` | Sinaliza necessidade de revisão humana obrigatória |
| `motivo_revisao` | `str \| None` | Justificativa da revisão (obrigatório quando `True`) |
| `confianca` | `float` [0, 1] | Score de confiança da classificação |
| `latencia_ms` | `float` | Latência de processamento em milissegundos |
| `campos_sem_suporte` | `list[str]` | Campos inferidos sem evidência direta (indicador de alucinação) |

### Categorias de falha (`FailureCategory`)

| Valor | Descrição |
|---|---|
| `MECANICA` | Falhas mecânicas (vibração, ruptura, desgaste) |
| `ELETRICA` | Falhas elétricas (painéis, motores, transformadores) |
| `INSTRUMENTACAO` | Falhas de instrumentação e sensores |
| `UTILIDADES` | Caldeiras, chillers, ar comprimido, HVAC |
| `SEGURANCA` | Situações de risco de segurança (NR-10, NR-35, etc.) |
| `QUALIDADE` | Produto fora de especificação |
| `PROCESSO` | Desvios de processo |
| `INFRAESTRUTURA` | Facilities, elevadores, infraestrutura predial |
| `TI_AUTOMACAO` | SCADA, CLP, redes industriais |
| `OUTROS` | Categorias não enquadradas acima |
| `FORA_DO_ESCOPO` | Solicitações fora do escopo de manutenção industrial |
| `DESCONHECIDA` | Não foi possível determinar a categoria |

---

## Solução de Problemas

### 1. Ollama não está rodando

**Erro esperado:**
```
ConnectionRefusedError: [Errno 111] Connection refused
```
ou
```
httpx.ConnectError: All connection attempts failed
```

**Solução:** inicie o servidor Ollama antes de executar as abordagens LLM ou híbrida:

```powershell
ollama serve
```

A abordagem por **Regras** não depende do Ollama e funciona normalmente sem ele.

---

### 2. Modelo não baixado

**Erro esperado:**
```
model 'qwen3:0.6b' not found
```

**Solução:** baixe o modelo configurado no `.env`:

```powershell
ollama pull qwen3:0.6b
```

Ou altere `OLLAMA_MODEL` no `.env` para um modelo já disponível:

```powershell
ollama list   # lista os modelos disponíveis localmente
```

---

### 3. Modelo diferente não produz JSON estruturado

Modelos muito pequenos ou que não foram ajustados para seguir instruções podem não
produzir JSON válido nas abordagens LLM e híbrida. O sistema possui um **parser
defensivo** que tenta recuperar JSON mesmo de respostas malformadas. Em caso de
falha, o campo é marcado em `campos_sem_suporte` e o resultado pode ter urgência
`DESCONHECIDA` com `requer_revisao_humana=True`.

**Solução:** troque para um modelo mais capaz no `.env`:

```env
OLLAMA_MODEL=llama3.2:3b
```

---

### 4. Porta 11434 em uso por outro processo

**Sintoma:** Ollama não inicia ou a aplicação não consegue se conectar.

**Solução:** configure uma porta alternativa no Ollama e atualize o `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11435
```

Consulte a documentação do Ollama para configurar a porta no servidor.

---

### 5. `ModuleNotFoundError: No module named 'src'`

**Causa:** ambiente virtual não está ativado ou as dependências não foram instaladas.

**Solução:**

```powershell
# PowerShell (Windows)
.venv\Scripts\activate
pip install -r requirements.txt
```

Certifique-se de executar os comandos a partir da **raiz do projeto** (diretório onde
está `pyproject.toml`).

---

### 6. `pytest: command not found`

**Causa:** ambiente virtual não está ativado.

**Solução:**

```powershell
# PowerShell (Windows)
.venv\Scripts\activate
pytest tests/ -v
```

---

### 7. Streamlit não abre no navegador automaticamente

Abra manualmente no navegador:

```
http://localhost:8501
```

Se a porta 8501 estiver em uso, use:

```powershell
python -m streamlit run src/interface/app.py --server.port 8502
```

---

### 8. Avaliação muito lenta

As abordagens LLM e híbrida chamam o modelo local para cada um dos 100 casos.
Em máquinas sem GPU dedicada, cada chamada pode levar 10–60 segundos, resultando em
**avaliação total de 30–100 minutos** para as abordagens LLM.

**Alternativas:**
- Execute apenas a abordagem por regras (rápida, sem dependência de LLM):
  ```powershell
  python -m src.evaluation --approaches regras
  ```
- Use um modelo menor e mais rápido (qualidade pode variar):
  ```env
  OLLAMA_MODEL=qwen3:0.6b
  ```

---

### 9. Arquivo `.env` não encontrado

O sistema funciona sem `.env` — todos os campos têm valores padrão. Porém, recomenda-se
criar o arquivo para persistir configurações entre sessões:

```powershell
copy .env.example .env
```

---

### 10. Erro de permissão em `sessions/` ou `results/`

**Erro esperado:**
```
PermissionError: [Errno 13] Permission denied: 'sessions/...'
```

**Solução:** verifique as permissões do diretório:

```powershell
# PowerShell (Windows) — verificar permissões
Get-Acl sessions

# Ou recriar os diretórios
New-Item -ItemType Directory -Force sessions, results
```

Certifique-se de que o usuário atual tem permissão de escrita nos diretórios
`sessions/` e `results/`.

---

## Limitações e Avisos Acadêmicos

Este protótipo foi desenvolvido exclusivamente para fins de pesquisa acadêmica.
**Não está pronto para uso em ambiente industrial real.**

### Dataset sintético
Os 100 casos foram criados com auxílio de IA Generativa seguindo padrões genéricos de manutenção
industrial. Não representam a distribuição real de falhas de nenhuma planta específica.
O tamanho do dataset é insuficiente para afirmações de significância estatística.

### Modelo LLM local
O comportamento do LLM varia com o modelo e a quantização utilizada. O modelo padrão (`qwen3:0.6b`)
é um modelo muito compacto — pode produzir saídas inconsistentes, especialmente para relatos
ambíguos ou com erros de escrita. Resultados variam entre execuções (temperatura > 0).
Se a infraestrutura disponível permitir (GPU com 4 GB+ de VRAM), recomenda-se utilizar
modelos maiores como `qwen3:4b` para maior qualidade de extração.

### Motor de regras
O sistema contém **18 regras de produção** que cobrem cenários genéricos. Cenários
não cobertos resultam em `urgencia=DESCONHECIDA` e `requer_revisao_humana=True`.
Para uso real, as regras precisariam ser revisadas e estendidas por especialistas
de domínio familiarizados com as normas aplicáveis (NR-10, NR-13, NR-35, etc.).

### Lacunas documentadas
- **Infraestrutura** (HVAC, elevadores): sem regra específica para casos sem emergência
- **Qualidade**: sem regra para produtos fora de especificação sem impacto de produção
- **SEGURANCA**: regras classificam urgência corretamente, mas não definem equipe
- **Manutenção preventiva**: pode ser sobre-escalada quando outra regra de categoria dispara

### Métricas de avaliação
As métricas são calculadas contra um gabarito sintético anotado editorialmente, não
por especialistas em manutenção industrial. Não use os valores de F1 para afirmações
de desempenho absoluto.

### Sem validação por especialistas de domínio
As regras, categorias e dados de contexto não foram validados por profissionais de
manutenção industrial. Os resultados refletem a modelagem acadêmica do problema.

### Sem conexão com sistemas reais
O sistema não encaminha ordens para sistemas reais, não acessa bancos de dados
operacionais e não executa nenhuma ação externa.

### Revisão humana obrigatória
Em qualquer aplicação industrial real, toda decisão automática de triagem deve ser
revisada por profissional habilitado antes de qualquer ação operacional.

---

## Licença

MIT — consulte o arquivo `pyproject.toml` para detalhes.

Este software é fornecido "como está", sem garantias de qualquer tipo. O uso em
ambiente industrial é de responsabilidade exclusiva do usuário e requer validação
especializada independente.
