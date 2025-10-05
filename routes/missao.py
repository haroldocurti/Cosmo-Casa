"""Blueprint de rotas de missão: seleção de nave/módulos e simulação.

Separa a lógica de missão do arquivo principal.
"""

import random
import json
import logging
import os
from flask import Blueprint, render_template, request, redirect, url_for, session, send_from_directory, current_app

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
        # Normalização de aliases de nave vindos por imagem/nome
        alias = {
            'foguete-longa-marcha': 'longmarch8a',
            'longmarch8a': 'longmarch8a',
            'falcon9': 'falcon9',
            'pslv': 'pslv'
        }
        nave_key = alias.get((nave_id or '').lower(), nave_id)
        nave_selecionada = NAVES_ESPACIAIS.get(nave_key)
        if not nave_selecionada:
            return "Nave não encontrada!", 404
        return render_template('selecao_modulos.html', destino=destino, nave=nave_selecionada, nave_id=nave_key, modulos=MODULOS_HABITAT, codigo_sala=request.args.get('codigo_sala'))
    except Exception:
        logging.exception("Falha ao renderizar selecao_modulos")
        return "Erro ao preparar seleção de módulos", 500


@missao_bp.route('/viagem/<string:destino>/<string:nave_id>', methods=['POST'])
def viagem(destino, nave_id):
    """Processa módulos selecionados e simula a viagem em turnos."""
    try:
        modulos_selecionados_ids = request.form.getlist('modulos_selecionados')
        modulos_a_bordo = {id: MODULOS_HABITAT[id] for id in modulos_selecionados_ids}
        # Normalizar id de nave para chave interna
        alias = {
            'foguete-longa-marcha': 'longmarch8a',
            'longmarch8a': 'longmarch8a',
            'falcon9': 'falcon9',
            'pslv': 'pslv'
        }
        nave_key = alias.get((nave_id or '').lower(), nave_id)
        nave = NAVES_ESPACIAIS.get(nave_key)

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
                    db_manager.atualizar_destino_e_nave(codigo_sala, destino, nave_key)
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

        # --- Cálculo de chegada e pontuação ---
        def calcular_resultado_e_pontos(destino_val, nave_val, modulos_dict, diario):
            # Base da pontuação por dificuldade
            dificuldade_base = {'lua': 50, 'marte': 120, 'exoplaneta': 300}.get(destino_val, 50)

            # Essenciais por destino
            essenciais_por_destino = {
                'lua': {'suporte_vida', 'habitacional'},
                'marte': {'suporte_vida', 'habitacional', 'medico'},
                'exoplaneta': {'suporte_vida', 'habitacional', 'blindagem', 'controle', 'hidroponia'}
            }
            essenciais = essenciais_por_destino.get(destino_val, {'suporte_vida', 'habitacional'})

            presentes = set(modulos_dict.keys())
            faltantes = essenciais - presentes
            pontos = dificuldade_base
            pontos += 20 * len(essenciais.intersection(presentes))
            pontos -= 25 * len(faltantes)

            # Massa e capacidade por dificuldade
            capacidade_kg = (nave_val.get('capacidade_carga', 0) or 0) * 1000 if nave_val else 0
            massa_total = sum(m.get('massa', 0) for m in modulos_dict.values())
            if capacidade_kg > 0:
                ratio = (massa_total / capacidade_kg)
                if destino_val == 'lua':
                    # Lua: mais maleável, aceita até 120% da capacidade com penalização
                    if massa_total > capacidade_kg * 1.2:
                        pontos -= 60
                    elif massa_total > capacidade_kg:
                        pontos -= 30
                    elif 0.5 <= ratio <= 1.0:
                        pontos += 20
                elif destino_val == 'marte':
                    # Marte: mediano, precisa respeitar capacidade, premia boa ocupação
                    if massa_total > capacidade_kg:
                        pontos -= 50
                    elif 0.6 <= ratio <= 0.95:
                        pontos += 30
                else:
                    # Exoplaneta: difícil, exige margem de segurança
                    if massa_total > capacidade_kg * 0.95:
                        pontos -= 60
                    elif 0.6 <= ratio <= 0.9:
                        pontos += 25

            # Avarias com penalização por destino
            avariados = sum(1 for m in modulos_dict.values() if m.get('status') == 'Avariado')
            penal_por_avaria = {'lua': 8, 'marte': 10, 'exoplaneta': 14}.get(destino_val, 10)
            pontos -= avariados * penal_por_avaria

            # Gate de chegada por dificuldade
            allowed_missing = {'lua': 2, 'marte': 1, 'exoplaneta': 0}.get(destino_val, 1)
            tolerancia_avarias = {'lua': 3, 'marte': 2, 'exoplaneta': 1}.get(destino_val, 2)

            # Regras de massa para gate
            if destino_val == 'lua':
                massa_ok = (capacidade_kg == 0) or (massa_total <= capacidade_kg * 1.2)
            elif destino_val == 'marte':
                massa_ok = (capacidade_kg == 0) or (massa_total <= capacidade_kg)
            else:
                massa_ok = (capacidade_kg == 0) or (massa_total <= capacidade_kg * 0.95)

            chegou = (len(faltantes) <= allowed_missing) and massa_ok and (avariados <= tolerancia_avarias)
            return chegou, max(pontos, 0), massa_total, capacidade_kg

        chegada_ok, pontuacao, massa_total, capacidade_kg = calcular_resultado_e_pontos(destino, nave, modulos_a_bordo, diario_de_bordo)

        # Persistir em sessão para gate do Habitat
        session['chegada_ok'] = chegada_ok
        session['missao_score'] = pontuacao
        session['missao_destino'] = destino
        session['missao_nave'] = nave_key

        # Registrar pontuação no ranking se aluno logado
        try:
            aluno_id = session.get('aluno_id')
            sala_id = session.get('sala_id')
            if aluno_id and sala_id:
                detalhes = {
                    'destino': destino,
                    'nave_id': nave_id,
                    'massa_total': massa_total,
                    'capacidade_kg': capacidade_kg,
                    'essenciais_ok': chegada_ok,
                    'aviso': 'pontuação de missão'
                }
                db_manager.registrar_resposta_desafio(
                    aluno_id, sala_id, 'missao_score', json.dumps(detalhes, ensure_ascii=False), None, int(pontuacao)
                )
        except Exception:
            logging.exception('Falha ao registrar pontuação da missão no ranking')

        return render_template('viagem.html', diario=diario_de_bordo, destino=destino, nave=nave, modulos=modulos_a_bordo, chegada_ok=chegada_ok, pontuacao=pontuacao)
    except Exception:
        logging.exception("Falha ao processar viagem")
        return "Erro ao processar a viagem", 500


@missao_bp.route('/habitat')
def habitat():
    """Gate para a montagem do Habitat: somente após chegada bem-sucedida."""
    try:
        if not session.get('chegada_ok'):
            return redirect(url_for('missao.game_over'))
        return render_template('Habitat.html')
    except Exception:
        logging.exception('Falha ao abrir Habitat')
        return "Erro ao abrir Habitat", 500


@missao_bp.route('/game-over')
def game_over():
    """Tela de Game Over caso a missão não tenha chegado ao destino."""
    try:
        return render_template('game_over.html')
    except Exception:
        logging.exception('Falha ao renderizar Game Over')
        return "Erro ao renderizar página", 500


@missao_bp.route('/retry-modulos')
def retry_modulos():
    """Redireciona para seleção de módulos, priorizando dados do aluno/sessão.

    - Se houver destino e nave na sessão, usa-os.
    - Caso contrário, tenta recuperar destino/nave da sala do aluno (session['sala_id']).
    - Aplica normalização de alias de nave.
    - Faz fallback para seleção de nave ou tela de seleção se necessário.
    """
    try:
        # Prioriza dados da sala do aluno para garantir consistência
        destino = None
        nave_id = None
        sala_id = session.get('sala_id')
        if sala_id:
            try:
                sala = db_manager.buscar_sala_por_id(sala_id)
            except Exception:
                sala = None
            if sala:
                destino = sala.get('destino')
                nave_id = sala.get('nave_id')
        # Se não houver sala, usa os dados já guardados na sessão da missão
        if not destino:
            destino = session.get('missao_destino')
        if not nave_id:
            nave_id = session.get('missao_nave')

        # Normalização de aliases
        alias = {
            'foguete-longa-marcha': 'longmarch8a',
            'longmarch8a': 'longmarch8a',
            'falcon9': 'falcon9',
            'pslv': 'pslv'
        }
        nave_key = alias.get((nave_id or '').lower(), nave_id)
        destino_norm = (destino or '').lower()

        # Sem fallback para outras páginas: aluno deve ir apenas à seleção de módulos
        if destino_norm not in {'lua', 'marte', 'exoplaneta'} or (nave_key not in NAVES_ESPACIAIS):
            return "Configuração de missão ausente ou inválida. Solicite ao professor para configurar a sala.", 400

        # Inclui codigo_sala se disponível
        codigo_sala = None
        try:
            sala_id = session.get('sala_id')
            if sala_id:
                sala = db_manager.buscar_sala_por_id(sala_id)
                if sala:
                    codigo_sala = sala.get('codigo_sala')
        except Exception:
            codigo_sala = None

        if codigo_sala:
            return redirect(url_for('missao.selecao_modulos', destino=destino, nave_id=nave_key, codigo_sala=codigo_sala))
        return redirect(url_for('missao.selecao_modulos', destino=destino, nave_id=nave_key))
    except Exception:
        logging.exception('Falha no redirecionamento para módulos')
        return redirect(url_for('tela_selecao'))


@missao_bp.route('/icons/<path:filename>')
def icons(filename):
    """Serve os ícones adicionados em templates/icons para uso no Habitat."""
    try:
        base = os.path.join(current_app.root_path, 'templates', 'icons')
        return send_from_directory(base, filename)
    except Exception:
        logging.exception('Falha ao servir ícone %s', filename)
        return "Ícone não encontrado", 404


@missao_bp.route('/ranking-rodada')
def ranking_rodada():
    """Painel simples de ranking dos participantes da rodada (salas ativas)."""
    try:
        try:
            ranking = db_manager.obter_ranking_salas_ativas(limit=100)
        except Exception:
            ranking = []
        return render_template('ranking_rodada.html', ranking=ranking)
    except Exception:
        logging.exception('Falha ao renderizar ranking da rodada')
        return "Erro ao renderizar ranking", 500