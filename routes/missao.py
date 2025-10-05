"""Blueprint de rotas de missão: seleção de nave/módulos e simulação.

Separa a lógica de missão do arquivo principal.
"""

import random
import json
import logging
from flask import Blueprint, render_template, request, redirect, url_for

from services.db import db_manager
from services.data import NAVES_ESPACIAIS, MODULOS_HABITAT, EVENTOS_ALEATORIOS


missao_bp = Blueprint('missao', __name__)


@missao_bp.route('/montagem-transporte/<string:destino>')
def montagem_transporte(destino):
    """Tela de seleção de naves, recebendo o destino como parâmetro."""
    try:
        # Validação: impedir acesso direto sem selecionar planeta
        destino_norm = (destino or '').lower()
        if destino_norm not in {'lua', 'marte', 'exoplaneta'}:
            return redirect(url_for('tela_selecao', codigo_sala=request.args.get('codigo_sala')))
        return render_template('montagem_transporte.html', naves=NAVES_ESPACIAIS, destino=destino, codigo_sala=request.args.get('codigo_sala'))
    except Exception:
        logging.exception("Falha ao renderizar montagem_transporte")
        return "Erro ao preparar montagem de transporte", 500


@missao_bp.route('/selecao-modulos/<string:destino>/<string:nave_id>')
def selecao_modulos(destino, nave_id):
    """Tela de seleção de módulos para a missão."""
    try:
        # Validação: destino precisa ser válido
        destino_norm = (destino or '').lower()
        if destino_norm not in {'lua', 'marte', 'exoplaneta'}:
            return redirect(url_for('tela_selecao', codigo_sala=request.args.get('codigo_sala')))
        nave_selecionada = NAVES_ESPACIAIS.get(nave_id)
        if not nave_selecionada:
            return "Nave não encontrada!", 404
        return render_template('selecao_modulos.html', destino=destino, nave=nave_selecionada, modulos=MODULOS_HABITAT, codigo_sala=request.args.get('codigo_sala'))
    except Exception:
        logging.exception("Falha ao renderizar selecao_modulos")
        return "Erro ao preparar seleção de módulos", 500


@missao_bp.route('/viagem/<string:destino>/<string:nave_id>', methods=['POST'])
def viagem(destino, nave_id):
    """Processa módulos selecionados e simula a viagem em turnos."""
    try:
        modulos_selecionados_ids = request.form.getlist('modulos_selecionados')
        modulos_a_bordo = {id: MODULOS_HABITAT[id] for id in modulos_selecionados_ids}
        nave = NAVES_ESPACIAIS.get(nave_id)

        if destino == 'marte':
            total_turnos = 60
        elif destino == 'exoplaneta':
            total_turnos = 250
        else:
            total_turnos = 15

        diario_de_bordo = []
        for turno_atual in range(1, total_turnos + 1):
            chance_evento = 0.8 if destino == 'exoplaneta' else 0.6
            evento = random.choice(EVENTOS_ALEATORIOS) if random.random() < chance_evento else EVENTOS_ALEATORIOS[4]
            diario_de_bordo.append({"turno": turno_atual, "evento": evento})
            if evento['efeito'] == 'risco_avaria_modulo' and modulos_a_bordo:
                modulo_avariado_id = random.choice(list(modulos_a_bordo.keys()))
                modulos_a_bordo[modulo_avariado_id]['status'] = 'Avariado'

        codigo_sala = request.args.get('codigo_sala') or request.form.get('codigo_sala')
        if codigo_sala:
            try:
                try:
                    db_manager.atualizar_destino_e_nave(codigo_sala, destino, nave_id)
                except Exception:
                    logging.exception("Falha ao atualizar destino/nave da sala")
                titulo = f"Missão {destino.capitalize()} — {nave['nome'] if nave else nave_id}"
                descricao = f"Missão planejada com {len(modulos_a_bordo)} módulos selecionados."
                sala = db_manager.buscar_sala_por_codigo_any(codigo_sala)
                if sala:
                    try:
                        desafios = json.loads(sala.get('desafios_json') or '[]')
                    except Exception:
                        desafios = []
                    desafios.append({'titulo': titulo, 'descricao': descricao})
                    db_manager.atualizar_desafios_json(codigo_sala, json.dumps(desafios, ensure_ascii=False))
            except Exception:
                logging.exception("Falha ao anexar desafio à sala")
            return redirect(url_for('professor.professor_dashboard'))

        return render_template('viagem.html', diario=diario_de_bordo, destino=destino, nave=nave, modulos=modulos_a_bordo)
    except Exception:
        logging.exception("Falha ao processar viagem")
        return "Erro ao processar a viagem", 500