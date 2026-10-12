# datasets/ — Conjunto de dados para avaliação

Esta pasta contém o **conjunto de casos de teste sintéticos** usados para avaliar e comparar as três abordagens de triagem (regras, LLM puro e híbrido).

> ⚠️ **DADOS SINTÉTICOS** — Todos os casos foram criados manualmente para fins acadêmicos. Não representam ocorrências reais de nenhuma planta industrial. Veja a seção de limitações ao final.

---

## Para que serve esta pasta?

Para comparar as três abordagens de forma justa, todas precisam ser testadas com os **mesmos casos de entrada** e avaliadas contra as **mesmas respostas esperadas** (gabarito).

Esta pasta fornece exatamente isso: um conjunto de 100 relatos de ocorrência em texto livre, cada um com a resposta correta anotada manualmente. O comando `python -m src.evaluation` usa estes dados automaticamente.

---

## Arquivos

### `synthetic_cases.json` — Os 100 casos de teste
Arquivo principal. Contém um array de 100 objetos JSON, cada um representando um caso de teste. Estrutura de cada caso:

```json
{
  "id": "CASE-001",
  "tipo": "CANONICO",
  "texto": "A bomba BOMB-001 está com vazamento de óleo...",
  "esperado": {
    "urgencia": "ALTA",
    "prioridade": "P2",
    "categoria": "MECANICA",
    "equipe": "Manutenção Mecânica",
    "requer_revisao_humana": false
  },
  "referencia_caso_canonico": null,
  "notas": "Caso claro com ativo identificado e sintoma explícito"
}
```

**Distribuição dos casos por tipo:**

| Tipo | Quantidade | O que representa |
|------|-----------|-----------------|
| `CANONICO` | 15 | Relatos claros e completos — o "caso ideal" |
| `PARAFRASES` | 15 | As mesmas situações dos canônicos, escritas de forma diferente |
| `ABREVIACOES` | 10 | Relatos com siglas e abreviações típicas de operadores |
| `ERROS_ESCRITA` | 10 | Relatos com erros de digitação e ortografia |
| `MULTIPLOS_SINTOMAS` | 10 | Relatos com dois ou mais problemas simultâneos |
| `INCOMPLETOS` | 10 | Relatos vagos, sem ativo identificado ou sem sintoma claro |
| `CONTRADITORIOS` | 8 | Relatos com informações conflitantes entre si |
| `FORA_ESCOPO` | 8 | Mensagens que não são ordens de serviço industriais |
| `ALTA_CRITICIDADE` | 11 | Situações com risco de segurança, incêndio ou explosão |
| `REVISAO_HUMANA` | 11 | Casos onde a resposta correta é sinalizar incerteza |

### `sample_report.json` — Exemplo de relatório de avaliação
Mostra o formato exato do arquivo gerado por `python -m src.evaluation`. Contém valores fictícios mas realistas, útil para entender o que esperar sem precisar executar a avaliação completa.

> `"_aviso": "Exemplo sintético gerado para fins de demonstração. Não representa execução real."`

### `DATASET_README.md` — Documentação técnica detalhada
Documentação mais detalhada sobre os critérios de anotação, limitações conhecidas e instruções para adicionar novos casos.

---

## Limitações conhecidas

- **100 casos é um número pequeno** para métricas estatisticamente confiáveis. Os resultados indicam tendências, não conclusões definitivas.
- Os casos foram anotados por um único avaliador (o autor da monografia), sem validação por especialistas em manutenção industrial.
- A distribuição dos tipos de casos foi escolhida para cobrir diversidade, não para refletir a distribuição real de ocorrências numa planta.
- Os casos `CONTRADITORIOS` têm contradições definidas editorialmente — não há verificação automática de que o texto é realmente ambíguo para um leitor humano.
