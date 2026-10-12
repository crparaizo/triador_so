"""
Módulo de interface do sistema de triagem de OS industriais.

AVISO: Este é um protótipo acadêmico. As sugestões geradas requerem revisão
humana e validação por especialistas antes de qualquer uso operacional.

Submódulos públicos
-------------------
app
    Aplicação Streamlit principal. Contém a função `main()` que inicializa a
    página e gerencia a navegação entre as abas de triagem e avaliação.
session_manager
    Gerenciamento de sessões locais em JSON. Provê `save_session`,
    `load_sessions` e `clear_sessions` para persistência de resultados
    de triagem na pasta configurada em ``Settings.sessions_dir``.
"""
