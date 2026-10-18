"""
Demonstração OPCIONAL de não-determinismo do modelo de linguagem.

ATENÇÃO: este script NÃO faz parte da avaliação oficial (src/evaluation). Ele é
uma demonstração complementar, à parte, que ilustra como a abordagem por LLM pode
produzir saídas diferentes para a MESMA entrada quando a amostragem é habilitada
(temperatura > 0, sem semente fixa). A avaliação principal da monografia é
conduzida de forma determinística (temperatura zero + semente fixa), e seus
resultados não dependem deste script.

Objetivo: executar o mesmo relato N vezes e mostrar se a classificação varia.

Uso:
    python -m scripts.demo_nao_determinismo
    python -m scripts.demo_nao_determinismo --texto "BOMB-001 com vibração" --n 5 --temperatura 0.8

Pré-requisito: Ollama rodando com o modelo configurado (OLLAMA_MODEL).

AVISO: Protótipo acadêmico — não usar em ambiente industrial real.
"""

import argparse
import sys

from langchain_ollama import ChatOllama

from src.approaches.llm_only import _preparar_prompt
from src.config.loader import get_settings
from src.utils.parsers import parsear_json_llm

# Relato de exemplo (sintético) usado quando nenhum texto é informado.
_TEXTO_PADRAO = (
    "A bomba BOMB-001 está com vibração excessiva e ruído anormal no Setor A. "
    "Parece estar esquentando. Pode parar a linha a qualquer momento."
)


def _campos(data: dict | None, erro: str | None) -> str:
    """Resume os campos classificados de uma resposta (ou o erro de parse)."""
    if erro or data is None:
        return f"ERRO DE PARSE: {erro}"
    return (
        f"urgencia={data.get('urgencia')!r} | "
        f"prioridade={data.get('prioridade')!r} | "
        f"categoria={data.get('categoria')!r} | "
        f"equipe={data.get('equipe_sugerida')!r}"
    )


def rodar(texto: str, n: int, temperatura: float) -> None:
    """Executa o mesmo relato n vezes e imprime a variação das saídas.

    Instancia o ChatOllama diretamente, SEM semente fixa e com temperatura > 0,
    para habilitar a amostragem — justamente o oposto da configuração usada na
    avaliação oficial. Reutiliza o prompt real da abordagem por LLM puro.
    """
    estado = _preparar_prompt({"texto_entrada": texto})
    prompt = estado["prompt"]
    settings = get_settings()

    print(f"Modelo: {settings.ollama_model} | temperatura: {temperatura} | execuções: {n}")
    print(f"Relato: {texto}\n")

    assinaturas: set[str] = set()
    for i in range(1, n + 1):
        # Sem 'seed' de propósito: cada chamada amostra de forma independente.
        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperatura,
            format="json",
            num_predict=settings.ollama_num_predict,
        )
        try:
            resposta = llm.invoke(prompt)
        except Exception as exc:  # noqa: BLE001 — demo tolera qualquer falha
            print(f"[{i}/{n}] Falha ao chamar o modelo: {type(exc).__name__}: {exc}")
            continue

        texto_resp = resposta.content if hasattr(resposta, "content") else str(resposta)
        data, erro = parsear_json_llm(texto_resp)
        resumo = _campos(data, erro)
        assinaturas.add(resumo)
        print(f"[{i}/{n}] {resumo}")

    print(
        f"\nResultados distintos: {len(assinaturas)} de {n} execuções. "
        + (
            "A saída variou — não-determinismo demonstrado."
            if len(assinaturas) > 1
            else "A saída foi consistente nesta amostra."
        )
    )


def main() -> None:
    """Ponto de entrada da demonstração de não-determinismo."""
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="python -m scripts.demo_nao_determinismo",
        description=(
            "Demonstração OPCIONAL de não-determinismo do LLM (não faz parte da "
            "avaliação oficial). Executa o mesmo relato N vezes com amostragem "
            "habilitada e mostra se a classificação varia."
        ),
    )
    parser.add_argument("--texto", type=str, default=_TEXTO_PADRAO, help="Relato a avaliar.")
    parser.add_argument("--n", type=int, default=5, help="Número de execuções (padrão: 5).")
    parser.add_argument(
        "--temperatura",
        type=float,
        default=0.8,
        help="Temperatura de geração (> 0 para habilitar amostragem; padrão: 0.8).",
    )
    args = parser.parse_args()

    rodar(args.texto, args.n, args.temperatura)


if __name__ == "__main__":
    main()
