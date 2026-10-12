"""
Carregamento e cache dos dados de contexto do sistema de triagem.

Este módulo lê os arquivos YAML de domínio (ativos, equipes e categorias) e
os expõe via funções cacheadas. Os dados são validados com Pydantic na carga.

Funções:
    load_knowledge_base() -> KnowledgeBase  — ativos e equipes
    load_categories()     -> dict           — categorias de falha com palavras-chave

Para recarregar os dados em testes, chamar .cache_clear() nas funções:
    load_knowledge_base.cache_clear()
    load_categories.cache_clear()

AVISO: Dados sintéticos para protótipo acadêmico. Não representam instalação real.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.config.loader import get_settings
from src.schemas.assets import Asset, KnowledgeBase, Team


@lru_cache(maxsize=1)
def load_knowledge_base() -> KnowledgeBase:
    """
    Carrega ativos e equipes dos arquivos YAML e valida com Pydantic.

    Usa cache — chamar load_knowledge_base.cache_clear() para recarregar.

    Returns:
        KnowledgeBase com ativos e equipes validados.

    Raises:
        FileNotFoundError: se os arquivos YAML não forem encontrados.
        ValueError: se os dados YAML forem inválidos (mensagem descritiva).
    """
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    assets_path = data_dir / "assets.yaml"
    teams_path = data_dir / "teams.yaml"

    # Verificar existência dos arquivos antes de tentar abrir
    if not assets_path.exists():
        raise FileNotFoundError(
            f"Arquivo de ativos não encontrado: {assets_path}. "
            "Verifique se o diretório 'data/' está presente na raiz do projeto."
        )
    if not teams_path.exists():
        raise FileNotFoundError(
            f"Arquivo de equipes não encontrado: {teams_path}. "
            "Verifique se o diretório 'data/' está presente na raiz do projeto."
        )

    # Carregar e parsear YAML
    with open(assets_path, encoding="utf-8") as f:
        assets_data = yaml.safe_load(f)

    with open(teams_path, encoding="utf-8") as f:
        teams_data = yaml.safe_load(f)

    # Validar com Pydantic — erros são convertidos em ValueError com descrição
    try:
        assets = [Asset(**a) for a in (assets_data or {}).get("assets", [])]
        teams = [Team(**t) for t in (teams_data or {}).get("teams", [])]
        return KnowledgeBase(assets=assets, teams=teams)
    except (ValidationError, TypeError) as exc:
        raise ValueError(
            f"Erro ao validar dados de ativos/equipes: {exc}"
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"Erro inesperado ao carregar base de conhecimento: {exc}"
        ) from exc


@lru_cache(maxsize=1)
def load_categories() -> dict:
    """
    Carrega categorias de falha do arquivo categories.yaml.

    Retorna dict cujas chaves são os nomes de categoria (ex: 'MECANICA') e
    os valores são dicts com: descricao, palavras_chave, equipe_padrao,
    urgencia_padrao.

    Usa cache — chamar load_categories.cache_clear() para recarregar.

    Returns:
        dict com categorias de falha validadas.

    Raises:
        FileNotFoundError: se o arquivo categories.yaml não for encontrado.
        ValueError: se os dados forem inválidos ou o arquivo estiver vazio.
    """
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    categories_path = data_dir / "categories.yaml"

    if not categories_path.exists():
        raise FileNotFoundError(
            f"Arquivo de categorias não encontrado: {categories_path}. "
            "Verifique se o diretório 'data/' está presente na raiz do projeto."
        )

    with open(categories_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cats = (data or {}).get("categorias", {})
    if not cats:
        raise ValueError(
            "Arquivo categories.yaml não contém categorias válidas. "
            "Verifique a estrutura do arquivo — esperado chave 'categorias'."
        )

    return cats
