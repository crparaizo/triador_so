# src/schemas/ — Definições dos modelos de dados

Esta pasta define os **formatos de dados** do sistema — o "vocabulário" que todos os módulos usam para se comunicar. Pense nelas como os formulários padronizados do sistema: cada campo tem nome, tipo e regra de validação.

Todos os modelos são definidos com **Pydantic**, uma biblioteca que valida automaticamente os dados quando um objeto é criado. Se um campo obrigatório estiver faltando ou tiver o tipo errado, um erro descritivo é gerado imediatamente.

---

## Arquivos

### `triage.py` — O resultado da triagem
Define o modelo central do sistema: **`TriageResult`** — o objeto que representa a resposta completa de uma triagem.

Campos do `TriageResult`:
- `id`: identificador único gerado automaticamente
- `timestamp`: data e hora da análise
- `abordagem`: qual dos três métodos gerou este resultado (`REGRAS`, `LLM` ou `HIBRIDO`)
- `texto_entrada`: o relato original enviado pelo usuário
- `urgencia`: nível de urgência (`IMEDIATA`, `ALTA`, `MEDIA`, `BAIXA`, `DESCONHECIDA`)
- `prioridade`: prioridade (`P1`, `P2`, `P3`, `P4`, `DESCONHECIDA`)
- `categoria`: tipo de falha (Mecânica, Elétrica, Instrumentação, etc.)
- `equipe_sugerida`: nome da equipe de manutenção recomendada
- `regras_acionadas`: lista dos IDs das regras que foram aplicadas (ex: `["RULE-001", "RULE-004"]`). Vazio para o LLM puro.
- `evidencias`: dicionário que mostra de onde veio cada informação (ex: `{"ativo": "bomba BOMB-001", "urgencia": "Urgente"}`)
- `requer_revisao_humana`: `true` se o sistema detectou incerteza ou risco que exige um especialista
- `motivo_revisao`: texto explicando por que a revisão humana é necessária (quando aplicável)
- `confianca`: número de 0 a 1 indicando a confiança do sistema na classificação
- `latencia_ms`: tempo de processamento em milissegundos
- `campos_sem_suporte`: campos classificados sem evidência direta no relato (indicador de possível alucinação)

Também define os **enums** (listas de valores válidos):
- `UrgencyLevel`: IMEDIATA, ALTA, MEDIA, BAIXA, DESCONHECIDA
- `PriorityLevel`: P1, P2, P3, P4, DESCONHECIDA
- `FailureCategory`: MECANICA, ELETRICA, INSTRUMENTACAO, UTILIDADES, SEGURANCA, QUALIDADE, PROCESSO, INFRAESTRUTURA, TI_AUTOMACAO, OUTROS, FORA_DO_ESCOPO, DESCONHECIDA
- `ApproachType`: REGRAS, LLM, HIBRIDO

### `assets.py` — Ativos e equipes
Define o formato dos **equipamentos** (`Asset`) e **equipes** (`Team`) cadastrados:

- `Asset`: tag, nome, tipo, localização, equipe responsável, criticidade, observações
- `Team`: nome, especialidades, contato, disponibilidade
- `KnowledgeBase`: a base de conhecimento completa (lista de Assets + lista de Teams), com métodos de busca:
  - `get_asset_by_tag("BOMB-001")` — busca exata por código
  - `find_assets_by_location("Setor A")` — busca por localização

### `extraction.py` — Informações extraídas do texto
Define o que os **extratores** retornam após analisar o relato:

- `ExtractedInfo`: resultado da extração — ativo mencionado, sintomas, localização, flags de impacto/risco, evidências textuais, confiança e lista de campos não encontrados no texto
- `ContextData`: resultado do enriquecimento — o ativo encontrado na base local, equipes candidatas e a fonte das informações

### `__init__.py`
Exporta todos os modelos para facilitar as importações: `from src.schemas import TriageResult, Asset, Team`.
