# Fluxos LangChain (LCEL) da triagem

> Arquivo gerado por `python -m src.orchestration`; não editar à mão.
> Protótipo acadêmico — não usar em ambiente industrial real.

Cada fluxo é uma cadeia LCEL composta de Runnables nomeados que trocam um
dicionário de estado. Todos começam com o nó `preparacao_entrada` (marca o início
da medição de latência e prepara o texto) seguido do envelope
`triagem_com_falha_segura`, um `RunnableWithFallbacks`: se qualquer nó do núcleo
lançar exceção, o fallback `resultado_seguro` devolve um resultado com revisão
humana obrigatória. Como o LangChain desenha esse envelope como um único nó opaco,
os diagramas abaixo mostram o núcleo de cada fluxo.

Leitura dos nós gerados pelo LCEL:

- `Parallel<...>Input` / `Parallel<...>Output`: ramos de um `RunnableParallel`,
  criados por `RunnablePassthrough.assign`; os nós entre eles rodam em paralelo.
- `Passthrough`: repassa o estado recebido para ser mesclado às novas chaves.
- `extracao_llm_com_fallback` (só no híbrido): `RunnableWithFallbacks` que executa
  `extracao_llm` e, se ela falhar (erro de parse ou exceção), usa
  `extracao_palavras_chave`.
- `motor_regras_producao`: o motor de regras inteiro, em um único nó; as regras
  continuam declaradas em `data/rules.yaml`.

Os fluxos por regras e híbrido têm a mesma estrutura e diferem apenas no nó de
extração. O cenário-diagnóstico `regras_catref` usa o mesmo grafo do fluxo por
regras (muda só a origem da categoria em `deteccao_categoria`).

## Fluxo por regras de produção

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	Parallel\3cdados\3eInput([Parallel<dados>Input]):::first
	Parallel\3cdados\3eOutput(Parallel<dados>Output)
	carregamento_dados(carregamento_dados)
	Passthrough_1(Passthrough)
	Parallel\3cextracao\2ccategoria\3eInput(Parallel<extracao,categoria>Input)
	Parallel\3cextracao\2ccategoria\3eOutput(Parallel<extracao,categoria>Output)
	extracao_palavras_chave(extracao_palavras_chave)
	deteccao_categoria(deteccao_categoria)
	Passthrough_2(Passthrough)
	Parallel\3ccontexto\3eInput(Parallel<contexto>Input)
	Parallel\3ccontexto\3eOutput(Parallel<contexto>Output)
	enriquecimento_contexto(enriquecimento_contexto)
	Passthrough_3(Passthrough)
	Parallel\3cregras\3eInput(Parallel<regras>Input)
	Parallel\3cregras\3eOutput(Parallel<regras>Output)
	motor_regras_producao(motor_regras_producao)
	Passthrough_4(Passthrough)
	montagem_resultado(montagem_resultado)
	TriageResult([TriageResult]):::last
	Parallel\3cdados\3eInput --> carregamento_dados;
	carregamento_dados --> Parallel\3cdados\3eOutput;
	Parallel\3cdados\3eInput --> Passthrough_1;
	Passthrough_1 --> Parallel\3cdados\3eOutput;
	Parallel\3cextracao\2ccategoria\3eInput --> extracao_palavras_chave;
	extracao_palavras_chave --> Parallel\3cextracao\2ccategoria\3eOutput;
	Parallel\3cextracao\2ccategoria\3eInput --> deteccao_categoria;
	deteccao_categoria --> Parallel\3cextracao\2ccategoria\3eOutput;
	Parallel\3cextracao\2ccategoria\3eInput --> Passthrough_2;
	Passthrough_2 --> Parallel\3cextracao\2ccategoria\3eOutput;
	Parallel\3cdados\3eOutput --> Parallel\3cextracao\2ccategoria\3eInput;
	Parallel\3ccontexto\3eInput --> enriquecimento_contexto;
	enriquecimento_contexto --> Parallel\3ccontexto\3eOutput;
	Parallel\3ccontexto\3eInput --> Passthrough_3;
	Passthrough_3 --> Parallel\3ccontexto\3eOutput;
	Parallel\3cextracao\2ccategoria\3eOutput --> Parallel\3ccontexto\3eInput;
	Parallel\3cregras\3eInput --> motor_regras_producao;
	motor_regras_producao --> Parallel\3cregras\3eOutput;
	Parallel\3cregras\3eInput --> Passthrough_4;
	Passthrough_4 --> Parallel\3cregras\3eOutput;
	Parallel\3ccontexto\3eOutput --> Parallel\3cregras\3eInput;
	montagem_resultado --> TriageResult;
	Parallel\3cregras\3eOutput --> montagem_resultado;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

## Fluxo híbrido (neurossimbólico)

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	Parallel\3cdados\3eInput([Parallel<dados>Input]):::first
	Parallel\3cdados\3eOutput(Parallel<dados>Output)
	carregamento_dados(carregamento_dados)
	Passthrough_1(Passthrough)
	Parallel\3cextracao\2ccategoria\3eInput(Parallel<extracao,categoria>Input)
	Parallel\3cextracao\2ccategoria\3eOutput(Parallel<extracao,categoria>Output)
	extracao_llm_com_fallback(extracao_llm_com_fallback)
	deteccao_categoria(deteccao_categoria)
	Passthrough_2(Passthrough)
	Parallel\3ccontexto\3eInput(Parallel<contexto>Input)
	Parallel\3ccontexto\3eOutput(Parallel<contexto>Output)
	enriquecimento_contexto(enriquecimento_contexto)
	Passthrough_3(Passthrough)
	Parallel\3cregras\3eInput(Parallel<regras>Input)
	Parallel\3cregras\3eOutput(Parallel<regras>Output)
	motor_regras_producao(motor_regras_producao)
	Passthrough_4(Passthrough)
	montagem_resultado(montagem_resultado)
	TriageResult([TriageResult]):::last
	Parallel\3cdados\3eInput --> carregamento_dados;
	carregamento_dados --> Parallel\3cdados\3eOutput;
	Parallel\3cdados\3eInput --> Passthrough_1;
	Passthrough_1 --> Parallel\3cdados\3eOutput;
	Parallel\3cextracao\2ccategoria\3eInput --> extracao_llm_com_fallback;
	extracao_llm_com_fallback --> Parallel\3cextracao\2ccategoria\3eOutput;
	Parallel\3cextracao\2ccategoria\3eInput --> deteccao_categoria;
	deteccao_categoria --> Parallel\3cextracao\2ccategoria\3eOutput;
	Parallel\3cextracao\2ccategoria\3eInput --> Passthrough_2;
	Passthrough_2 --> Parallel\3cextracao\2ccategoria\3eOutput;
	Parallel\3cdados\3eOutput --> Parallel\3cextracao\2ccategoria\3eInput;
	Parallel\3ccontexto\3eInput --> enriquecimento_contexto;
	enriquecimento_contexto --> Parallel\3ccontexto\3eOutput;
	Parallel\3ccontexto\3eInput --> Passthrough_3;
	Passthrough_3 --> Parallel\3ccontexto\3eOutput;
	Parallel\3cextracao\2ccategoria\3eOutput --> Parallel\3ccontexto\3eInput;
	Parallel\3cregras\3eInput --> motor_regras_producao;
	motor_regras_producao --> Parallel\3cregras\3eOutput;
	Parallel\3cregras\3eInput --> Passthrough_4;
	Passthrough_4 --> Parallel\3cregras\3eOutput;
	Parallel\3ccontexto\3eOutput --> Parallel\3cregras\3eInput;
	montagem_resultado --> TriageResult;
	Parallel\3cregras\3eOutput --> montagem_resultado;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

## Fluxo LLM puro

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	Parallel\3cpreparo\3eInput([Parallel<preparo>Input]):::first
	Parallel\3cpreparo\3eOutput(Parallel<preparo>Output)
	preparacao_prompt(preparacao_prompt)
	Passthrough_1(Passthrough)
	Parallel\3cresposta\3eInput(Parallel<resposta>Input)
	Parallel\3cresposta\3eOutput(Parallel<resposta>Output)
	chamada_llm(chamada_llm)
	Passthrough_2(Passthrough)
	Parallel\3canalise\3eInput(Parallel<analise>Input)
	Parallel\3canalise\3eOutput(Parallel<analise>Output)
	parser_defensivo(parser_defensivo)
	Passthrough_3(Passthrough)
	montagem_resultado(montagem_resultado)
	TriageResult([TriageResult]):::last
	Parallel\3cpreparo\3eInput --> preparacao_prompt;
	preparacao_prompt --> Parallel\3cpreparo\3eOutput;
	Parallel\3cpreparo\3eInput --> Passthrough_1;
	Passthrough_1 --> Parallel\3cpreparo\3eOutput;
	Parallel\3cresposta\3eInput --> chamada_llm;
	chamada_llm --> Parallel\3cresposta\3eOutput;
	Parallel\3cresposta\3eInput --> Passthrough_2;
	Passthrough_2 --> Parallel\3cresposta\3eOutput;
	Parallel\3cpreparo\3eOutput --> Parallel\3cresposta\3eInput;
	Parallel\3canalise\3eInput --> parser_defensivo;
	parser_defensivo --> Parallel\3canalise\3eOutput;
	Parallel\3canalise\3eInput --> Passthrough_3;
	Passthrough_3 --> Parallel\3canalise\3eOutput;
	Parallel\3cresposta\3eOutput --> Parallel\3canalise\3eInput;
	montagem_resultado --> TriageResult;
	Parallel\3canalise\3eOutput --> montagem_resultado;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```
