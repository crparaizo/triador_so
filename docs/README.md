# docs/ — Documentação técnica do projeto

Esta pasta contém documentação de referência para quem quer entender a arquitetura do sistema em maior profundidade.

---

## Arquivos

### `architecture.md` — Arquitetura do sistema
Descreve como o sistema é organizado internamente. Inclui:

- **Diagrama das três abordagens**: mostra o fluxo de dados de cada pipeline (regras, LLM puro e híbrido) do texto de entrada até o resultado final
- **Responsabilidade de cada módulo**: o que cada pasta de `src/` faz e como os módulos se comunicam
- **Formato de entrada e saída**: estrutura do `TriageResult` (o objeto de resposta do sistema) com todos os campos explicados
- **Como adicionar uma nova regra**: passo a passo para modificar `data/rules.yaml`
- **Como adicionar casos ao dataset**: instruções para expandir o conjunto de teste
- **Definições das métricas de avaliação**: o que cada métrica mede, como é calculada e quais são suas limitações

---

## Para quem é esta documentação?

- Para o leitor da monografia que quer entender as decisões de projeto
- Para quem quiser reproduzir ou estender o protótipo
- Para a banca de avaliação que precise verificar a implementação

O `README.md` na raiz do projeto é o ponto de partida para instalação e uso. Esta pasta aprofunda os detalhes técnicos.
