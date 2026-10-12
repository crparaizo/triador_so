# src/interface/ — Interface web Streamlit

Esta pasta contém a **interface gráfica** do sistema — a tela que o usuário vê ao executar `streamlit run src/interface/app.py`.

---

## Como iniciar

```bash
streamlit run src/interface/app.py
# Acesse em: http://localhost:8501
```

---

## Arquivos

### `app.py` — Aplicação Streamlit principal
O código da interface completa, organizado em três páginas acessíveis pela barra lateral:

#### Página "🔍 Triagem"
A página principal de uso:
1. Campo de texto grande para inserir o relato de ocorrência
2. Botão "Analisar" que executa **as três abordagens sequencialmente**
3. Resultados exibidos em **quatro abas**:
   - **Regras** — resultado da abordagem por regras puras
   - **LLM Puro** — resultado da abordagem com LLM
   - **Híbrido** — resultado da abordagem híbrida
   - **Comparação** — tabela lado a lado com os três resultados
4. Cada aba mostra: urgência e prioridade (com ícones coloridos 🔴🟠🟡🟢), categoria, equipe sugerida, confiança, evidências, regras acionadas e alertas de revisão humana
5. O resultado é salvo automaticamente em `sessions/`

Se o Ollama não estiver disponível: exibe mensagem de erro clara (sem stack trace). A abordagem de Regras continua funcionando normalmente.

#### Página "📊 Avaliação"
Permite executar a avaliação comparativa diretamente pela interface:
1. Checkboxes para selecionar quais abordagens incluir
2. Barra de progresso durante a execução
3. Tabela de resumo com as métricas ao final
4. Botões para baixar os relatórios gerados (CSV e JSON)

#### Página "📋 Histórico"
Lista todas as análises anteriores salvas em `sessions/`:
- Mostra timestamp, prévia do texto e urgência/prioridade do método híbrido
- Cada item pode ser expandido para ver todos os detalhes
- Botão para limpar o histórico (com confirmação)

**Nota sobre o modelo Ollama:** o modelo em uso é exibido na barra lateral como informação somente-leitura. Para trocar o modelo, edite a variável `OLLAMA_MODEL` no arquivo `.env` e reinicie o servidor.

### `session_manager.py` — Gerenciador de histórico
Módulo separado que cuida da persistência das sessões em `sessions/`:

- `save_session(results, texto)` → salva os três resultados num arquivo JSON com timestamp
- `load_sessions()` → carrega todos os arquivos da pasta, ordenados do mais recente ao mais antigo
- `clear_sessions()` → remove todos os arquivos de sessão, preserva o `.gitkeep`

Arquivos de sessão com erro de leitura são ignorados silenciosamente (para não quebrar o histórico inteiro por um arquivo corrompido).

### `__init__.py`
Marca a pasta como submódulo Python.
