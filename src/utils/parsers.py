"""
Funções de parsing defensivo para respostas JSON de LLMs.

Centraliza a lógica de extração de JSON que estava duplicada em
llm_extractor.py e llm_only.py, garantindo comportamento idêntico
em ambas as abordagens.

Estratégia em três passos:
  1. json.loads direto (resposta já é JSON puro).
  2. Regex {.*} com DOTALL (extrai bloco JSON de resposta em markdown).
  3. Falha total — retorna mensagem de erro descritiva.
"""

import json
import re


def parsear_json_llm(texto_resposta: str) -> tuple[dict | None, str | None]:
    """
    Tenta extrair um objeto JSON da resposta textual de um LLM.

    Aplica três estratégias em ordem crescente de tolerância:
      Passo 1: json.loads direto — funciona quando o LLM retorna JSON puro.
      Passo 2: busca por bloco ``{...}`` via regex com re.DOTALL — funciona
               quando o LLM envolve o JSON em markdown (```json ... ```).
      Passo 3: falha total — retorna mensagem de erro sem lançar exceção.

    A função nunca lança exceção ao chamador.

    Args:
        texto_resposta: texto bruto retornado pelo LLM.

    Returns:
        Tupla (dict, None) em caso de sucesso, ou
        (None, mensagem_de_erro) em caso de falha de parse.
    """
    texto_limpo = texto_resposta.strip()

    # Passo 1: tentativa direta
    try:
        return json.loads(texto_limpo), None
    except json.JSONDecodeError:
        pass

    # Passo 2: extrair bloco {...} via regex — lida com ```json ... ```
    match = re.search(r"\{.*\}", texto_limpo, re.DOTALL)
    if match:
        try:
            return json.loads(match.group()), None
        except json.JSONDecodeError as exc:
            return None, f"Falha ao parsear JSON: {exc}"

    # Passo 3: nenhum objeto JSON encontrado na resposta
    return None, "Falha ao parsear JSON: nenhum objeto JSON encontrado na resposta"
