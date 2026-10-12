"""
Motor de regras determinístico para triagem de ordens de serviço industriais.

Implementa a avaliação das regras de produção declarativas contra as
informações extraídas do relato e os dados de contexto enriquecido.

A função apply_rules() é determinística: mesma entrada sempre produz
mesma saída. Não usa LLM nem chamadas externas.

Protótipo acadêmico — monografia de especialização em Controle e Automação.
AVISO: Regras são exemplos sintéticos. Não usar em ambiente industrial real
sem validação por especialistas de manutenção e segurança.
"""

import unicodedata
from typing import Optional

from src.rules.definitions import Rule, RuleCondition
from src.schemas.extraction import ContextData, ExtractedInfo


def _normalize(texto: str) -> str:
    """
    Normaliza texto para matching insensível a acentos e maiúsculas.

    Remove acentos via decomposição NFD e converte para minúsculas ASCII.
    Mesma lógica usada no KeywordExtractor para garantir consistência.
    """
    nfd = unicodedata.normalize("NFD", texto.lower())
    return nfd.encode("ascii", "ignore").decode()


def _avalia_condicao(
    cond: RuleCondition,
    extracted: ExtractedInfo,
    context: ContextData,
    texto_norm: str,
    categoria_detectada: str,
) -> bool:
    """
    Avalia se as condições de uma regra são satisfeitas pela entrada.

    Constrói uma lista de verificações booleanas para cada campo não-None
    da condição, então aplica o operador lógico (AND ou OR).

    Retorna False se nenhuma condição for definida (regra sem condições
    nunca dispara automaticamente — proteção contra regras mal configuradas).

    Args:
        cond: condições da regra a avaliar.
        extracted: informações extraídas do relato.
        context: dados de contexto enriquecido da base local.
        texto_norm: texto original normalizado (sem acentos, minúsculas).
        categoria_detectada: string do enum FailureCategory detectado pelo extrator.

    Returns:
        True se as condições são satisfeitas conforme o operador.
    """
    verificacoes: list[bool] = []

    # Verificação de categoria detectada
    if cond.categoria is not None:
        verificacoes.append(categoria_detectada == cond.categoria)

    # Verificação de urgência mencionada (substring case-insensitive)
    if cond.urgencia_mencionada is not None:
        urgencia_extraida = extracted.urgencia_mencionada or ""
        verificacoes.append(
            cond.urgencia_mencionada.lower() in urgencia_extraida.lower()
        )

    # Verificação de risco de segurança
    if cond.risco_seguranca is not None:
        verificacoes.append(extracted.risco_seguranca == cond.risco_seguranca)

    # Verificação de impacto na produção
    if cond.impacto_producao is not None:
        verificacoes.append(extracted.impacto_producao == cond.impacto_producao)

    # Verificação de criticidade do ativo (False se ativo não encontrado)
    if cond.criticidade_ativo is not None:
        ativo = context.ativo_encontrado
        if ativo is None:
            verificacoes.append(False)
        else:
            verificacoes.append(ativo.criticidade == cond.criticidade_ativo)

    # Verificação de palavras-chave no texto normalizado ou nos sintomas
    if cond.palavras_chave:
        sintomas_norm = [_normalize(s) for s in extracted.sintomas]
        correspondencia = any(
            _normalize(kw) in texto_norm
            or any(_normalize(kw) in s for s in sintomas_norm)
            for kw in cond.palavras_chave
        )
        verificacoes.append(correspondencia)

    # Nenhuma condição definida → não dispara
    if not verificacoes:
        return False

    # Aplicar operador lógico
    if cond.operador == "OR":
        return any(verificacoes)
    else:  # AND (padrão)
        return all(verificacoes)


def apply_rules(
    extracted: ExtractedInfo,
    context: ContextData,
    rules: list[Rule],
    texto_original: str = "",
    categoria_detectada: Optional[str] = None,
) -> dict:
    """
    Aplica as regras de produção sobre as informações extraídas e de contexto.

    Avalia cada regra, coleta as que disparam, ordena por prioridade_regra
    decrescente e faz merge dos campos de ação (primeira regra não-None ganha).

    Fallback quando nenhuma regra dispara: urgência/prioridade DESCONHECIDA,
    requer_revisao_humana=True com motivo padrão.

    Args:
        extracted: informações extraídas do relato pelo extrator.
        context: dados de contexto enriquecido da base local.
        rules: lista de regras de produção a avaliar.
        texto_original: texto bruto do relato (usado para matching de palavras-chave).
        categoria_detectada: valor string do enum FailureCategory (ex: 'MECANICA').

    Returns:
        dict com chaves: urgencia, prioridade, equipe, requer_revisao_humana,
        motivo_revisao, confianca, regras_acionadas.
    """
    texto_norm = _normalize(texto_original)
    cat_str = categoria_detectada or ""

    # Identificar regras que disparam
    regras_disparadas = [
        rule
        for rule in rules
        if _avalia_condicao(rule.condicoes, extracted, context, texto_norm, cat_str)
    ]

    # Fallback: nenhuma regra disparou
    if not regras_disparadas:
        return {
            "urgencia": "DESCONHECIDA",
            "prioridade": "DESCONHECIDA",
            "equipe": "Revisão necessária",
            "requer_revisao_humana": True,
            "motivo_revisao": (
                "Nenhuma regra de triagem disparada — informações insuficientes "
                "para classificação automática."
            ),
            "confianca": 0.0,
            "regras_acionadas": [],
        }

    # Ordenar por prioridade_regra decrescente (maior = mais prioritário)
    regras_ordenadas = sorted(
        regras_disparadas, key=lambda r: r.prioridade_regra, reverse=True
    )

    # Merge de campos: primeiro valor não-None de maior prioridade prevalece
    urgencia: Optional[str] = None
    prioridade: Optional[str] = None
    equipe: Optional[str] = None
    requer_revisao_humana: Optional[bool] = None
    motivo_revisao: Optional[str] = None
    confianca: Optional[float] = None

    for rule in regras_ordenadas:
        if urgencia is None and rule.acoes.urgencia is not None:
            urgencia = rule.acoes.urgencia
        if prioridade is None and rule.acoes.prioridade is not None:
            prioridade = rule.acoes.prioridade
        if equipe is None and rule.acoes.equipe is not None:
            equipe = rule.acoes.equipe
        if requer_revisao_humana is None and rule.acoes.requer_revisao_humana is not None:
            requer_revisao_humana = rule.acoes.requer_revisao_humana
        if motivo_revisao is None and rule.acoes.motivo_revisao is not None:
            motivo_revisao = rule.acoes.motivo_revisao
        if confianca is None and rule.acoes.confianca is not None:
            confianca = rule.acoes.confianca

    # Aplicar defaults para campos não definidos por nenhuma regra
    urgencia = urgencia if urgencia is not None else "DESCONHECIDA"
    prioridade = prioridade if prioridade is not None else "DESCONHECIDA"
    equipe = equipe if equipe is not None else "Revisão necessária"
    requer_revisao_humana = requer_revisao_humana if requer_revisao_humana is not None else False
    confianca = confianca if confianca is not None else 0.0

    # Garantir motivo_revisao quando requer_revisao_humana=True
    # (protege contra TriageResult @model_validator que rejeita motivo None)
    if requer_revisao_humana and motivo_revisao is None:
        motivo_revisao = (
            "Regra de triagem requer verificação humana — revisar manualmente."
        )

    return {
        "urgencia": urgencia,
        "prioridade": prioridade,
        "equipe": equipe,
        "requer_revisao_humana": requer_revisao_humana,
        "motivo_revisao": motivo_revisao,
        "confianca": confianca,
        "regras_acionadas": [r.id for r in regras_ordenadas],
    }
