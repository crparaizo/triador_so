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

from src.extraction.keyword_extractor import contem_termo
from src.extraction.medicoes import pressoes_kpa
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
    texto_original: str = "",
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
        texto_original: texto bruto do relato, usado para ler valores de pressão.

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

    # Pressão relatada acima da PMTA do ativo cadastrado (NR-13, Glossário).
    # Lida do texto original, que preserva a vírgula decimal e a unidade.
    if cond.pressao_acima_pmta is not None:
        ativo = context.ativo_encontrado
        pmta = ativo.pmta_kpa if ativo is not None else None
        acima = pmta is not None and any(p > pmta for p in pressoes_kpa(texto_original))
        verificacoes.append(acima == cond.pressao_acima_pmta)

    # Verificação de palavras-chave no texto normalizado ou nos sintomas.
    # Cada grupo (palavras_chave e palavras_chave_condicao) é uma condição
    # própria, com OR interno entre os termos do grupo.
    sintomas_norm = [_normalize(s) for s in extracted.sintomas]

    def _casa_grupo(grupo: list[str]) -> bool:
        return any(
            contem_termo(_normalize(kw), texto_norm)
            or any(contem_termo(_normalize(kw), s) for s in sintomas_norm)
            for kw in grupo
        )

    # Norma do ativo cadastrado: alternativa (OR) ao grupo palavras_chave
    ativo_na_norma: Optional[bool] = None
    if cond.norma_ativo is not None:
        ativo = context.ativo_encontrado
        ativo_na_norma = ativo is not None and cond.norma_ativo in ativo.normas_aplicaveis

    if cond.palavras_chave:
        verificacoes.append(bool(ativo_na_norma) or _casa_grupo(cond.palavras_chave))
    elif ativo_na_norma is not None:
        verificacoes.append(ativo_na_norma)
    if cond.palavras_chave_condicao:
        verificacoes.append(_casa_grupo(cond.palavras_chave_condicao))

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
    A revisão humana é a exceção: basta uma regra disparada exigi-la.

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
        motivo_revisao, confianca, regras_acionadas e rastro (campo → regra
        que definiu o valor; em 'revisao', todas as que exigiram a revisão).
    """
    texto_norm = _normalize(texto_original)
    cat_str = categoria_detectada or ""

    # Identificar regras que disparam
    regras_disparadas = [
        rule
        for rule in rules
        if _avalia_condicao(rule.condicoes, extracted, context, texto_norm, cat_str, texto_original)
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
            "rastro": {},
        }

    # Ordenar por prioridade_regra decrescente (maior = mais prioritário)
    regras_ordenadas = sorted(
        regras_disparadas, key=lambda r: r.prioridade_regra, reverse=True
    )

    # Merge de campos: primeiro valor não-None de maior prioridade prevalece.
    # 'rastro' guarda a regra que definiu cada campo (explicação da decisão).
    valores: dict = {}
    rastro: dict[str, str] = {}
    for rule in regras_ordenadas:
        for campo in ("urgencia", "prioridade", "equipe", "confianca"):
            valor = getattr(rule.acoes, campo)
            if campo not in valores and valor is not None:
                valores[campo] = valor
                rastro[campo] = rule.id

    # Revisão humana por disjunção: basta uma regra disparada exigi-la, mesmo
    # que outra de maior precedência defina os demais campos. Os motivos dessas
    # regras são combinados na ordem de precedência.
    regras_revisao = [r for r in regras_ordenadas if r.acoes.requer_revisao_humana]
    requer_revisao_humana = bool(regras_revisao)
    motivos = dict.fromkeys(
        r.acoes.motivo_revisao for r in regras_revisao if r.acoes.motivo_revisao
    )
    motivo_revisao: Optional[str] = " | ".join(motivos) or None
    if regras_revisao:
        rastro["revisao"] = ", ".join(r.id for r in regras_revisao)

    # Aplicar defaults para campos não definidos por nenhuma regra
    urgencia = valores.get("urgencia", "DESCONHECIDA")
    prioridade = valores.get("prioridade", "DESCONHECIDA")
    equipe = valores.get("equipe", "Revisão necessária")
    confianca = valores.get("confianca", 0.0)

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
        "rastro": rastro,
    }


_ROTULOS_RASTRO = {
    "urgencia": "urgência",
    "prioridade": "prioridade",
    "equipe": "equipe",
    "confianca": "confiança",
    "revisao": "revisão",
}


def descrever_regras(resultado: dict) -> str:
    """
    Texto da evidência 'regras_classificacao': regras disparadas e, por campo,
    a regra que definiu o valor (ex: "urgência ← RULE-019; revisão ← RULE-019,
    RULE-001").
    """
    texto = "Regras: " + ", ".join(resultado["regras_acionadas"])
    rastro = resultado.get("rastro") or {}
    if rastro:
        texto += ". " + "; ".join(
            f"{_ROTULOS_RASTRO[campo]} ← {regras}" for campo, regras in rastro.items()
        )
    return texto
