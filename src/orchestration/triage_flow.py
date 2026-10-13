"""
Fábrica comum dos fluxos de triagem compostos em LCEL (LangChain Expression Language).

Este módulo define apenas a TOPOLOGIA dos fluxos e o nome de cada nó. As funções
que executam cada etapa continuam nos módulos de abordagem (src/approaches/), onde
resolvem os loaders e extratores pelos nomes globais do próprio módulo em tempo de
chamada — por isso os patches dos testes (ex.: 'src.approaches.hybrid.LLMExtractor')
continuam valendo mesmo para fluxos construídos no import.

Topologia compartilhada pelos fluxos por regras e híbrido (difere só no extrator):

    preparacao_entrada
    | triagem_com_falha_segura (RunnableWithFallbacks, fallback = resultado_seguro)
        └─ núcleo:
             assign(dados = carregamento_dados)
           | assign(extracao = <extrator>, categoria = deteccao_categoria)  # RunnableParallel
           | assign(contexto = enriquecimento_contexto)
           | assign(regras = motor_regras_producao)   # apply_rules: um único nó
           | montagem_resultado

    <extrator> regras:  extracao_palavras_chave
    <extrator> híbrido: extracao_llm_com_fallback
                        (extracao_llm com fallback para extracao_palavras_chave)

O fluxo LLM puro usa o mesmo envelope de falha segura com outro núcleo
(preparacao_prompt → chamada_llm → parser_defensivo → montagem_resultado),
montado em src/approaches/llm_only.py.

Contrato do estado (dict que trafega pela cadeia via RunnablePassthrough.assign):
    texto          entrada bruta recebida pelo fluxo
    categoria_ref  categoria de referência (só no fluxo por regras com catref)
    texto_entrada  texto usado na triagem (sanitizado no híbrido e no LLM)
    inicio         time.perf_counter() gravado em preparacao_entrada
    dados          {"kb", "cats", "rules"} (+ "llm_extractor" no híbrido)
    extracao       {"extraido": ExtractedInfo, "fallback_ativado": bool}
    categoria      FailureCategory detectada (ou de referência)
    contexto       ContextData de enrich_context
    regras         dict retornado por apply_rules
    erro / erro_extracao  exceção injetada por RunnableWithFallbacks(exception_key=...)
Nenhum nó itera sobre as chaves do estado; cada nó lê chaves explícitas.

Divergências conhecidas em relação à versão anterior (função única por abordagem):
    D2: no híbrido, a detecção de categoria roda em paralelo com a extração LLM
        (thread do RunnableParallel); a ordem das linhas de log pode intercalar.
    D3: se a extração LLM falhar E o fallback por palavras-chave também lançar,
        RunnableWithFallbacks relança o PRIMEIRO erro; o motivo do resultado seguro
        mostra então a classe do erro do LLM. Inalcançável com kb/cats válidos.
    D4: with_fallbacks(exception_key=...) grava a exceção no dict de entrada;
        as chaves 'erro_extracao'/'erro' podem aparecer no estado interno.

AVISO: Protótipo acadêmico. Não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança.
"""

from typing import Any, Callable

from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnablePassthrough,
    RunnableSequence,
    RunnableWithFallbacks,
)

# ---------------------------------------------------------------------------
# Nomes dos nós (aparecem no grafo exportado e nos traces do LangChain)
# ---------------------------------------------------------------------------

NO_PREPARACAO_ENTRADA = "preparacao_entrada"
NO_CARREGAMENTO_DADOS = "carregamento_dados"
NO_EXTRACAO_PALAVRAS_CHAVE = "extracao_palavras_chave"
NO_EXTRACAO_LLM = "extracao_llm"
NO_EXTRACAO_LLM_COM_FALLBACK = "extracao_llm_com_fallback"
NO_DETECCAO_CATEGORIA = "deteccao_categoria"
NO_ENRIQUECIMENTO_CONTEXTO = "enriquecimento_contexto"
NO_MOTOR_REGRAS = "motor_regras_producao"
NO_MONTAGEM_RESULTADO = "montagem_resultado"
NO_RESULTADO_SEGURO = "resultado_seguro"
NO_FALHA_SEGURA = "triagem_com_falha_segura"
NO_PREPARACAO_PROMPT = "preparacao_prompt"
NO_CHAMADA_LLM = "chamada_llm"
NO_PARSER_DEFENSIVO = "parser_defensivo"

# Nomes dos fluxos completos
FLUXO_REGRAS = "fluxo_regras"
FLUXO_REGRAS_CATEGORIA_REF = "fluxo_regras_categoria_ref"
FLUXO_HIBRIDO = "fluxo_hibrido"
FLUXO_LLM = "fluxo_llm"

Etapa = Callable[[dict], Any]


class FalhaExtracaoLLM(Exception):
    """
    Sinaliza que o LLMExtractor devolveu ExtractedInfo com erro_parse preenchido.

    O LLMExtractor não lança exceção em falhas de parse/conexão: ele retorna
    erro_parse. Como o mecanismo de fallback do LangChain reage a exceções,
    o nó extracao_llm converte esse sinal nesta exceção, preservando a mensagem
    original em erro_parse (inclusive string vazia).
    """

    def __init__(self, erro_parse: str) -> None:
        super().__init__(erro_parse)
        self.erro_parse = erro_parse


def no(funcao: Etapa, nome: str) -> RunnableLambda:
    """Cria um nó LCEL nomeado a partir de uma função de etapa."""
    return RunnableLambda(funcao, name=nome)


def envolver_com_falha_segura(
    *,
    nome: str,
    preparar_entrada: Etapa,
    nucleo: Runnable,
    resultado_seguro: Etapa,
) -> RunnableSequence:
    """
    Envolve o núcleo de um fluxo com o envelope de falha segura.

    preparacao_entrada fica FORA do envelope: grava 'inicio' e 'texto_entrada',
    que o resultado seguro usa para medir a latência e montar a resposta.
    Qualquer exceção do núcleo é entregue a resultado_seguro na chave 'erro'.
    """
    return RunnableSequence(
        no(preparar_entrada, NO_PREPARACAO_ENTRADA),
        RunnableWithFallbacks(
            runnable=nucleo,
            fallbacks=[no(resultado_seguro, NO_RESULTADO_SEGURO)],
            exception_key="erro",
            name=NO_FALHA_SEGURA,
        ),
        name=nome,
    )


def extracao_com_fallback(primaria: Runnable, fallback: Runnable) -> RunnableWithFallbacks:
    """
    Nó de extração com fallback nativo do LangChain.

    Se 'primaria' lançar exceção, 'fallback' recebe o mesmo estado com a
    exceção na chave 'erro_extracao'.
    """
    return RunnableWithFallbacks(
        runnable=primaria,
        fallbacks=[fallback],
        exception_key="erro_extracao",
        name=NO_EXTRACAO_LLM_COM_FALLBACK,
    )


def compor_fluxo_triagem(
    *,
    nome: str,
    preparar_entrada: Etapa,
    carregar_dados: Etapa,
    extrator: Runnable,
    detectar_categoria: Etapa,
    enriquecer_contexto: Etapa,
    aplicar_regras: Etapa,
    montar_resultado: Etapa,
    resultado_seguro: Etapa,
) -> RunnableSequence:
    """
    Monta o fluxo comum de triagem (regras e híbrido) e o envolve com falha segura.

    Os dois fluxos compartilham esta mesma estrutura de grafo; o único nó que
    muda é o 'extrator'. Extração e detecção de categoria são independentes e
    ficam no mesmo assign, que o LCEL executa como RunnableParallel.
    O motor de regras inteiro é UM nó: as regras continuam declaradas em
    data/rules.yaml e são avaliadas por apply_rules.
    """
    nucleo = RunnableSequence(
        RunnablePassthrough.assign(dados=no(carregar_dados, NO_CARREGAMENTO_DADOS)),
        RunnablePassthrough.assign(
            extracao=extrator,
            categoria=no(detectar_categoria, NO_DETECCAO_CATEGORIA),
        ),
        RunnablePassthrough.assign(
            contexto=no(enriquecer_contexto, NO_ENRIQUECIMENTO_CONTEXTO)
        ),
        RunnablePassthrough.assign(regras=no(aplicar_regras, NO_MOTOR_REGRAS)),
        no(montar_resultado, NO_MONTAGEM_RESULTADO),
    )
    return envolver_com_falha_segura(
        nome=nome,
        preparar_entrada=preparar_entrada,
        nucleo=nucleo,
        resultado_seguro=resultado_seguro,
    )


def obter_nucleo(fluxo: Runnable) -> Runnable:
    """
    Retorna o núcleo de um fluxo montado por envolver_com_falha_segura.

    Usado para exportar o grafo: RunnableWithFallbacks aparece como nó opaco em
    get_graph(), então o diagrama é gerado a partir do núcleo.
    """
    if not isinstance(fluxo, RunnableSequence) or not isinstance(
        fluxo.last, RunnableWithFallbacks
    ):
        raise TypeError("Fluxo não segue o formato preparacao_entrada | falha_segura(núcleo).")
    return fluxo.last.runnable
