"""
Fixtures compartilhadas para os testes do sistema de triagem.

Todos os dados são criados inline — nenhuma fixture depende de arquivos YAML,
Ollama ou qualquer serviço externo. As fixtures cobrem schemas, configurações
e a base de conhecimento de teste.
"""

import pytest

from src.config.loader import Settings
from src.schemas.assets import Asset, KnowledgeBase, Team
from src.schemas.extraction import ExtractedInfo
from src.schemas.triage import (
    ApproachType,
    FailureCategory,
    PriorityLevel,
    TriageResult,
    UrgencyLevel,
)


@pytest.fixture
def sample_asset() -> Asset:
    """Ativo mecânico de teste (não representa instalação real)."""
    return Asset(
        id="test-001",
        nome="Bomba Centrífuga Teste",
        tag="BOMB-TEST",
        tipo="Mecânico",
        localizacao="Setor A - Linha 1",
        equipe_responsavel="Manutenção Mecânica",
        criticidade="ALTA",
        observacoes="Ativo de teste",
    )


@pytest.fixture
def sample_team() -> Team:
    """Equipe de manutenção mecânica de teste."""
    return Team(
        id="team-001",
        nome="Manutenção Mecânica",
        especialidades=["bombas centrífugas", "compressores", "motores elétricos"],
        contato="mecanica@planta.com",
        disponivel=True,
    )


@pytest.fixture
def sample_knowledge_base(sample_asset: Asset, sample_team: Team) -> KnowledgeBase:
    """Base de conhecimento com 2 ativos e 2 equipes de teste."""
    segundo_ativo = Asset(
        id="test-002",
        nome="Painel Elétrico Teste",
        tag="PANEL-TEST",
        tipo="Elétrico",
        localizacao="Setor B - Subestação",
        equipe_responsavel="Manutenção Elétrica",
        criticidade="MEDIA",
    )
    segunda_equipe = Team(
        id="team-002",
        nome="Manutenção Elétrica",
        especialidades=["painéis elétricos", "transformadores"],
        contato="eletrica@planta.com",
        disponivel=True,
    )
    return KnowledgeBase(
        assets=[sample_asset, segundo_ativo],
        teams=[sample_team, segunda_equipe],
    )


@pytest.fixture
def sample_extracted_info() -> ExtractedInfo:
    """ExtractedInfo de teste com campos preenchidos a partir de texto sintético."""
    return ExtractedInfo(
        ativo_mencionado="BOMB-TEST",
        sintomas=["vibração excessiva", "ruído anormal"],
        localizacao="Setor A",
        impacto_producao=True,
        risco_seguranca=False,
        urgencia_mencionada="alta",
        evidencias={
            "ativo": "bomba BOMB-TEST",
            "sintoma": "vibração excessiva",
        },
        confianca_extracao=0.85,
        campos_sem_suporte=[],
    )


@pytest.fixture
def sample_triage_result() -> TriageResult:
    """TriageResult de teste gerado pela abordagem híbrida."""
    return TriageResult(
        abordagem=ApproachType.HIBRIDO,
        texto_entrada="Bomba BOMB-TEST com vibração excessiva no Setor A",
        urgencia=UrgencyLevel.ALTA,
        prioridade=PriorityLevel.P2,
        categoria=FailureCategory.MECANICA,
        equipe_sugerida="Manutenção Mecânica",
        regras_acionadas=["REGRA_VIBRACAO_ALTA", "REGRA_CRITICIDADE_ALTA"],
        evidencias={"urgencia": "vibração excessiva"},
        requer_revisao_humana=False,
        confianca=0.9,
        latencia_ms=150.0,
        campos_sem_suporte=[],
    )


@pytest.fixture
def settings() -> Settings:
    """Settings com valores de teste — não depende de arquivo .env nem de Ollama."""
    return Settings(
        ollama_model="test-model",
        ollama_base_url="http://localhost:11434",
        data_dir="data",
        results_dir="results",
        sessions_dir="sessions",
    )
