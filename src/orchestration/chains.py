"""
Chains LangChain (LCEL) para os pipelines de triagem de ordens de serviço.

Cada builder devolve um fluxo LCEL composto de Runnables nomeados, montado pelos
módulos de abordagem a partir da fábrica comum src.orchestration.triage_flow.
Todos aceitam um dict com a chave 'texto' (e 'categoria_ref', usada apenas pelo
cenário-diagnóstico) e retornam TriageResult.

Chains disponíveis:
  - build_rules_chain(): abordagem por regras de produção — sem LLM, execução local.
  - build_llm_chain(): abordagem LLM puro — requer Ollama rodando com modelo configurado.
  - build_hybrid_chain(): abordagem híbrida — LLM extrai, regras classificam.
  - build_rules_catref_chain(): regras com categoria de referência (diagnóstico).

Regras e híbrido compartilham a mesma estrutura de grafo e diferem só no nó de
extração. Os grafos podem ser exportados em Mermaid com salvar_diagramas_mermaid()
(ou `python -m src.orchestration`), que grava docs/fluxos_langchain.md.

AVISO: Protótipo acadêmico. As chains aqui definidas são para fins de pesquisa
e comparação de abordagens. Não usar em ambiente industrial real.
"""

from pathlib import Path

from langchain_core.runnables import Runnable

from src.approaches.hybrid import build_hybrid_flow
from src.approaches.llm_only import build_llm_flow
from src.approaches.rules_only import build_rules_flow
from src.orchestration.triage_flow import obter_nucleo


def build_rules_chain() -> Runnable:
    """
    Constrói o fluxo LCEL da abordagem de triagem baseada em regras.

    Aceita {"texto": str} e retorna TriageResult. A chave 'categoria_ref', se
    presente, é ignorada (a categoria é detectada por palavras-chave).
    Não depende de LLM nem de Ollama — execução completamente local.

    Uso:
        chain = build_rules_chain()
        resultado = chain.invoke({"texto": "BOMB-001 com vibração excessiva"})
    """
    return build_rules_flow()


def build_llm_chain() -> Runnable:
    """
    Constrói o fluxo LCEL da abordagem de triagem baseada em LLM puro.

    Aceita {"texto": str} e retorna TriageResult.
    Requer Ollama rodando com o modelo configurado em settings.ollama_model.
    A conexão com Ollama ocorre apenas em tempo de execução, nunca na construção da chain.
    """
    return build_llm_flow()


def build_hybrid_chain() -> Runnable:
    """
    Constrói o fluxo LCEL da abordagem de triagem híbrida (LLM + regras).

    Aceita {"texto": str} e retorna TriageResult. O LLM é usado apenas para
    extração de informações — a classificação de urgência, prioridade e equipe é
    determinística via motor de regras de produção. Se a extração LLM falhar, o
    fallback nativo do LangChain usa o extrator por palavras-chave.
    A conexão com Ollama ocorre apenas em tempo de execução, nunca na construção da chain.
    """
    return build_hybrid_flow()


def build_rules_catref_chain() -> Runnable:
    """
    Constrói o fluxo do cenário-diagnóstico "regras com categoria de referência".

    Igual à abordagem por regras, mas a categoria é fixada no valor de referência
    (gabarito), em vez de detectada por palavras-chave. Serve para medir quanto do
    erro das regras decorre da detecção de categoria, isolando-o da decisão.

    IMPORTANTE: não é um teto por "fatos de referência" completos — o dataset não
    contém os atributos intermediários (risco, impacto, ativo) como gabarito; apenas
    a categoria está disponível. Risco/impacto continuam vindo da extração por
    palavras-chave. Cenário opcional, não executado por padrão.

    Aceita {"texto": str, "categoria_ref": str} e não depende de LLM nem de Ollama.
    """
    return build_rules_flow(usar_categoria_ref=True)


# ---------------------------------------------------------------------------
# Exportação dos grafos (Mermaid)
# ---------------------------------------------------------------------------

_CAMINHO_PADRAO = Path(__file__).resolve().parents[2] / "docs" / "fluxos_langchain.md"

_TEMPLATE_DOC = """# Fluxos LangChain (LCEL) da triagem

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
{regras}
```

## Fluxo híbrido (neurossimbólico)

```mermaid
{hibrido}
```

## Fluxo LLM puro

```mermaid
{llm}
```
"""


def gerar_diagramas_mermaid() -> dict[str, str]:
    """
    Gera o diagrama Mermaid do núcleo de cada fluxo.

    Returns:
        Dict com chaves "regras", "hibrido" e "llm" e o texto Mermaid de cada uma.
    """
    return {
        "regras": obter_nucleo(build_rules_chain()).get_graph().draw_mermaid(),
        "hibrido": obter_nucleo(build_hybrid_chain()).get_graph().draw_mermaid(),
        "llm": obter_nucleo(build_llm_chain()).get_graph().draw_mermaid(),
    }


def salvar_diagramas_mermaid(caminho: str | Path | None = None) -> Path:
    """
    Grava os três diagramas em Markdown (padrão: docs/fluxos_langchain.md).

    Args:
        caminho: arquivo de destino; None usa docs/fluxos_langchain.md.

    Returns:
        Caminho do arquivo gravado.
    """
    destino = Path(caminho) if caminho is not None else _CAMINHO_PADRAO
    diagramas = {k: v.strip() for k, v in gerar_diagramas_mermaid().items()}
    conteudo = _TEMPLATE_DOC
    for chave, texto in diagramas.items():
        conteudo = conteudo.replace("{" + chave + "}", texto)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
    return destino
