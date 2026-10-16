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

Embora sintético, o dataset e os dados de domínio não foram concebidos de forma
arbitrária: sua nomenclatura, estrutura e critérios de conformidade apoiam-se em
normas reconhecidas de manutenção industrial e segurança do trabalho. O objetivo
é dar rastreabilidade normativa ao caso de uso — e não certificar conformidade,
já que se trata de um protótipo acadêmico com dados fictícios.

### Normas de referência

| Norma | Título | O que fundamenta neste projeto |
|---|---|---|
| **ABNT NBR ISO 14224** (base ISO 14224:2016) | Indústrias de petróleo e gás natural — Coleta e intercâmbio de dados de confiabilidade e manutenção para equipamentos | Taxonomia de classes de equipamento (campo `classe_iso14224` em `data/assets.yaml`) e a organização dos dados de falha/manutenção. |
| **ABNT NBR 5462:1994** | Confiabilidade e mantenabilidade (terminologia) | Vocabulário de falha, defeito, pane, manutenção corretiva/preventiva, confiabilidade, mantenabilidade e criticidade usado nos relatos e no sistema. |
| **NR-10** | Segurança em Instalações e Serviços em Eletricidade | Gatilho de revisão humana obrigatória para intervenções elétricas de risco (RULE-003; ver `data/rules.yaml`). |
| **NR-13** | Caldeiras, Vasos de Pressão, Tubulações e Tanques Metálicos de Armazenamento | Gatilho de revisão humana obrigatória para caldeiras/vapor (RULE-006). |
| **NR-35** | Trabalho em Altura | Gatilho de revisão para cenários de segurança em altura (RULE-001/002, categoria SEGURANCA). |

> Confira o título e o ano/edição vigentes no catálogo oficial da ABNT e no site do
> Ministério do Trabalho e Emprego (MTE) antes da citação final na monografia — a
> edição nacional da NBR ISO 14224 e as redações das NRs são atualizadas
> periodicamente.

### Mapeamento ISO 14224 dos ativos

Cada ativo em `data/assets.yaml` recebeu o campo `classe_iso14224`, mapeando-o à
taxonomia de classes de equipamento da norma. Como a ISO 14224 é específica das
indústrias de petróleo, gás e petroquímica, parte dos ativos (quadros de
distribuição, MCC, HVAC, elevador) **não possui classe direta** — esses casos são
marcados explicitamente como "Não coberto diretamente pela ISO 14224", evidenciando
os limites de aplicabilidade da norma a uma planta genérica.

| Classe ISO 14224 | Ativos (tags) |
|---|---|
| Bombas (Pumps) | BOMB-001, BOMB-002 |
| Compressores (Compressors) | COMP-001, COMP-002, COMP-003 |
| Motores elétricos (Electric motors) | MOTOR-001 |
| Transformadores de potência (Power transformers) | TRANS-001 |
| Geradores elétricos (Electric generators) | GER-001 |
| Dispositivos de entrada (Input devices) | SENS-001, TRANS-002 |
| Válvulas (Valves) | VALV-001, VALV-002 |
| Aquecedores e caldeiras (Heaters and boilers) | CAL-001 |
| Trocadores de calor (Heat exchangers) | CHIL-001 |
| Não coberto diretamente pela ISO 14224 | PANEL-001, PANEL-002, HVAC-001, ELEV-001 |

### Glossário (terminologia ABNT NBR 5462:1994)

Termos empregados nos relatos, regras e métricas, conforme a terminologia da norma:

- **Falha**: término da capacidade de um item desempenhar a função requerida.
- **Defeito**: desvio de uma característica em relação aos requisitos, que pode ou não levar à falha.
- **Pane**: estado de um item incapaz de desempenhar a função requerida (resultado de uma falha).
- **Manutenção corretiva**: efetuada após a ocorrência de uma pane, para recolocar o item em condição de funcionamento.
- **Manutenção preventiva**: efetuada em intervalos predeterminados para reduzir a probabilidade de falha (relacionada ao tipo de caso e à RULE-016).
- **Criticidade**: grau de impacto de um item sobre a produção/segurança — base do campo `criticidade` (ALTA/MEDIA/BAIXA) dos ativos.

> As definições acima são paráfrases para uso interno; o texto normativo exato
> deve ser consultado na ABNT NBR 5462:1994 ao citá-las na monografia.

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
| `data/rules.yaml` | 18 regras de produção com condições e ações |
| `data/assets.yaml` | 18 ativos com tag, criticidade, localização, equipe responsável e classe ISO 14224 |
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
