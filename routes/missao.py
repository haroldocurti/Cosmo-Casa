"""Blueprint de Missão: seleção de nave/módulos e simulação.

Responsabilidades:
- Seleção de nave e destino para criar contexto da missão;
- Escolha e montagem dos módulos do habitat com conteúdo educativo;
- Simulação em turnos de eventos aleatórios com impacto nos recursos;
- Exposição de assets estáticos associados (imagens, dados educativos).

Design pedagógico:
- Progressão em etapas com feedback imediato (texto e métricas);
- Eventos aleatórios ilustram trade-offs de engenharia e sustentabilidade.
"""

import random
import json
import logging
import os
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, session, send_from_directory, current_app

from services.db import db_manager
from services.data import NAVES_ESPACIAIS, MODULOS_HABITAT, EVENTOS_ALEATORIOS


missao_bp = Blueprint('missao', __name__)


# --- Controle de fluxo e cache para páginas do aluno (missão) ---
@missao_bp.before_request
def _require_aluno_session():
    """Exige sessão de aluno para acessar páginas da missão.

    Permite acesso livre a páginas públicas como ranking e game over.
    Evita que o usuário volte a páginas da missão após sair (sem sessão).
    """
    try:
        # Endpoints públicos do blueprint
        public_endpoints = {'missao.ranking_rodada', 'missao.game_over'}
        ep = request.endpoint
        if ep in public_endpoints:
            return None

        # Permitir que professores/admins acessem a tela de montagem de transporte
        # para configurar destino/nave e então retornar ao dashboard via rota dedicada.
        try:
            if ep == 'missao.montagem_transporte' and (session.get('user_role') in {'professor', 'admin'} or session.get('professor_id')):
                return None
        except Exception:
            pass

        # Sessão obrigatória nas páginas da missão
        if not session.get('aluno_id'):
            return redirect(url_for('index'))

        # Controle de fluxo por etapa (apenas para alunos): impedir volta a páginas anteriores
        etapa = session.get('missao_etapa')
        if etapa == 'viagem' and ep in {'missao.montagem_transporte', 'missao.selecao_modulos'}:
            destino = session.get('viagem_destino') or session.get('missao_destino')
            nave_id = session.get('viagem_nave_id') or session.get('missao_nave')
            if destino and nave_id:
                return redirect(url_for('missao.viagem_get', destino=destino, nave_id=nave_id))
            return redirect(url_for('missao.ranking_rodada'))
        if etapa == 'selecao' and ep == 'missao.montagem_transporte':
            return redirect(url_for('missao.retry_modulos'))
        return None
    except Exception:
        # Em erro, preserve segurança exigindo retorno à index
        return redirect(url_for('index'))


@missao_bp.after_request
def _missao_no_cache(response):
    """Evita cache/bfcache nas páginas HTML da missão.

    Garante revalidação pelo navegador ao pressionar Voltar/Avançar.
    """
    try:
        if response.mimetype == 'text/html':
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    except Exception:
        pass
    return response


@missao_bp.route('/montagem-transporte/<string:destino>')
def montagem_transporte(destino):
    """Tela de seleção de naves, recebendo o destino como parâmetro."""
    try:
        # Validação: impedir acesso direto sem selecionar planeta
        destino_norm = (destino or '').lower()
        if destino_norm not in {'lua', 'marte', 'exoplaneta'}:
            return redirect(url_for('tela_selecao', codigo_sala=request.args.get('codigo_sala')))
        try:
            session['missao_etapa'] = 'montagem'
        except Exception:
            pass
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
        try:
            session['missao_etapa'] = 'selecao'
            session['missao_destino'] = destino
            session['missao_nave'] = nave_key
        except Exception:
            pass
        return render_template('selecao_modulos.html', destino=destino, nave=nave_selecionada, nave_id=nave_key, modulos=MODULOS_HABITAT, codigo_sala=request.args.get('codigo_sala'))
    except Exception:
        logging.exception("Falha ao renderizar selecao_modulos")
        return "Erro ao preparar seleção de módulos", 500


@missao_bp.route('/viagem/<string:destino>/<string:nave_id>', methods=['POST'])
def viagem(destino, nave_id):
    """Processa módulos selecionados e simula a viagem em turnos."""
    try:
        # Normalizar id de nave para chave interna
        alias = {
            'foguete-longa-marcha': 'longmarch8a',
            'longmarch8a': 'longmarch8a',
            'falcon9': 'falcon9',
            'pslv': 'pslv'
        }
        nave_key = alias.get((nave_id or '').lower(), nave_id)
        nave = NAVES_ESPACIAIS.get(nave_key)

        # Ler módulos selecionados e validar pelo menos um
        modulos_selecionados_ids = request.form.getlist('modulos_selecionados')
        if not modulos_selecionados_ids:
            try:
                session['erro_modulos'] = 'Selecione pelo menos um módulo antes de lançar a missão.'
            except Exception:
                pass
            codigo_sala = request.args.get('codigo_sala') or request.form.get('codigo_sala')
            if codigo_sala:
                return redirect(url_for('missao.selecao_modulos', destino=destino, nave_id=nave_key, codigo_sala=codigo_sala))
            return redirect(url_for('missao.selecao_modulos', destino=destino, nave_id=nave_key))

        modulos_a_bordo = {id: MODULOS_HABITAT[id] for id in modulos_selecionados_ids}

        if destino == 'marte':
            total_turnos = 60
        elif destino == 'exoplaneta':
            total_turnos = 250
        else:
            total_turnos = 15

        # Guardar módulos escolhidos para uso posterior no Habitat
        try:
            session['modulos_selecionados'] = modulos_selecionados_ids
        except Exception:
            logging.exception('Falha ao salvar módulos selecionados na sessão')

        # IA simples: personalizar mensagens por turno com base nos módulos e destino
        ids_set = set(modulos_selecionados_ids)
        ids_list = list(ids_set)
        diario_de_bordo = []

        def evento_personalizado(turno:int):
            # 30% de chance de evento aleatório conhecido; caso contrário, evento positivo personalizado
            if random.random() < (0.3 if destino != 'exoplaneta' else 0.4):
                base = random.choice([e for e in EVENTOS_ALEATORIOS if e.get('nome') != 'Tudo Calmo'])
                evt = dict(base)
                # Ícones por evento aleatório
                icones_eventos = {
                    'Tempestade Solar': 'solar-storm.svg',
                    'Falha Mecânica Menor': 'wrench.svg',
                    'Impacto de Micrometeoroide': 'meteor.svg',
                    'Surto de Energia': 'surge.svg',
                    'Navegação Otimizada': 'navigation.svg'
                }
                evt['icone'] = icones_eventos.get(base['nome'], 'event-default.svg')
                # Ajuste descritivo conforme módulos presentes
                if base['nome'] == 'Tempestade Solar':
                    if 'suporte_vida' in ids_set:
                        evt['descricao'] += ' Sistemas de suporte mantêm níveis estáveis para a tripulação.'
                    else:
                        evt['descricao'] += ' A ausência de Suporte à Vida agrava a resposta da tripulação.'
                elif base['nome'] == 'Falha Mecânica Menor' and 'impressao3d' in ids_set:
                    evt['descricao'] += ' A Impressão 3D fabrica uma peça de reposição e reduz o atraso.'
                elif base['nome'] == 'Impacto de Micrometeoroide' and 'armazenamento' in ids_set:
                    evt['descricao'] += ' A carga está bem acondicionada; danos são mínimos.'
                elif base['nome'] == 'Surto de Energia' and 'controle' in ids_set:
                    evt['descricao'] += ' O módulo de Controle estabiliza rapidamente os sistemas.'
                elif base['nome'] == 'Navegação Otimizada' and 'exercicios' in ids_set:
                    evt['descricao'] += ' A equipe em boa forma física mantém procedimentos com precisão.'
                return evt
            # Evento positivo relacionado a um módulo selecionado
            if ids_list:
                mod_id = ids_list[(turno - 1) % len(ids_list)]
                mod = MODULOS_HABITAT.get(mod_id, {"nome": mod_id})
                nome_evt = f"Operação do Módulo: {mod.get('nome')}"
                dicas = {
                    'hidroponia': 'Produção de alimentos estabiliza moral e reduz consumo de estoque.',
                    'medico': 'Atendimento médico lida com indisposição leve na tripulação.',
                    'airlock': 'EVA realizada para inspeção externa; retorno seguro ao habitat.',
                    'impressao3d': 'Peça fabricada para reparo rápido de um subsistema.',
                    'sanitario': 'Sistema de reciclagem de água mantém níveis adequados.',
                    'armazenamento': 'Reorganização de suprimentos otimiza acesso e segurança.',
                    'exercicios': 'Rotina de exercícios mitiga fadiga em microgravidade.',
                    'inflavel': 'Módulo expansível aumenta volume útil para operações.',
                    'pesquisa': 'Experimento científico rende dados importantes da missão.',
                    'alimentacao': 'Refeição balanceada melhora coesão da equipe.',
                    'habitacional': 'Descanso adequado melhora desempenho da equipe.',
                    'suporte_vida': 'Níveis de oxigênio e pressão se mantêm estáveis.'
                }
                icones_modulos = {
                    'hidroponia': 'plant.svg',
                    'medico': 'medical.svg',
                    'airlock': 'airlock.svg',
                    'impressao3d': 'printer3d.svg',
                    'sanitario': 'water-recycle.svg',
                    'armazenamento': 'storage.svg',
                    'exercicios': 'dumbbell.svg',
                    'inflavel': 'expand.svg',
                    'pesquisa': 'flask.svg',
                    'alimentacao': 'food.svg',
                    'habitacional': 'habitat.svg',
                    'suporte_vida': 'life-support.svg'
                }
                desc = dicas.get(mod_id, 'O módulo contribui positivamente para o andamento da missão.')
                return {"nome": nome_evt, "descricao": desc, "efeito": "nenhum", "icone": icones_modulos.get(mod_id, 'module-default.svg')}
            # Fallback
            return {"nome": "Rotina Estável", "descricao": "A equipe segue procedimentos padrão enquanto sistemas operam normalmente.", "efeito": "nenhum", "icone": "calm.svg"}

        for turno_atual in range(1, total_turnos + 1):
            evento = evento_personalizado(turno_atual)
            diario_de_bordo.append({"turno": turno_atual, "evento": evento})
            if evento.get('efeito') == 'risco_avaria_modulo' and modulos_a_bordo:
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
            # Apenas professores devem ser redirecionados ao dashboard; alunos seguem na simulação
            if not session.get('aluno_id'):
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

        # Gerar feedback inteligente em caso de falha
        try:
            if not chegada_ok:
                essenciais_por_destino = {
                    'lua': {'suporte_vida', 'habitacional'},
                    'marte': {'suporte_vida', 'habitacional', 'medico'},
                    'exoplaneta': {'suporte_vida', 'habitacional', 'blindagem', 'controle', 'hidroponia'}
                }
                essenciais = essenciais_por_destino.get(destino, {'suporte_vida', 'habitacional'})
                presentes = set(modulos_a_bordo.keys())
                faltantes = list(essenciais - presentes)
                avariados = [k for k, m in modulos_a_bordo.items() if m.get('status') == 'Avariado']
                ratio = (massa_total / capacidade_kg) if (capacidade_kg or 0) > 0 else 0
                causas = []
                if faltantes:
                    causas.append(f"Módulos essenciais ausentes: {', '.join(faltantes)}.")
                if destino == 'lua' and capacidade_kg and massa_total > capacidade_kg * 1.2:
                    causas.append('Excesso de massa acima de 120% da capacidade da nave.')
                elif destino == 'marte' and capacidade_kg and massa_total > capacidade_kg:
                    causas.append('Massa total excedeu a capacidade da nave.')
                elif destino == 'exoplaneta' and capacidade_kg and massa_total > capacidade_kg * 0.95:
                    causas.append('Para exoplaneta, a margem de segurança de massa não foi atendida (95%).')
                if avariados:
                    causas.append(f"Avarias em módulos críticos: {', '.join(avariados)}.")
                resumo = (
                    f"Destino: {destino.capitalize()} | Nave: {nave.get('nome') if nave else nave_key} | "
                    f"Massa: {int(massa_total)}kg / Capacidade: {int(capacidade_kg)}kg (uso {int(ratio*100)}%)."
                )
                feedback = "\n".join(["Análise de Game Over:", resumo] + (causas or ["Condições insuficientes para a missão."]))
                session['missao_feedback'] = feedback
        except Exception:
            logging.exception('Falha ao gerar feedback de Game Over')

        # Registrar pontuação no ranking se aluno logado
        try:
            aluno_id = session.get('aluno_id')
            sala_id = session.get('sala_id')
            # Fallback robusto: tentar resolver aluno/sala por nome e código se ausentes
            if not (aluno_id and sala_id):
                try:
                    codigo_sala_req = request.args.get('codigo_sala') or request.form.get('codigo_sala')
                    nome_aluno = session.get('nome_aluno')
                    # Resolver sala_id pelo código, se disponível
                    if not sala_id and codigo_sala_req:
                        sala = db_manager.buscar_sala_por_codigo_any(codigo_sala_req)
                        if sala:
                            sala_id = sala.get('id')
                            session['sala_id'] = sala_id
                    # Resolver aluno_id pelo nome dentro da sala
                    if not aluno_id and sala_id and nome_aluno:
                        with sqlite3.connect(db_manager.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT id FROM alunos WHERE sala_id = ? AND nome = ?', (sala_id, nome_aluno))
                            row = cursor.fetchone()
                            if row:
                                aluno_id = row[0]
                                session['aluno_id'] = aluno_id
                except Exception:
                    logging.exception('Fallback para obter aluno/sala ao registrar pontuação falhou')

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
                    aluno_id, sala_id, 'missao_score', json.dumps(detalhes, ensure_ascii=False), 1, int(pontuacao)
                )
        except Exception:
            logging.exception('Falha ao registrar pontuação da missão no ranking')

        # PRG: salvar resultados e redirecionar para GET
        try:
            session['viagem_diario'] = diario_de_bordo
            session['viagem_destino'] = destino
            session['viagem_nave_id'] = nave_key
            session['viagem_nave'] = nave
            session['viagem_modulos'] = modulos_a_bordo
            session['viagem_chegada_ok'] = chegada_ok
            session['viagem_pontuacao'] = pontuacao
            session['missao_etapa'] = 'viagem'
        except Exception:
            logging.exception('Falha ao salvar dados da viagem na sessão')
        codigo_sala = request.args.get('codigo_sala') or request.form.get('codigo_sala')
        if codigo_sala:
            return redirect(url_for('missao.viagem_get', destino=destino, nave_id=nave_key, codigo_sala=codigo_sala))
        return redirect(url_for('missao.viagem_get', destino=destino, nave_id=nave_key))
    except Exception:
        logging.exception("Falha ao processar viagem")
        return "Erro ao processar a viagem", 500


@missao_bp.route('/habitat')
def habitat():
    """Gate para a montagem do Habitat: somente após chegada bem-sucedida."""
    try:
        if not session.get('chegada_ok'):
            return redirect(url_for('missao.game_over'))
        # Carregar módulos previamente selecionados para limitar a paleta
        mod_ids = session.get('modulos_selecionados') or []
        # Mapear para chaves usadas no editor de Habitat (normalização simples)
        # Tabela de equivalência: ids de seleção -> chaves de ícone do editor
        mapper = {
            'suporte_vida': 'suporte',
            'habitacional': 'habitacional',
            'alimentacao': 'refeicoes',
            'medico': 'medico',
            'exercicios': 'exercicios',
            'pesquisa': 'trabalho',
            'armazenamento': 'armazenamento',
            'sanitario': 'sanitario',
            'inflavel': 'inflavel',
            'airlock': 'airlock',
            'hidroponia': 'hidroponia',
            'impressao3d': 'imp3d',
            # novos módulos adicionados ao catálogo (services/data.py)
            'blindagem': 'blindagem',
            'estrutural': 'tesserae',    # Estrutural Modular (TESSERAE)
            'lazer': 'cultura',          # Cultura e Lazer
            'robotico': 'robotico',
            'controle': 'controle',
            'multifuncional': 'multifuncional'
        }
        # Lista com possíveis duplicatas para refletir quantidade levada por tipo
        mod_chaves = [mapper.get(m) for m in mod_ids if mapper.get(m)]
        # Deduplificar para paleta de módulos no editor (evita botões repetidos)
        modulos_permitidos = []
        limites_por_tipo = {}
        for k in mod_chaves:
            if k not in modulos_permitidos:
                modulos_permitidos.append(k)
            limites_por_tipo[k] = (limites_por_tipo.get(k, 0) + 1)
        # Limite total de peças de módulo que podem ser colocadas
        max_modulos = len(mod_chaves)
        return render_template(
            'Habitat.html',
            modulos_permitidos=modulos_permitidos,
            max_modulos=max_modulos,
            limites_por_tipo=limites_por_tipo,
            destino=session.get('missao_destino')
        )
    except Exception:
        logging.exception('Falha ao abrir Habitat')
        return "Erro ao abrir Habitat", 500


@missao_bp.route('/habitat/finalizar', methods=['POST'])
def habitat_finalizar():
    """Finaliza o game pelo aluno e registra progresso/itens escolhidos."""
    try:
        aluno_id = session.get('aluno_id')
        sala_id = session.get('sala_id')
        # Fallback: se aluno_id estiver ausente, tentar resolver pelo nome na mesma sala
        if not aluno_id and sala_id:
            try:
                nome_aluno = session.get('nome_aluno')
                if nome_aluno:
                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT id FROM alunos WHERE sala_id = ? AND nome = ?', (sala_id, nome_aluno))
                        row = cursor.fetchone()
                        if row:
                            aluno_id = row[0]
            except Exception:
                logging.exception('Fallback de aluno_id por nome/sala falhou')
        itens = session.get('modulos_selecionados') or []
        # Análise de sobrevivência com base nos itens selecionados
        essenciais_por_destino = {
            'lua': {'suporte_vida', 'habitacional'},
            'marte': {'suporte_vida', 'habitacional', 'medico'},
            'exoplaneta': {'suporte_vida', 'habitacional', 'blindagem', 'controle', 'hidroponia'}
        }
        destino = session.get('missao_destino')
        essenciais = essenciais_por_destino.get(destino, {'suporte_vida', 'habitacional'})
        presentes = set(itens)
        faltantes = list(essenciais - presentes)
        sobrevivencia_ok = len(faltantes) == 0

        detalhes = {
            'destino': session.get('missao_destino'),
            'nave_id': session.get('missao_nave'),
            'modulos': itens,
            'chegada_ok': session.get('chegada_ok'),
            'score': session.get('missao_score'),
            'avaliacao_sobrevivencia': {
                'ok': sobrevivencia_ok,
                'faltantes': faltantes
            }
        }
        if aluno_id and sala_id:
            try:
                db_manager.registrar_resposta_desafio(
                    aluno_id, sala_id, 'habitat_finalizado', json.dumps(detalhes, ensure_ascii=False), 1, int(session.get('missao_score') or 0)
                )
            except Exception:
                logging.exception('Falha ao registrar finalização de habitat no ranking')
        # Após finalizar, direcionar para ranking ou dashboard
        return redirect(url_for('missao.ranking_rodada'))
    except Exception:
        logging.exception('Falha ao finalizar Habitat')
        return "Erro ao finalizar Habitat", 500


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
@missao_bp.route('/viagem/<string:destino>/<string:nave_id>', methods=['GET'], endpoint='viagem_get')
def viagem_get(destino, nave_id):
    """Exibe resultados da viagem via GET (PRG)."""
    try:
        diario = session.get('viagem_diario')
        destino_sess = session.get('viagem_destino') or destino
        nave = session.get('viagem_nave')
        modulos = session.get('viagem_modulos')
        chegada_ok = session.get('viagem_chegada_ok')
        pontuacao = session.get('viagem_pontuacao')
        if not diario or not modulos:
            return redirect(url_for('missao.retry_modulos'))
        return render_template('viagem.html', diario=diario, destino=destino_sess, nave=nave, modulos=modulos, chegada_ok=chegada_ok, pontuacao=pontuacao)
    except Exception:
        logging.exception('Falha ao exibir viagem (GET)')
        return "Erro ao exibir a viagem", 500
