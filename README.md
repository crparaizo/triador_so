# Triador de Ordens de Serviço Industriais

> ⚠️ **Protótipo acadêmico** — desenvolvido para monografia de especialização em
> Controle e Automação (IFSP). **Não utilizar em ambiente industrial real.**
> Toda decisão gerada pelo sistema deve ser revisada por especialistas qualificados.

Sistema de triagem de ordens de serviço industriais que compara três abordagens:
1. **Regras de produção** — classificação determinística por regras explícitas
2. **LLM puro** — extração e classificação inteiramente via modelo de linguagem local
3. **Híbrido** — LLM extrai informações do texto e regras classificam/encaminham

---

## Pré-requisitos

- Python 3.10 ou superior
- [Ollama](https://ollama.com) instalado e rodando (necessário apenas para as abordagens LLM e híbrida)
- Git

---

## Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd hibrido

# 2. Crie e ative o ambiente virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Copie o arquivo de configuração
copy .env.example .env    # Windows
cp .env.example .env      # Linux / macOS
```

---

## Configuração do Ollama

### Instalar o Ollama

Acesse [https://ollama.com](https://ollama.com) e siga as instruções para o seu sistema operacional.

### Iniciar o servidor

```bash
ollama serve
```

### Baixar o modelo padrão

```bash
ollama pull qwen3:4b
```

O modelo utilizado é configurável via variável de ambiente `OLLAMA_MODEL` no arquivo `.env`.

---

## Configuração

Edite o arquivo `.env` conforme necessário:

```env
OLLAMA_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://localhost:11434
LOG_LEVEL=INFO
```

---

## Executar a aplicação

### Interface gráfica (Streamlit)

```bash
streamlit run src/interface/app.py
```

Acesse `http://localhost:8501` no navegador.

### Linha de comando — abordagem por regras (sem Ollama)

```bash
python -m src.approaches.rules_only
```

---

## Avaliação das três abordagens

O comando de avaliação executa os três métodos sobre o mesmo conjunto de 100 casos sintéticos e gera relatórios em `results/`.

```bash
python -m src.evaluation
```

### Opções disponíveis

```bash
# Avaliar apenas a abordagem por regras (sem necessidade do Ollama)
python -m src.evaluation --approaches regras

# Avaliar LLM puro e híbrido
python -m src.evaluation --approaches llm hibrido

# Especificar um dataset alternativo
python -m src.evaluation --dataset datasets/synthetic_cases.json

# Ver todas as opções
python -m src.evaluation --help
```

Os arquivos de saída são gravados em `results/` no formato CSV e JSON, incluindo métricas por classe, matriz de confusão e latência por abordagem.

---

## Executar os testes automatizados

```bash
pytest tests/ -v
```

Resultado esperado: ≥ 175 testes aprovados, 0 falhas.

Para executar um módulo específico:

```bash
pytest tests/test_schemas.py -v
pytest tests/test_rules_engine.py -v
pytest tests/test_evaluation.py -v
```

---

## Estrutura do projeto

```
hibrido/
├── src/
│   ├── approaches/      # Três abordagens: rules_only, llm_only, hybrid
│   ├── config/          # Carregamento de configurações (.env / YAML)
│   ├── data/            # Carregamento de ativos, equipes e dataset
│   ├── evaluation/      # Métricas, runner, relatórios e CLI (__main__.py)
│   ├── extraction/      # Extração por palavras-chave e por LLM
│   ├── interface/       # Interface Streamlit
│   ├── orchestration/   # Chains LangChain
│   ├── rules/           # Motor de regras e definições
│   └── schemas/         # Modelos Pydantic (ativos, extração, triagem)
├── datasets/
│   ├── synthetic_cases.json   # 100 casos sintéticos de avaliação
│   └── DATASET_README.md      # Documentação do dataset
├── tests/               # Testes automatizados (pytest)
├── results/             # Relatórios gerados pela avaliação
├── config/              # Arquivos YAML de configuração de ativos/equipes/regras
├── .env.example         # Modelo de variáveis de ambiente
├── requirements.txt     # Dependências com versões fixadas
└── pyproject.toml       # Metadados do projeto
```

---

## Formato de entrada e saída

### Entrada

Texto livre em português descrevendo a ocorrência, por exemplo:

```
Bomba centrífuga P-101 na área de utilidades apresentando vibração excessiva
e ruído anormal. Temperatura mancal acima de 80°C. Risco de parada de linha.
```

### Saída (TriageResult)

| Campo | Descrição |
|---|---|
| `categoria` | Categoria da falha (mecânica, elétrica, instrumentação…) |
| `urgencia` | Nível de urgência (imediata, alta, media, baixa) |
| `prioridade` | Nível de prioridade (critica, alta, media, baixa) |
| `equipe_responsavel` | Nome da equipe recomendada |
| `revisao_humana` | Se o caso deve ser escalado para revisão humana |
| `motivo_revisao` | Justificativa da revisão humana (quando aplicável) |
| `evidencias` | Trechos do texto que suportam a decisão |
| `regras_acionadas` | Lista de regras disparadas (abordagens com regras) |
| `confianca` | Score de confiança entre 0.0 e 1.0 |
| `abordagem` | Método utilizado (regras, llm, hibrido) |

---

## Métricas de avaliação

- Precisão, revocação e F1 por classe (equipe, urgência, prioridade)
- Matriz de confusão
- Taxa de campos sem suporte no texto (indicador de alucinação)
- Taxa de casos críticos subestimados
- Taxa de encaminhamento para revisão humana
- Robustez em paráfrases e variações de escrita
- Latência por abordagem

As definições e limitações de cada métrica estão documentadas em `src/evaluation/metrics.py`.

> **Importante:** a avaliação usa rótulos esperados do dataset sintético, nunca
> um LLM como árbitro da saída de outro LLM.

---

## Solução de problemas comuns

### Ollama não está rodando

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solução:** inicie o Ollama antes de executar as abordagens LLM ou híbrida:

```bash
ollama serve
```

### Modelo não encontrado

```
model 'qwen3:4b' not found
```

**Solução:** baixe o modelo:

```bash
ollama pull qwen3:4b
```

Ou altere `OLLAMA_MODEL` no `.env` para um modelo já disponível (`ollama list`).

### Avaliação apenas das regras (sem Ollama)

```bash
python -m src.evaluation --approaches regras
```

### Erro de importação (`ModuleNotFoundError: src`)

Certifique-se de executar os comandos a partir da raiz do projeto (onde está `pyproject.toml`) e com o ambiente virtual ativado.

---

## Limitações do protótipo

- Dataset sintético com 100 casos — não representa a diversidade de um ambiente industrial real.
- O modelo LLM local (qwen3:4b) tem capacidade limitada em comparação a modelos maiores; resultados podem variar.
- Regras de exemplo cobrem cenários genéricos; para uso real precisariam de revisão por especialistas de domínio.
- Latências de LLM dependem do hardware local e podem ser altas em máquinas sem GPU.
- **Nenhuma ação externa é executada** — o sistema não encaminha OS para sistemas reais.

---

## Aviso acadêmico

Este sistema é um protótipo desenvolvido exclusivamente para fins de pesquisa acadêmica.
Resultados gerados não substituem o julgamento de profissionais qualificados.
Não utilizar para tomada de decisões em ambiente industrial sem validação especializada.
