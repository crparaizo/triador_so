"""
Carregamento de configurações do sistema via pydantic-settings.

Lê variáveis de ambiente e arquivo .env (opcional). Todos os campos têm
valores padrão funcionais para que o sistema execute sem .env configurado.

Usar get_settings() para obter a instância cacheada.
Chamar get_settings.cache_clear() em testes para reiniciar o cache.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações globais do sistema de triagem.

    Valores podem ser sobrescritos por variáveis de ambiente ou por arquivo
    .env na raiz do projeto. Consulte .env.example para referência.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Não lança exceção se .env não existir
    )

    # LLM / Ollama
    ollama_model: str = Field(
        default="qwen3:0.6b",
        description=(
            "Nome do modelo Ollama a ser utilizado. Padrão qwen3:0.6b (~500 MB), "
            "escolhido para rodar inteiramente em GPU com VRAM limitada — o modelo "
            "efetivamente usado nos experimentos da monografia. Modelos maiores "
            "(qwen3:1.7b, qwen3:4b) exigem mais VRAM; configurável via .env."
        ),
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="URL base do servidor Ollama",
    )
    ollama_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description=(
            "Temperatura de geração do LLM. 0.0 torna a saída praticamente "
            "determinística — recomendado para reprodutibilidade da avaliação."
        ),
    )
    ollama_seed: int = Field(
        default=42,
        description=(
            "Semente de geração do LLM. Fixá-la, junto com temperature=0, "
            "reduz a variação entre execuções e favorece a reprodutibilidade."
        ),
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

    # Controle de chamadas LLM
    max_retries_llm: int = Field(
        default=3,
        ge=1,
        description="Número máximo de tentativas para chamadas LLM",
    )
    llm_timeout_seconds: int = Field(
        default=60,
        ge=1,
        description="Timeout em segundos para chamadas LLM",
    )
    ollama_num_predict: int = Field(
        default=1024,
        ge=64,
        description=(
            "Limite de tokens gerados por chamada ao LLM (inclui o raciocínio do "
            "qwen3). Com format='json', modelos pequenos podem entrar em laço "
            "repetindo chaves sem fechar o objeto; o limite encerra a geração e a "
            "resposta truncada segue a política de falha segura (revisão humana)."
        ),
    )
    ollama_num_ctx: int = Field(
        default=4096,
        ge=512,
        description=(
            "Janela de contexto do modelo (parâmetro num_ctx do Ollama), fixada "
            "para não depender do padrão do servidor. 4.096 tokens comportam o "
            "maior prompt do protótipo somado ao limite de num_predict."
        ),
    )
    ollama_reasoning: Optional[bool] = Field(
        default=True,
        description=(
            "Modo de raciocínio do modelo (parâmetro reasoning do ChatOllama). "
            "True ativa o raciocínio de forma explícita — mesma geração do padrão "
            "do qwen3, mas com o texto do raciocínio devolvido à parte, o que "
            "permite registrá-lo. False desativa o raciocínio (variante "
            "experimental, OLLAMA_REASONING=false). None deixa o padrão do modelo."
        ),
    )

    @field_validator("ollama_reasoning", mode="before")
    @classmethod
    def _reasoning_vazio_e_padrao(cls, v):
        """OLLAMA_REASONING vazio equivale a não definido (raciocínio ativado)."""
        return True if isinstance(v, str) and not v.strip() else v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Retorna instância singleton de Settings com cache.
    Usar get_settings.cache_clear() em testes para reiniciar.
    """
    return Settings()
