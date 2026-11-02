"""
Entrada por alarmes de um supervisório (SCADA) simulado.

Expõe:
    AlarmEvent        — evento de alarme estruturado
    alarme_para_relato — converte o evento no texto de uma OS para as três abordagens

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

from src.alarms.adapter import AlarmEvent, alarme_para_relato

__all__ = ["AlarmEvent", "alarme_para_relato"]
