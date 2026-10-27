"""
Ponto de entrada de conveniência para IDEs e execução direta.

Execução recomendada via Streamlit:
    python -m streamlit run src/interface/app.py

Execução alternativa por este módulo (apenas para IDEs que não suportam
o comando streamlit diretamente):
    python run_app.py

AVISO: Este é um protótipo acadêmico desenvolvido para monografia de
especialização em Controle e Automação. Não usar em ambiente industrial
real sem revisão humana e validação por especialistas.
"""

from src.interface.app import main

if __name__ == "__main__":
    main()
