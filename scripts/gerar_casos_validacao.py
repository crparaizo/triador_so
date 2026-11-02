"""
Gera datasets/holdout_cases.json: 100 casos de validação não vistos pelas regras.

Os casos seguem a mesma distribuição de tipos do conjunto principal e foram
redigidos a partir dos ativos e categorias cadastrados, sem consultar as
palavras-chave das regras. O gabarito segue os critérios de anotação do
DATASET_README e deve ser validado pela autora antes de qualquer execução;
depois disso, o arquivo é congelado (hash SHA-256 registrado em results/).

    python scripts/gerar_casos_validacao.py

Protótipo acadêmico — monografia de especialização em Controle e Automação.
"""

import json
from pathlib import Path

from src.data.dataset_loader import load_dataset

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "datasets" / "holdout_cases.json"

MEC, ELE, INS, UTI, INF, TI = ("Manutenção Mecânica", "Manutenção Elétrica", "Instrumentação e Controle",
                               "Utilidades", "Infraestrutura e Facilities", "TI e Automação")
DES = "DESCONHECIDA"

# (tipo, texto, urgência, prioridade, categoria, equipe, revisão, notas[, referência])
CASOS = [
    # ---------------------------------------------------------------- CANONICO (15)
    ("CANONICO", "A bomba de transferência BOMB-002 apresenta aquecimento anormal no mancal e ruído metálico. Setor B - Produção.",
     "ALTA", "P2", "MECANICA", MEC, False, "Falha mecânica em ativo de criticidade ALTA, sem impacto declarado: ALTA/P2."),
    ("CANONICO", "Compressor de ar instrumento COMP-001 desarmou duas vezes no turno. As válvulas pneumáticas da Linha 2 perderam pressão de atuação e a produção da linha foi interrompida.",
     "ALTA", "P1", "MECANICA", MEC, False, "Ativo crítico com produção interrompida: prioridade P1, como no CASE-002."),
    ("CANONICO", "Motor da correia transportadora MOTOR-001 com ruído de rolamento e leve vibração. Equipamento segue operando.",
     "MEDIA", "P3", "MECANICA", MEC, False, "Falha mecânica em ativo de criticidade MEDIA, sem impacto: MEDIA/P3."),
    ("CANONICO", "Painel MCC PANEL-002 com cheiro de isolamento queimado e disjuntor de um dos inversores desarmando repetidamente.",
     "IMEDIATA", "P1", "ELETRICA", ELE, True, "Falha em painel elétrico de potência com indício de queima: intervenção sujeita à NR-10, como no CASE-004."),
    ("CANONICO", "Transformador TRANS-001 com temperatura do óleo acima do normal no monitoramento contínuo. Sem desligamento até o momento.",
     "ALTA", "P2", "ELETRICA", ELE, True, "Anomalia em transformador de potência ainda sem falha: ALTA/P2, com revisão por envolver intervenção sujeita à NR-10."),
    ("CANONICO", "Sensor de temperatura SENS-001 do Reator 1 com leitura oscilando 15 °C em poucos segundos, sem mudança no processo.",
     "ALTA", "P2", "INSTRUMENTACAO", INS, False, "Leitura incoerente de instrumento: ALTA/P2, critério de instrumentação do conjunto principal."),
    ("CANONICO", "Válvula de controle elétrica VALV-002 não responde ao comando do supervisório; atuador sem retorno de posição.",
     "ALTA", "P2", "INSTRUMENTACAO", INS, False, "Falha de elemento final de controle: ALTA/P2."),
    ("CANONICO", "Caldeira CAL-001 com chama apagando várias vezes durante a manhã. Produção de vapor instável e linha de envase parada.",
     "IMEDIATA", "P1", "UTILIDADES", UTI, True, "Caldeira com impacto na produção, equipamento abrangido pela NR-13: IMEDIATA/P1, como no CASE-008."),
    ("CANONICO", "Compressor de refrigeração COMP-003 com consumo de corrente acima do habitual e ciclos curtos. Temperatura da câmara ainda dentro do limite.",
     "MEDIA", "P3", "UTILIDADES", UTI, False, "Utilidade de criticidade MEDIA sem impacto: MEDIA/P3."),
    ("CANONICO", "Elevador de carga ELEV-001 parando fora do nível do andar na área de armazenagem.",
     "MEDIA", "P3", "INFRAESTRUTURA", INF, False, "Infraestrutura sem risco declarado: MEDIA/P3, como no CASE-010."),
    ("CANONICO", "Estação de engenharia não consegue baixar a lógica para o CLP da Linha 2; erro de comunicação na rede industrial.",
     "ALTA", "P2", "TI_AUTOMACAO", TI, False, "Falha de automação (CLP e rede industrial): ALTA/P2."),
    ("CANONICO", "Reator 1 com temperatura de reação acima do setpoint e controle automático saturado. Produção do Setor B reduzida.",
     "ALTA", "P2", "PROCESSO", INS, False, "Desvio de processo com redução de produção: ALTA/P2, como no CASE-012."),
    ("CANONICO", "Lote produzido no turno da noite com viscosidade fora da especificação. Produto segregado para análise.",
     "ALTA", "P2", "QUALIDADE", INS, False, "Produto fora de especificação: ALTA/P2, como no CASE-013."),
    ("CANONICO", "Vazamento de vapor quente na casa de caldeiras atingiu um operador, que sofreu queimadura leve. Área isolada.",
     "IMEDIATA", "P1", "SEGURANCA", UTI, True, "Acidente com trabalhador: grave e iminente risco (NR-3)."),
    ("CANONICO", "Inspeção preventiva semestral do painel PANEL-001 com termografia, conforme plano de manutenção.",
     "BAIXA", "P4", "ELETRICA", ELE, False, "Manutenção preventiva programada, sem falha relatada: BAIXA/P4, como no CASE-015."),
    # ---------------------------------------------------------------- PARAFRASES (15) — referência ao canônico de mesmo índice
    ("PARAFRASES", "O mancal da BOMB-002 está esquentando demais e fazendo um barulho de metal raspando, lá no setor de produção B.",
     "ALTA", "P2", "MECANICA", MEC, False, "Paráfrase de VAL-001 em linguagem informal.", 1),
    ("PARAFRASES", "A Linha 2 parou porque as válvulas ficaram sem ar: o COMP-001 desligou sozinho duas vezes hoje.",
     "ALTA", "P1", "MECANICA", MEC, False, "Paráfrase de VAL-002 com efeito antes da causa.", 2),
    ("PARAFRASES", "Correia transportadora: o motor MOTOR-001 está com barulho de rolamento e tremendo um pouco, mas continua funcionando.",
     "MEDIA", "P3", "MECANICA", MEC, False, "Paráfrase de VAL-003.", 3),
    ("PARAFRASES", "Sentimos cheiro de queimado no MCC (PANEL-002) e um dos disjuntores dos inversores não para de desarmar.",
     "IMEDIATA", "P1", "ELETRICA", ELE, True, "Paráfrase de VAL-004.", 4),
    ("PARAFRASES", "O monitoramento do TRANS-001 mostra o óleo mais quente que o normal; o transformador ainda não desligou.",
     "ALTA", "P2", "ELETRICA", ELE, True, "Paráfrase de VAL-005.", 5),
    ("PARAFRASES", "A leitura do SENS-001 no Reator 1 sobe e desce uns 15 graus em segundos, sem nada mudar no processo.",
     "ALTA", "P2", "INSTRUMENTACAO", INS, False, "Paráfrase de VAL-006.", 6),
    ("PARAFRASES", "O supervisório manda abrir a VALV-002 e ela não se mexe; também não aparece a posição do atuador.",
     "ALTA", "P2", "INSTRUMENTACAO", INS, False, "Paráfrase de VAL-007.", 7),
    ("PARAFRASES", "A chama da CAL-001 apagou várias vezes desde cedo, o vapor oscila e o envase está parado.",
     "IMEDIATA", "P1", "UTILIDADES", UTI, True, "Paráfrase de VAL-008.", 8),
    ("PARAFRASES", "COMP-003 da refrigeração puxando mais corrente que o normal e ligando e desligando toda hora; a câmara ainda segura a temperatura.",
     "MEDIA", "P3", "UTILIDADES", UTI, False, "Paráfrase de VAL-009.", 9),
    ("PARAFRASES", "O ELEV-001 do armazém está parando desalinhado com o piso dos andares.",
     "MEDIA", "P3", "INFRAESTRUTURA", INF, False, "Paráfrase de VAL-010.", 10),
    ("PARAFRASES", "Não conseguimos carregar o programa no CLP da Linha 2 pela estação de engenharia: dá falha de comunicação na rede.",
     "ALTA", "P2", "TI_AUTOMACAO", TI, False, "Paráfrase de VAL-011.", 11),
    ("PARAFRASES", "Temperatura do Reator 1 passou do setpoint e a malha de controle está no limite; o Setor B reduziu a produção.",
     "ALTA", "P2", "PROCESSO", INS, False, "Paráfrase de VAL-012.", 12),
    ("PARAFRASES", "O lote da noite saiu com viscosidade fora do especificado e foi separado para análise.",
     "ALTA", "P2", "QUALIDADE", INS, False, "Paráfrase de VAL-013.", 13),
    ("PARAFRASES", "Um operador foi atingido por vapor quente que vazou na casa de caldeiras e teve uma queimadura leve; isolamos a área.",
     "IMEDIATA", "P1", "SEGURANCA", UTI, True, "Paráfrase de VAL-014.", 14),
    ("PARAFRASES", "Programar a termografia semestral do PANEL-001, prevista no plano de manutenção preventiva.",
     "BAIXA", "P4", "ELETRICA", ELE, False, "Paráfrase de VAL-015.", 15),
    # ---------------------------------------------------------------- ABREVIACOES (8)
    ("ABREVIACOES", "BOMB-002 c/ temp. alta no mancal e ruído metál. Set. B.",
     "ALTA", "P2", "MECANICA", MEC, False, "Abreviações: c/, temp., metál., Set."),
    ("ABREVIACOES", "COMP-001 desarmou, s/ ar p/ válv. pneum. L2 parada.",
     "ALTA", "P1", "MECANICA", MEC, False, "Abreviações: s/, p/, válv., pneum., L2. Produção interrompida."),
    ("ABREVIACOES", "PANEL-002 c/ ch. de queimado, disj. desarmando. Verif. NR-10.",
     "IMEDIATA", "P1", "ELETRICA", ELE, True, "Abreviações: ch., disj., Verif. Indício de queima em painel (NR-10)."),
    ("ABREVIACOES", "TRANS-002 c/ sinal travado em 20 mA, s/ var. Verif. instr.",
     "ALTA", "P2", "INSTRUMENTACAO", INS, False, "Abreviações: s/ var., instr. Sinal travado de transmissor."),
    ("ABREVIACOES", "CAL-001 c/ válv. seg. vazando e press. oscilando. Verif. urg.",
     "IMEDIATA", "P1", "UTILIDADES", UTI, True, "Abreviações: válv. seg., press., urg. Dispositivo de segurança da caldeira com defeito (NR-13)."),
    ("ABREVIACOES", "CLP L1 s/ com. c/ SCADA. Tela congelada.",
     "ALTA", "P2", "TI_AUTOMACAO", TI, False, "Abreviações: L1, s/ com. Perda de comunicação CLP-SCADA."),
    ("ABREVIACOES", "Eqp. parado set. C, s/ info.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Abreviações e ausência de informação: sem ativo nem sintoma."),
    ("ABREVIACOES", "Prev. mens. MOTOR-001: lubrif. e insp. correia.",
     "BAIXA", "P4", "MECANICA", MEC, False, "Abreviações: Prev. mens., lubrif., insp. Manutenção preventiva mensal."),
    # ---------------------------------------------------------------- ERROS_ESCRITA (8)
    ("ERROS_ESCRITA", "Bomba BOMB-002 com mancal esquentano e baruho metalico no setor B.",
     "ALTA", "P2", "MECANICA", MEC, False, "Erros: esquentano, baruho, metalico."),
    ("ERROS_ESCRITA", "Compresor COMP-001 desamrou e a linha 2 pârou sem ar nas valvulas.",
     "ALTA", "P1", "MECANICA", MEC, False, "Erros: Compresor, desamrou, pârou, valvulas. Produção interrompida."),
    ("ERROS_ESCRITA", "Painel PANEL-002 com xeiro de queimado e disjuntor desarmano toda ora.",
     "IMEDIATA", "P1", "ELETRICA", ELE, True, "Erros: xeiro, desarmano, ora. Indício de queima em painel (NR-10)."),
    ("ERROS_ESCRITA", "Transmisor TRANS-002 com sinau parado, não varia com a presão.",
     "ALTA", "P2", "INSTRUMENTACAO", INS, False, "Erros: Transmisor, sinau, presão."),
    ("ERROS_ESCRITA", "Caudeira CAL-001 sem controle de nivel de agua funcionando, operador no manual.",
     "IMEDIATA", "P1", "UTILIDADES", UTI, True, "Erros: Caudeira, nivel, agua. Controle de nível indisponível: NR-13, item 13.3.1, alínea d."),
    ("ERROS_ESCRITA", "Chiler CHIL-001 com temperatura da agua gelada subino devagar.",
     "MEDIA", "P3", "UTILIDADES", UTI, False, "Erros: Chiler, agua, subino. Utilidade sem impacto, como no CASE-009."),
    ("ERROS_ESCRITA", "Ta dando problema em algum equipamento do setor A, ninguem sabe direito.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Erros: Ta, ninguem. Relato vago."),
    ("ERROS_ESCRITA", "Elevadro ELEV-001 com porta nao fechando direito.",
     "MEDIA", "P3", "INFRAESTRUTURA", INF, False, "Erros: Elevadro, nao. Infraestrutura sem risco declarado."),
    # ---------------------------------------------------------------- MULTIPLOS_SINTOMAS (8)
    ("MULTIPLOS_SINTOMAS", "BOMB-002 com vibração alta, vazamento pelo selo mecânico e corrente do motor elevada. Setor B.",
     "ALTA", "P2", "MECANICA", MEC, False, "Sintomas mecânicos e elétricos; categoria dominante mecânica; ativo crítico sem impacto."),
    ("MULTIPLOS_SINTOMAS", "COMP-002 com temperatura de descarga alta, óleo escurecido e queda de vazão. Produção do Setor C parada.",
     "ALTA", "P1", "MECANICA", MEC, False, "Sintomas mecânicos e de processo com produção parada: P1."),
    ("MULTIPLOS_SINTOMAS", "PANEL-001 com aquecimento em barramento detectado na termografia, ruído de zumbido e oscilação de tensão na planta.",
     "IMEDIATA", "P1", "ELETRICA", ELE, True, "Sintomas elétricos em painel principal com efeito na planta (NR-10)."),
    ("MULTIPLOS_SINTOMAS", "VALV-001 com vazamento pela gaxeta, posicionador oscilando e malha de pressão do Reator 1 instável.",
     "ALTA", "P2", "INSTRUMENTACAO", INS, False, "Sintomas de instrumentação e processo; categoria dominante instrumentação."),
    ("MULTIPLOS_SINTOMAS", "CHIL-001 com alarme de baixa pressão de sucção, gelo na linha e água gelada acima do setpoint.",
     "MEDIA", "P3", "UTILIDADES", UTI, False, "Sintomas de refrigeração sem impacto declarado: MEDIA/P3, como no CASE-009."),
    ("MULTIPLOS_SINTOMAS", "SCADA lento, histórico com lacunas e alarmes chegando com atraso ao operador.",
     "ALTA", "P2", "TI_AUTOMACAO", TI, False, "Sintomas de automação no supervisório."),
    ("MULTIPLOS_SINTOMAS", "Motor MOTOR-001 com cheiro de queimado, correia patinando e ruído de rolamento.",
     "ALTA", "P2", "MECANICA", MEC, False, "Cheiro de queimado eleva a urgência em relação a uma falha mecânica comum em ativo de criticidade MEDIA."),
    ("MULTIPLOS_SINTOMAS", "Vários sintomas no Setor C: ruído, aquecimento e cheiro forte, sem identificação do equipamento.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Sintomas múltiplos sem ativo identificado."),
    # ---------------------------------------------------------------- INCOMPLETOS (8)
    ("INCOMPLETOS", "Parou de novo. Mesma coisa de ontem.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Sem ativo, sintoma ou local."),
    ("INCOMPLETOS", "Preciso de um técnico no Setor B o quanto antes.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Só local e pedido de urgência, sem sintoma."),
    ("INCOMPLETOS", "Equipamento com defeito, favor verificar.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Relato genérico."),
    ("INCOMPLETOS", "Deu problema na produção.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Relato genérico."),
    ("INCOMPLETOS", "Alguma coisa vazando perto da casa de máquinas.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Vazamento sem identificação do fluido nem do equipamento."),
    ("INCOMPLETOS", "Motor fazendo barulho estranho, não sei qual.",
     "MEDIA", "P3", "MECANICA", MEC, True, "Sintoma mecânico sem ativo identificado: MEDIA/P3, como no CASE-060."),
    ("INCOMPLETOS", "Painel elétrico com luz de falha acesa, local não informado.",
     "MEDIA", "P3", "ELETRICA", ELE, True, "Sintoma elétrico sem ativo nem local: MEDIA/P3, como no CASE-062."),
    ("INCOMPLETOS", "Válvula travada em alguma linha do Setor C.",
     "MEDIA", "P3", "INSTRUMENTACAO", INS, True, "Sintoma de instrumentação sem ativo identificado."),
    # ---------------------------------------------------------------- CONTRADITORIOS (8)
    ("CONTRADITORIOS", "COMP-002 desligou por alarme de alta temperatura, mas o operador diz que o equipamento está frio e operando.",
     "DESCONHECIDA", "DESCONHECIDA", "MECANICA", MEC, True, "Contradição entre desligamento por alarme e equipamento operando."),
    ("CONTRADITORIOS", "TRANS-002 indica pressão zero na Linha 2, porém o manômetro local mostra pressão normal.",
     "ALTA", "P2", "INSTRUMENTACAO", INS, True, "Prevalece a evidência técnica: indicação falsa do transmissor."),
    ("CONTRADITORIOS", "Relato de vazamento grande de óleo na BOMB-001; a equipe que foi ao local diz que não encontrou vazamento.",
     "DESCONHECIDA", "DESCONHECIDA", "MECANICA", MEC, True, "Relato não confirmado em campo."),
    ("CONTRADITORIOS", "PANEL-001 com cheiro de queimado segundo o turno da noite; o turno da manhã não sentiu nada.",
     "ALTA", "P2", "ELETRICA", ELE, True, "Indício de queima não confirmado: prevalece a cautela, com revisão (NR-10)."),
    ("CONTRADITORIOS", "Chiller CHIL-001 parado por falha, mas a sala de controle informa que a água gelada está no setpoint.",
     "DESCONHECIDA", "DESCONHECIDA", "UTILIDADES", UTI, True, "Contradição entre falha e variável controlada normal."),
    ("CONTRADITORIOS", "Elevador ELEV-001 funcionando normalmente, mas preso entre andares com carga.",
     "ALTA", "P2", "INFRAESTRUTURA", INF, True, "Contradição; prevalece o fato de o elevador estar preso com carga."),
    ("CONTRADITORIOS", "Falha urgente sem importância no Setor A.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Contradição interna e ausência de informação."),
    ("CONTRADITORIOS", "CAL-001 com pressão alta segundo o painel e baixa segundo o operador de campo.",
     "ALTA", "P2", "UTILIDADES", UTI, True, "Leituras divergentes em caldeira: revisão para confirmar antes de agir."),
    # ---------------------------------------------------------------- FORA_ESCOPO (8)
    ("FORA_ESCOPO", "Solicito segunda via do holerite do mês passado.",
     "BAIXA", "P4", "FORA_DO_ESCOPO", DES, False, "Fora do escopo: folha de pagamento."),
    ("FORA_ESCOPO", "Preciso agendar minhas férias para dezembro.",
     "BAIXA", "P4", "FORA_DO_ESCOPO", DES, False, "Fora do escopo: gestão de pessoas."),
    ("FORA_ESCOPO", "A impressora do escritório está sem toner.",
     "BAIXA", "P4", "FORA_DO_ESCOPO", DES, False, "Fora do escopo: suprimentos de escritório."),
    ("FORA_ESCOPO", "Gostaria de reservar o auditório para o treinamento da equipe comercial.",
     "BAIXA", "P4", "FORA_DO_ESCOPO", DES, False, "Fora do escopo: reserva de espaço."),
    ("FORA_ESCOPO", "Preciso trocar a senha do sistema de folha de pagamento.",
     "BAIXA", "P4", "FORA_DO_ESCOPO", DES, False, "Fora do escopo: acesso a sistema corporativo."),
    ("FORA_ESCOPO", "Pedido de compra de cadeiras novas para o setor comercial.",
     "BAIXA", "P4", "FORA_DO_ESCOPO", DES, False, "Fora do escopo: compras."),
    ("FORA_ESCOPO", "Dúvida sobre o reembolso do plano de saúde.",
     "BAIXA", "P4", "FORA_DO_ESCOPO", DES, False, "Fora do escopo: benefícios."),
    ("FORA_ESCOPO", "Preciso do relatório de vendas do trimestre para a diretoria.",
     "BAIXA", "P4", "FORA_DO_ESCOPO", DES, False, "Fora do escopo: relatório comercial."),
    # ---------------------------------------------------------------- ALTA_CRITICIDADE (11)
    ("ALTA_CRITICIDADE", "Incêndio no painel PANEL-002, chamas visíveis no Setor A. Brigada acionada.",
     "IMEDIATA", "P1", "ELETRICA", ELE, True, "Incêndio em painel elétrico."),
    ("ALTA_CRITICIDADE", "Explosão seguida de vazamento de vapor na linha da CAL-001. Área evacuada.",
     "IMEDIATA", "P1", "UTILIDADES", UTI, True, "Explosão e vazamento de vapor em caldeira."),
    ("ALTA_CRITICIDADE", "Válvula de segurança da caldeira CAL-001 bloqueada para manutenção com a caldeira em operação.",
     "IMEDIATA", "P1", "UTILIDADES", UTI, True, "Bloqueio de dispositivo de segurança com a caldeira operando: NR-13, item 13.3.1, alínea c."),
    ("ALTA_CRITICIDADE", "Operador caiu de uma plataforma durante a troca de lâmpadas no galpão; atendimento médico a caminho.",
     "IMEDIATA", "P1", "SEGURANCA", INF, True, "Acidente com queda de trabalhador."),
    ("ALTA_CRITICIDADE", "Vazamento de gás refrigerante do COMP-003 na casa de máquinas, operadores com tontura.",
     "IMEDIATA", "P1", "SEGURANCA", UTI, True, "Vazamento de gás com efeito sobre trabalhadores."),
    ("ALTA_CRITICIDADE", "Reator 1 com pressão subindo sem controle e alarme de emergência ativo. Risco de ruptura.",
     "IMEDIATA", "P1", "PROCESSO", INS, True, "Perda de controle de processo com risco de ruptura."),
    ("ALTA_CRITICIDADE", "Transformador TRANS-001 em chamas na subestação principal. Planta sem energia.",
     "IMEDIATA", "P1", "ELETRICA", ELE, True, "Incêndio em transformador com perda total de energia."),
    ("ALTA_CRITICIDADE", "Rompimento do eixo da BOMB-001 com projeção de peças. Operador atingido de raspão.",
     "IMEDIATA", "P1", "MECANICA", MEC, True, "Falha mecânica grave com trabalhador atingido."),
    ("ALTA_CRITICIDADE", "Indicador de pressão da caldeira CAL-001 quebrado e nível de água sem controle automático, com a caldeira operando.",
     "IMEDIATA", "P1", "UTILIDADES", UTI, True, "Dispositivos de segurança da caldeira indisponíveis: NR-13, item 13.3.1, alíneas a e d."),
    ("ALTA_CRITICIDADE", "Choque elétrico em técnico durante intervenção no PANEL-001 energizado.",
     "IMEDIATA", "P1", "SEGURANCA", ELE, True, "Acidente elétrico em intervenção (NR-10)."),
    ("ALTA_CRITICIDADE", "Alarme geral de emergência acionado no Setor D sem causa conhecida; evacuação em andamento.",
     "IMEDIATA", "P1", "OUTROS", DES, True, "Emergência geral sem causa identificada, como no CASE-089."),
    # ---------------------------------------------------------------- REVISAO_HUMANA (11)
    ("REVISAO_HUMANA", "Barulho estranho em algum ponto da linha, some e volta sem padrão.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Sintoma intermitente sem origem identificada."),
    ("REVISAO_HUMANA", "Operador acha que algo pode estar errado com a caldeira, mas não sabe dizer o quê.",
     "MEDIA", "P3", "UTILIDADES", UTI, True, "Suspeita vaga em equipamento identificado."),
    ("REVISAO_HUMANA", "Leituras divergentes entre dois sensores redundantes do Reator 1; não se sabe qual está correto.",
     "MEDIA", "P3", "INSTRUMENTACAO", INS, True, "Incerteza de medição entre instrumentos redundantes."),
    ("REVISAO_HUMANA", "Possível falha intermitente na rede industrial, ainda sem confirmação.",
     "MEDIA", "P3", "TI_AUTOMACAO", TI, True, "Suspeita não confirmada de falha de automação."),
    ("REVISAO_HUMANA", "Funcionário relata ter visto faísca, mas não lembra em qual painel.",
     "ALTA", "P2", "ELETRICA", ELE, True, "Indício elétrico sem ativo identificado: cautela e revisão (NR-10)."),
    ("REVISAO_HUMANA", "Troca de telhas danificadas no telhado do galpão exige trabalho em altura.",
     "MEDIA", "P3", "INFRAESTRUTURA", INF, True, "Serviço de infraestrutura com trabalho em altura: revisão pela NR-35, itens 35.2.1 e 35.3.1."),
    ("REVISAO_HUMANA", "Cheiro diferente na área de armazenagem desde ontem, origem desconhecida.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Sintoma vago sem origem."),
    ("REVISAO_HUMANA", "O desempenho da planta caiu sem motivo aparente nesta semana.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Sintoma global sem ativo nem causa."),
    ("REVISAO_HUMANA", "Equipamento com comportamento diferente após a última manutenção; ninguém confirma o problema.",
     "DESCONHECIDA", "DESCONHECIDA", "DESCONHECIDA", DES, True, "Suspeita não confirmada, sem ativo."),
    ("REVISAO_HUMANA", "Montagem de andaime para inspeção da tubulação de vapor a 6 metros de altura.",
     "MEDIA", "P3", "UTILIDADES", UTI, True, "Serviço com trabalho em altura acima de 2 m: revisão pela NR-35."),
    ("REVISAO_HUMANA", "Alarmes repetidos do HVAC-001 aparecem e somem; a sala de controle às vezes fica quente.",
     "MEDIA", "P3", "INFRAESTRUTURA", INF, True, "Comportamento intermitente, como no CASE-096."),
]


def main() -> None:
    casos = []
    for i, item in enumerate(CASOS, start=1):
        tipo, texto, urg, prio, cat, equipe, rev, notas, *ref = item
        casos.append({
            "id": f"VAL-{i:03d}",
            "tipo": tipo,
            "texto": texto,
            "esperado": {"urgencia": urg, "prioridade": prio, "categoria": cat, "equipe": equipe,
                         "requer_revisao_humana": rev},
            "referencia_caso_canonico": f"VAL-{ref[0]:03d}" if ref else None,
            "notas": notas,
        })
    DESTINO.write_text(json.dumps(casos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(load_dataset(str(DESTINO)))} casos de validação gravados em {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
