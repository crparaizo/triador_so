"""
Módulo de enriquecimento de contexto para triagem de ordens de serviço.

Fornece a função enrich_context, compartilhada pelas abordagens rules_only e hybrid,
que busca dados locais de ativos e equipes para enriquecer as informações extraídas
do relato.

Ordem de busca do ativo:
    1. Tag exata (case-insensitive) via get_asset_by_tag.
    2. Nome substring (case-insensitive) varrendo kb.assets.
    3. Localização (fallback) via find_assets_by_location.

Convenção de fonte_enriquecimento (D2):
    - 'assets.yaml'    → ativo encontrado por qualquer método.
    - 'não encontrado' → nenhum ativo correspondeu.

AVISO: Protótipo acadêmico. Não usar em ambiente industrial real sem validação
por especialistas de manutenção e segurança.
"""

import logging

from src.schemas.assets import KnowledgeBase
from src.schemas.extraction import ContextData, ExtractedInfo

# Logger do módulo — erros registrados sem expor traceback ao usuário final
logger = logging.getLogger(__name__)


def enrich_context(
    extracted: ExtractedInfo,
    kb: KnowledgeBase,
    categorias: dict | None = None,
    categoria_detectada: str | None = None,
) -> ContextData:
    """
    Enriquece o contexto cruzando ExtractedInfo com a base de conhecimento local.

    Busca o ativo na ordem: tag exata → nome substring → localização.
    Monta equipes_candidatas com a equipe responsável pelo ativo encontrado e,
    opcionalmente, com a equipe_padrao da categoria detectada (sem duplicatas).

    Args:
        extracted: informações extraídas do relato de ocorrência.
        kb: base de conhecimento com ativos e equipes cadastrados.
        categorias: dicionário de categorias com campo 'equipe_padrao' (opcional).
        categoria_detectada: chave da categoria detectada no texto (opcional).

    Returns:
        ContextData com ativo_encontrado, equipes_candidatas, historico_notas e
        fonte_enriquecimento.
    """
    ativo = None

    if extracted.ativo_mencionado:
        # 1. Busca por tag exata (case-insensitive via get_asset_by_tag)
        ativo = kb.get_asset_by_tag(extracted.ativo_mencionado)

        # 2. Fallback: busca por nome substring (case-insensitive)
        if ativo is None:
            mencionado_lower = extracted.ativo_mencionado.lower()
            for asset in kb.assets:
                if mencionado_lower in asset.nome.lower():
                    ativo = asset
                    break

    # 3. Fallback: busca por localização mencionada no relato
    if ativo is None and extracted.localizacao:
        ativos_por_local = kb.find_assets_by_location(extracted.localizacao)
        if ativos_por_local:
            ativo = ativos_por_local[0]

    # Montar lista de equipes candidatas
    equipes_candidatas = []

    # Equipe responsável pelo ativo encontrado
    if ativo and ativo.equipe_responsavel:
        equipe_ativo = kb.get_team_by_name(ativo.equipe_responsavel)
        if equipe_ativo:
            equipes_candidatas.append(equipe_ativo)

    # Equipe padrão da categoria detectada (sem duplicata por nome)
    if categorias and categoria_detectada and categoria_detectada in categorias:
        nome_equipe_padrao = categorias[categoria_detectada].get("equipe_padrao")
        if nome_equipe_padrao:
            equipe_padrao = kb.get_team_by_name(nome_equipe_padrao)
            if equipe_padrao:
                nomes_existentes = {e.nome for e in equipes_candidatas}
                if equipe_padrao.nome not in nomes_existentes:
                    equipes_candidatas.append(equipe_padrao)

    # Notas históricas do ativo (observacoes não vazias)
    historico_notas = [ativo.observacoes] if ativo and ativo.observacoes else []

    # Fonte de enriquecimento conforme convenção D2
    fonte = "assets.yaml" if ativo else "não encontrado"

    logger.debug(
        "enrich_context: ativo=%s fonte=%s equipes=%d",
        ativo.tag if ativo else None,
        fonte,
        len(equipes_candidatas),
    )

    return ContextData(
        ativo_encontrado=ativo,
        equipes_candidatas=equipes_candidatas,
        historico_notas=historico_notas,
        fonte_enriquecimento=fonte,
    )
