"""
Definições Pydantic v2 das regras de produção para triagem de ordens de serviço.

Define os modelos RuleCondition, RuleAction e Rule que representam a estrutura
declarativa de uma regra de triagem industrial. Inclui a função load_rules()
com cache para carregar as regras do arquivo data/rules.yaml.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
AVISO: Não usar em ambiente industrial real sem validação por especialistas.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

from src.config.loader import get_settings


class RuleCondition(BaseModel):
    """
    Condições de disparo de uma regra de produção.

    Todos os campos são opcionais. O campo 'operador' controla como as
    condições não-nulas são combinadas:
      AND (padrão) — todas as condições não-nulas devem ser satisfeitas.
      OR           — qualquer condição não-nula satisfeita dispara a regra.

    O campo 'palavras_chave' é internamente sempre OR: basta uma palavra-chave
    corresponder no texto ou nos sintomas extraídos.
    """

    # Categoria da falha esperada (valor de FailureCategory, ex: "MECANICA")
    categoria: Optional[str] = None

    # Substring verificada em ExtractedInfo.urgencia_mencionada
    urgencia_mencionada: Optional[str] = None

    # Indica se risco de segurança deve estar presente (True) ou ausente (False)
    risco_seguranca: Optional[bool] = None

    # Indica se impacto na produção deve estar presente (True) ou ausente (False)
    impacto_producao: Optional[bool] = None

    # Criticidade do ativo encontrado: "ALTA" | "MEDIA" | "BAIXA"
    criticidade_ativo: Optional[str] = None

    # Lista de palavras-chave — basta uma coincidir no texto ou sintomas
    palavras_chave: Optional[list[str]] = None

    # Operador lógico que combina as condições não-nulas desta regra
    operador: Literal["AND", "OR"] = "AND"


class RuleAction(BaseModel):
    """
    Ações executadas quando uma regra de produção dispara.

    Todos os campos são opcionais. O motor de regras aplica os valores
    por precedência — o campo da regra com maior prioridade_regra prevalece.

    Quando requer_revisao_humana=True, o campo motivo_revisao deve ser
    preenchido. Esta restrição é validada no YAML de entrada e respeitada
    pelo motor de regras.
    """

    # Nível de urgência resultante (valor de UrgencyLevel, ex: "IMEDIATA")
    urgencia: Optional[str] = None

    # Nível de prioridade resultante (valor de PriorityLevel, ex: "P1")
    prioridade: Optional[str] = None

    # Nome da equipe responsável pelo atendimento
    equipe: Optional[str] = None

    # Indica se revisão humana é obrigatória para este resultado
    requer_revisao_humana: Optional[bool] = None

    # Justificativa para revisão humana — obrigatório quando requer_revisao_humana=True
    motivo_revisao: Optional[str] = None

    # Confiança associada a esta ação (0.0 = nenhuma, 1.0 = total)
    confianca: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class Rule(BaseModel):
    """
    Regra de produção completa com condições, ações e nível de precedência.

    O campo prioridade_regra controla a ordem de aplicação no motor:
    valores maiores têm precedência. Quando múltiplas regras disparam para
    o mesmo campo de ação, vence a de maior prioridade_regra.
    """

    # Identificador único da regra (ex: "RULE-001")
    id: str

    # Descrição legível da regra em português
    descricao: str

    # Condições de disparo
    condicoes: RuleCondition

    # Ações a executar quando as condições são satisfeitas
    acoes: RuleAction

    # Precedência no motor de regras — maior valor = maior prioridade
    prioridade_regra: int = Field(..., ge=1, description="Maior valor = maior precedência")


@lru_cache(maxsize=1)
def load_rules() -> list[Rule]:
    """
    Carrega regras de triagem do arquivo data/rules.yaml e valida com Pydantic.

    Usa cache (lru_cache) — chamar load_rules.cache_clear() para recarregar,
    especialmente necessário em testes para garantir isolamento.

    Returns:
        list[Rule] com todas as regras validadas pelo Pydantic.

    Raises:
        FileNotFoundError: se o arquivo rules.yaml não for encontrado.
        ValueError: se a estrutura do YAML for inválida ou falhar na validação.
    """
    settings = get_settings()
    rules_path = Path(settings.data_dir) / "rules.yaml"

    # Verificar existência do arquivo antes de tentar abrir
    if not rules_path.exists():
        raise FileNotFoundError(
            f"Arquivo de regras não encontrado: {rules_path}. "
            "Verifique se o diretório 'data/' e o arquivo 'rules.yaml' estão "
            "presentes na raiz do projeto."
        )

    # Carregar conteúdo YAML
    with open(rules_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Extrair lista de regras sob a chave 'regras'
    regras_raw = (data or {}).get("regras", [])
    if not regras_raw:
        raise ValueError(
            "Arquivo rules.yaml não contém regras válidas. "
            "Verifique a estrutura do arquivo — esperado chave 'regras' com lista de itens."
        )

    # Validar cada regra com Pydantic — erros são convertidos em ValueError descritivo
    try:
        return [Rule(**item) for item in regras_raw]
    except (ValidationError, TypeError) as exc:
        raise ValueError(
            f"Erro ao validar estrutura das regras em rules.yaml: {exc}"
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"Erro inesperado ao carregar regras: {exc}"
        ) from exc
