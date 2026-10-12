# data/ — Base de conhecimento local

Esta pasta contém os **dados de referência** que o sistema usa para enriquecer e classificar as ordens de serviço. Todos os arquivos são escritos em YAML, um formato de texto simples que qualquer editor consegue abrir.

> Estes dados são **fictícios e sintéticos**, criados exclusivamente para fins acadêmicos. Não representam uma planta industrial real.

---

## Para que serve esta pasta?

Quando o sistema recebe um relato de ocorrência, ele precisa de contexto para tomar uma decisão. Por exemplo:
- "A bomba BOMB-001 está com vazamento" — o sistema consulta `assets.yaml` para saber que essa bomba é de criticidade ALTA e qual equipe cuida dela.
- "Ruído excessivo no motor" — o sistema consulta `categories.yaml` para identificar que isso é uma falha mecânica.
- O motor de regras consulta `rules.yaml` para decidir urgência e prioridade.

Estes quatro arquivos formam a **memória local** do protótipo.

---

## Arquivos

### `assets.yaml` — Equipamentos cadastrados
Lista os 18 ativos (equipamentos) fictícios da planta. Cada ativo tem:
- **tag**: código único do equipamento (ex: `BOMB-001`, `COMP-002`)
- **nome**: nome descritivo (ex: "Bomba de Água da Linha 1")
- **tipo**: categoria do equipamento (bomba, compressor, motor, painel elétrico, etc.)
- **localizacao**: setor ou área da planta onde está instalado
- **equipe_responsavel**: qual equipe cuida desse ativo por padrão
- **criticidade**: `ALTA`, `MEDIA` ou `BAIXA` — indica o impacto de uma falha na produção
- **observacoes**: notas adicionais relevantes

### `teams.yaml` — Equipes de manutenção
Lista as 6 equipes disponíveis para atender as ordens de serviço:
- Manutenção Mecânica
- Manutenção Elétrica
- Instrumentação e Controle
- Utilidades
- Infraestrutura e Facilities
- TI e Automação

Cada equipe tem suas especialidades listadas, o que ajuda o motor de regras a fazer o encaminhamento correto.

### `categories.yaml` — Categorias de falha
Define as categorias de falha reconhecidas pelo sistema (Mecânica, Elétrica, Instrumentação, etc.). Para cada categoria, há:
- **descricao**: o que esta categoria abrange
- **palavras_chave**: lista de termos que indicam este tipo de falha (ex: "vazamento", "vibração", "ruptura" para falhas mecânicas). O extrator por palavras-chave usa esta lista.
- **equipe_padrao**: equipe que normalmente atende este tipo de falha
- **urgencia_padrao**: urgência presumida na ausência de outros indicadores

### `rules.yaml` — Regras de produção
Contém as 18 regras de decisão do motor de regras. Cada regra especifica:
- **condições** que devem ser satisfeitas (tipo de falha, presença de risco, impacto na produção, etc.)
- **ações** a executar quando as condições são atendidas (urgência, prioridade, equipe, necessidade de revisão humana)
- **prioridade_regra**: quando mais de uma regra se aplica, a de maior número prevalece

Exemplos de regras:
- RULE-001: Se há risco de segurança → urgência IMEDIATA, P1, revisão humana obrigatória
- RULE-003: Falha elétrica em alta tensão → IMEDIATA, P1, equipe Elétrica, revisão obrigatória (NR-10)
- RULE-016: Manutenção preventiva programada → BAIXA, P4

---

## Como alterar estes dados?

Para adicionar um novo ativo: edite `assets.yaml` seguindo o mesmo padrão dos existentes.  
Para adicionar uma nova regra: edite `rules.yaml` com um `id` único (ex: `RULE-019`) e certifique-se de que as condições e ações estão corretas.  
Para adicionar palavras-chave a uma categoria: edite `categories.yaml` na lista `palavras_chave` da categoria desejada.

Qualquer alteração é lida automaticamente na próxima execução — não é necessário recompilar nada.
