"""Blueprint de rotas de aluno: login, entrada e respostas.

Foco em usabilidade e clareza para estudantes:
- `aluno_login`: valida nome exato na lista da sala (feedback claro);
- `aluno_entrar`: fluxo por código + nome com normalização (acentos/espaços);
- `modulo_underscore_espaco`: página pós-login com informações da sala;
- `api/registrar-resposta`: registro simplificado das respostas dos desafios.

Mantém a mesma API pública, separando responsabilidades de app.py.
"""

import sqlite3
import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify

from services.db import db_manager


aluno_bp = Blueprint('aluno', __name__)


# Impedir voltar às páginas de login/entrada quando já autenticado como aluno
@aluno_bp.before_request
def _aluno_block_back_to_login():
    """Controla acesso às páginas de login/entrada quando já autenticado.

    Objetivo: permitir que o botão "Iniciar Missão" abra `aluno_entrar.html`
    mesmo quando o aluno já tem sessão, porém impedir reenvio de formulário.

    Regras:
    - Bloqueia qualquer acesso (GET/POST) a `aluno_login` quando autenticado.
    - Permite GET em `aluno_entrar` mesmo autenticado (renderiza a página).
    - Bloqueia POST em `aluno_entrar` quando autenticado (evita re-login).
    """
    try:
        ep = request.endpoint
        if session.get('aluno_id'):
            # Nunca voltar para a rota de login se já autenticado
            if ep == 'aluno.aluno_login':
                return redirect(url_for('missao.retry_modulos'))
            # Permite visualizar a página de entrar, mas bloqueia reenvio de POST
            if ep == 'aluno.aluno_entrar' and request.method == 'POST':
                return redirect(url_for('missao.retry_modulos'))
    except Exception:
        pass
    return None


@aluno_bp.after_request
def _aluno_no_cache_login_pages(response):
    """Evita cache do navegador nas páginas de login/entrada do aluno.

    Isso previne que o botão Voltar exiba o formulário a partir do cache.
    """
    try:
        if request.endpoint in {'aluno.aluno_login', 'aluno.aluno_entrar', 'aluno.modulo_underscore_espaco'}:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    except Exception:
        pass
    return response


@aluno_bp.route('/aluno/login/<codigo_sala>', methods=['GET', 'POST'])
def aluno_login(codigo_sala):
    """Login do aluno: valida se nome corresponde exatamente à lista.

    Mostra mensagem de erro amigável em casos comuns:
    - Sala inexistente ou inativa
    - Campo de nome vazio
    - Nome não encontrado (sugere verificar acentos e espaços)
    """
    sala = db_manager.buscar_sala_por_codigo(codigo_sala)
    if not sala:
        return "Sala não encontrada", 404

    erro = None
    if request.method == 'POST':
        nome_digitado = request.form.get('nome_aluno', '').strip()
        logging.info(f"Tentativa de login para sala {codigo_sala} com nome: '{nome_digitado}'")
        if not nome_digitado:
            erro = 'Digite seu nome completo.'
        else:
            try:
                with sqlite3.connect(db_manager.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id, nome FROM alunos WHERE sala_id = ?
                    ''', (sala['id'],))
                    alunos_na_sala = cursor.fetchall()
                    logging.info(f"Alunos registrados na sala {codigo_sala}: {[a[1] for a in alunos_na_sala]}")

                    # Verifica se o nome digitado corresponde exatamente a algum nome na lista
                    row = next((a for a in alunos_na_sala if a[1] == nome_digitado), None)
                    if row:
                        session['aluno_id'] = row[0]
                        session['nome_aluno'] = row[1]
                        session['sala_id'] = sala['id']
                        # Limpar qualquer estado anterior de viagem para garantir ida à seleção
                        try:
                            for k in [
                                'missao_etapa','viagem_diario','viagem_destino','viagem_nave_id','viagem_nave',
                                'viagem_modulos','viagem_chegada_ok','viagem_pontuacao','missao_score','chegada_ok',
                                'missao_feedback','erro_modulos'
                            ]:
                                session.pop(k, None)
                            session['missao_etapa'] = 'selecao'
                            session['missao_destino'] = sala.get('destino')
                            session['missao_nave'] = sala.get('nave_id')
                        except Exception:
                            pass
                        logging.info(f"Login bem-sucedido para aluno {row[1]} na sala {codigo_sala}")
                        return redirect(url_for('missao.selecao_modulos', destino=sala['destino'], nave_id=sala['nave_id']))
                    else:
                        erro = 'Nome não encontrado na lista. Verifique e tente novamente.'
            except Exception:
                logging.exception("Erro ao validar login do aluno")
                erro = 'Ocorreu um erro ao validar seu login.'

    return render_template('aluno_login.html', sala=sala, erro=erro)


@aluno_bp.route('/aluno/entrar', methods=['GET', 'POST'])
def aluno_entrar():
    """Entrada do aluno por código da sala e nome; vai direto ao desafio.

    Validação estrita por nome exatamente como cadastrado na sala.
    (Sem normalização: exige acentos, espaços e maiúsculas/minúsculas iguais)
    """
    erro = None
    sala = None
    if request.method == 'POST':
        # Validação estrita: sem normalização

        codigo = request.form.get('codigo_sala', '').strip().upper()
        nome = request.form.get('nome_aluno', '').strip()
        logging.info(f"Tentativa de entrada para sala '{codigo}' com nome: '{nome}'")
        if not codigo or not nome:
            erro = 'Informe o código da sala e seu nome completo.'
        else:
            sala = db_manager.buscar_sala_por_codigo(codigo)
            if not sala:
                # Se não encontrar ativa, verificar se existe inativa para mensagem mais clara
                sala_any = db_manager.buscar_sala_por_codigo_any(codigo)
                if sala_any:
                    erro = 'Sala encontrada, porém está inativa. Peça ao professor para reabrir.'
                else:
                    erro = 'Sala não encontrada. Verifique o código e tente novamente.'
            else:
                try:
                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        # Validação estrita diretamente no banco: nome precisa existir exatamente na sala
                        nome_exato = (nome or '').strip()
                        logging.info(f"Nome digitado (estrito): '{nome_exato}'")
                        cursor.execute('SELECT id, nome FROM alunos WHERE sala_id = ? AND nome = ?', (sala['id'], nome_exato))
                        row = cursor.fetchone()
                        if row:
                            session['aluno_id'] = row[0]
                            session['nome_aluno'] = row[1]
                            session['sala_id'] = sala['id']
                            # Limpar qualquer estado anterior de viagem para garantir ida à seleção
                            try:
                                for k in [
                                    'missao_etapa','viagem_diario','viagem_destino','viagem_nave_id','viagem_nave',
                                    'viagem_modulos','viagem_chegada_ok','viagem_pontuacao','missao_score','chegada_ok',
                                    'missao_feedback','erro_modulos'
                                ]:
                                    session.pop(k, None)
                                session['missao_etapa'] = 'selecao'
                                session['missao_destino'] = sala.get('destino')
                                session['missao_nave'] = sala.get('nave_id')
                            except Exception:
                                pass
                            logging.info(f"Entrada bem-sucedida para aluno {row[1]} na sala {codigo}")
                            return redirect(url_for('missao.selecao_modulos', destino=sala['destino'], nave_id=sala['nave_id']))
                        else:
                            erro = 'Nome não encontrado na lista dessa sala. Digite exatamente como está no arquivo do professor.'
                except Exception:
                    logging.exception("Erro ao processar entrada do aluno")
                    erro = 'Ocorreu um erro ao processar sua entrada.'

    return render_template('aluno_entrar.html', erro=erro)


@aluno_bp.route('/modulo_underscore_espaco/<codigo_sala>')
def modulo_underscore_espaco(codigo_sala):
    """Página pós-login (Módulo_Underscore_Espaço).

    Exibe dados essenciais da sala e oferece retorno à página inicial.
    """
    sala = db_manager.buscar_sala_por_codigo(codigo_sala)
    if not sala:
        return "Sala não encontrada", 404
    if not session.get('aluno_id'):
        return redirect(url_for('aluno.aluno_login', codigo_sala=codigo_sala))
    nome_aluno = session.get('nome_aluno')
    return render_template('Modulo_Underscore_Espaco.html', sala=sala, nome_aluno=nome_aluno)


@aluno_bp.route('/api/registrar-resposta', methods=['POST'])
def api_registrar_resposta():
    """API para registrar respostas dos alunos.

    Em produção, recomenda-se validar formato e conteúdo da resposta,
    bem como associar o desafio à sala e ao aluno via chaves estritas.
    """
    try:
        data = request.get_json()
        aluno_id = data.get('aluno_id') or session.get('aluno_id')
        sala_id = data.get('sala_id') or session.get('sala_id')
        desafio_id = data.get('desafio_id') or 'resposta_desafio'
        resposta = data.get('resposta')

        correta = 1  # contar como concluído
        pontuacao = int(data.get('pontuacao') or 10)

        db_manager.registrar_resposta_desafio(
            aluno_id, sala_id, desafio_id, resposta, correta, pontuacao
        )

        return jsonify({'success': True, 'pontuacao': pontuacao})

    except Exception as e:
        logging.exception("Falha ao registrar resposta do aluno")
        return jsonify({'success': False, 'error': str(e)}), 400