# sessions/ — Histórico de análises da interface

Esta pasta armazena o **histórico das triagens realizadas** pela interface Streamlit. Cada análise feita pelo usuário na tela de "Triagem" gera um arquivo aqui.

> Os arquivos nesta pasta são gerados em tempo de execução. A pasta está vazia no repositório — os arquivos surgem ao usar a interface.

---

## Como os arquivos são gerados?

Toda vez que o usuário insere um relato na interface e clica em "Analisar", o sistema executa as três abordagens e salva automaticamente os resultados. O arquivo é criado em segundo plano — o usuário não precisa fazer nada.

---

## Formato dos arquivos

Cada arquivo segue o padrão `YYYYMMDD_HHMMSS_<id>.json` e contém:

```json
{
  "timestamp": "2025-10-11T14:30:00",
  "texto": "Relato original inserido pelo usuário",
  "results": {
    "regras": { "urgencia": "ALTA", "prioridade": "P2", ... },
    "llm":    { "urgencia": "ALTA", "prioridade": "P2", ... },
    "hibrido":{ "urgencia": "ALTA", "prioridade": "P1", ... }
  }
}
```

Cada entrada em `results` é um `TriageResult` completo com urgência, prioridade, categoria, equipe sugerida, evidências, regras acionadas e latência.

---

## Visualizando o histórico

Na interface Streamlit, acesse a aba **"Histórico"** na barra lateral para ver todas as análises anteriores, com filtro por data e possibilidade de expandir cada sessão para ver os detalhes.

O botão "Limpar histórico" (com confirmação) apaga todos os arquivos desta pasta.

---

## Privacidade

Os textos dos relatos inseridos pelo usuário são salvos nestes arquivos. Em um ambiente de uso real, isso precisaria de política de retenção de dados adequada. Como este é um protótipo acadêmico de uso local, os dados ficam apenas na sua máquina.
