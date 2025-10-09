import sys
import os
from urllib.parse import urlparse

# Garantir import do app
PROJECT_ROOT = r'C:\Users\ricardo.moretti\CosmoCasa\Cosmo-Casa'
sys.path.append(PROJECT_ROOT)

import sqlite3
from services.db import db_manager
from app import app


def get_active_room_and_student():
    conn = sqlite3.connect(db_manager.db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, codigo_sala, destino, nave_id FROM salas_virtuais WHERE ativa=1 ORDER BY data_criacao DESC LIMIT 1"
    )
    sala = cur.fetchone()
    if not sala:
        conn.close()
        return None, None
    sala_id, codigo, destino, nave_id = sala
    cur.execute("SELECT nome FROM alunos WHERE sala_id=? ORDER BY id LIMIT 1", (sala_id,))
    aluno = cur.fetchone()
    conn.close()
    return {
        'id': sala_id,
        'codigo': codigo,
        'destino': destino,
        'nave_id': nave_id
    }, (aluno[0] if aluno else None)


def main():
    app.testing = True
    client = app.test_client()

    print('=== Testes de aluno_entrar e selecao_modulos ===')

    # 1) Código/Nome inválidos devem ser rejeitados (sem redirecionar para selecao_modulos)
    resp = client.post('/aluno/entrar', data={
        'codigo_sala': 'INVALID123',
        'nome_aluno': 'Nome Qualquer'
    }, follow_redirects=False)
    print('POST /aluno/entrar inválido -> status:', resp.status_code)
    assert resp.status_code == 200, 'Deve permanecer na página com erro (200).'
    body = resp.get_data(as_text=True)
    assert ('Sala não encontrada' in body) or ('inativa' in body) or ('Nome não encontrado' in body), 'Deve mostrar mensagem de erro.'
    print('✔ Rejeição de código/nome inválidos confirmada.')

    # 2) Acesso direto à selecao_modulos sem sessão deve redirecionar
    resp = client.get('/selecao-modulos/lua/falcon9', follow_redirects=False)
    print('GET /selecao-modulos sem sessão -> status:', resp.status_code)
    assert resp.status_code in (301, 302), 'Sem sessão, deve redirecionar.'
    loc = resp.headers.get('Location', '')
    print('Redirect Location:', loc)
    assert ('/aluno/entrar' in loc) or (loc == '/'), 'Deve redirecionar para aluno_entrar ou página inicial.'
    print('✔ Proteção de acesso direto confirmada.')

    # 3) Fluxo válido com sala ativa e aluno existente deve redirecionar para selecao_modulos
    sala, aluno_nome = get_active_room_and_student()
    if not sala or not aluno_nome:
        print('⚠ Sem sala ativa ou aluno para teste. Pulei teste de fluxo válido.')
        return

    # 3a) Sala válida, mas nome inexistente deve ser rejeitado (ficar na página com erro)
    resp_bad_name = client.post('/aluno/entrar', data={
        'codigo_sala': sala['codigo'],
        'nome_aluno': 'Aluno Inexistente 123'
    }, follow_redirects=False)
    print('POST /aluno/entrar com nome inexistente -> status:', resp_bad_name.status_code)
    assert resp_bad_name.status_code == 200, 'Nome inválido manter na página com erro (200).'
    body_bad = resp_bad_name.get_data(as_text=True)
    assert ('Nome não encontrado' in body_bad) or ('Digite exatamente' in body_bad) or ('não encontrado na lista' in body_bad), 'Deve mostrar erro de nome inexistente.'
    print('✔ Rejeição de nome inexistente confirmada.')

    resp = client.post('/aluno/entrar', data={
        'codigo_sala': sala['codigo'],
        'nome_aluno': aluno_nome
    }, follow_redirects=False)
    print('POST /aluno/entrar válido -> status:', resp.status_code)
    assert resp.status_code in (301, 302), 'Com dados válidos, deve redirecionar.'
    loc = resp.headers.get('Location', '')
    print('Redirect Location:', loc)
    parsed = urlparse(loc)
    assert parsed.path.startswith('/selecao-modulos'), 'Deve redirecionar para selecao_modulos.'
    print('✔ Redirecionamento para selecao_modulos confirmado.')

    # 4) Com sessão ativa, acesso à selecao_modulos deve renderizar 200
    # Seguir o redirect para carregar a sessão do cliente
    resp_follow = client.post('/aluno/entrar', data={
        'codigo_sala': sala['codigo'],
        'nome_aluno': aluno_nome
    }, follow_redirects=True)
    assert resp_follow.status_code == 200, 'Follow redirects deve chegar na página de seleção.'
    body2 = resp_follow.get_data(as_text=True)
    assert ('Módulos Disponíveis' in body2) or ('Lançar Missão' in body2) or ('Montagem da Carga' in body2), 'Conteúdo de seleção deve estar presente.'
    print('✔ Renderização da selecao_modulos com sessão confirmada.')


if __name__ == '__main__':
    main()