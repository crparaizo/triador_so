"""
Testes unitários para src/extraction/llm_extractor.py.

Todos os testes mockam ChatOllama — Ollama não precisa estar rodando.
O mock é aplicado em 'src.extraction.llm_extractor.ChatOllama' para interceptar
a instanciação dentro do método extract().

14 testes cobrindo: extração bem-sucedida, campos sem suporte, markdown,
JSON malformado, resposta vazia, retry de conexão, confiança calculada,
evidências, campos extras e verificação do prompt.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import json
from unittest.mock import MagicMock

import pytest

from src.extraction.llm_extractor import LLMExtractor
from src.schemas.extraction import ExtractedInfo

# JSON completo com todos os campos rastreáveis preenchidos — reutilizado em vários testes
JSON_COMPLETO = json.dumps(
    {
        "ativo_mencionado": "BOMB-001",
        "sintomas": ["vibração excessiva"],
        "localizacao": "Setor A",
        "impacto_producao": True,
        "risco_seguranca": False,
        "urgencia_mencionada": "urgente",
        "evidencias": {
            "ativo_mencionado": "bomba BOMB-001",
            "sintomas": "vibração excessiva",
        },
        "confianca_extracao": 0.8,
    }
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ollama(mocker):
    """
    Patcha ChatOllama em llm_extractor para evitar qualquer conexão com Ollama.
    Retorna a instância mock (mock_classe.return_value) — configure invoke nela.
    """
    mock_classe = mocker.patch("src.extraction.llm_extractor.ChatOllama")
    mock_instancia = mock_classe.return_value
    return mock_instancia


@pytest.fixture(autouse=True)
def limpar_settings_cache():
    """Limpa o cache de get_settings antes e depois de cada teste."""
    from src.config.loader import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def test_extracao_json_valido_retorna_campos_preenchidos(mock_ollama):
    """T01 — JSON válido com todos os rastreáveis preenchidos extrai campos corretamente."""
    mock_ollama.invoke.return_value = MagicMock(content=JSON_COMPLETO)

    extrator = LLMExtractor()
    result = extrator.extract("A bomba BOMB-001 está vibrando no Setor A. Urgente!")

    assert result.ativo_mencionado == "BOMB-001"
    assert result.sintomas == ["vibração excessiva"]
    assert result.localizacao == "Setor A"
    assert result.erro_parse is None


def test_json_com_nulls_popula_campos_sem_suporte(mock_ollama):
    """T02 — Campos rastreáveis null no JSON aparecem em campos_sem_suporte."""
    json_parcial = json.dumps(
        {
            "ativo_mencionado": None,
            "sintomas": ["ruído"],
            "localizacao": None,
            "impacto_producao": True,
            "risco_seguranca": False,
            "urgencia_mencionada": "urgente",
            "evidencias": {},
            "confianca_extracao": 0.5,
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_parcial)

    result = LLMExtractor().extract("Ruído anormal. Urgente!")

    assert "ativo_mencionado" in result.campos_sem_suporte
    assert "localizacao" in result.campos_sem_suporte


def test_json_em_bloco_markdown_extraido(mock_ollama):
    """T03 — JSON encapsulado em bloco markdown ```json ... ``` é extraído corretamente."""
    conteudo_markdown = f"```json\n{JSON_COMPLETO}\n```"
    mock_ollama.invoke.return_value = MagicMock(content=conteudo_markdown)

    result = LLMExtractor().extract("Bomba BOMB-001 vibrando.")

    assert result.erro_parse is None
    assert result.ativo_mencionado == "BOMB-001"


def test_json_malformado_retorna_erro_parse(mock_ollama):
    """T04 — Resposta sem JSON válido retorna erro_parse iniciando com 'Falha ao parsear JSON'."""
    mock_ollama.invoke.return_value = MagicMock(
        content="Desculpe, não entendi o pedido."
    )

    result = LLMExtractor().extract("texto qualquer")

    assert result.erro_parse is not None
    assert result.erro_parse.startswith("Falha ao parsear JSON")


def test_resposta_vazia_retorna_erro_parse(mock_ollama):
    """T05 — Resposta vazia retorna erro_parse não nulo."""
    mock_ollama.invoke.return_value = MagicMock(content="")

    result = LLMExtractor().extract("texto qualquer")

    assert result.erro_parse is not None


def test_parse_falho_preserva_resposta_bruta_em_evidencias(mock_ollama):
    """Em falha de parse, a resposta bruta do LLM é preservada em evidencias."""
    conteudo = "Desculpe, não entendi o pedido."
    mock_ollama.invoke.return_value = MagicMock(content=conteudo)

    result = LLMExtractor().extract("texto qualquer")

    assert result.erro_parse is not None
    assert result.evidencias.get("resposta_llm_bruta") == conteudo


def test_json_sem_ativo_mencionado_nao_gera_erro_parse(mock_ollama):
    """T06 — JSON válido sem chave 'ativo_mencionado' não gera erro_parse; campo fica None."""
    json_sem_ativo = json.dumps(
        {
            "sintomas": ["vibração"],
            "localizacao": "Setor B",
            "impacto_producao": None,
            "risco_seguranca": None,
            "urgencia_mencionada": None,
            "evidencias": {},
            "confianca_extracao": 0.2,
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_sem_ativo)

    result = LLMExtractor().extract("Vibração no Setor B.")

    assert result.ativo_mencionado is None
    assert result.erro_parse is None


def test_connection_error_retorna_erro_parse_ollama_indisponivel(mock_ollama):
    """T07 — ConnectionError em invoke retorna erro_parse com 'Ollama indisponível'."""
    mock_ollama.invoke.side_effect = ConnectionError("conexão recusada")

    result = LLMExtractor().extract("texto qualquer")

    assert result.erro_parse is not None
    assert "Ollama indisponível" in result.erro_parse


def test_timeout_error_retorna_erro_parse(mock_ollama):
    """T08 — TimeoutError em invoke retorna erro_parse não nulo."""
    mock_ollama.invoke.side_effect = TimeoutError("tempo esgotado")

    result = LLMExtractor().extract("texto qualquer")

    assert result.erro_parse is not None


def test_evidencias_preservadas_no_resultado(mock_ollama):
    """T09 — Dicionário 'evidencias' do LLM é preservado em ExtractedInfo.evidencias."""
    json_com_evidencias = json.dumps(
        {
            "ativo_mencionado": "BOMB-001",
            "sintomas": [],
            "localizacao": None,
            "impacto_producao": None,
            "risco_seguranca": None,
            "urgencia_mencionada": None,
            "evidencias": {"ativo_mencionado": "bomba BOMB-001"},
            "confianca_extracao": 0.2,
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_com_evidencias)

    result = LLMExtractor().extract("Problema na bomba BOMB-001.")

    assert result.evidencias["ativo_mencionado"] == "bomba BOMB-001"


def test_confianca_extracao_calculada_pela_proporcao(mock_ollama):
    """T10 — confianca_extracao = rastreáveis_preenchidos/5, não valor informado pelo LLM."""
    # Apenas ativo_mencionado e localizacao preenchidos (2/5 = 0.4)
    json_dois_campos = json.dumps(
        {
            "ativo_mencionado": "BOMB-001",
            "sintomas": [],
            "localizacao": "Setor A",
            "impacto_producao": None,
            "risco_seguranca": None,
            "urgencia_mencionada": None,
            "evidencias": {},
            "confianca_extracao": 0.99,  # valor do LLM deve ser ignorado
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_dois_campos)

    result = LLMExtractor().extract("Bomba BOMB-001 no Setor A.")

    # confianca calculada localmente: 2/5 = 0.4
    assert result.confianca_extracao == pytest.approx(2 / 5)
    assert len(result.campos_sem_suporte) == 3


def test_campos_sem_suporte_listados_corretamente(mock_ollama):
    """T11 — urgencia_mencionada e risco_seguranca null aparecem em campos_sem_suporte."""
    json_faltando = json.dumps(
        {
            "ativo_mencionado": "BOMB-001",
            "sintomas": ["vibração"],
            "localizacao": "Setor A",
            "impacto_producao": True,
            "risco_seguranca": None,
            "urgencia_mencionada": None,
            "evidencias": {},
            "confianca_extracao": 0.6,
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_faltando)

    result = LLMExtractor().extract("Bomba BOMB-001 vibrando no Setor A com impacto na produção.")

    assert "urgencia_mencionada" in result.campos_sem_suporte
    assert "risco_seguranca" in result.campos_sem_suporte


def test_prompt_inclui_instrucao_nao_inventar(mock_ollama):
    """T12 — O prompt enviado ao LLM contém instrução para não inventar dados."""
    mock_ollama.invoke.return_value = MagicMock(content=JSON_COMPLETO)

    LLMExtractor().extract("Bomba BOMB-001 vibrando.")

    # Capturar o argumento passado para invoke
    assert mock_ollama.invoke.called
    call_args = mock_ollama.invoke.call_args
    # Primeiro argumento posicional é o texto do prompt
    prompt_enviado = call_args[0][0]

    # Verificar que o prompt contém instrução de não inventar
    assert "Não invente" in prompt_enviado or "SOMENTE" in prompt_enviado or "não invente" in prompt_enviado


def test_retry_conexao_falha_primeiro_sucesso_segundo(mock_ollama):
    """T13 — ConnectionError na 1ª tentativa + JSON válido na 2ª = sucesso sem erro_parse."""
    mock_ollama.invoke.side_effect = [
        ConnectionError("falha de rede"),
        MagicMock(content=JSON_COMPLETO),
    ]

    result = LLMExtractor().extract("Bomba BOMB-001 vibrando.")

    assert result.erro_parse is None
    assert mock_ollama.invoke.call_count == 2


def test_json_com_campos_extras_nao_causa_erro(mock_ollama):
    """T14 — JSON com campos adicionais desconhecidos não causa erro_parse."""
    json_com_extras = json.dumps(
        {
            "ativo_mencionado": "BOMB-001",
            "sintomas": ["vibração"],
            "localizacao": "Setor A",
            "impacto_producao": True,
            "risco_seguranca": False,
            "urgencia_mencionada": "urgente",
            "evidencias": {},
            "confianca_extracao": 0.9,
            "campo_desconhecido": "valor ignorado",  # campo extra
            "outro_campo": 42,
        }
    )
    mock_ollama.invoke.return_value = MagicMock(content=json_com_extras)

    result = LLMExtractor().extract("Bomba BOMB-001 vibrando no Setor A.")

    assert result.erro_parse is None


def test_chatollama_extrator_recebe_format_json_e_limite_de_tokens(mocker):
    """O extrator do híbrido deve pedir JSON ao Ollama e limitar os tokens gerados."""
    from src.config.loader import get_settings
    from src.extraction.llm_extractor import LLMExtractor

    mock_classe = mocker.patch("src.extraction.llm_extractor.ChatOllama")
    LLMExtractor()._criar_llm()

    kwargs = mock_classe.call_args.kwargs
    assert kwargs["format"] == "json"
    assert kwargs["num_predict"] == get_settings().ollama_num_predict
