import sqlite3
import secrets
from datetime import datetime, timedelta


class DatabaseManager:
    """Gerencia conexão e operações no banco SQLite.

    Notas:
    - Usa `db_path` como arquivo único do banco;
    - As operações são focadas em robustez e simplicidade para ambiente escolar;
    - Em produção, recomenda-se migração para um ORM (SQLAlchemy) e testes unitários.
    """
    def __init__(self, db_path='salas_virtuais.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de professores
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS professores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
                    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de salas virtuais
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS salas_virtuais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_sala TEXT UNIQUE NOT NULL,
                    professor_id INTEGER NOT NULL,
                    nome_sala TEXT NOT NULL,
                    destino TEXT NOT NULL,
                    nave_id TEXT NOT NULL,
                    desafios_json TEXT NOT NULL,
                    ativa BOOLEAN DEFAULT 1,
                    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_expiracao DATETIME,
                    -- A coluna abaixo pode já existir em bancos criados previamente
                    -- Mantemos a criação aqui para ambientes novos.
                    desafio_selecionado_index INTEGER,
                    FOREIGN KEY (professor_id) REFERENCES professores (id)
                )
            ''')
            
            # Tabela de alunos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alunos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sala_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    email TEXT,
                    progresso_json TEXT,
                    data_ingresso DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sala_id) REFERENCES salas_virtuais (id)
                )
            ''')
            
            # Tabela de respostas aos desafios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS respostas_desafios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id INTEGER NOT NULL,
                    sala_id INTEGER NOT NULL,
                    desafio_id TEXT NOT NULL,
                    resposta TEXT NOT NULL,
                    correta BOOLEAN,
                    pontuacao INTEGER,
                    data_resposta DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (aluno_id) REFERENCES alunos (id),
                    FOREIGN KEY (sala_id) REFERENCES salas_virtuais (id)
                )
            ''')
            
            conn.commit()

            # Garantir coluna de exclusão no ranking para alunos
            try:
                cursor.execute("PRAGMA table_info(alunos)")
                cols = [row[1] for row in cursor.fetchall()]
                if 'excluir_ranking' not in cols:
                    cursor.execute("ALTER TABLE alunos ADD COLUMN excluir_ranking INTEGER DEFAULT 0")
                    conn.commit()
            except Exception:
                pass

            # Garantir coluna de seleção de desafio na sala
            try:
                cursor.execute("PRAGMA table_info(salas_virtuais)")
                cols = [row[1] for row in cursor.fetchall()]
                if 'desafio_selecionado_index' not in cols:
                    cursor.execute("ALTER TABLE salas_virtuais ADD COLUMN desafio_selecionado_index INTEGER")
                    conn.commit()
            except Exception:
                pass
    
    def gerar_codigo_sala(self):
        """Gera um código único para a sala"""
        return secrets.token_hex(4).upper()
    
    def criar_professor(self, nome, email, senha):
        """Cria um novo professor no banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Em produção, usar bcrypt para hash de senha
            cursor.execute(
                "INSERT INTO professores (nome, email, senha_hash) VALUES (?, ?, ?)",
                (nome, email, senha)  # Em produção, usar hash seguro
            )
            conn.commit()
            return cursor.lastrowid
    
    def criar_sala_virtual(self, professor_id, nome_sala, destino, nave_id, desafios):
        """Cria uma nova sala virtual"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Garantir regra de exclusividade: somente uma sala ativa por vez
            try:
                cursor.execute('UPDATE salas_virtuais SET ativa = 0 WHERE ativa = 1')
            except Exception:
                pass
            codigo_sala = self.gerar_codigo_sala()
            data_expiracao = datetime.now() + timedelta(days=30)
            
            cursor.execute('''
                INSERT INTO salas_virtuais 
                (codigo_sala, professor_id, nome_sala, destino, nave_id, desafios_json, data_expiracao, ativa)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (codigo_sala, professor_id, nome_sala, destino, nave_id, desafios, data_expiracao, 1))
            
            conn.commit()
            return codigo_sala
    
    def buscar_sala_por_codigo(self, codigo_sala):
        """Busca uma sala pelo código"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, p.nome as professor_nome
                FROM salas_virtuais s
                LEFT JOIN professores p ON s.professor_id = p.id
                WHERE UPPER(s.codigo_sala) = UPPER(?) AND s.ativa = 1
            ''', (codigo_sala,))
            
            sala = cursor.fetchone()
            if sala:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, sala))
            return None

    def buscar_sala_por_codigo_any(self, codigo_sala):
        """Busca uma sala pelo código, incluindo inativas (uso administrativo/professor)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, p.nome as professor_nome
                FROM salas_virtuais s
                LEFT JOIN professores p ON s.professor_id = p.id
                WHERE UPPER(s.codigo_sala) = UPPER(?)
            ''', (codigo_sala,))
            sala = cursor.fetchone()
            if sala:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, sala))
            return None

    def buscar_sala_por_id(self, sala_id):
        """Busca uma sala pelo ID (inclui inativas), útil para sessão do aluno."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, p.nome as professor_nome
                FROM salas_virtuais s
                LEFT JOIN professores p ON s.professor_id = p.id
                WHERE s.id = ?
            ''', (sala_id,))
            sala = cursor.fetchone()
            if sala:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, sala))
            return None
    
    def adicionar_aluno(self, sala_id, nome, email=None):
        """Adiciona um aluno à sala"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO alunos (sala_id, nome, email, progresso_json)
                VALUES (?, ?, ?, ?)
            ''', (sala_id, nome, email, '{}'))
            
            conn.commit()
            return cursor.lastrowid
    
    def buscar_alunos_por_sala(self, sala_id):
        """Busca todos os alunos de uma sala"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, nome, email, progresso_json, data_ingresso
                FROM alunos 
                WHERE sala_id = ?
                ORDER BY data_ingresso DESC
            ''', (sala_id,))
            
            alunos = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, aluno)) for aluno in alunos]

    # --- Operações administrativas de salas (professor) ---
    def fechar_sala_por_codigo(self, codigo_sala):
        """Desativa (fecha) a sala pelo código."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE salas_virtuais SET ativa = 0 WHERE UPPER(codigo_sala) = UPPER(?)
            ''', (codigo_sala,))
            conn.commit()

    def reabrir_sala_por_codigo(self, codigo_sala):
        """Reativa (reabre) a sala pelo código."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE salas_virtuais SET ativa = 1 WHERE UPPER(codigo_sala) = UPPER(?)
            ''', (codigo_sala,))
            conn.commit()

    def reabrir_sala_exclusiva(self, codigo_sala):
        """Ativa somente a sala informada, desativando todas as demais."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE salas_virtuais SET ativa = 0')
            cursor.execute('UPDATE salas_virtuais SET ativa = 1 WHERE UPPER(codigo_sala) = UPPER(?)', (codigo_sala,))
            conn.commit()

    def excluir_sala_por_codigo(self, codigo_sala):
        """Exclui definitivamente a sala e seus dados relacionados (alunos e respostas)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Encontrar ID da sala
            cursor.execute('SELECT id FROM salas_virtuais WHERE UPPER(codigo_sala) = UPPER(?)', (codigo_sala,))
            row = cursor.fetchone()
            if not row:
                return False
            sala_id = row[0]
            # Excluir respostas e alunos vinculados
            cursor.execute('DELETE FROM respostas_desafios WHERE sala_id = ?', (sala_id,))
            cursor.execute('DELETE FROM alunos WHERE sala_id = ?', (sala_id,))
            # Excluir sala
            cursor.execute('DELETE FROM salas_virtuais WHERE id = ?', (sala_id,))
            conn.commit()
            return True

    def atualizar_destino_e_nave(self, codigo_sala, destino, nave_id):
        """Atualiza destino e nave da sala pelo código."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE salas_virtuais SET destino = ?, nave_id = ? WHERE UPPER(codigo_sala) = UPPER(?)
            ''', (destino, nave_id, codigo_sala))
            conn.commit()

    def atualizar_desafios_json(self, codigo_sala, desafios_json):
        """Atualiza o campo desafios_json da sala pelo código."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE salas_virtuais SET desafios_json = ? WHERE UPPER(codigo_sala) = UPPER(?)
            ''', (desafios_json, codigo_sala))
            conn.commit()

    def selecionar_desafio_index(self, codigo_sala, idx):
        """Define o índice do desafio selecionado para a sala."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE salas_virtuais SET desafio_selecionado_index = ? WHERE UPPER(codigo_sala) = UPPER(?)
            ''', (idx, codigo_sala))
            conn.commit()

    # --- Listagens de salas para dashboards ---
    def listar_salas_ativas(self):
        """Lista salas ativas com contagem de alunos e desafios."""
        with sqlite3.connect(self.db_path) as conn:
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
            result = []
            for r in rows:
                result.append(dict(zip(cols, r)))
            return result

    def listar_salas_inativas(self):
        """Lista salas inativas com contagem de alunos."""
        with sqlite3.connect(self.db_path) as conn:
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
            return [dict(zip(cols, r)) for r in rows]

    def obter_estatisticas_por_sala(self):
        """Retorna estatísticas agregadas por sala (tentativas, corretas, média de pontos, precisão)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id AS sala_id,
                       s.codigo_sala,
                       s.nome_sala,
                       s.ativa,
                       COALESCE(COUNT(r.id), 0) AS tentativas_total,
                       COALESCE(SUM(CASE WHEN r.correta = 1 THEN 1 ELSE 0 END), 0) AS corretas_total,
                       COALESCE(AVG(COALESCE(r.pontuacao, 0)), 0) AS media_pontuacao
                FROM salas_virtuais s
                LEFT JOIN respostas_desafios r ON r.sala_id = s.id
                GROUP BY s.id, s.codigo_sala, s.nome_sala, s.ativa
                ORDER BY s.data_criacao DESC
            ''')
            rows = cursor.fetchall()
            result = []
            for sala_id, codigo, nome, ativa, tent, corr, media in rows:
                precisao = int(round((corr / tent) * 100)) if tent else 0
                result.append({
                    'sala_id': sala_id,
                    'codigo_sala': codigo,
                    'nome_sala': nome,
                    'ativa': ativa,
                    'tentativas_total': tent,
                    'corretas_total': corr,
                    'media_pontuacao': float(media) if media is not None else 0.0,
                    'precisao_geral_pct': precisao
                })
            return result
    
    def registrar_resposta_desafio(self, aluno_id, sala_id, desafio_id, resposta, correta, pontuacao):
        """Registra uma resposta a um desafio"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO respostas_desafios 
                (aluno_id, sala_id, desafio_id, resposta, correta, pontuacao)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (aluno_id, sala_id, desafio_id, resposta, correta, pontuacao))
            
            conn.commit()
            return cursor.lastrowid

    # --- Ranking ---
    def obter_ranking_sala(self, sala_id, limit=50):
        """Retorna ranking de alunos por sala com total de pontos, tentativas e concluídos."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Detectar coluna de exclusão no ranking
            cursor.execute('PRAGMA table_info(alunos)')
            cols = [row[1] for row in cursor.fetchall()]
            exclude_col = 'excluir_ranking' if 'excluir_ranking' in cols else ('exclude_ranking' if 'exclude_ranking' in cols else None)

            base_sql = (
                "SELECT a.id AS aluno_id, a.nome AS nome, "
                "COALESCE(SUM(CASE WHEN r.correta = 1 THEN r.pontuacao ELSE 0 END), 0) AS total, "
                "COUNT(r.id) AS tentativas, "
                "COALESCE(SUM(CASE WHEN r.correta = 1 THEN 1 ELSE 0 END), 0) AS concluidos "
                "FROM alunos a "
                "LEFT JOIN respostas_desafios r ON r.aluno_id = a.id AND r.sala_id = a.sala_id "
                "WHERE a.sala_id = ? "
            )
            if exclude_col:
                base_sql += f"AND COALESCE(a.{exclude_col}, 0) = 0 "
            base_sql += "GROUP BY a.id, a.nome ORDER BY total DESC, a.nome ASC LIMIT ?"

            cursor.execute(base_sql, (sala_id, limit))
            rows = cursor.fetchall()
            return [{'id': r[0], 'nome': r[1], 'total': r[2], 'tentativas': r[3], 'concluidos': r[4]} for r in rows]

    def obter_ranking_salas_ativas(self, limit=100):
        """Ranking consolidado das salas ativas com total de pontos, tentativas e concluídos."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Detectar coluna de exclusão no ranking
            cursor.execute('PRAGMA table_info(alunos)')
            cols = [row[1] for row in cursor.fetchall()]
            exclude_col = 'excluir_ranking' if 'excluir_ranking' in cols else ('exclude_ranking' if 'exclude_ranking' in cols else None)

            base_sql = (
                "SELECT a.id AS aluno_id, a.nome AS nome, "
                "COALESCE(SUM(CASE WHEN r.correta = 1 THEN r.pontuacao ELSE 0 END), 0) AS total, "
                "COUNT(r.id) AS tentativas, "
                "COALESCE(SUM(CASE WHEN r.correta = 1 THEN 1 ELSE 0 END), 0) AS concluidos "
                "FROM alunos a "
                "JOIN salas_virtuais s ON s.id = a.sala_id AND s.ativa = 1 "
                "LEFT JOIN respostas_desafios r ON r.aluno_id = a.id AND r.sala_id = a.sala_id "
                "WHERE 1 = 1 "
            )
            if exclude_col:
                base_sql += f"AND COALESCE(a.{exclude_col}, 0) = 0 "
            base_sql += "GROUP BY a.id, a.nome ORDER BY total DESC, a.nome ASC LIMIT ?"

            cursor.execute(base_sql, (limit,))
            rows = cursor.fetchall()
            return [{'id': r[0], 'nome': r[1], 'total': r[2], 'tentativas': r[3], 'concluidos': r[4]} for r in rows]

    def obter_estatisticas_por_desafio(self, sala_id):
        """Agrupa respostas por desafio dentro da sala e calcula tentativas, corretas e média de pontuação."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT desafio_id,
                       COUNT(id) AS tentativas,
                       COALESCE(SUM(CASE WHEN correta = 1 THEN 1 ELSE 0 END), 0) AS corretas,
                       COALESCE(AVG(COALESCE(pontuacao, 0)), 0) AS media_pontuacao
                FROM respostas_desafios
                WHERE sala_id = ?
                GROUP BY desafio_id
                ORDER BY desafio_id ASC
                '''
            , (sala_id,))
            rows = cursor.fetchall()
            return [
                {
                    'desafio_id': r[0],
                    'tentativas': r[1],
                    'corretas': r[2],
                    'media_pontuacao': float(r[3]) if r[3] is not None else 0.0,
                    'precisao_pct': int(round((r[2] / r[1]) * 100)) if r[1] else 0
                }
                for r in rows
            ]


# Instância compartilhada
db_manager = DatabaseManager('C:\\Users\\ricardo.moretti\\CosmoCasa\\Cosmo-Casa\\salas_virtuais.db')
"""Camada de acesso a dados (SQLite) do Cosmo-Casa.

Fornece operações para professores e alunos:
- Salas virtuais: criar, atualizar destino/nave, fechar/reabrir, excluir;
- Alunos: adicionar, listar, ranking e estatísticas;
- Desafios: armazenados em JSON por sala (simplificado para esta versão).

Mantém a aplicação simples e portável, sem dependências de servidor externo.
"""