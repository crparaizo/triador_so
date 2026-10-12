"""
Gerenciador de sessões para o sistema de triagem de OS industriais.

AVISO: Este é um protótipo acadêmico. Os resultados armazenados requerem
revisão humana e validação por especialistas antes de qualquer uso operacional.

As sessões são persistidas como arquivos JSON na pasta configurada em
``Settings.sessions_dir``. Cada arquivo contém o texto de entrada, o
timestamp da triagem e os resultados produzidos pelas abordagens executadas.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.config.loader import get_settings
from src.schemas.triage import TriageResult

logger = logging.getLogger(__name__)


def save_session(results: dict[str, TriageResult], texto: str) -> str:
    """Persiste os resultados de uma triagem como arquivo JSON na pasta de sessões.

    Parâmetros
    ----------
    results:
        Dicionário mapeando nome da abordagem (p.ex. ``'hibrido'``) ao
        respectivo :class:`TriageResult`.
    texto:
        Texto de entrada da triagem.

    Retorno
    -------
    str
        Caminho absoluto (str) do arquivo JSON criado.
    """
    sessions_dir = Path(get_settings().sessions_dir)
    # Garante que a pasta existe, inclusive pais intermediários
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Nome único: YYYYMMDD_HHMMSS_<8 primeiros chars do UUID>
    timestamp = datetime.now()
    suffix = uuid4().hex[:8]
    filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{suffix}.json"
    filepath = sessions_dir / filename

    # Serializa cada TriageResult para dict JSON-safe com Pydantic v2
    resultados_serializados = {
        abordagem: resultado.model_dump(mode="json")
        for abordagem, resultado in results.items()
    }

    payload = {
        "timestamp": timestamp.isoformat(),
        "texto": texto,
        "results": resultados_serializados,
    }

    with filepath.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    logger.debug("Sessão salva em: %s", filepath)
    return str(filepath)


def load_sessions() -> list[dict]:
    """Carrega todas as sessões salvas na pasta de sessões, ordenadas por timestamp.

    Arquivos JSON inválidos ou ilegíveis são ignorados individualmente sem
    propagar exceção. Se a pasta ainda não existir, retorna lista vazia.

    Retorno
    -------
    list[dict]
        Lista de dicionários de sessão, ordenada por ``'timestamp'`` descendente
        (sessão mais recente primeiro). Retorna ``[]`` se não houver sessões.
    """
    sessions_dir = Path(get_settings().sessions_dir)

    if not sessions_dir.exists():
        return []

    sessions: list[dict] = []
    for json_file in sessions_dir.glob("*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            sessions.append(data)
        except json.JSONDecodeError as exc:
            logger.warning("Arquivo de sessão inválido ignorado (%s): %s", json_file.name, exc)
        except OSError as exc:
            logger.warning("Erro ao ler arquivo de sessão (%s): %s", json_file.name, exc)

    # Ordena por timestamp descendente; arquivos sem campo usam string vazia
    sessions.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
    return sessions


def clear_sessions() -> int:
    """Remove todos os arquivos JSON da pasta de sessões, preservando .gitkeep.

    Retorno
    -------
    int
        Quantidade de arquivos removidos.
    """
    sessions_dir = Path(get_settings().sessions_dir)

    if not sessions_dir.exists():
        return 0

    removidos = 0
    for json_file in sessions_dir.glob("*.json"):
        try:
            json_file.unlink()
            removidos += 1
        except OSError as exc:
            logger.warning("Falha ao remover sessão (%s): %s", json_file.name, exc)

    logger.debug("%d sessão(ões) removida(s).", removidos)
    return removidos
