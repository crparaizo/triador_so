"""
Testes para src/approaches/hybrid.py — abordagem de triagem híbrida (LLM + regras).

Todos os testes usam mock via pytest-mock — nenhum teste conecta ao Ollama.
Os dados de teste são sintéticos e não representam instalação industrial real.

Padrão de mock:
    mock_llm    patcha 'src.approaches.hybrid.LLMExtractor'
    mock_kb     patcha 'src.approaches.hybrid.load_knowledge_base'
    mock_cats   patcha 'src.approaches.hybrid.load_categories'
    mock_rules  patcha 'src.approaches.hybrid.load_rules'
    limpar_caches (autouse) limpa caches de funções cacheadas antes e após cada teste

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import json as json_mod

import pytest

from src.approaches.hybrid import run_hybrid
from src.orchestration.chains import build_hybrid_chain, build_llm_chain, build_rules_chain
from src.rules.definitions import Rule, RuleAction, RuleCondition
from src.schemas.assets import Asset, KnowledgeBase, Team
from src.schemas.extraction import ExtractedInfo
from src.schemas.triage import ApproachType, PriorityLevel, TriageResult, UrgencyLevel


# ---------------------------------------------------------------------------
# Fixture autouse: limpar caches antes e depois de cada teste
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def limpar_caches():
    """Garante isolamento dos testes limpando o cache de todos os loaders."""
    from src.config.loader import get_settings
    from src.data.loader import load_categories, load_knowledge_base
    from src.rules.definitions import load_rules

    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    load_rules.cache_clear()
    get_settings.cache_clear()
    yield
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()
    load_rules.cache_clear()
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Helpers para criação de regras de teste — mesmo padrão de test_rules_engine
# ---------------------------------------------------------------------------


def _regra(
    rule_id: str = "RULE-MOCK",
    risco_seguranca: bool | None = None,
    impacto_producao: bool | None = None,
    categoria: str | None = None,
    criticidade_ativo: str | None = None,
    palavras_chave: list[str] | None = None,
    operador: str = "AND",
    urgencia: str | None = None,
    prioridade: str | None = None,
    equipe: str | None = None,
    requer_revisao: bool | None = None,
    motivo: str | None = None,
    confianca: float | None = None,
    prioridade_regra: int = 50,
) -> Rule:
    """Cria uma Rule de teste com os parâmetros fornecidos."""
    return Rule(
        id=rule_id,
        descricao=f"Regra de teste {rule_id}",
        condicoes=RuleCondition(
            risco_seguranca=risco_seguranca,
            impacto_producao=impacto_producao,
            categoria=categoria,
            criticidade_ativo=criticidade_ativo,
            palavras_chave=palavras_chave,
            operador=operador,
        ),
        acoes=RuleAction(
            urgencia=urgencia,
            prioridade=prioridade,
            equipe=equipe,
            requer_revisao_humana=requer_revisao,
            motivo_revisao=motivo,
            confianca=confianca,
        ),
        prioridade_regra=prioridade_regra,
    )


# ---------------------------------------------------------------------------
# Fixtures padrão de mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm(mocker):
    """Patcha LLMExtractor em hybrid para evitar conexão com Ollama."""
    mock_cls = mocker.patch("src.approaches.hybrid.LLMExtractor")
    instancia = mock_cls.return_value
    instancia.extract.return_value = ExtractedInfo(
        ativo_mencionado="BOMB-TEST",
        sintomas=["vibração excessiva"],
        impacto_producao=True,
        risco_seguranca=False,
        urgencia_mencionada="urgente",
        evidencias={"ativo_mencionado": "BOMB-TEST"},
        confianca_extracao=0.8,
    )
    return instancia


@pytest.fixture
def mock_kb(mocker, sample_knowledge_base):
    """Patcha load_knowledge_base para retornar KB de teste (sem leitura de YAML)."""
    mocker.patch(
        "src.approaches.hybrid.load_knowledge_base",
        return_value=sample_knowledge_base,
    )


@pytest.fixture
def mock_cats(mocker):
    """Patcha load_categories para retornar mapa de categorias de teste."""
    cats = {
        "MECANICA": {
            "equipe_padrao": "Manutenção Mecânica",
            "palavras_chave": ["vibração", "bomba"],
        }
    }
    mocker.patch("src.approaches.hybrid.load_categories", return_value=cats)
    return cats


@pytest.fixture
def mock_rules_basicas(mocker):
    """Patcha load_rules com regras mínimas para categoria MECANICA."""
    regras = [
        _regra(
            rule_id="RULE-T001",
            categoria="MECANICA",
            urgencia="MEDIA",
            prioridade="P2",
            equipe="Manutenção Mecânica",
            requer_revisao=False,
            confianca=0.7,
            prioridade_regra=50,
        )
    ]
    mocker.patch("src.approaches.hybrid.load_rules", return_value=regras)
    return regras


# ---------------------------------------------------------------------------
# Testes (16)
# ---------------------------------------------------------------------------


def test_fluxo_completo_json_valido_llm_mock(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """Fluxo nominal: LLM mock retorna ExtractedInfo válida; abordagem deve ser HIBRIDO."""
    resultado = run_hybrid("bomba BOMB-TEST com vibração no Setor A")

    assert isinstance(resultado, TriageResult)
    assert resultado.abordagem == ApproachType.HIBRIDO


def test_urgencia_prioridade_vem_das_regras(mock_llm, mock_kb, mock_cats, mocker):
    """Urgência/prioridade devem vir das regras de produção, não do LLM."""
    # LLM retorna risco_seguranca=True sem urgência mencionada explicitamente
    mock_llm.extract.return_value = ExtractedInfo(
        risco_seguranca=True,
        evidencias={"risco": "risco na bomba"},
        confianca_extracao=0.8,
    )
    regra_risco = _regra(
        rule_id="RULE-T-RISCO",
        risco_seguranca=True,
        urgencia="IMEDIATA",
        prioridade="P1",
        equipe="Manutenção Mecânica",
        requer_revisao=True,
        motivo="Risco de segurança confirmado pelas regras",
        confianca=0.95,
        prioridade_regra=100,
    )
    mocker.patch("src.approaches.hybrid.load_rules", return_value=[regra_risco])

    resultado = run_hybrid("risco na bomba")

    assert resultado.urgencia == UrgencyLevel.IMEDIATA
    assert resultado.prioridade == PriorityLevel.P1
    assert resultado.requer_revisao_humana is True


def test_llm_excecao_fallback_keyword_revisao_humana(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """Exceção no LLM deve ativar fallback KeywordExtractor e marcar revisão humana."""
    mock_llm.extract.side_effect = ConnectionError("Ollama indisponível no teste")

    resultado = run_hybrid("bomba com vibração no Setor A")

    assert resultado.requer_revisao_humana is True
    assert resultado.motivo_revisao is not None
    assert "Falha na extração LLM" in resultado.motivo_revisao
    assert resultado.abordagem == ApproachType.HIBRIDO


def test_erro_parse_fallback_keyword_revisao_humana(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """erro_parse na ExtractedInfo deve ativar fallback e documentar nas evidências."""
    mock_llm.extract.return_value = ExtractedInfo(
        erro_parse="Falha ao parsear JSON: resposta inválida do modelo"
    )

    resultado = run_hybrid("bomba com vibração")

    assert resultado.requer_revisao_humana is True
    assert "extracao_fallback" in resultado.evidencias


def test_baixa_confianca_extracao_revisao_humana(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """confianca_extracao < 0.4 deve sinalizar revisão humana com motivo adequado."""
    mock_llm.extract.return_value = ExtractedInfo(
        ativo_mencionado="BOMB-TEST",
        sintomas=["problema desconhecido"],
        evidencias={"ativo_mencionado": "BOMB-TEST"},
        confianca_extracao=0.3,
    )

    resultado = run_hybrid("problema na bomba")

    assert resultado.requer_revisao_humana is True
    assert resultado.motivo_revisao is not None
    assert "Baixa confiança" in resultado.motivo_revisao


def test_ativo_encontrado_evidencia_recuperado_assets_yaml(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """Ativo encontrado na KB deve gerar evidência com 'recuperado de assets.yaml'."""
    # mock_llm padrão retorna ativo_mencionado="BOMB-TEST" presente na sample_knowledge_base
    resultado = run_hybrid("bomba BOMB-TEST com vibração")

    assert "ativo_encontrado" in resultado.evidencias
    assert "recuperado de assets.yaml" in resultado.evidencias["ativo_encontrado"]


def test_ativo_nao_encontrado_em_campos_sem_suporte(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """Ativo mencionado no texto mas não encontrado na KB deve aparecer em campos_sem_suporte."""
    mock_llm.extract.return_value = ExtractedInfo(
        ativo_mencionado="INEXISTENTE-999",
        sintomas=["vibração"],
        evidencias={"ativo_mencionado": "INEXISTENTE-999"},
        confianca_extracao=0.8,
    )

    resultado = run_hybrid("equipamento INEXISTENTE-999 com vibração")

    assert "ativo_mencionado" in resultado.campos_sem_suporte


def test_regras_acionadas_nao_vazio_para_risco(mock_llm, mock_kb, mock_cats, mocker):
    """risco_seguranca=True com regra correspondente deve preencher regras_acionadas."""
    mock_llm.extract.return_value = ExtractedInfo(
        risco_seguranca=True,
        evidencias={"risco": "risco identificado no relato"},
        confianca_extracao=0.9,
    )
    regra_risco = _regra(
        rule_id="RULE-T-RISCO2",
        risco_seguranca=True,
        urgencia="IMEDIATA",
        prioridade="P1",
        equipe="Manutenção Mecânica",
        requer_revisao=True,
        motivo="Risco de segurança detectado",
        confianca=0.95,
        prioridade_regra=100,
    )
    mocker.patch("src.approaches.hybrid.load_rules", return_value=[regra_risco])

    resultado = run_hybrid("risco de segurança na bomba")

    assert resultado.regras_acionadas != []
    assert "RULE-T-RISCO2" in resultado.regras_acionadas


def test_evidencias_tem_origem_llm_e_regras(mock_llm, mock_kb, mock_cats, mocker):
    """Evidências devem conter chave do LLM ('ativo_mencionado') e das regras ('regras_classificacao')."""
    regra = _regra(
        rule_id="RULE-T-EV",
        categoria="MECANICA",
        urgencia="MEDIA",
        prioridade="P2",
        equipe="Manutenção Mecânica",
        requer_revisao=False,
        confianca=0.7,
        prioridade_regra=50,
    )
    mocker.patch("src.approaches.hybrid.load_rules", return_value=[regra])

    # mock_llm padrão tem evidencias={"ativo_mencionado": "BOMB-TEST"}
    resultado = run_hybrid("bomba BOMB-TEST com vibração no Setor A")

    # Evidência proveniente da extração LLM
    assert "ativo_mencionado" in resultado.evidencias
    # Evidência proveniente da classificação por regras
    assert "regras_classificacao" in resultado.evidencias


def test_latencia_ms_maior_zero(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """latencia_ms deve ser maior que zero após execução normal."""
    resultado = run_hybrid("bomba com vibração")

    assert resultado.latencia_ms > 0


def test_abordagem_sempre_hibrido(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """abordagem deve ser sempre ApproachType.HIBRIDO independente do conteúdo do relato."""
    resultado = run_hybrid("qualquer relato de manutenção industrial")

    assert resultado.abordagem == ApproachType.HIBRIDO


def test_texto_realista_bomb001_p1_imediata_revisao(mocker):
    """Relato realista com ativo crítico + risco + impacto deve resultar em IMEDIATA/P1/revisão."""
    # KB inline com BOMB-001 criticidade=ALTA
    ativo_bomb001 = Asset(
        id="bomb-001",
        nome="Bomba Centrífuga Principal",
        tag="BOMB-001",
        tipo="Mecânico",
        localizacao="Setor A - Linha 1",
        equipe_responsavel="Manutenção Mecânica",
        criticidade="ALTA",
    )
    equipe_mecanica = Team(
        id="team-001",
        nome="Manutenção Mecânica",
        especialidades=["bombas centrífugas", "compressores"],
        contato="mecanica@planta.com",
        disponivel=True,
    )
    kb_realista = KnowledgeBase(assets=[ativo_bomb001], teams=[equipe_mecanica])
    cats_realistas = {
        "MECANICA": {
            "equipe_padrao": "Manutenção Mecânica",
            "palavras_chave": ["vibração", "bomba", "risco"],
        }
    }
    # Regra: risco_seguranca AND impacto_producao → IMEDIATA/P1/revisão
    regra_critica = _regra(
        rule_id="RULE-T-CRIT",
        risco_seguranca=True,
        impacto_producao=True,
        urgencia="IMEDIATA",
        prioridade="P1",
        equipe="Manutenção Mecânica",
        requer_revisao=True,
        motivo="Risco de segurança com impacto na produção — revisão obrigatória",
        confianca=0.98,
        prioridade_regra=100,
    )

    # Montar mocks inline (sem usar fixtures globais para KB diferente)
    mock_cls = mocker.patch("src.approaches.hybrid.LLMExtractor")
    mock_cls.return_value.extract.return_value = ExtractedInfo(
        ativo_mencionado="BOMB-001",
        sintomas=["risco", "vibração"],
        risco_seguranca=True,
        impacto_producao=True,
        evidencias={"ativo_mencionado": "BOMB-001", "risco": "risco identificado"},
        confianca_extracao=0.9,
    )
    mocker.patch("src.approaches.hybrid.load_knowledge_base", return_value=kb_realista)
    mocker.patch("src.approaches.hybrid.load_categories", return_value=cats_realistas)
    mocker.patch("src.approaches.hybrid.load_rules", return_value=[regra_critica])

    resultado = run_hybrid("BOMB-001 com risco de segurança e impacto na produção")

    assert resultado.urgencia == UrgencyLevel.IMEDIATA
    assert resultado.prioridade == PriorityLevel.P1
    assert resultado.requer_revisao_humana is True


def test_ativo_desconhecido_sem_excecao(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """Ativo desconhecido não deve lançar exceção e deve retornar TriageResult válido."""
    mock_llm.extract.return_value = ExtractedInfo(
        ativo_mencionado="DESCONHECIDO-000",
        sintomas=["vibração"],
        evidencias={"ativo_mencionado": "DESCONHECIDO-000"},
        confianca_extracao=0.7,
    )

    resultado = run_hybrid("equipamento DESCONHECIDO-000 com vibração")

    assert isinstance(resultado, TriageResult)
    # Ativo não encontrado na KB → deve aparecer em campos_sem_suporte
    assert "ativo_mencionado" in resultado.campos_sem_suporte


def test_build_hybrid_chain_invoke_retorna_triage_result(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """build_hybrid_chain().invoke({'texto': ...}) deve retornar TriageResult com abordagem HIBRIDO."""
    chain = build_hybrid_chain()
    resultado = chain.invoke({"texto": "bomba com vibração"})

    assert isinstance(resultado, TriageResult)
    assert resultado.abordagem == ApproachType.HIBRIDO


def test_tres_pipelines_mesma_sessao(
    mock_llm, mock_kb, mock_cats, mock_rules_basicas, mocker, sample_knowledge_base
):
    """As três chains devem funcionar em sequência retornando a abordagem correta cada uma."""
    # Mock adicional para run_llm_only: ChatOllama e load_knowledge_base
    json_valido = json_mod.dumps(
        {
            "urgencia": "ALTA",
            "prioridade": "P2",
            "categoria": "MECANICA",
            "equipe_sugerida": "Manutenção Mecânica",
            "regras_acionadas": [],
            "evidencias": {"urgencia": "alta"},
            "requer_revisao_humana": False,
            "motivo_revisao": None,
            "confianca": 0.8,
            "campos_sem_suporte": [],
        }
    )
    mock_ollama_cls = mocker.patch("src.approaches.llm_only.ChatOllama")
    # Criar objeto com atributo content para simular AIMessage
    ai_msg = type("AIMsg", (), {"content": json_valido})()
    mock_ollama_cls.return_value.invoke.return_value = ai_msg
    mocker.patch(
        "src.approaches.llm_only.load_knowledge_base",
        return_value=sample_knowledge_base,
    )

    # Executar as três chains em sequência na mesma sessão
    resultado_regras = build_rules_chain().invoke({"texto": "bomba com vibração"})
    resultado_llm = build_llm_chain().invoke({"texto": "bomba com vibração"})
    resultado_hibrido = build_hybrid_chain().invoke({"texto": "bomba com vibração"})

    assert resultado_regras.abordagem == ApproachType.REGRAS
    assert resultado_llm.abordagem == ApproachType.LLM
    assert resultado_hibrido.abordagem == ApproachType.HIBRIDO


def test_texto_vazio_retorna_triage_result_valido(mock_llm, mock_kb, mock_cats, mock_rules_basicas):
    """Texto vazio não deve lançar exceção e deve retornar TriageResult com texto sanitizado."""
    resultado = run_hybrid("")

    assert isinstance(resultado, TriageResult)
    assert resultado.texto_entrada == "(relato vazio)"
