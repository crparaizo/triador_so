# Dataset Sintético de Triagem de Ordens de Serviço

> ⚠️ **DADOS SINTÉTICOS**
> Este dataset foi gerado exclusivamente para fins acadêmicos de monografia
> de especialização em Controle e Automação (IFSP).
> **Não representa eventos, equipamentos ou instalações reais.**
> **Não utilizar para decisões operacionais.**
> Toda análise baseada neste dataset deve ser revisada por especialistas
> antes de qualquer uso em ambiente industrial.

---

## Versão e Data de Criação

- **Versão**: 1.0.0
- **Data de criação**: 2026-07-01
- **Arquivo**: `datasets/synthetic_cases.json`
- **Total de casos**: 100

---

## Descrição dos Campos JSON

Cada objeto no array JSON possui os seguintes campos:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | string | sim | Identificador único do caso. Padrão: `CASE-NNN` (3 dígitos) |
| `tipo` | string (enum) | sim | Tipo/estilo do caso — ver seção abaixo |
| `texto` | string | sim | Relato da ocorrência em português |
| `esperado` | objeto | sim | Gabarito de avaliação (ver subcampos abaixo) |
| `referencia_caso_canonico` | string \| null | não | ID do caso CANONICO base (para tipo=PARAFRASES) |
| `notas` | string \| null | não | Observações sobre o caso, regras esperadas ou lacunas documentadas |

### Subcampos de `esperado`

| Campo | Tipo | Valores válidos |
|---|---|---|
| `urgencia` | string | `IMEDIATA`, `ALTA`, `MEDIA`, `BAIXA`, `DESCONHECIDA` |
| `prioridade` | string | `P1`, `P2`, `P3`, `P4`, `DESCONHECIDA` |
| `categoria` | string | `MECANICA`, `ELETRICA`, `INSTRUMENTACAO`, `UTILIDADES`, `SEGURANCA`, `QUALIDADE`, `PROCESSO`, `INFRAESTRUTURA`, `TI_AUTOMACAO`, `OUTROS`, `FORA_DO_ESCOPO`, `DESCONHECIDA` |
| `equipe` | string | `Manutenção Mecânica`, `Manutenção Elétrica`, `Instrumentação e Controle`, `Utilidades`, `Infraestrutura e Facilities`, `TI e Automação`, `DESCONHECIDA` |
| `requer_revisao_humana` | boolean | `true` / `false` |

---

## Distribuição por Tipo

| Tipo | Quantidade | IDs | Descrição |
|---|:---:|---|---|
| CANONICO | 15 | CASE-001 a CASE-015 | Casos de referência com texto direto e preciso |
| PARAFRASES | 15 | CASE-016 a CASE-030 | Reescrita dos canônicos com linguagem diferente |
| ABREVIACOES | 8 | CASE-031 a CASE-038 | Relatos com abreviações industriais comuns |
| ERROS_ESCRITA | 8 | CASE-039 a CASE-046 | Relatos com 1–3 erros ortográficos ou de digitação |
| MULTIPLOS_SINTOMAS | 8 | CASE-047 a CASE-054 | Relatos com 3+ sintomas de subcategorias diferentes |
| INCOMPLETOS | 8 | CASE-055 a CASE-062 | Relatos vagos sem tag de ativo ou sintoma específico |
| CONTRADITORIOS | 8 | CASE-063 a CASE-070 | Relatos com contradição interna |
| FORA_ESCOPO | 8 | CASE-071 a CASE-078 | Solicitações fora do escopo de manutenção industrial |
| ALTA_CRITICIDADE | 11 | CASE-079 a CASE-089 | Emergências de criticidade máxima |
| REVISAO_HUMANA | 11 | CASE-090 a CASE-100 | Cenários que exigem revisão humana por incerteza |
| **Total** | **100** | | |

---

## Distribuição por Categoria

| Categoria | Quantidade aproximada | Observação |
|---|:---:|---|
| MECANICA | ~21 | Maior grupo; vibração, ruptura, mecânica geral |
| ELETRICA | ~15 | Painéis, geradores, transformadores |
| INSTRUMENTACAO | ~10 | Transmissores, válvulas de controle, sensores |
| UTILIDADES | ~9 | Caldeiras, chillers, vapor |
| DESCONHECIDA | ~15 | Casos incompletos, contraditórios e de revisão sem diagnóstico |
| FORA_DO_ESCOPO | 8 | Todos os FORA_ESCOPO |
| OUTROS | ~5 | Casos sem categoria primária definida |
| SEGURANCA | ~5 | Emergências de segurança |
| INFRAESTRUTURA | ~5 | HVAC, elevadores, facilities |
| PROCESSO | ~3 | Desvios de processo e reator |
| QUALIDADE | ~2 | Produto fora de especificação |
| TI_AUTOMACAO | ~2 | SCADA, CLP, supervisório |

---

## Critérios de Anotação

O gabarito (`esperado`) foi definido com base nas seguintes regras:

| Regra/Critério | Descrição |
|---|---|
| RULE-001 | Risco à segurança → urgencia=IMEDIATA, prioridade=P1, revisão=true |
| RULE-002 | Fogo/fumaça/emergência → urgencia=IMEDIATA, prioridade=P1, revisão=true |
| RULE-003 | Painel elétrico com falha → ELETRICA, IMEDIATA/P1, revisão NR-10 |
| RULE-004 | Impacto de produção + categoria alta → prioridade=P1 |
| RULE-005 | Ruptura mecânica → MECANICA, IMEDIATA/P1, revisão=true |
| RULE-006 | Caldeira com impacto → UTILIDADES, IMEDIATA/P1, revisão NR-13 |
| RULE-007 | Falha de instrumentação → INSTRUMENTACAO, ALTA/P2 |
| RULE-008 | Utilidades com impacto → urgencia=ALTA |
| RULE-010 | Falha elétrica geral → ELETRICA, ALTA/P2 |
| RULE-011 | Falha mecânica → MECANICA, ALTA/P2 |
| RULE-012 | SCADA/CLP → TI_AUTOMACAO, ALTA/P2 |
| RULE-013 | Processo com impacto → PROCESSO, ALTA/P2 |
| RULE-014 | Falha mecânica geral → MEDIA/P3 (menor prioridade que RULE-011) |
| RULE-015 | Utilidades sem impacto → MEDIA/P3 |
| RULE-016 | Manutenção preventiva → BAIXA/P4 |

Para casos sem regra aplicável, o gabarito reflete o julgamento humano esperado (ground truth), que o sistema híbrido/LLM deve aproximar.

---

## Fundamentação Normativa

Embora sintético, o dataset usa as Normas Regulamentadoras (NR) de segurança do
trabalho como gatilhos de revisão humana obrigatória nas regras de segurança. O
objetivo é dar rastreabilidade a esses critérios, sem certificar conformidade, já
que se trata de um protótipo acadêmico com dados fictícios.

| Norma | Redação considerada | O que fundamenta neste projeto |
|---|---|---|
| **NR-1** — Disposições gerais e gerenciamento de riscos ocupacionais | Redação vigente (gerenciamento de riscos ocupacionais) | Nível de risco pela combinação de severidade e probabilidade (item 1.5.4.4.2) e exigência de critérios documentados (item 1.5.4.4.2.2): cada regra registra no campo `fundamentacao` a norma que a determina ou se o critério é da autora. |
| **NR-3** — Embargo e interdição | Portaria SEPRT nº 1.068/2019 | Conceito de grave e iminente risco (item 3.2.1), base da urgência IMEDIATA com revisão obrigatória nas regras de segurança (RULE-001, RULE-002 e RULE-019). |
| **NR-10** — Segurança em instalações e serviços em eletricidade | Portaria SEPRT nº 915/2019 (vigente até 31/05/2027) | Revisão humana obrigatória para intervenções em painéis, quadros e equipamentos elétricos de potência (RULE-003). "Alta tensão" segue o glossário: acima de 1000 V CA ou 1500 V CC. |
| **NR-13** — Caldeiras, vasos de pressão, tubulações e tanques metálicos de armazenamento | Portaria MTP nº 1.846/2022, alterada pela Portaria MTP nº 4.219/2022 | Campo de aplicação (item 13.2.1) e condições de grave e iminente risco (item 13.3.1): dispositivo de segurança ausente, bloqueado ou indisponível em caldeira ou vaso de pressão leva a IMEDIATA/P1 com revisão (RULE-019). A caldeira CAL-001 traz `normas_aplicaveis: ["NR-13"]` em `assets.yaml`, de modo que a RULE-019 reconhece o equipamento pelo cadastro mesmo quando o relato não o nomeia. Caldeira com impacto na produção: RULE-006. Pressão relatada acima da PMTA cadastrada da caldeira (PMTA, Glossário; válvula de segurança ajustada em valor igual ou inferior à PMTA, item 13.4.1.2, a): RULE-021, com urgência IMEDIATA por critério da autora. |
| **NR-35** — Trabalho em altura | Portaria MTE nº 1.259/2026 | Atividade com diferença de nível acima de 2 m e risco de queda (item 35.2.1) exige revisão humana, por depender de análise de risco e permissão de trabalho (item 35.3.1) (RULE-020). |

O campo `criticidade` (ALTA/MEDIA/BAIXA) dos ativos foi definido pela autora com
base na lógica de priorização de ordens de serviço que combina a prioridade do
tipo de trabalho, a criticidade do ativo e o tempo decorrido desde a abertura da
OS (English; Yunusa-Kaltungo, 2022, Seção 4).

---

## Conjunto de alarmes simulados

O arquivo `datasets/alarm_events.json` traz 10 eventos de um supervisório (SCADA)
simulado, cada um com o gabarito anotado pela autora e o critério em `notas`.
O script `scripts/gerar_casos_alarme.py` converte cada evento no texto de uma OS
(`src/alarms`) e grava `datasets/alarm_cases.json`, com casos do tipo `ALARME`,
que podem ser avaliados como o conjunto principal:

```bash
python scripts/gerar_casos_alarme.py
python -m src.evaluation --dataset datasets/alarm_cases.json
```

A PMTA da caldeira CAL-001 em `data/assets.yaml` (1.000 kPa) é fictícia e serve
apenas para a RULE-021. Nenhum dos 100 relatos do conjunto principal contém valor
de pressão, de modo que essa regra não altera os resultados dele.

---

## Conjunto de validação (casos não vistos pelas regras)

O arquivo `datasets/holdout_cases.json` traz 100 casos novos (`VAL-001` a `VAL-100`),
redigidos depois de concluída a base de regras, na mesma distribuição por tipo do
conjunto principal e com os mesmos ativos, categorias e equipes. Os relatos foram
escritos a partir do cadastro de ativos e das categorias, sem consulta às listas de
palavras-chave das regras, e o critério de cada gabarito está em `notas`. O arquivo é
gerado por `scripts/gerar_casos_validacao.py`; a planilha de revisão do gabarito está
em `results/holdout_revisao_gabarito.csv`.

```bash
python scripts/gerar_casos_validacao.py
python -m src.evaluation --dataset datasets/holdout_cases.json
python scripts/analise_estatistica.py results/evaluation_raw_<timestamp>.json --dataset datasets/holdout_cases.json
```

As regras e o motor **não** devem ser ajustados com base nos erros deste conjunto;
caso contrário, ele deixa de medir o desempenho em casos não vistos (Seção 3.4.5 da
monografia).

---

## Lacunas Documentadas

As seguintes situações expõem limitações conhecidas do motor de regras:

1. **INFRAESTRUTURA (HVAC, elevadores)**: Nenhuma regra específica para categoria INFRAESTRUTURA sem condição de emergência. CASE-010 e CASE-025 são exemplos; as regras produzem DESCONHECIDA, mas o gabarito espera INFRAESTRUTURA/MEDIA/P3.

2. **QUALIDADE (produto fora de especificação)**: Nenhuma regra cobre produtos fora de spec sem impacto de produção. CASE-013 e CASE-028 são exemplos; regras produzem DESCONHECIDA.

3. **SEGURANCA — equipe sem atribuição**: As regras classificam urgência corretamente (IMEDIATA/P1) mas não definem equipe para categoria SEGURANCA. CASE-014 e CASE-029 ilustram este gap — regras deixam equipe indefinida.

4. **Manutenção preventiva**: RULE-014 (prio=40) supera RULE-016 (prio=30), causando over-escalation para casos preventivos. CASE-015 e CASE-030 ilustram este comportamento.

---

## Como Adicionar Novos Casos

1. Abra `datasets/synthetic_cases.json` em um editor de texto.
2. Acrescente um novo objeto JSON ao array seguindo a estrutura descrita acima.
3. O `id` deve seguir o padrão `CASE-NNN` com 3 dígitos; use o próximo número disponível.
4. Se o tipo for `PARAFRASES`, preencha `referencia_caso_canonico` com o ID de um caso `CANONICO` existente.
5. Valide o arquivo executando:
   ```bash
   python -c "from src.data.dataset_loader import load_dataset; cases = load_dataset(); print(f'{len(cases)} casos OK')"
   ```
6. Execute os testes para garantir que as invariantes são satisfeitas:
   ```bash
   pytest tests/test_dataset.py -v
   ```

---

## Referências aos Arquivos de Domínio

| Arquivo | Conteúdo |
|---|---|
| `data/rules.yaml` | 21 regras de produção com condições e ações |
| `data/assets.yaml` | 18 ativos com tag, criticidade, localização, equipe responsável e normas aplicáveis (NR-10 nos equipamentos de potência, NR-13 na caldeira) |
| `data/teams.yaml` | 6 equipes com especialidades e disponibilidade |
| `data/categories.yaml` | 12 categorias com palavras-chave e equipe padrão |

---

## Limitações do Dataset Sintético

1. **Geração artificial**: Os casos foram escritos com auxílio de IA Generativa seguindo padrões industriais genéricos. Não representam incidentes reais documentados.

2. **Viés de cobertura**: As categorias e regras refletem apenas os dados de domínio configurados em `data/`. Falhas em equipamentos não cadastrados não estão representadas.

3. **Sem dados temporais**: O dataset não inclui informações de turno, horário, histórico de falhas ou sazonalidade.

4. **Textos em português do Brasil**: Variações de dialeto, jargões regionais ou termos específicos de determinadas indústrias podem não estar representados.

5. **Gabarito baseado em regras e julgamento sintético**: O campo `esperado` foi anotado com base nas regras do sistema e julgamento editorial — não por especialistas em manutenção industrial real.

6. **Tamanho limitado**: Com 100 casos, o dataset é suficiente para demonstração e comparação de abordagens, mas insuficiente para treinamento ou validação estatística robusta.

7. **Sem casos de equipamentos novos**: O dataset cobre apenas ativos cadastrados em `data/assets.yaml`. Equipamentos não cadastrados gerariam casos de DESCONHECIDA não cobertos.
