"""
Interface Streamlit do sistema de triagem de ordens de serviço industriais.

Implementa três páginas navegáveis via barra lateral:
  - Triagem: insere um relato e executa as três abordagens comparáveis.
  - Avaliação: executa avaliação completa sobre o dataset sintético.
  - Histórico: exibe sessões salvas e permite limpeza.

AVISO: Este é um protótipo acadêmico desenvolvido para monografia de
especialização em Controle e Automação. As sugestões geradas por este sistema
NÃO devem ser utilizadas em ambiente industrial real sem revisão humana e
validação por especialistas habilitados em manutenção e segurança industrial.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config.loader import get_settings
from src.data.dataset_loader import load_dataset
from src.evaluation.report import save_evaluation_report
from src.evaluation.runner import evaluate_approach
from src.orchestration.chains import (
    build_hybrid_chain,
    build_llm_chain,
    build_rules_chain,
)
from src.interface.session_manager import clear_sessions, load_sessions, save_session
from src.schemas.triage import TriageResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de UI
# ---------------------------------------------------------------------------

_URGENCY_EMOJI: dict[str, str] = {
    "IMEDIATA": "🔴",
    "ALTA": "🟠",
    "MEDIA": "🟡",
    "BAIXA": "🟢",
    "DESCONHECIDA": "⚫",
}

_PRIORITY_EMOJI: dict[str, str] = {
    "P1": "🔴",
    "P2": "🟠",
    "P3": "🟡",
    "P4": "🟢",
    "DESCONHECIDA": "⚫",
}

_AVISO_ACADEMICO = (
    "⚠️ **Protótipo acadêmico** — resultados gerados por modelos de IA local. "
    "Toda classificação deve ser revisada por especialistas antes de qualquer ação industrial."
)

# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------


def _exibir_resultado(result: TriageResult, show_regras: bool = True) -> None:
    """Renderiza um TriageResult como blocos Streamlit formatados.

    Parâmetros
    ----------
    result:
        Resultado de triagem a exibir.
    show_regras:
        Se True, exibe o expander de regras acionadas. Para a abordagem LLM puro
        não há regras, portanto pode ser omitido.
    """
    urgencia_val: str = result.urgencia.value if hasattr(result.urgencia, "value") else str(result.urgencia)
    prioridade_val: str = result.prioridade.value if hasattr(result.prioridade, "value") else str(result.prioridade)
    categoria_val: str = result.categoria.value if hasattr(result.categoria, "value") else str(result.categoria)

    urg_emoji = _URGENCY_EMOJI.get(urgencia_val, "⚫")
    pri_emoji = _PRIORITY_EMOJI.get(prioridade_val, "⚫")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Urgência",
            value=f"{urg_emoji} {urgencia_val}",
        )
        st.metric(
            label="Categoria",
            value=categoria_val,
        )
    with col2:
        st.metric(
            label="Prioridade",
            value=f"{pri_emoji} {prioridade_val}",
        )
        st.metric(
            label="Equipe Sugerida",
            value=result.equipe_sugerida,
        )

    confianca_pct = int(result.confianca * 100)
    st.progress(
        result.confianca,
        text=f"Confiança: {confianca_pct}%",
    )

    with st.expander("📎 Evidências textuais"):
        if result.evidencias:
            st.json(result.evidencias)
        else:
            st.info("Nenhuma evidência textual registrada.")

    if show_regras:
        with st.expander("📋 Regras acionadas"):
            if result.regras_acionadas:
                for regra in result.regras_acionadas:
                    st.markdown(f"- `{regra}`")
            else:
                st.caption("(nenhuma)")

    if result.requer_revisao_humana:
        st.warning(f"🔍 **Revisão humana necessária:** {result.motivo_revisao}")

    if result.campos_sem_suporte:
        lista = ", ".join(result.campos_sem_suporte)
        st.info(
            f"ℹ️ Campos inferidos sem evidência direta no texto (possível alucinação): {lista}"
        )

    st.caption(f"⏱️ Latência: {result.latencia_ms:.1f} ms")


def _exibir_comparacao(results: dict[str, TriageResult]) -> None:
    """Exibe comparação lado a lado das três abordagens em tabela pandas.

    Parâmetros
    ----------
    results:
        Dicionário com chaves 'regras', 'llm', 'hibrido' mapeando para TriageResult.
    """
    st.subheader("📊 Comparação entre abordagens")

    colunas_map = {
        "regras": "Regras",
        "llm": "LLM Puro",
        "hibrido": "Híbrido",
    }

    def _val(result: TriageResult | None, campo: str) -> str:
        if result is None:
            return "—"
        if campo == "urgencia":
            v = result.urgencia.value if hasattr(result.urgencia, "value") else str(result.urgencia)
            return f"{_URGENCY_EMOJI.get(v, '⚫')} {v}"
        if campo == "prioridade":
            v = result.prioridade.value if hasattr(result.prioridade, "value") else str(result.prioridade)
            return f"{_PRIORITY_EMOJI.get(v, '⚫')} {v}"
        if campo == "categoria":
            return result.categoria.value if hasattr(result.categoria, "value") else str(result.categoria)
        if campo == "equipe":
            return result.equipe_sugerida
        return "—"

    linhas = {
        "Urgência": [],
        "Prioridade": [],
        "Categoria": [],
        "Equipe Sugerida": [],
    }

    campos = ["urgencia", "prioridade", "categoria", "equipe"]
    rotulos = list(linhas.keys())

    for abordagem in ["regras", "llm", "hibrido"]:
        r = results.get(abordagem)
        for campo, rotulo in zip(campos, rotulos):
            linhas[rotulo].append(_val(r, campo))

    df = pd.DataFrame(
        linhas,
        index=[colunas_map.get(a, a) for a in ["regras", "llm", "hibrido"]],
    ).T

    st.dataframe(df, width='stretch')

    # Indicadores de revisão humana por abordagem
    cols = st.columns(3)
    for col, abordagem in zip(cols, ["regras", "llm", "hibrido"]):
        r = results.get(abordagem)
        with col:
            nome = colunas_map.get(abordagem, abordagem)
            if r is not None and r.requer_revisao_humana:
                st.warning(f"⚠️ {nome}: revisão solicitada")
            elif r is not None:
                st.success(f"✅ {nome}: sem revisão")
            else:
                st.error(f"❌ {nome}: erro")


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------


def _pagina_triagem() -> None:
    """Renderiza a página de triagem de ordens de serviço."""
    st.header("🔧 Triagem de Ordem de Serviço")
    st.markdown(
        "Insira o relato da ocorrência no campo abaixo. "
        "O sistema executará as três abordagens de triagem e exibirá os resultados comparados."
    )

    texto = st.text_area(
        label="Relato da ocorrência",
        placeholder="Ex.: A bomba de água da linha 3 está fazendo barulho estranho e perdendo pressão...",
        height=160,
        key="texto_triagem",
    )

    if st.button("🔍 Analisar", type="primary", width='stretch'):
        # Validação de entrada
        if not texto or not texto.strip():
            st.warning("⚠️ Por favor, insira um relato antes de analisar.")
            return

        results: dict[str, TriageResult] = {}
        erros: dict[str, str] = {}

        with st.spinner("Executando análise — aguarde..."):
            # Regras
            try:
                results["regras"] = build_rules_chain().invoke({"texto": texto.strip()})
            except Exception as exc:
                logger.error("Erro na abordagem regras: %s", exc)
                erros["regras"] = str(exc)

            # LLM puro
            try:
                results["llm"] = build_llm_chain().invoke({"texto": texto.strip()})
            except ConnectionError as exc:
                logger.error("Ollama indisponível (LLM puro): %s", exc)
                erros["llm"] = "ollama_indisponivel"
            except Exception as exc:
                _msg = str(exc).lower()
                if "connection" in _msg or "connect" in _msg or "httpx" in _msg or "ollama" in _msg:
                    logger.error("Ollama indisponível (LLM puro): %s", exc)
                    erros["llm"] = "ollama_indisponivel"
                else:
                    logger.error("Erro na abordagem LLM puro: %s", exc)
                    erros["llm"] = str(exc)

            # Híbrido
            try:
                results["hibrido"] = build_hybrid_chain().invoke({"texto": texto.strip()})
            except ConnectionError as exc:
                logger.error("Ollama indisponível (híbrido): %s", exc)
                erros["hibrido"] = "ollama_indisponivel"
            except Exception as exc:
                _msg = str(exc).lower()
                if "connection" in _msg or "connect" in _msg or "httpx" in _msg or "ollama" in _msg:
                    logger.error("Ollama indisponível (híbrido): %s", exc)
                    erros["hibrido"] = "ollama_indisponivel"
                else:
                    logger.error("Erro na abordagem híbrida: %s", exc)
                    erros["hibrido"] = str(exc)

        # Verificar se Ollama está indisponível
        ollama_erro = any(v == "ollama_indisponivel" for v in erros.values())
        if ollama_erro:
            modelo_atual = get_settings().ollama_model
            st.error(
                "🔌 **Ollama indisponível.** Verifique se o servidor Ollama está em execução "
                f"(`ollama serve`) e se o modelo `{modelo_atual}` está baixado "
                f"(`ollama pull {modelo_atual}`). "
                "A abordagem de Regras não depende do Ollama e foi executada normalmente."
            )

        # Salvar sessão (silenciosamente em caso de erro)
        if results:
            try:
                save_session(results, texto.strip())
            except Exception as exc:
                logger.warning("Falha ao salvar sessão: %s", exc)

        if not results:
            st.error("❌ Nenhuma abordagem produziu resultado. Verifique os erros acima.")
            return

        # Exibir resultados em abas
        abas = st.tabs(["Regras", "LLM Puro", "Híbrido", "Comparação"])

        with abas[0]:
            if "regras" in results:
                _exibir_resultado(results["regras"], show_regras=True)
            elif "regras" in erros:
                st.error(f"Erro na abordagem de regras: {erros['regras']}")

        with abas[1]:
            if "llm" in results:
                _exibir_resultado(results["llm"], show_regras=False)
            elif "llm" in erros:
                if erros["llm"] == "ollama_indisponivel":
                    st.error(
                        "🔌 Ollama indisponível. Inicie o servidor e baixe o modelo para usar esta abordagem."
                    )
                else:
                    st.error(f"Erro na abordagem LLM puro: {erros['llm']}")

        with abas[2]:
            if "hibrido" in results:
                _exibir_resultado(results["hibrido"], show_regras=True)
            elif "hibrido" in erros:
                if erros["hibrido"] == "ollama_indisponivel":
                    st.error(
                        "🔌 Ollama indisponível. Inicie o servidor e baixe o modelo para usar esta abordagem."
                    )
                else:
                    st.error(f"Erro na abordagem híbrida: {erros['hibrido']}")

        with abas[3]:
            if len(results) >= 1:
                _exibir_comparacao(results)
            else:
                st.info("Nenhum resultado disponível para comparação.")

        st.caption(_AVISO_ACADEMICO)


def _pagina_avaliacao() -> None:
    """Renderiza a página de avaliação comparativa das abordagens sobre o dataset sintético."""
    st.header("📊 Avaliação Comparativa")
    st.markdown(
        "Execute as abordagens de triagem sobre o dataset sintético completo e compare as métricas."
    )

    st.warning(
        "⏳ As abordagens LLM Puro e Híbrido chamam o modelo de linguagem para cada caso — "
        "podem ser muito lentas com datasets grandes. Use a **avaliação rápida** (≤ 20 casos) "
        "na interface. Para o dataset completo (100 casos), prefira o comando: "
        "`python -m src.evaluation`"
    )

    st.subheader("Abordagens a avaliar")
    col_cb1, col_cb2, col_cb3 = st.columns(3)
    with col_cb1:
        cb_regras = st.checkbox("Regras", value=True, key="cb_regras")
    with col_cb2:
        cb_llm = st.checkbox("LLM Puro", value=True, key="cb_llm")
    with col_cb3:
        cb_hibrido = st.checkbox("Híbrido", value=True, key="cb_hibrido")

    max_casos = st.slider(
        "Número de casos por abordagem",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
        help=(
            "Reduza para uma avaliação rápida na interface. "
            "Para avaliar todos os 100 casos, use o comando de linha: "
            "`python -m src.evaluation`"
        ),
        key="max_casos_slider",
    )

    abordagens_selecionadas = []
    if cb_regras:
        abordagens_selecionadas.append("regras")
    if cb_llm:
        abordagens_selecionadas.append("llm")
    if cb_hibrido:
        abordagens_selecionadas.append("hibrido")

    if st.button("▶ Executar Avaliação", type="primary", width='stretch'):
        if not abordagens_selecionadas:
            st.warning("⚠️ Selecione ao menos uma abordagem para avaliar.")
            return

        # Carregar dataset
        try:
            cases_todos = load_dataset()
        except FileNotFoundError as exc:
            st.error(f"❌ Dataset não encontrado: {exc}")
            return
        except ValueError as exc:
            st.error(f"❌ Dataset inválido: {exc}")
            return
        except Exception as exc:
            logger.error("Erro ao carregar dataset: %s", exc)
            st.error(f"❌ Erro ao carregar dataset: {exc}")
            return

        cases = cases_todos[:max_casos]
        st.info(
            f"Dataset: {len(cases_todos)} casos disponíveis — "
            f"avaliando os primeiros **{len(cases)}**."
        )

        barra = st.progress(0, text="Iniciando avaliação...")
        eval_data: dict = {
            "timestamp": datetime.now().isoformat(),
            "dataset_size": len(cases),
            "approaches": {},
        }
        caminhos: dict = {}

        total = len(abordagens_selecionadas)
        for i, abordagem in enumerate(abordagens_selecionadas):
            nome_display = {"regras": "Regras", "llm": "LLM Puro", "hibrido": "Híbrido"}.get(
                abordagem, abordagem
            )
            barra.progress(
                int(i / total * 100),
                text=f"Avaliando abordagem: {nome_display} ({i + 1}/{total})...",
            )
            with st.spinner(f"Executando {nome_display} ({len(cases)} casos)..."):
                try:
                    resultado_abordagem = evaluate_approach(abordagem, cases)
                    eval_data["approaches"][abordagem] = resultado_abordagem
                    erros_abordagem = resultado_abordagem.get("errors", [])
                    if erros_abordagem:
                        st.warning(
                            f"⚠️ {nome_display}: {len(erros_abordagem)} caso(s) com erro."
                        )
                    else:
                        st.success(f"✅ {nome_display} concluído ({len(cases)} casos).")
                except Exception as exc:
                    logger.error("Erro ao avaliar abordagem %s: %s", abordagem, exc)
                    st.error(f"❌ Erro ao avaliar {nome_display}: {exc}")
                    continue

            # Salvar resultado parcial após cada abordagem — garante que resultados
            # já concluídos não sejam perdidos se uma abordagem seguinte falhar
            if eval_data["approaches"]:
                try:
                    caminhos = save_evaluation_report(eval_data)
                    logger.info("Resultado parcial salvo após %s", abordagem)
                except Exception as exc:
                    logger.error("Erro ao salvar resultado parcial após %s: %s", abordagem, exc)

        barra.progress(100, text="Avaliação concluída.")

        if not eval_data["approaches"]:
            st.error("❌ Nenhuma abordagem produziu resultados.")
            return

        # Salvar relatório final consolidado (sobrescreve o parcial com o completo)
        try:
            caminhos = save_evaluation_report(eval_data)
            st.success(f"✅ Relatório final salvo em: `{Path(caminhos['summary_json']).parent}`")
        except Exception as exc:
            logger.error("Erro ao salvar relatório de avaliação: %s", exc)
            st.error(f"❌ Erro ao salvar relatório: {exc}")
            caminhos = {}

        # Exibir resumo tabular
        if caminhos.get("summary_json") and Path(caminhos["summary_json"]).exists():
            try:
                with open(caminhos["summary_json"], encoding="utf-8") as f:
                    summary_dict = json.load(f)

                st.subheader("📋 Resumo das métricas")
                linhas = []
                for abordagem, metricas in summary_dict.items():
                    linhas.append({
                        "Abordagem": abordagem.upper(),
                        "F1 Urgência": round(metricas.get("f1_urgencia", 0.0), 3),
                        "F1 Prioridade": round(metricas.get("f1_prioridade", 0.0), 3),
                        "F1 Categoria": round(metricas.get("f1_categoria", 0.0), 3),
                        "F1 Equipe": round(metricas.get("f1_equipe", 0.0), 3),
                        "Taxa Revisão": round(metricas.get("human_review_rate", 0.0), 3),
                        "Taxa Subest.": round(metricas.get("critical_underestimation_rate", 0.0), 3),
                        "Lat. Média (ms)": round(metricas.get("latency", {}).get("media", 0.0), 1),
                        "Total Casos": metricas.get("total_cases", 0),
                        "Erros": metricas.get("total_errors", 0),
                    })

                df_summary = pd.DataFrame(linhas)
                st.dataframe(df_summary, width='stretch', hide_index=True)
            except Exception as exc:
                logger.error("Erro ao exibir resumo: %s", exc)
                st.warning(f"Não foi possível exibir o resumo: {exc}")

        # Botões de download
        if caminhos:
            st.subheader("⬇️ Downloads")
            col_dl1, col_dl2 = st.columns(2)

            with col_dl1:
                csv_path = caminhos.get("summary_csv", "")
                if csv_path and Path(csv_path).exists():
                    with open(csv_path, "rb") as f:
                        st.download_button(
                            label="📥 Baixar resumo CSV",
                            data=f.read(),
                            file_name=Path(csv_path).name,
                            mime="text/csv",
                            width='stretch',
                        )

            with col_dl2:
                json_path = caminhos.get("summary_json", "")
                if json_path and Path(json_path).exists():
                    with open(json_path, "rb") as f:
                        st.download_button(
                            label="📥 Baixar resumo JSON",
                            data=f.read(),
                            file_name=Path(json_path).name,
                            mime="application/json",
                            width='stretch',
                        )

        st.caption(
            "ℹ️ **Aviso sobre o dataset:** Os casos utilizados nesta avaliação são completamente "
            "sintéticos, criados para fins acadêmicos. As métricas obtidas não representam "
            "desempenho real em ambiente industrial. Consulte a documentação para limitações."
        )


def _pagina_historico() -> None:
    """Renderiza a página de histórico de análises salvas."""
    st.header("📁 Histórico de Análises")

    sessoes = load_sessions()

    if not sessoes:
        st.info("Nenhuma análise realizada ainda. Acesse a página de Triagem para começar.")
        return

    st.markdown(f"**{len(sessoes)} sessão(ões) encontrada(s)**, mais recente primeiro.")

    for idx, sessao in enumerate(sessoes):
        timestamp_raw = sessao.get("timestamp", "")
        texto_sessao = sessao.get("texto", "")
        results_dict = sessao.get("results", {})

        # Formatar timestamp para exibição
        try:
            dt = datetime.fromisoformat(timestamp_raw)
            ts_display = dt.strftime("%d/%m/%Y às %H:%M:%S")
        except (ValueError, TypeError):
            ts_display = timestamp_raw or f"Sessão {idx + 1}"

        # Preview do texto (primeiros 80 caracteres)
        texto_preview = texto_sessao[:80] + "..." if len(texto_sessao) > 80 else texto_sessao

        # Urgência/prioridade do híbrido para o título do expander
        hibrido_raw = results_dict.get("hibrido", {})
        urg_hibrido = hibrido_raw.get("urgencia", "?")
        pri_hibrido = hibrido_raw.get("prioridade", "?")
        urg_emoji = _URGENCY_EMOJI.get(urg_hibrido, "⚫")

        titulo_expander = (
            f"{ts_display}  |  {urg_emoji} {urg_hibrido} / {pri_hibrido}  |  "
            f"\"{texto_preview}\""
        )

        with st.expander(titulo_expander, expanded=False):
            st.markdown(f"**Relato completo:**\n\n{texto_sessao}")
            st.divider()

            abas_hist = st.tabs(["Regras", "LLM Puro", "Híbrido"])

            for aba, abordagem in zip(abas_hist, ["regras", "llm", "hibrido"]):
                with aba:
                    raw = results_dict.get(abordagem)
                    if raw is None:
                        st.info("Esta abordagem não foi executada nesta sessão.")
                        continue
                    try:
                        result_obj = TriageResult.model_validate(raw)
                        _exibir_resultado(
                            result_obj,
                            show_regras=(abordagem != "llm"),
                        )
                    except Exception as exc:
                        logger.warning(
                            "Falha ao reconstruir TriageResult da sessão %s (%s): %s",
                            timestamp_raw,
                            abordagem,
                            exc,
                        )
                        st.warning(f"Não foi possível exibir o resultado: {exc}")

    # Seção de limpeza
    st.divider()
    st.subheader("🗑️ Limpeza do histórico")
    confirmar = st.checkbox(
        "Confirmo que desejo apagar todas as sessões salvas (esta ação é irreversível)",
        key="confirmar_limpeza",
    )
    if st.button(
        "🧹 Limpar histórico",
        disabled=not confirmar,
        width='stretch',
    ):
        try:
            removidos = clear_sessions()
            st.success(f"✅ {removidos} sessão(ões) removida(s).")
            st.rerun()
        except Exception as exc:
            logger.error("Erro ao limpar sessões: %s", exc)
            st.error(f"❌ Erro ao limpar histórico: {exc}")


# ---------------------------------------------------------------------------
# Ponto de entrada principal
# ---------------------------------------------------------------------------


def main() -> None:
    """Inicializa e executa a aplicação Streamlit de triagem de OS industriais."""
    # st.set_page_config deve ser a primeira chamada st.* dentro de main()
    st.set_page_config(
        page_title="Triador de OS Industrial",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ---------------------------------------------------------------------------
    # Barra lateral
    # ---------------------------------------------------------------------------
    with st.sidebar:
        st.title("🔧 Triador de OS Industrial")
        st.caption("Protótipo acadêmico — especialização em Controle e Automação")
        st.divider()

        modelo_atual = get_settings().ollama_model
        st.caption(
            f"**Modelo em uso:** `{modelo_atual}`  \n"
            "Para alterar, edite `OLLAMA_MODEL` no arquivo `.env` e reinicie o servidor."
        )

        st.divider()
        st.warning(
            "⚠️ **Protótipo acadêmico**\n\n"
            "Este sistema foi desenvolvido para fins de pesquisa em monografia de especialização. "
            "Toda classificação gerada deve ser revisada por profissionais habilitados em "
            "manutenção e segurança industrial antes de qualquer ação operacional."
        )
        st.divider()

        pagina = st.radio(
            label="Navegação",
            options=["Triagem", "Avaliação", "Histórico"],
            index=0,
            key="pagina_selecionada",
        )

    # ---------------------------------------------------------------------------
    # Roteamento
    # ---------------------------------------------------------------------------
    if pagina == "Triagem":
        _pagina_triagem()
    elif pagina == "Avaliação":
        _pagina_avaliacao()
    elif pagina == "Histórico":
        _pagina_historico()


if __name__ == "__main__":
    main()
