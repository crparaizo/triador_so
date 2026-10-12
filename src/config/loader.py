"""
Carregamento de configurações do sistema via pydantic-settings.

Lê variáveis de ambiente e arquivo .env (opcional). Todos os campos têm
valores padrão funcionais para que o sistema execute sem .env configurado.

Usar get_settings() para obter a instância cacheada.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações globais do sistema de triagem.

    Valores podem ser sobrescritos por variáveis de ambiente ou por arquivo
    .env na raiz do projeto. Consulte .env.example para referência.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM / Ollama
    ollama_model: str = Field(
        default="qwen3:4b",
        description="Nome do modelo Ollama a ser utilizado",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="URL base do servidor Ollama",
    )

    # Diretórios
    data_dir: str = Field(
        default="data",
        description="Diretório contendo os arquivos YAML de dados locais",
    )
    results_dir: str = Field(
        default="results",
        description="Diretório para salvar relatórios de avaliação",
    )
    sessions_dir: str = Field(
        default="sessions",
        description="Diretório para persistir resultados de sessões",
    )

    # Comportamento
    log_level: str = Field(
        default="INFO",
        description="Nível de log (DEBUG, INFO, WARNING, ERROR)",
    )


@lru_cache()
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações. Lê .env uma única vez."""
    return Settings()
