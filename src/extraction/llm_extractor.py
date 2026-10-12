"""
Extrator de informações via LLM (ChatOllama) para triagem de ordens de serviço.

Recebe texto livre de um relato, envia ao LLM com prompt em português e retorna
ExtractedInfo com os campos extraídos. Nunca lança exceção ao chamador — falhas
de conexão ou parse retornam ExtractedInfo com erro_parse preenchido.

A conexão com Ollama ocorre APENAS dentro de extract(), nunca no __init__ nem
no escopo de módulo.

AVISO: Protótipo acadêmico. Revisão humana obrigatória antes de uso operacional.
"""

import logging
from typing import Optional

from langchain_ollama import ChatOllama  # import seguro — sem conexão TCP

from src.config.loader import get_settings
from src.schemas.extraction import ExtractedInfo
from src.utils.parsers import parsear_json_llm

logger = logging.getLogger(__name__)

# Campos rastreáveis para cálculo de campos_sem_suporte e confianca_extracao.
# Proporção preenchidos/total define a confiança calculada localmente — não
# depende do valor que o LLM retorna no campo confianca_extracao.
_CAMPOS_RASTREÁVEIS: list[str] = [
    "ativo_mencionado",
    "localizacao",
    "impacto_producao",
    "risco_seguranca",
    "urgencia_mencionada",
]

# Prompt em português. Chaves {{ e }} no exemplo one-shot são literais Python
# (escapadas) — apenas {texto} é substituído em .format(texto=...).
_PROMPT_TEMPLATE = """Você é um extrator de informações de relatos de manutenção industrial.

Extraia SOMENTE informações presentes no texto abaixo. Não invente dados.
Se um campo não está mencionado no texto, retorne null.

Campos esperados:
- ativo_mencionado: tag ou nome do ativo explicitamente citado (string ou null)
- sintomas: lista de sintomas ou problemas descritos (array de strings, pode ser [])
- localizacao: localização mencionada no relato (string ou null)
- impacto_producao: true se menciona impacto na produção, false se nega, null se não menciona
- risco_seguranca: true se menciona risco de segurança, false se nega, null se não menciona
- urgencia_mencionada: expressão de urgência usada literalmente no texto (string ou null)
- evidencias: objeto JSON com trechos exatos do texto que fundamentam cada campo preenchido
- confianca_extracao: número entre 0.0 e 1.0 indicando sua confiança na extração

Exemplo de saída para "A bomba BOMB-001 está com vibração excessiva no Setor A. Urgente!":
{{
  "ativo_mencionado": "BOMB-001",
  "sintomas": ["vibração excessiva"],
  "localizacao": "Setor A",
  "impacto_producao": null,
  "risco_seguranca": null,
  "urgencia_mencionada": "Urgente",
  "evidencias": {{
    "ativo_mencionado": "bomba BOMB-001",
    "sintomas": "vibração excessiva",
    "localizacao": "Setor A",
    "urgencia_mencionada": "Urgente!"
  }},
  "confianca_extracao": 0.8
}}

Texto do relato:
---
{texto}
---

Retorne APENAS o JSON puro. Sem explicações, sem markdown, sem comentários."""


class LLMExtractor:
    """
    Extrator de informações de relatos via LLM (ChatOllama).

    Conexão com Ollama ocorre apenas em extract(), nunca no __init__ nem no
    import. Retry automático para falhas de invocação (conexão/timeout).
    Erros de parse retornam imediatamente sem retry.

    Nunca lança exceção ao chamador — qualquer falha retorna ExtractedInfo
    com erro_parse preenchido.
    """

    def __init__(self, model: str | None = None) -> None:
        """
        Armazena configurações do modelo. Não instancia ChatOllama nem conecta.

        Args:
            model: nome do modelo Ollama. Se None, usa settings.ollama_model.
        """
        settings = get_settings()
        self._model: str = model or settings.ollama_model
        self._base_url: str = settings.ollama_base_url
        self._max_retries: int = settings.max_retries_llm
        self._timeout: int = settings.llm_timeout_seconds
        self._temperature: float = settings.ollama_temperature
        self._seed: int = settings.ollama_seed

    def _build_prompt(self, texto: str) -> str:
        """Monta o prompt substituindo {texto} no template."""
        return _PROMPT_TEMPLATE.format(texto=texto)

    def _criar_llm(self) -> ChatOllama:
        """
        Instancia ChatOllama em runtime. Chamado apenas dentro de extract().
        Separado para facilitar testes e eventual parametrização.
        """
        return ChatOllama(
            model=self._model,
            base_url=self._base_url,
            temperature=self._temperature,
            seed=self._seed,
        )

    def _dict_para_extracted_info(self, data: dict) -> ExtractedInfo:
        """
        Converte dict retornado pelo LLM em ExtractedInfo.

        Calcula campos_sem_suporte e confianca_extracao localmente —
        não usa o valor de confianca_extracao informado pelo próprio LLM.
        """
        # Extração defensiva de cada campo
        ativo = data.get("ativo_mencionado")
        sintomas_raw = data.get("sintomas") or []
        localizacao = data.get("localizacao")
        impacto = data.get("impacto_producao")
        risco = data.get("risco_seguranca")
        urgencia = data.get("urgencia_mencionada")
        evidencias_raw = data.get("evidencias") or {}

        # Campos rastreáveis com valor None no dict = sem suporte no texto
        campos_sem_suporte = [
            campo for campo in _CAMPOS_RASTREÁVEIS
            if data.get(campo) is None
        ]

        # Confiança calculada localmente: proporção de rastreáveis preenchidos
        num_com_valor = len(_CAMPOS_RASTREÁVEIS) - len(campos_sem_suporte)
        confianca = num_com_valor / len(_CAMPOS_RASTREÁVEIS)

        return ExtractedInfo(
            ativo_mencionado=str(ativo) if isinstance(ativo, str) else None,
            sintomas=[str(s) for s in sintomas_raw if isinstance(s, str)],
            localizacao=str(localizacao) if isinstance(localizacao, str) else None,
            impacto_producao=bool(impacto) if isinstance(impacto, bool) else None,
            risco_seguranca=bool(risco) if isinstance(risco, bool) else None,
            urgencia_mencionada=str(urgencia) if isinstance(urgencia, str) else None,
            evidencias={k: str(v) for k, v in evidencias_raw.items() if isinstance(k, str)},
            confianca_extracao=confianca,
            campos_sem_suporte=campos_sem_suporte,
            erro_parse=None,
        )

    def extract(self, texto: str) -> ExtractedInfo:
        """
        Extrai informações do relato usando o LLM.

        Fluxo:
        - Monta prompt com _build_prompt.
        - Para cada tentativa (até _max_retries):
            - Instancia ChatOllama e chama invoke().
            - Exceção de invoke → registra aviso e tenta novamente.
            - Erro de parse → retorna imediatamente (sem retry).
        - Esgotados os retries → retorna ExtractedInfo com erro_parse.

        Nunca lança exceção ao chamador.

        Args:
            texto: relato livre da ocorrência.

        Returns:
            ExtractedInfo com campos preenchidos ou com erro_parse em caso de falha.
        """
        prompt = self._build_prompt(texto)
        ultimo_erro: str = "desconhecido"

        for tentativa in range(self._max_retries):
            try:
                # Instanciar ChatOllama em runtime — nunca em __init__
                llm = self._criar_llm()
                resposta = llm.invoke(prompt)

                # Obter texto da resposta (AIMessage.content ou str)
                texto_resposta = (
                    resposta.content if hasattr(resposta, "content") else str(resposta)
                )

                data, erro = parsear_json_llm(texto_resposta)

                if erro:
                    # Erro de parse: retornar imediatamente, sem retry
                    logger.warning("LLMExtractor: erro de parse na tentativa %d: %s", tentativa + 1, erro)
                    return ExtractedInfo(erro_parse=erro)

                # Parse bem-sucedido
                return self._dict_para_extracted_info(data)

            except Exception as exc:
                # Qualquer exceção de invoke = falha de conexão/runtime → retry
                ultimo_erro = str(exc)
                logger.warning(
                    "LLMExtractor: tentativa %d/%d falhou — %s: %s",
                    tentativa + 1,
                    self._max_retries,
                    type(exc).__name__,
                    exc,
                )
                # Continua para próxima tentativa

        # Esgotou todos os retries sem sucesso
        logger.error(
            "Ollama indisponível após %d tentativas: %s",
            self._max_retries,
            ultimo_erro,
        )
        return ExtractedInfo(erro_parse=f"Ollama indisponível: {ultimo_erro}")
