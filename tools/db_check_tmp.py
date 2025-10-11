import sqlite3, os
DB=r"C:\\Users\\ricardo.moretti\\CosmoCasa\\Cosmo-Casa\\salas_virtuais.db"
print('DB exists:', os.path.exists(DB))
conn=sqlite3.connect(DB)
cur=conn.cursor()
cur.execute("SELECT id, codigo_sala FROM salas_virtuais WHERE ativa=1 ORDER BY data_criacao DESC LIMIT 1")
s=cur.fetchone()
print('Sala ativa:', s)
sid=s[0] if s else None
cur.execute("SELECT COUNT(1), COALESCE(SUM(pontuacao),0) FROM respostas_desafios WHERE sala_id=?", (sid,))
print('Respostas/pontos:', cur.fetchone())
cur.execute("SELECT id, nome FROM alunos WHERE sala_id=? ORDER BY id LIMIT 1", (sid,))
a=cur.fetchone()
print('Primeiro aluno:', a)
cur.execute("SELECT COUNT(1) FROM alunos WHERE sala_id=? AND nome=?", (sid, 'Aluno Inexistente 123'))
print('Nome errado presente?', cur.fetchone()[0]>0)
nome_existente=a[1] if a else ''
cur.execute("SELECT COUNT(1) FROM alunos WHERE sala_id=? AND nome=?", (sid, nome_existente))
print('Nome existente confere?', cur.fetchone()[0]>0, '->', nome_existente)
conn.close()
