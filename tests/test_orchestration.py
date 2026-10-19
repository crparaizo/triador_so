"""
Testes para a orquestração LCEL (src/orchestration/triage_flow.py e chains.py).

Cobre a estrutura dos grafos (nós esperados; regras e híbrido diferem só no nó de
extração), o fallback LLM → palavras-chave via RunnableWithFallbacks, o resultado
seguro externo e a exportação Mermaid.

Nenhum teste conecta ao Ollama: LLMExtractor e ChatOllama são substituídos por mocks.
Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from pathlib import Path

import pytest
from langchain_core.runnables import RunnableSequence, RunnableWithFallbacks

from src.approaches.hybrid import run_hybrid
from src.approaches.rules_only import run_rules_only
from src.orchestration.chains import (
    build_hybrid_chain,
    build_llm_chain,
    build_rules_catref_chain,
    build_rules_chain,
    gerar_diagramas_mermaid,
    salvar_diagramas_mermaid,
)
from src.orchestration.triage_flow import obter_nucleo
from src.schemas.extraction import ExtractedInfo
from src.schemas.triage import (
    ApproachType,
    FailureCategory,
    PriorityLevel,
    UrgencyLevel,
)

_BUILDERS = [build_rules_chain, build_hybrid_chain, build_llm_chain, build_rules_catref_chain]
_MOTIVO_FALLBACK = (
    "Falha na extração LLM — resultado baseado em extrator por "
    "palavras-chave. Revisar manualmente."
)


@pytest.fixture(autouse=True)
def limpar_caches():
    """Garante isolamento dos testes limpando o cache de todos os loaders."""
    from src.config.loader import get_settings
    from src.data.loader import load_categories, load_knowledge_base
    from src.rules.definitions import load_rules

    for fn in (load_knowledge_base, load_categories, load_rules, get_settings):
        fn.cache_clear()
    yield
    for fn in (load_knowledge_base, load_categories, load_rules, get_settings):
        fn.cache_clear()


@pytest.fixture
def mock_llm(mocker):
    """Patcha LLMExtractor em hybrid (dados reais de YAML nos demais loaders)."""
    return mocker.patch("src.approaches.hybrid.LLMExtractor")


def _grafo(builder):
    return obter_nucleo(builder()).get_graph()


def _nomes(grafo) -> list[str]:
    return sorted(n.name for n in grafo.nodes.values())


def _arestas(grafo) -> set[tuple[str, str]]:
    return {(grafo.nodes[e.source].name, grafo.nodes[e.target].name) for e in grafo.edges}


# ---------------------------------------------------------------------------
# Estrutura dos grafos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("builder", _BUILDERS)
def test_envelope_falha_segura(builder):
    """Todo fluxo: preparacao_entrada | RunnableWithFallbacks(núcleo, resultado_seguro)."""
    fluxo = builder()
    assert isinstance(fluxo, RunnableSequence)
    assert fluxo.first.get_name() == "preparacao_entrada"
    envelope = fluxo.last
    assert isinstance(envelope, RunnableWithFallbacks)
    assert envelope.exception_key == "erro"
    assert envelope.name == "triagem_com_falha_segura"
    assert envelope.fallbacks[0].get_name() == "resultado_seguro"


def test_nucleo_regras_contem_nos_esperados():
    nomes = set(_nomes(_grafo(build_rules_chain)))
    for esperado in (
        "carregamento_dados",
        "extracao_palavras_chave",
        "deteccao_categoria",
        "enriquecimento_contexto",
        "motor_regras_producao",
        "montagem_resultado",
    ):
        assert esperado in nomes


def test_regras_e_hibrido_diferem_so_no_no_de_extracao():
    g_regras, g_hib = _grafo(build_rules_chain), _grafo(build_hybrid_chain)
    troca = {"extracao_llm_com_fallback": "extracao_palavras_chave"}

    nomes_hib = sorted(troca.get(n, n) for n in _nomes(g_hib))
    arestas_hib = {(troca.get(a, a), troca.get(b, b)) for a, b in _arestas(g_hib)}

    assert "extracao_llm_com_fallback" in _nomes(g_hib)
    assert nomes_hib == _nomes(g_regras)
    assert arestas_hib == _arestas(g_regras)
    assert g_hib.draw_mermaid().replace(
        "extracao_llm_com_fallback", "extracao_palavras_chave"
    ) == g_regras.draw_mermaid()


def test_catref_tem_mesmo_grafo_do_fluxo_por_regras():
    assert _grafo(build_rules_catref_chain).draw_mermaid() == _grafo(build_rules_chain).draw_mermaid()


@pytest.mark.parametrize(
    "builder,extrator",
    [(build_rules_chain, "extracao_palavras_chave"), (build_hybrid_chain, "extracao_llm_com_fallback")],
)
def test_extracao_e_categoria_em_paralelo(builder, extrator):
    arestas = _arestas(_grafo(builder))
    assert ("Parallel<extracao,categoria>Input", extrator) in arestas
    assert ("Parallel<extracao,categoria>Input", "deteccao_categoria") in arestas


def test_no_extracao_hibrido_usa_with_fallbacks():
    g = _grafo(build_hybrid_chain)
    no = next(n for n in g.nodes.values() if n.name == "extracao_llm_com_fallback")
    assert isinstance(no.data, RunnableWithFallbacks)
    assert no.data.runnable.get_name() == "extracao_llm"
    assert no.data.fallbacks[0].get_name() == "extracao_palavras_chave"
    assert no.data.exception_key == "erro_extracao"


@pytest.mark.parametrize("builder", [build_rules_chain, build_hybrid_chain])
def test_motor_de_regras_e_um_unico_no(builder):
    nomes = _nomes(_grafo(builder))
    assert nomes.count("motor_regras_producao") == 1
    assert not any("RULE-" in n for n in nomes)


def test_grafo_llm_puro_cadeia_prompt_llm_parser():
    g = _grafo(build_llm_chain)
    arestas = _arestas(g)
    assert ("Parallel<preparo>Output", "Parallel<resposta>Input") in arestas
    assert ("Parallel<resposta>Input", "chamada_llm") in arestas
    assert ("Parallel<preparo>Input", "preparacao_prompt") in arestas
    assert ("Parallel<resposta>Output", "Parallel<analise>Input") in arestas
    assert ("Parallel<analise>Input", "parser_defensivo") in arestas
    assert ("Parallel<analise>Output", "montagem_resultado") in arestas
    assert "motor_regras_producao" not in _nomes(g)


# ---------------------------------------------------------------------------
# Fallback LLM → palavras-chave (RunnableWithFallbacks)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "configurar,trecho",
    [
        (lambda m: setattr(m.extract, "return_value", ExtractedInfo(erro_parse="Falha X")), "Falha X"),
        (lambda m: setattr(m.extract, "side_effect", ConnectionError("recusada")), "recusada"),
        (lambda m: setattr(m.extract, "side_effect", ConnectionError()), "ConnectionError"),
        (lambda m: setattr(m.extract, "return_value", ExtractedInfo(erro_parse="")), ""),
    ],
    ids=["erro_parse", "excecao", "excecao_sem_mensagem", "erro_parse_vazio"],
)
@pytest.mark.parametrize("via_chain", [False, True], ids=["run_hybrid", "chain"])
def test_fallback_llm_para_palavras_chave(mock_llm, configurar, trecho, via_chain):
    instancia = mock_llm.return_value
    configurar(instancia)
    texto = "Bomba BOMB-001 com vibração excessiva no Setor A"

    r = build_hybrid_chain().invoke({"texto": texto}) if via_chain else run_hybrid(texto)

    assert r.evidencias["extracao_fallback"] == (
        f"Extração LLM falhou ({trecho}); usado extrator por palavras-chave."
    )
    assert r.requer_revisao_humana is True
    assert r.motivo_revisao == _MOTIVO_FALLBACK
    assert r.abordagem == ApproachType.HIBRIDO
    assert instancia.extract.call_count == 1


def test_falha_no_construtor_llm_extractor_vai_para_resultado_seguro(mocker):
    mocker.patch("src.approaches.hybrid.LLMExtractor", side_effect=RuntimeError("ctor"))

    r = run_hybrid("Bomba BOMB-001 com vibração")

    assert r.equipe_sugerida == "Revisão necessária"
    assert r.motivo_revisao == (
        "Erro interno no processamento (RuntimeError) — revisar manualmente."
    )
    assert "extracao_fallback" not in r.evidencias


# ---------------------------------------------------------------------------
# Resultado seguro externo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("texto,texto_esperado", [("Bomba parada", "Bomba parada"), ("", "(relato vazio)")])
def test_resultado_seguro_hibrido(mock_llm, mocker, texto, texto_esperado):
    mocker.patch("src.approaches.hybrid.load_rules", side_effect=RuntimeError("regras"))

    r = run_hybrid(texto)

    assert r.abordagem == ApproachType.HIBRIDO
    assert r.texto_entrada == texto_esperado
    assert r.urgencia == UrgencyLevel.DESCONHECIDA
    assert r.prioridade == PriorityLevel.DESCONHECIDA
    assert r.categoria == FailureCategory.DESCONHECIDA
    assert r.equipe_sugerida == "Revisão necessária"
    assert r.requer_revisao_humana is True
    assert r.motivo_revisao == (
        "Erro interno no processamento (RuntimeError) — revisar manualmente."
    )
    assert r.confianca == 0.0
    assert r.latencia_ms >= 0


def test_resultado_seguro_regras(mocker):
    mocker.patch("src.approaches.rules_only.load_rules", side_effect=KeyError("x"))

    r = run_rules_only("Bomba parada")

    assert r.abordagem == ApproachType.REGRAS
    assert r.equipe_sugerida == "Revisão necessária"
    assert r.motivo_revisao == "Erro interno no processamento (KeyError) — revisar manualmente."
    assert r.confianca == 0.0


def test_resultado_seguro_llm(mocker):
    mocker.patch("src.approaches.llm_only.ChatOllama")
    mocker.patch("src.approaches.llm_only.load_knowledge_base", side_effect=RuntimeError("kb"))

    r = build_llm_chain().invoke({"texto": "Bomba parada"})

    assert r.abordagem == ApproachType.LLM
    assert r.motivo_revisao == "LLM indisponível: kb"
    assert r.equipe_sugerida == "Revisão Manual"
    assert r.confianca == 0.0


# ---------------------------------------------------------------------------
# Equivalência das chains e categoria_ref
# ---------------------------------------------------------------------------


def test_rules_chain_ignora_categoria_ref_e_catref_aplica():
    texto = "Nao sei o que esta acontecendo, o equipamento esta estranho."
    entrada = {"texto": texto, "categoria_ref": "INSTRUMENTACAO"}

    assert build_rules_chain().invoke(entrada).categoria == FailureCategory.DESCONHECIDA
    assert build_rules_catref_chain().invoke(entrada).categoria == FailureCategory.INSTRUMENTACAO


@pytest.mark.parametrize(
    "texto",
    [
        "Bomba BOMB-001 com vibração excessiva e ruído no Setor A.",
        "Vazamento de óleo no compressor COMP-002, produção parada.",
        "Solicitação de pintura da sala administrativa.",
    ],
)
def test_run_rules_only_igual_a_chain(texto):
    def limpar(r):
        return r.model_dump(mode="json", exclude={"latencia_ms", "id", "timestamp"})

    assert limpar(run_rules_only(texto)) == limpar(build_rules_chain().invoke({"texto": texto}))


@pytest.mark.parametrize(
    "categoria_ref,fluxo_esperado",
    [(None, "fluxo_regras"), ("INSTRUMENTACAO", "fluxo_regras_categoria_ref")],
)
def test_run_rules_only_escolhe_fluxo_conforme_categoria_ref(mocker, categoria_ref, fluxo_esperado):
    """Triagem comum roda 'fluxo_regras'; só o cenário-diagnóstico roda o fluxo catref."""
    import src.approaches.rules_only as rules_only

    original = rules_only.build_rules_flow
    nomes_usados: list[str] = []

    def espiao(*args, **kwargs):
        fluxo = original(*args, **kwargs)
        nomes_usados.append(fluxo.get_name())
        return fluxo

    mocker.patch.object(rules_only, "build_rules_flow", side_effect=espiao)
    run_rules_only("Bomba BOMB-001 com vibração excessiva.", categoria_ref)

    assert nomes_usados == [fluxo_esperado]


# ---------------------------------------------------------------------------
# Exportação Mermaid
# ---------------------------------------------------------------------------


def test_gerar_diagramas_mermaid():
    diagramas = gerar_diagramas_mermaid()
    assert set(diagramas) == {"regras", "hibrido", "llm"}
    assert all("graph TD" in d for d in diagramas.values())


def test_salvar_diagramas_mermaid(tmp_path):
    caminho = salvar_diagramas_mermaid(tmp_path / "f.md")
    texto = caminho.read_text(encoding="utf-8")
    assert texto.count("```mermaid") == 3
