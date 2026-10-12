# src/ — Código-fonte principal

Esta pasta contém todo o código Python do sistema de triagem. Ela é organizada em **submódulos com responsabilidades separadas** — cada pasta cuida de uma parte específica do problema.

---

## Visão geral do fluxo

```
Texto do relato (entrada)
        │
        ▼
┌───────────────┐     ┌──────────────────┐     ┌───────────────┐
│  extraction/  │────▶│     data/        │────▶│    rules/     │
│  Extrai info  │     │ Enriquece contexto│     │  Classifica   │
└───────────────┘     └──────────────────┘     └───────────────┘
                                                       │
                                                       ▼
                                              ┌───────────────┐
                                              │  TriageResult │
                                              │  (saída final)│
                                              └───────────────┘
```

---

## Submódulos

### `schemas/` — Definições dos dados
Descreve o "formato" de todos os objetos do sistema: como é um resultado de triagem, como é um ativo, o que é uma informação extraída. É a fundação sobre a qual todo o resto é construído.

### `config/` — Configurações do sistema
Lê as configurações do arquivo `.env` (qual modelo usar, qual URL do Ollama, etc.) e as disponibiliza para o resto do código.

### `data/` — Acesso aos dados
Carrega os arquivos YAML da pasta `data/` da raiz, valida seu conteúdo e disponibiliza funções para buscar ativos, equipes e categorias. Também carrega o dataset de avaliação.

### `extraction/` — Extração de informações do texto
Dois extratores: um que usa palavras-chave (rápido, determinístico) e outro que usa o LLM (mais flexível, mais lento).

### `rules/` — Motor de regras
Implementa as regras de decisão declarativas: dadas as informações extraídas, qual é a urgência, a prioridade e a equipe responsável?

### `approaches/` — As três abordagens comparadas
Monta os três pipelines completos de triagem: regras puras, LLM puro e híbrido.

### `orchestration/` — Integração com LangChain
Envolve cada pipeline numa estrutura do LangChain (`RunnableSequence`) para compatibilidade com o ecossistema da biblioteca.

### `evaluation/` — Avaliação e métricas
Executa os três pipelines sobre o dataset sintético, calcula as métricas de desempenho e salva os relatórios.

### `interface/` — Interface web Streamlit
A tela que o usuário vê: formulário de entrada, exibição dos três resultados em abas, histórico de análises.

### `utils/` — Utilitários compartilhados
Funções auxiliares usadas por mais de um módulo (ex: o parser defensivo de JSON do LLM).

---

## Arquivo raiz: `__init__.py`
Marca a pasta `src/` como um pacote Python, permitindo que os módulos se importem entre si com `from src.schemas import ...`.
