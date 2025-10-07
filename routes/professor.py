"""Blueprint administrativo de professor: dashboard e gestão de salas."""

import json
import sqlite3
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, Response

from services.db import db_manager


professor_bp = Blueprint('professor', __name__)


@professor_bp.route('/dashboard', endpoint='professor_dashboard')
def dashboard():
    """Dashboard do professor lendo apenas do SQLite (salas ativas e inativas)."""
    ranking = []
    salas = []
    salas_inativas = []
    estatisticas_salas = []

    # Salas ativas
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id, s.codigo_sala, s.nome_sala, s.destino, s.nave_id,
                       s.data_criacao, s.desafios_json, s.desafio_selecionado_index,
                       COUNT(a.id) AS aluno_count
                FROM salas_virtuais s
                LEFT JOIN alunos a ON a.sala_id = s.id
                WHERE s.ativa = 1
                GROUP BY s.id
                ORDER BY s.data_criacao DESC
            ''')
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            for r in rows:
                d = dict(zip(cols, r))
                try:
                    desafios = json.loads(d.get('desafios_json') or '[]')
                except Exception:
                    desafios = []
                salas.append({
                    'id': d.get('id'),
                    'codigo': d.get('codigo_sala'),
                    'nome_sala': d.get('nome_sala'),
                    'destino': d.get('destino'),
                    'nave_id': d.get('nave_id'),
                    'aluno_count': d.get('aluno_count') or 0,
                    'data_criacao': d.get('data_criacao'),
                    'desafios': desafios,
                    'desafio_selecionado_index': d.get('desafio_selecionado_index')
                })
    except Exception:
        pass

    # Salas inativas
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id, s.codigo_sala, s.nome_sala, s.destino, s.nave_id,
                       s.data_criacao, COUNT(a.id) AS aluno_count
                FROM salas_virtuais s
                LEFT JOIN alunos a ON a.sala_id = s.id
                WHERE s.ativa = 0
                GROUP BY s.id
                ORDER BY s.data_criacao DESC
            ''')
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            for r in rows:
                d = dict(zip(cols, r))
                salas_inativas.append({
                    'codigo': d.get('codigo_sala'),
                    'nome_sala': d.get('nome_sala'),
                    'destino': d.get('destino'),
                    'nave_id': d.get('nave_id'),
                    'aluno_count': d.get('aluno_count') or 0,
                    'data_criacao': d.get('data_criacao')
                })
    except Exception:
        pass

    # Popular ranking com base nas salas ativas
    try:
        if len(salas) == 1 and salas[0].get('id'):
            ranking = db_manager.obter_ranking_sala(salas[0]['id'], limit=50)
        elif len(salas) > 1:
            ranking = db_manager.obter_ranking_salas_ativas(limit=100)
    except Exception:
        logging.exception('Falha ao obter ranking')

    # Estatísticas agregadas por sala (ativas e inativas)
    try:
        estatisticas_salas = db_manager.obter_estatisticas_por_sala()
    except Exception:
        estatisticas_salas = []

    return render_template('professor_dashboard.html', ranking=ranking, salas=salas, salas_inativas=salas_inativas, estatisticas_salas=estatisticas_salas)


@professor_bp.route('/criar-desafio', methods=['POST'], endpoint='professor_criar_desafio')
def criar_desafio():
    """Cria um novo desafio a partir do dashboard do professor (placeholder)."""
    return redirect(url_for('tela_selecao'))


@professor_bp.route('/sala/<codigo_sala>/desafio/criar', methods=['GET', 'POST'], endpoint='professor_criar_desafio_para_sala')
def criar_desafio_para_sala(codigo_sala):
    """Cria um desafio simples diretamente no SQLite e retorna ao dashboard."""
    try:
        sala = db_manager.buscar_sala_por_codigo_any(codigo_sala)
        if sala:
            try:
                desafios = json.loads(sala.get('desafios_json') or '[]')
            except Exception:
                desafios = []
            desafios.append({
                'titulo': 'Novo desafio',
                'descricao': 'Desafio criado a partir do dashboard.'
            })
            db_manager.atualizar_desafios_json(codigo_sala, json.dumps(desafios, ensure_ascii=False))
    except Exception:
        pass
    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/sala/fechar', methods=['POST'], endpoint='professor_sala_fechar')
def sala_fechar():
    """Fecha (desativa) uma sala ativa pelo código."""
    codigo_sala = request.form.get('codigo_sala')
    if not codigo_sala:
        return redirect(url_for('professor.professor_dashboard'))
    try:
        db_manager.fechar_sala_por_codigo(codigo_sala)
    except Exception:
        logging.exception("Falha ao fechar sala")
    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/sala/reabrir', methods=['POST'], endpoint='professor_sala_reabrir')
def sala_reabrir():
    """Reabre uma sala inativa e fecha as demais para manter uma ativa."""
    codigo_sala = request.form.get('codigo_sala')
    if not codigo_sala:
        return redirect(url_for('professor.professor_dashboard'))
    try:
        # Garante apenas uma sala ativa: desativa todas e ativa a escolhida
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE salas_virtuais SET ativa = 0')
            cursor.execute('UPDATE salas_virtuais SET ativa = 1 WHERE UPPER(codigo_sala) = UPPER(?)', (codigo_sala,))
            conn.commit()
    except Exception:
        logging.exception("Falha ao reabrir sala")
    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/desafio/editar', methods=['POST'], endpoint='professor_editar_desafio')
def editar_desafio():
    """Edita título/descrição de um desafio pelo índice."""
    codigo_sala = request.form.get('codigo_sala')
    idx_raw = request.form.get('desafio_index')
    titulo = request.form.get('titulo', '').strip()
    descricao = request.form.get('descricao', '').strip()
    if not codigo_sala or idx_raw is None:
        return redirect(url_for('professor.professor_dashboard'))
    try:
        idx = int(idx_raw)
    except ValueError:
        return redirect(url_for('professor.professor_dashboard'))

    try:
        sala = db_manager.buscar_sala_por_codigo_any(codigo_sala)
        if not sala:
            return redirect(url_for('professor.professor_dashboard'))
        try:
            desafios = json.loads(sala.get('desafios_json') or '[]')
        except Exception:
            desafios = []
        if 0 <= idx < len(desafios):
            desafios[idx]['titulo'] = titulo or f'Desafio {idx+1}'
            desafios[idx]['descricao'] = descricao or ''
            db_manager.atualizar_desafios_json(codigo_sala, json.dumps(desafios, ensure_ascii=False))
    except Exception:
        pass
    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/desafio/excluir', methods=['POST'], endpoint='professor_excluir_desafio')
def excluir_desafio():
    """Exclui um desafio de uma sala a partir do índice enviado."""
    codigo_sala = request.form.get('codigo_sala')
    idx_raw = request.form.get('desafio_index')
    if not codigo_sala or idx_raw is None:
        return redirect(url_for('professor.professor_dashboard'))

    try:
        idx = int(idx_raw)
    except ValueError:
        return redirect(url_for('professor.professor_dashboard'))

    try:
        sala = db_manager.buscar_sala_por_codigo_any(codigo_sala)
        if sala:
            try:
                desafios = json.loads(sala.get('desafios_json') or '[]')
            except Exception:
                desafios = []
            if 0 <= idx < len(desafios):
                desafios.pop(idx)
                db_manager.atualizar_desafios_json(codigo_sala, json.dumps(desafios, ensure_ascii=False))
    except Exception:
        pass

    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/desafio/selecionar', methods=['POST'], endpoint='professor_selecionar_desafio')
def selecionar_desafio():
    """Seleciona um desafio da sala para que a descrição seja exibida."""
    codigo_sala = request.form.get('codigo_sala')
    idx_raw = request.form.get('desafio_index')
    if not codigo_sala or idx_raw is None:
        return redirect(url_for('professor.professor_dashboard'))

    try:
        idx = int(idx_raw)
    except ValueError:
        return redirect(url_for('professor.professor_dashboard'))

    try:
        db_manager.selecionar_desafio_index(codigo_sala, idx)
    except Exception:
        logging.exception("Falha ao selecionar desafio")

    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/criar-sala', methods=['POST'], endpoint='professor_criar_sala')
def criar_sala():
    """Cria uma sala e faz upload de lista de alunos (.txt)."""
    nome_sala = request.form.get('nome_sala')
    arquivo = request.files.get('lista_alunos')

    if not nome_sala or not arquivo:
        return redirect(url_for('professor.professor_dashboard'))

    try:
        # Desativar qualquer sala ativa existente para manter apenas uma ativa
        try:
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE salas_virtuais SET ativa = 0 WHERE ativa = 1')
                conn.commit()
        except Exception:
            logging.exception("Falha ao desativar salas ativas")

        # Ler nomes dos alunos do arquivo TXT
        conteudo = arquivo.read().decode('utf-8', errors='ignore')
        nomes = [n.strip() for n in conteudo.splitlines() if n.strip()]

        # Parâmetros padrão da sala (professor_id temporário)
        professor_id = 1
        destino = 'lua'
        nave_id = 'falcon9'
        desafios = json.dumps([])

        codigo_sala = db_manager.criar_sala_virtual(
            professor_id, nome_sala, destino, nave_id, desafios
        )

        # Buscar sala para obter id
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM salas_virtuais WHERE codigo_sala = ?', (codigo_sala,))
            sala_row = cursor.fetchone()
            sala_id = sala_row[0] if sala_row else None

        # Inserir alunos
        if sala_id:
            for nome in nomes:
                db_manager.adicionar_aluno(sala_id, nome)

        # Removida a sincronização com JSONStore: agora usamos apenas SQLite
        # Permanecer no dashboard após criação, sem redirecionar para detalhes
        return redirect(url_for('professor.professor_dashboard'))
    except Exception:
        logging.exception("Falha ao criar sala virtual")
        return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/ranking/excluir', methods=['POST'], endpoint='professor_excluir_aluno_ranking')
def excluir_aluno_ranking():
    """Marca um aluno para ser excluído do ranking."""
    aluno_id = request.form.get('aluno_id')
    if not aluno_id:
        return redirect(url_for('professor.professor_dashboard'))
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE alunos SET excluir_ranking = 1 WHERE id = ?', (aluno_id,))
            conn.commit()
    except Exception:
        pass
    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/sala/<codigo_sala>', endpoint='professor_sala_detalhes')
def sala_detalhes(codigo_sala):
    
    """Detalhes da sala e links de acesso dos alunos, lendo exclusivamente do SQLite."""
    print(f'Função sala_detalhes chamada para código: {codigo_sala}')  # Print de depuração
    # Tentar buscar pelo banco (inclui salas inativas)
    sala_db = db_manager.buscar_sala_por_codigo_any(codigo_sala)
    if sala_db:
        try:
            alunos = db_manager.buscar_alunos_por_sala(sala_db['id'])
        except Exception:
            alunos = []
        # Ranking e métricas por aluno
        try:
            ranking = db_manager.obter_ranking_sala(sala_db['id'], limit=500)
        except Exception:
            ranking = []
        stats_map = {r.get('id') or r.get('aluno_id'): r for r in ranking}
        for aluno in alunos:
            st = stats_map.get(aluno.get('id'))
            if st:
                aluno['tentativas'] = st.get('tentativas') or 0
                aluno['concluidos'] = st.get('concluidos') or 0
                aluno['total'] = st.get('total') or 0
                tent = aluno['tentativas'] or 0
                concl = aluno['concluidos'] or 0
                aluno['precisao_pct'] = int(round((concl / tent) * 100)) if tent else 0
            else:
                aluno['tentativas'] = 0
                aluno['concluidos'] = 0
                aluno['total'] = 0
                aluno['precisao_pct'] = 0
        # Gerar link de acesso por aluno
        for aluno in alunos:
            base = url_for('aluno.aluno_login', codigo_sala=codigo_sala, _external=True)
            try:
                from urllib.parse import urlencode
                aluno['acesso_url'] = f"{base}?" + urlencode({'nome': aluno.get('nome', '')})
            except Exception:
                aluno['acesso_url'] = base

        # Desafios do banco (JSON campo desafios_json)
        try:
            desafios = json.loads(sala_db.get('desafios_json') or '[]')
        except Exception:
            desafios = []

        # Estatísticas da turma e desempenho por desafio
        try:
            desempenho_desafios = db_manager.obter_estatisticas_por_desafio(sala_db['id'])
        except Exception:
            desempenho_desafios = []
        try:
            tentativas_total = sum((a.get('tentativas') or 0) for a in alunos)
            concluidos_total = sum((a.get('concluidos') or 0) for a in alunos)
            total_pontos = sum((a.get('total') or 0) for a in alunos)
            alunos_total = len(alunos)
            precisao_geral_pct = int(round((concluidos_total / tentativas_total) * 100)) if tentativas_total else 0
            media_pontos_aluno = (total_pontos / alunos_total) if alunos_total else 0.0
            media_pontos_por_tentativa = (total_pontos / tentativas_total) if tentativas_total else 0.0
            turma_stats = {
                'alunos_total': alunos_total,
                'tentativas_total': tentativas_total,
                'concluidos_total': concluidos_total,
                'precisao_geral_pct': precisao_geral_pct,
                'media_pontos_aluno': media_pontos_aluno,
                'media_pontos_por_tentativa': media_pontos_por_tentativa
            }
        except Exception:
            turma_stats = {
                'alunos_total': len(alunos),
                'tentativas_total': 0,
                'concluidos_total': 0,
                'precisao_geral_pct': 0,
                'media_pontos_aluno': 0.0,
                'media_pontos_por_tentativa': 0.0
            }

        sala_view = {
            'codigo_sala': sala_db.get('codigo_sala'),
            'nome_sala': sala_db.get('nome_sala'),
            'destino': sala_db.get('destino'),
            'nave_id': sala_db.get('nave_id'),
            'data_criacao': sala_db.get('data_criacao'),
            'ativa': sala_db.get('ativa'),
            'alunos': alunos,
            'desafios': desafios,
            'desafio_selecionado_index': sala_db.get('desafio_selecionado_index')
        }
        return render_template('professor_sala_detalhes.html', sala=sala_view, alunos=alunos, turma_stats=turma_stats, desempenho_desafios=desempenho_desafios)

    # Apenas SQLite
    return "Sala não encontrada", 404


@professor_bp.route('/desafio/registrar', endpoint='professor_registrar_desafio')
def registrar_desafio():
    codigo_sala = request.args.get('codigo_sala')
    destino = request.args.get('destino')
    nave_id = request.args.get('nave_id')
    if not codigo_sala or not destino or not nave_id:
        return redirect(url_for('professor.professor_dashboard'))
    try:
        # Atualizar destino e nave no SQLite
        try:
            db_manager.atualizar_destino_e_nave(codigo_sala, destino, nave_id)
        except Exception:
            pass

        # Criar desafio básico vinculado à sala no SQLite
        titulo = f"Missão {destino.capitalize()} — {nave_id}"
        descricao = "Desafio criado pelo professor com seleção de destino e foguete."
        try:
            sala = db_manager.buscar_sala_por_codigo_any(codigo_sala)
            if sala:
                try:
                    desafios = json.loads(sala.get('desafios_json') or '[]')
                except Exception:
                    desafios = []
                desafios.append({'titulo': titulo, 'descricao': descricao})
                db_manager.atualizar_desafios_json(codigo_sala, json.dumps(desafios, ensure_ascii=False))
        except Exception:
            pass
    except Exception:
        pass
    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/sala/excluir', methods=['POST'], endpoint='professor_sala_excluir')
def sala_excluir():
    """Exclui definitivamente uma sala (permitido para salas inativas)."""
    codigo_sala = request.form.get('codigo_sala')
    if not codigo_sala:
        return redirect(url_for('professor.professor_dashboard'))
    try:
        # Excluir apenas se estiver inativa
        sala = db_manager.buscar_sala_por_codigo_any(codigo_sala)
        if sala and (sala.get('ativa') == 0):
            db_manager.excluir_sala_por_codigo(codigo_sala)
    except Exception:
        logging.exception('Falha ao excluir sala')
    return redirect(url_for('professor.professor_dashboard'))


@professor_bp.route('/sala/<codigo_sala>/exportar', endpoint='professor_sala_exportar')
def sala_exportar(codigo_sala):
    """Exporta CSV com alunos e respostas da sala."""
    try:
        sala = db_manager.buscar_sala_por_codigo_any(codigo_sala)
        if not sala:
            return redirect(url_for('professor.professor_dashboard'))
        # Coletar alunos e respostas
        with sqlite3.connect(db_manager.db_path) as conn:
            cur = conn.cursor()
            cur.execute('SELECT id, nome, email, data_ingresso FROM alunos WHERE sala_id = ? ORDER BY nome ASC', (sala['id'],))
            alunos = cur.fetchall()
            cur.execute('''
                SELECT r.id, r.aluno_id, a.nome, r.desafio_id, r.resposta, r.correta, r.pontuacao, r.data_resposta
                FROM respostas_desafios r
                LEFT JOIN alunos a ON a.id = r.aluno_id
                WHERE r.sala_id = ?
                ORDER BY r.data_resposta ASC
            ''', (sala['id'],))
            respostas = cur.fetchall()

        # Montar CSV
        lines = []
        lines.append('tipo,id_aluno,nome,email,desafio_id,resposta,correta,pontuacao,data\n')
        for a in alunos:
            lines.append(f"aluno,{a[0]},{a[1]},{a[2] or ''},,,,{a[3]}\n")
        for r in respostas:
            correta = '' if r[5] is None else ('1' if r[5] else '0')
            safe_resp = (r[4] or '').replace('\n', ' ').replace('\r', ' ')
            lines.append(f"resposta,{r[1]},{r[2]},{''},{r[3]},\"{safe_resp}\",{correta},{r[6] or 0},{r[7]}\n")
        csv_data = ''.join(lines)
        return Response(csv_data, mimetype='text/csv', headers={
            'Content-Disposition': f"attachment; filename=sala_{codigo_sala}.csv"
        })
    except Exception:
        logging.exception('Falha ao exportar CSV da sala')
        return redirect(url_for('professor.professor_dashboard'))