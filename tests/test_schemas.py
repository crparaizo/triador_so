"""
Testes automatizados dos schemas Pydantic do sistema de triagem.

Cobre: criação válida, erros de validação, serialização/deserialização JSON,
enums, métodos da KnowledgeBase e comportamento de campos opcionais.

Nenhum teste depende de Ollama ou de arquivos de dados externos.
"""

import re

import pytest
from pydantic import ValidationError

from src.schemas.assets import Asset, KnowledgeBase, Team
from src.schemas.extraction import ContextData, ExtractedInfo
from src.schemas.triage import (
    ApproachType,
    FailureCategory,
    PriorityLevel,
    TriageResult,
    UrgencyLevel,
)


# ---------------------------------------------------------------------------
# Testes de TriageResult
# ---------------------------------------------------------------------------


def test_triage_result_criacao_valida(sample_triage_result: TriageResult) -> None:
    """TriageResult criado via fixture deve ter campos preenchidos corretamente."""
    assert sample_triage_result.id  # id não deve estar vazio
    assert sample_triage_result.confianca == 0.9
    assert sample_triage_result.abordagem == ApproachType.HIBRIDO


def test_triage_result_id_uuid4_automatico() -> None:
    """id deve ser gerado automaticamente no formato UUID4."""
    result = TriageResult(
        abordagem=ApproachType.REGRAS,
        texto_entrada="Teste de geração de UUID",
        urgencia=UrgencyLevel.BAIXA,
        prioridade=PriorityLevel.P4,
        categoria=FailureCategory.OUTROS,
        equipe_sugerida="Equipe Geral",
        requer_revisao_humana=False,
        confianca=0.5,
        latencia_ms=10.0,
    )
    # Formato esperado: 8-4-4-4-12 hexadecimais
    padrao_uuid = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
    assert padrao_uuid.match(result.id), f"id '{result.id}' não está no formato UUID4"


def test_triage_result_timestamp_automatico() -> None:
    """timestamp deve ser gerado automaticamente como datetime válido."""
    from datetime import datetime

    r1 = TriageResult(
        abordagem=ApproachType.LLM,
        texto_entrada="Relato 1",
        urgencia=UrgencyLevel.MEDIA,
        prioridade=PriorityLevel.P3,
        categoria=FailureCategory.ELETRICA,
        equipe_sugerida="Elétrica",
        requer_revisao_humana=False,
        confianca=0.7,
        latencia_ms=20.0,
    )
    r2 = TriageResult(
        abordagem=ApproachType.LLM,
        texto_entrada="Relato 2",
        urgencia=UrgencyLevel.MEDIA,
        prioridade=PriorityLevel.P3,
        categoria=FailureCategory.ELETRICA,
        equipe_sugerida="Elétrica",
        requer_revisao_humana=False,
        confianca=0.7,
        latencia_ms=20.0,
    )
    assert isinstance(r1.timestamp, datetime)
    assert isinstance(r2.timestamp, datetime)


def test_triage_result_campos_obrigatorios() -> None:
    """TriageResult sem campos obrigatórios deve levantar ValidationError."""
    with pytest.raises(ValidationError):
        TriageResult()  # type: ignore[call-arg]


def test_triage_result_confianca_invalida() -> None:
    """confianca fora do intervalo [0, 1] deve levantar ValidationError."""
    base_kwargs = dict(
        abordagem=ApproachType.REGRAS,
        texto_entrada="Teste",
        urgencia=UrgencyLevel.BAIXA,
        prioridade=PriorityLevel.P4,
        categoria=FailureCategory.OUTROS,
        equipe_sugerida="Equipe",
        requer_revisao_humana=False,
        latencia_ms=5.0,
    )
    with pytest.raises(ValidationError):
        TriageResult(**base_kwargs, confianca=1.5)  # acima do limite

    with pytest.raises(ValidationError):
        TriageResult(**base_kwargs, confianca=-0.1)  # abaixo do limite


def test_triage_result_revisao_humana_sem_motivo() -> None:
    """
    Comportamento esperado: requer_revisao_humana=True sem motivo_revisao deve
    levantar ValidationError (validação cruzada via @model_validator).
    """
    with pytest.raises(ValidationError):
        TriageResult(
            abordagem=ApproachType.HIBRIDO,
            texto_entrada="Caso com revisão necessária",
            urgencia=UrgencyLevel.IMEDIATA,
            prioridade=PriorityLevel.P1,
            categoria=FailureCategory.SEGURANCA,
            equipe_sugerida="Segurança",
            requer_revisao_humana=True,
            motivo_revisao=None,  # faltando motivo — deve falhar
            confianca=0.3,
            latencia_ms=50.0,
        )


def test_triage_result_revisao_humana_com_motivo() -> None:
    """requer_revisao_humana=True com motivo preenchido deve ser válido."""
    result = TriageResult(
        abordagem=ApproachType.HIBRIDO,
        texto_entrada="Caso com revisão necessária e motivo informado",
        urgencia=UrgencyLevel.IMEDIATA,
        prioridade=PriorityLevel.P1,
        categoria=FailureCategory.SEGURANCA,
        equipe_sugerida="Segurança",
        requer_revisao_humana=True,
        motivo_revisao="Risco de segurança não confirmado — requer inspeção presencial.",
        confianca=0.3,
        latencia_ms=50.0,
    )
    assert result.requer_revisao_humana is True
    assert result.motivo_revisao is not None


def test_triage_result_serializacao_json(sample_triage_result: TriageResult) -> None:
    """model_dump e model_dump_json devem serializar corretamente."""
    data = sample_triage_result.model_dump()
    assert "abordagem" in data

    json_str = sample_triage_result.model_dump_json()
    assert "HIBRIDO" in json_str


def test_triage_result_desserializacao_json(sample_triage_result: TriageResult) -> None:
    """model_validate deve reconstruir TriageResult a partir de dict com mesmo id."""
    data = sample_triage_result.model_dump()
    result2 = TriageResult.model_validate(data)
    assert result2.id == sample_triage_result.id


# ---------------------------------------------------------------------------
# Testes de Asset
# ---------------------------------------------------------------------------


def test_asset_criacao_valida(sample_asset: Asset) -> None:
    """Asset criado via fixture deve ter campos corretos."""
    assert sample_asset.tag == "BOMB-TEST"
    assert sample_asset.criticidade == "ALTA"


def test_asset_campos_obrigatorios() -> None:
    """Asset sem campos obrigatórios deve levantar ValidationError."""
    with pytest.raises(ValidationError):
        Asset()  # type: ignore[call-arg]


def test_asset_criticidade_invalida() -> None:
    """criticidade com valor fora do Literal deve levantar ValidationError."""
    with pytest.raises(ValidationError):
        Asset(
            id="x",
            nome="X",
            tag="X-001",
            tipo="Elétrico",
            localizacao="Setor Z",
            equipe_responsavel="Equipe Z",
            criticidade="CRITICA",  # valor inválido
        )


# ---------------------------------------------------------------------------
# Testes de Team
# ---------------------------------------------------------------------------


def test_team_criacao_valida(sample_team: Team) -> None:
    """Team criado via fixture deve ter campos corretos."""
    assert "Mecânica" in sample_team.nome
    assert sample_team.disponivel is True


def test_team_disponivel_padrao() -> None:
    """disponivel deve ser True por padrão."""
    team = Team(
        id="t-x",
        nome="Equipe X",
        especialidades=["especialidade_a"],
        contato="x@planta.com",
    )
    assert team.disponivel is True


# ---------------------------------------------------------------------------
# Testes de KnowledgeBase
# ---------------------------------------------------------------------------


def test_knowledge_base_get_asset_by_tag(sample_knowledge_base: KnowledgeBase) -> None:
    """get_asset_by_tag deve retornar ativo correto pelo tag exato."""
    asset = sample_knowledge_base.get_asset_by_tag("BOMB-TEST")
    assert asset is not None
    assert asset.nome == "Bomba Centrífuga Teste"


def test_knowledge_base_get_asset_by_tag_nao_encontrado(
    sample_knowledge_base: KnowledgeBase,
) -> None:
    """get_asset_by_tag deve retornar None para tag inexistente."""
    result = sample_knowledge_base.get_asset_by_tag("NAO-EXISTE")
    assert result is None


def test_knowledge_base_get_asset_by_tag_case_insensitive(
    sample_knowledge_base: KnowledgeBase,
) -> None:
    """get_asset_by_tag deve ser case-insensitive."""
    result = sample_knowledge_base.get_asset_by_tag("bomb-test")
    assert result is not None
    assert result.tag == "BOMB-TEST"


def test_knowledge_base_find_assets_by_location(
    sample_knowledge_base: KnowledgeBase,
) -> None:
    """find_assets_by_location deve retornar ativos que contenham a localização."""
    assets = sample_knowledge_base.find_assets_by_location("Setor A")
    assert len(assets) >= 1
    assert any(a.tag == "BOMB-TEST" for a in assets)


def test_knowledge_base_find_assets_by_location_sem_resultado(
    sample_knowledge_base: KnowledgeBase,
) -> None:
    """find_assets_by_location deve retornar lista vazia para localização inexistente."""
    assets = sample_knowledge_base.find_assets_by_location("Setor Z")
    assert assets == []


def test_knowledge_base_get_team_by_name(sample_knowledge_base: KnowledgeBase) -> None:
    """get_team_by_name deve retornar equipe com busca parcial case-insensitive."""
    team = sample_knowledge_base.get_team_by_name("Mecânica")
    assert team is not None
    assert "Mecânica" in team.nome


def test_knowledge_base_get_team_by_name_nao_encontrado(
    sample_knowledge_base: KnowledgeBase,
) -> None:
    """get_team_by_name deve retornar None para nome inexistente."""
    team = sample_knowledge_base.get_team_by_name("Equipe Fantasma")
    assert team is None


# ---------------------------------------------------------------------------
# Testes de ExtractedInfo
# ---------------------------------------------------------------------------


def test_extracted_info_criacao_valida(sample_extracted_info: ExtractedInfo) -> None:
    """ExtractedInfo criado via fixture deve ter campos corretos."""
    assert "vibração excessiva" in sample_extracted_info.sintomas
    assert sample_extracted_info.confianca_extracao == 0.85


def test_extracted_info_valores_nulos_por_padrao() -> None:
    """ExtractedInfo vazio deve ter campos opcionais como None e listas vazias."""
    info = ExtractedInfo()
    assert info.ativo_mencionado is None
    assert info.sintomas == []
    assert info.erro_parse is None
    assert info.confianca_extracao == 0.0
    assert info.campos_sem_suporte == []


def test_extracted_info_confianca_invalida() -> None:
    """confianca_extracao fora do intervalo [0, 1] deve levantar ValidationError."""
    with pytest.raises(ValidationError):
        ExtractedInfo(confianca_extracao=1.1)


# ---------------------------------------------------------------------------
# Testes de ContextData
# ---------------------------------------------------------------------------


def test_context_data_criacao_valida(sample_asset: Asset, sample_team: Team) -> None:
    """ContextData deve aceitar ativo e equipes opcionais."""
    ctx = ContextData(
        ativo_encontrado=sample_asset,
        equipes_candidatas=[sample_team],
        fonte_enriquecimento="base_local",
    )
    assert ctx.ativo_encontrado is not None
    assert len(ctx.equipes_candidatas) == 1
    assert ctx.fonte_enriquecimento == "base_local"


def test_context_data_sem_dados() -> None:
    """ContextData vazio deve ter campos padrão corretos."""
    ctx = ContextData()
    assert ctx.ativo_encontrado is None
    assert ctx.equipes_candidatas == []
    assert ctx.historico_notas == []
    assert ctx.fonte_enriquecimento == ""


# ---------------------------------------------------------------------------
# Testes de Enums
# ---------------------------------------------------------------------------


def test_enum_failure_category_fora_do_escopo() -> None:
    """FailureCategory.FORA_DO_ESCOPO deve ter valor string correto."""
    assert FailureCategory.FORA_DO_ESCOPO.value == "FORA_DO_ESCOPO"


def test_enum_failure_category_desconhecida() -> None:
    """FailureCategory.DESCONHECIDA deve ter valor string correto."""
    assert FailureCategory.DESCONHECIDA.value == "DESCONHECIDA"


def test_enum_failure_category_total_de_valores() -> None:
    """FailureCategory deve ter exatamente 12 valores."""
    assert len(FailureCategory) == 12


def test_enum_urgency_todos_os_valores() -> None:
    """UrgencyLevel deve conter IMEDIATA e DESCONHECIDA entre seus valores."""
    valores = [e.value for e in UrgencyLevel]
    assert "IMEDIATA" in valores
    assert "DESCONHECIDA" in valores


def test_enum_approach_type_hibrido() -> None:
    """ApproachType.HIBRIDO deve ter valor string correto."""
    assert ApproachType.HIBRIDO.value == "HIBRIDO"


def test_enum_priority_level_todos_os_valores() -> None:
    """PriorityLevel deve conter P1, P2, P3, P4 e DESCONHECIDA."""
    valores = {e.value for e in PriorityLevel}
    assert {"P1", "P2", "P3", "P4", "DESCONHECIDA"}.issubset(valores)
