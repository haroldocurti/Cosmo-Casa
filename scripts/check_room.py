import sqlite3
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_room.py <codigo_sala>")
        sys.exit(1)

    codigo = sys.argv[1]
    # Resolve caminho do banco relativo ao projeto
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(project_root, 'salas_virtuais.db')

    print('DB path:', db_path)
    print('Codigo sala:', codigo)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Consulta específica da sala
    cur.execute(
        "SELECT id, codigo_sala, nome_sala, ativa, data_criacao FROM salas_virtuais WHERE UPPER(codigo_sala)=UPPER(?)",
        (codigo,)
    )
    row = cur.fetchone()
    print('Match:', row)

    # Verificar integridade do professor vinculado (possível causa de JOIN vazio)
    cur.execute(
        "SELECT s.id, s.codigo_sala, s.professor_id, p.id AS prof_id, p.nome AS prof_nome "
        "FROM salas_virtuais s LEFT JOIN professores p ON s.professor_id = p.id "
        "WHERE UPPER(s.codigo_sala) = UPPER(?)",
        (codigo,)
    )
    join_row = cur.fetchone()
    print('Join check:', join_row)

    # Listagem recente para contexto
    cur.execute(
        "SELECT id, codigo_sala, nome_sala, ativa FROM salas_virtuais ORDER BY data_criacao DESC LIMIT 20"
    )
    print('Recent 20:', cur.fetchall())

    conn.close()

if __name__ == '__main__':
    main()