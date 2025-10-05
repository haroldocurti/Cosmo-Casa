# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
import json
import sqlite3
import os
from datetime import datetime, timedelta
import secrets
import threading

# Inicializa a aplicação Flask
app = Flask(__name__)
# Usa SECRET_KEY do ambiente em produção; mantém fallback para desenvolvimento
app.secret_key = os.getenv('SECRET_KEY', 'minha_nasa_minha_vida_secret_key_2024')

class DatabaseManager:
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
                JOIN professores p ON s.professor_id = p.id
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
                JOIN professores p ON s.professor_id = p.id
                WHERE UPPER(s.codigo_sala) = UPPER(?)
            ''', (codigo_sala,))
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

# Instância global do gerenciador de banco de dados
db_manager = DatabaseManager()


class JSONStore:
    """Armazenamento interno em JSON para dados essenciais do sistema."""
    def __init__(self, path='data.json'):
        self.path = path
        self._lock = threading.Lock()
        self._default = {
            'professores': [{'id': 1, 'nome': 'Professor'}],
            'salas': [],
            'progresso': {}
        }
        if not os.path.exists(self.path):
            self._save(self._default)

    def _load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return json.loads(json.dumps(self._default))

    def _save(self, data):
        with self._lock:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    # Salas
    def listar_salas(self):
        data = self._load()
        return data.get('salas', [])

    def listar_salas_por_atividade(self, ativa=True):
        return [s for s in self.listar_salas() if bool(s.get('ativa', True)) == bool(ativa)]

    def buscar_sala(self, codigo):
        c = (codigo or '').upper()
        for s in self.listar_salas():
            if (s.get('codigo') or '').upper() == c:
                return s
        return None

    def criar_sala(self, nome_sala, destino, nave_id, alunos=None):
        data = self._load()
        from random import choices
        import string
        codigo = ''.join(choices(string.ascii_uppercase + string.digits, k=8))
        nova = {
            'codigo': codigo,
            'nome_sala': nome_sala,
            'destino': destino,
            'nave_id': nave_id,
            'alunos': [{'nome': a} for a in (alunos or [])],
            'desafios': [],
            'desafio_selecionado_index': None,
            'ativa': True,
            'data_criacao': datetime.now().isoformat()[:19]
        }
        data['salas'].append(nova)
        self._save(data)
        return codigo

    def fechar_sala(self, codigo):
        data = self._load()
        for s in data.get('salas', []):
            if s.get('codigo') == codigo:
                s['ativa'] = False
        self._save(data)

    def reabrir_sala_unica(self, codigo):
        data = self._load()
        for s in data.get('salas', []):
            s['ativa'] = (s.get('codigo') == codigo)
        self._save(data)

    # Desafios
    def criar_desafio_para_sala(self, codigo, titulo, descricao):
        data = self._load()
        for s in data.get('salas', []):
            if s.get('codigo') == codigo:
                s.setdefault('desafios', []).append({'titulo': titulo, 'descricao': descricao})
                break
        self._save(data)

    def editar_desafio(self, codigo, idx, titulo, descricao):
        data = self._load()
        for s in data.get('salas', []):
            if s.get('codigo') == codigo:
                ds = s.setdefault('desafios', [])
                if 0 <= idx < len(ds):
                    ds[idx] = {'titulo': titulo, 'descricao': descricao}
                break
        self._save(data)

    def excluir_desafio(self, codigo, idx):
        data = self._load()
        for s in data.get('salas', []):
            if s.get('codigo') == codigo:
                ds = s.setdefault('desafios', [])
                if 0 <= idx < len(ds):
                    ds.pop(idx)
                break
        self._save(data)

    def selecionar_desafio(self, codigo, idx):
        data = self._load()
        for s in data.get('salas', []):
            if s.get('codigo') == codigo:
                ds = s.setdefault('desafios', [])
                if 0 <= idx < len(ds):
                    s['desafio_selecionado_index'] = idx
                break
        self._save(data)

json_store = JSONStore()


# --- DEFINIÇÃO DAS ROTAS ---

# --- CONSTANTES FÍSICAS PARA CÁLCULOS ---
GRAVIDADE_TERRA = 9.81  # m/s²
CONSTANTE_GRAVITACIONAL = 6.67430e-11  # m³/kg/s²
MASA_TERRA = 5.972e24  # kg
RAIO_TERRA = 6371000  # m

# --- BANCO DE DADOS DAS NAVES (com parâmetros de propulsão realistas) ---
NAVES_ESPACIAIS = {
    'falcon9': {
        'nome': 'Falcon 9',
        'operador': 'EUA / SpaceX',
        'imagem': 'Falcon9.png',
        'descricao': 'Foguete de dois estágios reutilizável com excelente relação empuxo-peso. Ideal para cargas pesadas em órbita baixa.',
        'capacidade_carga': 22.8,  # toneladas para LEO
        'perfil_missao': 'Dois Estágios',
        # Parâmetros de propulsão adicionados
        'empuxo_total': 7607,  # kN (1º estágio: 7.607 kN)
        'impulso_especifico': 282,  # segundos (vacuum)
        'massa_seca': 28.2,  # toneladas (dry mass)
        'massa_combustivel': 433.1,  # toneladas (propellant mass)
        'delta_v_total': 9300,  # m/s (total capability)
        'taxa_empuxo_peso': 1.8  # T/W ratio
    },
    'pslv': {
        'nome': 'PSLV',
        'operador': 'Índia / ISRO',
        'imagem': 'PSLV.jpg',
        'descricao': 'Foguete confiável com múltiplos estágios e capacidade de inserção em órbitas polares e sincronizadas com o sol.',
        'capacidade_carga': 3.8,  # toneladas para LEO
        'perfil_missao': 'Múltiplas Queimas',
        'empuxo_total': 4800,  # kN
        'impulso_especifico': 262,  # segundos
        'massa_seca': 18.5,  # toneladas
        'massa_combustivel': 230.0,  # toneladas
        'delta_v_total': 8200,  # m/s
        'taxa_empuxo_peso': 1.4
    },
    'longmarch8a': {
        'nome': 'Long-March8A',
        'operador': 'China',
        'imagem': 'foguete-longa-marcha.png',
        'descricao': 'Foguete de médio porte com capacidade para múltiplas órbitas e fases de coasting estendidas.',
        'capacidade_carga': 9.8,  # toneladas para LEO
        'perfil_missao': 'Coasting Estendido',
        'empuxo_total': 5800,  # kN
        'impulso_especifico': 275,  # segundos
        'massa_seca': 22.1,  # toneladas
        'massa_combustivel': 320.5,  # toneladas
        'delta_v_total': 8800,  # m/s
        'taxa_empuxo_peso': 1.6
    },
    'gslv': {
        'nome': 'GSLV',
        'operador': 'Índia / ISRO',
        'imagem': 'LVM3_M3.png',
        'descricao': 'Foguete com estágio criogênico superior para inserção precisa em órbitas de transferência geossíncronas.',
        'capacidade_carga': 2.5,  # toneladas para GTO
        'perfil_missao': 'Estágio Criogênico',
        'empuxo_total': 4200,  # kN
        'impulso_especifico': 295,  # segundos (estágio criogênico)
        'massa_seca': 16.8,  # toneladas
        'massa_combustivel': 198.7,  # toneladas
        'delta_v_total': 9500,  # m/s
        'taxa_empuxo_peso': 1.3
    }
}

# --- FUNÇÕES DE CÁLCULO DE PERFORMANCE ---
def calcular_delta_v(massa_seca, massa_combustivel, impulso_especifico):
    """
    Calcula o Delta-V usando a Equação de Foguete de Tsiolkovsky
    Δv = Isp * g0 * ln(m0/mf)
    
    Onde:
    - Isp: Impulso específico (segundos)
    - g0: Gravidade padrão na Terra (9.81 m/s²)
    - m0: Massa inicial (seca + combustível)
    - mf: Massa final (apenas seca)
    """
    massa_inicial = massa_seca + massa_combustivel
    massa_final = massa_seca
    
    if massa_final <= 0:
        return 0
    
    return impulso_especifico * GRAVIDADE_TERRA * math.log(massa_inicial / massa_final)

def calcular_distancia_maxima_sem_carga(nave, destino='leo'):
    """
    Calcula a distância máxima que um foguete pode alcançar sem carga útil
    considerando sua performance máxima (Delta-V total).
    
    Para órbitas: 
    - LEO: ~7800 m/s Delta-V necessário
    - GTO: ~10700 m/s Delta-V necessário
    - Lua: ~10800 m/s Delta-V necessário
    - Marte: ~13600 m/s Delta-V necessário
    """
    delta_v_disponivel = nave['delta_v_total']
    
    # Delta-V necessário para diferentes destinos (em m/s)
    requisitos_delta_v = {
        'leo': 7800,    # Órbita Terrestre Baixa
        'gto': 10700,   # Órbita de Transferência Geossíncrona
        'lua': 10800,   # Órbita Lunar/Trajetória Lua
        'marte': 13600  # Trajetória Marte
    }
    
    delta_v_necessario = requisitos_delta_v.get(destino.lower(), 7800)
    
    # Se o foguete tem Delta-V suficiente para o destino
    if delta_v_disponivel >= delta_v_necessario:
        # Calcular distância máxima baseada no Delta-V excedente
        delta_v_excedente = delta_v_disponivel - delta_v_necessario
        
        # Converter Delta-V excedente em distância adicional
        # (aproximação simplificada para órbitas)
        distancia_base = {
            'leo': 400,      # km de altitude
            'gto': 35786,    # km (órbita geoestacionária)
            'lua': 384400,   # km
            'marte': 225e6   # km (média)
        }
        
        distancia_adicional = (delta_v_excedente / 1000) * 10000  # Aproximação
        return distancia_base.get(destino.lower(), 0) + distancia_adicional
    
    # Se não tem Delta-V suficiente, calcular fração alcançável
    fracao_alcancavel = delta_v_disponivel / delta_v_necessario
    
    distancias_maximas = {
        'leo': 400 * fracao_alcancavel,
        'gto': 35786 * fracao_alcancavel,
        'lua': 384400 * fracao_alcancavel,
        'marte': 225e6 * fracao_alcancavel
    }
    
    return distancias_maximas.get(destino.lower(), 0)

def calcular_carga_maxima_para_destino(nave, destino, distancia_destino):
    """
    Calcula a carga máxima possível para um destino específico
    baseado na distância máxima sem carga.
    
    Usa a relação: carga_max = capacidade_nominal * (1 - (distancia_destino / distancia_max_sem_carga))
    """
    distancia_max_sem_carga = calcular_distancia_maxima_sem_carga(nave, destino)
    
    if distancia_max_sem_carga <= 0:
        return 0
    
    # Fator de redução baseado na distância
    fator_reducao = 1 - (distancia_destino / distancia_max_sem_carga)
    
    # Limitar entre 0 e 1
    fator_reducao = max(0, min(1, fator_reducao))
    
    # Capacidade nominal da nave (em kg)
    capacidade_nominal = nave['capacidade_carga'] * 1000  # Convertendo para kg
    
    return capacidade_nominal * fator_reducao

# --- BANCO DE DADOS DOS MÓDULOS (com imagens e observações para tooltips) ---
MODULOS_HABITAT = {
    'suporte_vida': {"nome": "Suporte à Vida", "massa": 800, "energia": 15, "agua": 50, 
                     "imagem": "suporte_vida.png", "obs": "Essencial. Conecta-se ao Habitacional, Sanitário e Produção de Alimentos."},
    'habitacional': {"nome": "Habitacional Privado", "massa": 200, "energia": 1, "agua": 5, 
                     "imagem": "habitacional.png", "obs": "Acomodações para a tripulação. Pode ser integrado com Lazer."},
    'alimentacao': {"nome": "Alimentação e Refeições", "massa": 300, "energia": 3, "agua": 20, 
                    "imagem": "alimentacao.png", "obs": "Área de preparo e consumo de alimentos."},
    'medico': {"nome": "Módulo Médico", "massa": 250, "energia": 2, "agua": 5, 
               "imagem": "medico.png", "obs": "Para emergências médicas e monitoramento da saúde da tripulação."},
    'exercicios': {"nome": "Exercícios", "massa": 400, "energia": 5, "agua": 2, 
                   "imagem": "exercicios.png", "obs": "Equipamentos para mitigar a perda de massa muscular e óssea."},
    'pesquisa': {"nome": "Trabalho e Pesquisa", "massa": 350, "energia": 4, "agua": 2, 
                 "imagem": "pesquisa.png", "obs": "Laboratório para condução de experimentos científicos."},
    'armazenamento': {"nome": "Armazenamento", "massa": 150, "energia": 0.5, "agua": 0, 
                      "imagem": "armazenamento.png", "obs": "Estoque de suprimentos, ferramentas e amostras."},
    'sanitario': {"nome": "Sanitário e Higiene", "massa": 250, "energia": 2, "agua": 30, 
                  "imagem": "sanitario.png", "obs": "Banheiro, chuveiro e sistemas de reciclagem de água."},
    'inflavel': {"nome": "Inflável Expansível", "massa": 500, "energia": 2, "agua": 5, 
                 "imagem": "inflavel.png", "obs": "Módulo de grande volume quando inflado, altamente versátil."},
    'airlock': {"nome": "Airlock", "massa": 300, "energia": 2, "agua": 2, 
                "imagem": "airlock.png", "obs": "Câmara de descompressão para atividades extraveiculares (EVAs)."},
    'hidroponia': {"nome": "Produção de Alimentos (Hidroponia)", "massa": 500, "energia": 8, "agua": 40, 
                   "imagem": "hidroponia.png", "obs": "Cultivo de plantas em ambiente controlado para suplementar a dieta."},
    'impressao3d': {"nome": "Impressão 3D/Manufatura", "massa": 300, "energia": 5, "agua": 2, 
                    "imagem": "impressao3d.png", "obs": "Fabricação de peças de reposição e ferramentas sob demanda."}
}

# --- BANCO DE DADOS DE EVENTOS ALEATÓRIOS ---
EVENTOS_ALEATORIOS = [
    {
        "nome": "Tempestade Solar",
        "descricao": "Uma onda de radiação atinge a nave. Módulos com baixa blindagem podem sofrer avarias.",
        "efeito": "risco_avaria_modulo"
    },
    {
        "nome": "Falha Mecânica Menor",
        "descricao": "Um subsistema apresenta uma pequena falha, consumindo recursos extras para reparo e causando um pequeno atraso.",
        "efeito": "atraso_e_consumo_extra"
    },
    {
        "nome": "Impacto de Micrometeoroide",
        "descricao": "Pequenos detritos espaciais colidem com o casco. A blindagem da nave é testada.",
        "efeito": "risco_perda_carga"
    },
    {
        "nome": "Surto de Energia",
        "descricao": "Uma flutuação nos sistemas de energia força um desvio de recursos para estabilização.",
        "efeito": "consumo_extra"
    },
    {
        "nome": "Tudo Calmo",
        "descricao": "A viagem prossegue sem incidentes. A equipe aproveita a calmaria para verificar os sistemas.",
        "efeito": "nenhum"
    },
    {
        "nome": "Navegação Otimizada",
        "descricao": "A equipe de voo encontra uma trajetória mais eficiente, economizando propelente e adiantando levemente a chegada.",
        "efeito": "bonus_economia"
    }
]

# --- DEFINIÇÃO DAS ROTAS ---

# Rota para a página inicial ('/') com endpoint 'index' para compatibilidade
@app.route('/', endpoint='index')
def tela_inicial():
    """Renderiza a tela inicial do jogo."""
    return render_template('index.html')

# Rota para a página de seleção de missão ('/selecao')
@app.route('/selecao')
def tela_selecao():
    """Renderiza a tela de seleção de destino."""
    missoes = {
        'lua': {
            'nome': 'Lua', 
            'imagem': 'lua.png',
            # ADIÇÃO: Descrição e stats para o card
            'descricao': 'A porta de entrada para a exploração espacial. Um ambiente conhecido, ideal para testar novos habitats e tecnologias com menor risco.',
            'stats': {
                'Distância': '384.400 km',
                'Duração Estimada': 'Curta (15 turnos)',
                'Riscos': 'Baixos'
            }
        },
        'marte': {
            'nome': 'Marte', 
            'imagem': 'marte.png',
            # ADIÇÃO: Descrição e stats para o card
            'descricao': 'O próximo grande salto da humanidade. Enfrente tempestades de poeira e um ambiente hostil em uma missão de longa duração.',
            'stats': {
                'Distância': '225 milhões km',
                'Duração Estimada': 'Longa (60 turnos)',
                'Riscos': 'Elevados'
            }
        },
        'exoplaneta': {
            'nome': 'Exoplaneta', 
            'imagem': 'Exoplaneta.png',
            # ADIÇÃO: Descrição e stats para o card
            'descricao': 'Uma jornada para as estrelas em busca de um novo lar. Desafios desconhecidos e extremos aguardam no primeiro habitat interestelar.',
            'stats': {
                'Distância': '500 anos-luz',
                'Duração Estimada': 'Extrema (250 turnos)',
                'Riscos': 'Desconhecidos'
            }
        }
    }
    return render_template('selecao.html', missoes=missoes, codigo_sala=request.args.get('codigo_sala'))

# NOVA ROTA: Tela para montar o transporte
@app.route('/montagem-transporte/<string:destino>')
def montagem_transporte(destino):
    """
    Renderiza a tela de seleção de naves, recebendo o destino como parâmetro.
    O destino pode ser 'lua' ou 'marte'.
    """
    print(f"Destino recebido: {destino.upper()}")
    # No futuro, o destino pode afetar quais naves estão disponíveis
    return render_template('montagem_transporte.html', naves=NAVES_ESPACIAIS, destino=destino, codigo_sala=request.args.get('codigo_sala'))

# NOVA ROTA: Tela para selecionar os módulos do habitat
@app.route('/selecao-modulos/<string:destino>/<string:nave_id>')
def selecao_modulos(destino, nave_id):
    """
    Renderiza a tela de seleção de módulos.
    Recebe o destino e o ID da nave escolhida.
    """
    # Busca os dados da nave selecionada no nosso "banco de dados"
    nave_selecionada = NAVES_ESPACIAIS.get(nave_id)
    if not nave_selecionada:
        # Lida com o caso de um ID de nave inválido
        return "Nave não encontrada!", 404

    # Passa todos os dados necessários para o template
    return render_template('selecao_modulos.html', 
                           destino=destino, 
                           nave=nave_selecionada, 
                           modulos=MODULOS_HABITAT,
                           codigo_sala=request.args.get('codigo_sala'))
    
# NOVA ROTA: Simula a viagem em turnos
@app.route('/viagem/<string:destino>/<string:nave_id>', methods=['POST'])
def viagem(destino, nave_id):
    """
    Processa a lista de módulos selecionados e simula a viagem.
    """
    # Pega a lista de IDs dos módulos enviados pelo formulário
    modulos_selecionados_ids = request.form.getlist('modulos_selecionados')
    
    # Busca os dados completos dos módulos selecionados
    modulos_a_bordo = {id: MODULOS_HABITAT[id] for id in modulos_selecionados_ids}
    
    # Busca os dados da nave
    nave = NAVES_ESPACIAIS.get(nave_id)

    # LÓGICA DE TURNOS ATUALIZADA
    if destino == 'marte':
        total_turnos = 60
    elif destino == 'exoplaneta':
        total_turnos = 250 # Uma viagem muito mais longa e perigosa!
    else: # O destino padrão é a Lua
        total_turnos = 15

    diario_de_bordo = []
    for turno_atual in range(1, total_turnos + 1):
        # Aumentamos a chance de um evento ocorrer em missões mais longas
        chance_evento = 0.8 if destino == 'exoplaneta' else 0.6
        
        if random.random() < chance_evento:
            evento = random.choice(EVENTOS_ALEATORIOS)
        else:
            evento = EVENTOS_ALEATORIOS[4] # "Tudo Calmo"
        
        diario_de_bordo.append({"turno": turno_atual, "evento": evento})
        
        if evento['efeito'] == 'risco_avaria_modulo' and modulos_a_bordo:
            modulo_avariado_id = random.choice(list(modulos_a_bordo.keys()))
            modulos_a_bordo[modulo_avariado_id]['status'] = 'Avariado'

    # Se a viagem for parte da criação de desafio para uma sala, gravar e redirecionar
    codigo_sala = request.args.get('codigo_sala') or request.form.get('codigo_sala')
    if codigo_sala:
        try:
            titulo = f"Missão {destino.capitalize()} — {nave['nome'] if nave else nave_id}"
            descricao = f"Missão planejada com {len(modulos_a_bordo)} módulos selecionados."
            json_store.criar_desafio_para_sala(codigo_sala, titulo, descricao)
        except Exception:
            pass
        return redirect(url_for('professor_dashboard'))

    return render_template('viagem.html', 
                           diario=diario_de_bordo,
                           destino=destino,
                           nave=nave,
                           modulos=modulos_a_bordo)

# --- EXECUÇÃO DO SERVIDOR ---



@app.route('/professor/dashboard')
def professor_dashboard():
    """Dashboard do professor usando JSONStore (salas ativas e inativas)."""
    ranking = []
    salas = []
    salas_inativas = []
    for s in json_store.listar_salas_por_atividade(True):
        salas.append({
            'codigo': s.get('codigo'),
            'nome_sala': s.get('nome_sala'),
            'destino': s.get('destino'),
            'nave_id': s.get('nave_id'),
            'aluno_count': len(s.get('alunos', [])),
            'data_criacao': s.get('data_criacao'),
            'desafios': s.get('desafios', []),
            'desafio_selecionado_index': s.get('desafio_selecionado_index')
        })
    for s in json_store.listar_salas_por_atividade(False):
        salas_inativas.append({
            'codigo': s.get('codigo'),
            'nome_sala': s.get('nome_sala'),
            'destino': s.get('destino'),
            'nave_id': s.get('nave_id'),
            'aluno_count': len(s.get('alunos', [])),
            'data_criacao': s.get('data_criacao')
        })
    return render_template('professor_dashboard.html', ranking=ranking, salas=salas, salas_inativas=salas_inativas)

@app.route('/professor/criar-desafio', methods=['POST'])
def professor_criar_desafio():
    """Cria um novo desafio a partir do dashboard do professor (placeholder)."""
    # Neste fluxo reformulado, o botão redireciona para /selecao.
    return redirect(url_for('tela_selecao'))

@app.route('/professor/sala/<codigo_sala>/desafio/criar', methods=['GET', 'POST'])
def professor_criar_desafio_para_sala(codigo_sala):
    """Cria um desafio placeholder no JSONStore e retorna ao dashboard."""
    try:
        json_store.criar_desafio_para_sala(codigo_sala, 'Novo desafio', 'Desafio criado a partir do dashboard.')
    except Exception:
        pass
    return redirect(url_for('professor_dashboard'))

@app.route('/professor/sala/fechar', methods=['POST'])
def professor_sala_fechar():
    """Fecha (desativa) uma sala ativa pelo código."""
    codigo_sala = request.form.get('codigo_sala')
    if not codigo_sala:
        return redirect(url_for('professor_dashboard'))
    try:
        json_store.fechar_sala(codigo_sala)
    except Exception:
        pass
    return redirect(url_for('professor_dashboard'))

@app.route('/professor/sala/reabrir', methods=['POST'])
def professor_sala_reabrir():
    """Reabre uma sala inativa e fecha as demais para manter uma ativa."""
    codigo_sala = request.form.get('codigo_sala')
    if not codigo_sala:
        return redirect(url_for('professor_dashboard'))
    try:
        json_store.reabrir_sala_unica(codigo_sala)
    except Exception:
        pass
    return redirect(url_for('professor_dashboard'))

@app.route('/professor/desafio/editar', methods=['POST'])
def professor_editar_desafio():
    """Edita título/descrição de um desafio pelo índice."""
    codigo_sala = request.form.get('codigo_sala')
    idx_raw = request.form.get('desafio_index')
    titulo = request.form.get('titulo', '').strip()
    descricao = request.form.get('descricao', '').strip()
    if not codigo_sala or idx_raw is None:
        return redirect(url_for('professor_dashboard'))
    try:
        idx = int(idx_raw)
    except ValueError:
        return redirect(url_for('professor_dashboard'))

    try:
        json_store.editar_desafio(codigo_sala, idx, titulo or f'Desafio {idx+1}', descricao or '')
    except Exception:
        pass
    return redirect(url_for('professor_dashboard'))

@app.route('/professor/desafio/excluir', methods=['POST'])
def professor_excluir_desafio():
    """Exclui um desafio de uma sala a partir do índice enviado."""
    codigo_sala = request.form.get('codigo_sala')
    idx_raw = request.form.get('desafio_index')
    if not codigo_sala or idx_raw is None:
        return redirect(url_for('professor_dashboard'))

    try:
        idx = int(idx_raw)
    except ValueError:
        return redirect(url_for('professor_dashboard'))

    try:
        json_store.excluir_desafio(codigo_sala, idx)
    except Exception:
        pass

    return redirect(url_for('professor_dashboard'))

@app.route('/professor/desafio/selecionar', methods=['POST'])
def professor_selecionar_desafio():
    """Seleciona um desafio da sala para que a descrição seja exibida."""
    codigo_sala = request.form.get('codigo_sala')
    idx_raw = request.form.get('desafio_index')
    if not codigo_sala or idx_raw is None:
        return redirect(url_for('professor_dashboard'))

    try:
        idx = int(idx_raw)
    except ValueError:
        return redirect(url_for('professor_dashboard'))

    try:
        json_store.selecionar_desafio(codigo_sala, idx)
    except Exception:
        pass

    return redirect(url_for('professor_dashboard'))

@app.route('/professor/criar-sala', methods=['POST'])
def professor_criar_sala():
    """Cria uma sala e faz upload de lista de alunos (.txt)."""
    nome_sala = request.form.get('nome_sala')
    arquivo = request.files.get('lista_alunos')

    if not nome_sala or not arquivo:
        return redirect(url_for('professor_dashboard'))

    try:
        # Desativar qualquer sala ativa existente para manter apenas uma ativa
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE salas_virtuais SET ativa = 0 WHERE ativa = 1')
            conn.commit()

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

        return redirect(url_for('professor_sala_detalhes', codigo_sala=codigo_sala))
    except Exception:
        return redirect(url_for('professor_dashboard'))

@app.route('/professor/ranking/excluir', methods=['POST'])
def professor_excluir_aluno_ranking():
    """Marca um aluno para ser excluído do ranking."""
    aluno_id = request.form.get('aluno_id')
    if not aluno_id:
        return redirect(url_for('professor_dashboard'))
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE alunos SET excluir_ranking = 1 WHERE id = ?', (aluno_id,))
            conn.commit()
    except Exception:
        pass
    return redirect(url_for('professor_dashboard'))

@app.route('/professor/sala/<codigo_sala>')
def professor_sala_detalhes(codigo_sala):
    """Detalhes da sala e links de acesso dos alunos via JSONStore."""
    s = json_store.buscar_sala(codigo_sala)
    if not s:
        return "Sala não encontrada", 404
    alunos = s.get('alunos', [])
    # Gerar link de acesso por aluno
    for aluno in alunos:
        base = url_for('aluno_login', codigo_sala=codigo_sala, _external=True)
        try:
            from urllib.parse import urlencode
            aluno['acesso_url'] = f"{base}?" + urlencode({'nome': aluno.get('nome', '')})
        except Exception:
            aluno['acesso_url'] = base
    sala_view = {
        'codigo_sala': s.get('codigo'),
        'nome_sala': s.get('nome_sala'),
        'destino': s.get('destino'),
        'nave_id': s.get('nave_id'),
        'data_criacao': s.get('data_criacao'),
        'ativa': s.get('ativa'),
        'alunos': alunos,
        'desafios': s.get('desafios', [])
    }
    return render_template('professor_sala_detalhes.html', sala=sala_view, alunos=alunos)

@app.route('/aluno/login/<codigo_sala>', methods=['GET', 'POST'])
def aluno_login(codigo_sala):
    """Login do aluno: valida se nome corresponde exatamente à lista."""
    sala = db_manager.buscar_sala_por_codigo(codigo_sala)
    if not sala:
        return "Sala não encontrada", 404

    erro = None
    if request.method == 'POST':
        nome_digitado = request.form.get('nome_aluno', '').strip()
        if not nome_digitado:
            erro = 'Digite seu nome completo.'
        else:
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, nome FROM alunos WHERE sala_id = ? AND nome = ?
                ''', (sala['id'], nome_digitado))
                row = cursor.fetchone()
                if row:
                    session['aluno_id'] = row[0]
                    session['nome_aluno'] = row[1]
                    # Redirecionar direto para o desafio (Seleção de Módulos) com base na sala
                    return redirect(url_for('selecao_modulos', destino=sala['destino'], nave_id=sala['nave_id']))
                else:
                    erro = 'Nome não encontrado na lista. Verifique e tente novamente.'

    return render_template('aluno_login.html', sala=sala, erro=erro)

@app.route('/aluno/entrar', methods=['GET', 'POST'])
def aluno_entrar():
    """Entrada do aluno via código da sala e nome; redireciona direto ao desafio."""
    erro = None
    sala = None
    if request.method == 'POST':
        import unicodedata

        def strip_accents(text: str) -> str:
            return ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')

        def normalize_name(text: str) -> str:
            return ' '.join(strip_accents(text).strip().split()).casefold()

        codigo = request.form.get('codigo_sala', '').strip().upper()
        nome = request.form.get('nome_aluno', '').strip()
        if not codigo or not nome:
            erro = 'Informe o código da sala e seu nome completo.'
        else:
            sala = db_manager.buscar_sala_por_codigo(codigo)
            if not sala:
                erro = 'Sala não encontrada. Verifique o código e tente novamente.'
            else:
                with sqlite3.connect(db_manager.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id, nome FROM alunos WHERE sala_id = ?', (sala['id'],))
                    alunos = cursor.fetchall()
                    nome_norm = normalize_name(nome)
                    row = next((r for r in alunos if normalize_name(r[1]) == nome_norm), None)
                    if row:
                        session['aluno_id'] = row[0]
                        session['nome_aluno'] = row[1]
                        session['sala_id'] = sala['id']
                        return redirect(url_for('selecao_modulos', destino=sala['destino'], nave_id=sala['nave_id']))
                    else:
                        erro = 'Nome não encontrado na lista dessa sala. Verifique acentos e espaços.'

    return render_template('aluno_entrar.html', erro=erro)

@app.route('/modulo_underscore_espaco/<codigo_sala>')
def modulo_underscore_espaco(codigo_sala):
    """Página pós-login (Módulo_Underscore_Espaço)."""
    sala = db_manager.buscar_sala_por_codigo(codigo_sala)
    if not sala:
        return "Sala não encontrada", 404
    # Guarda de sessão: exige aluno autenticado
    if not session.get('aluno_id'):
        return redirect(url_for('aluno_login', codigo_sala=codigo_sala))
    nome_aluno = session.get('nome_aluno')
    return render_template('Modulo_Underscore_Espaco.html', sala=sala, nome_aluno=nome_aluno)


@app.route('/api/registrar-resposta', methods=['POST'])
def api_registrar_resposta():
    """API para registrar respostas dos alunos"""
    try:
        data = request.get_json()
        aluno_id = data.get('aluno_id')
        sala_id = data.get('sala_id')
        desafio_id = data.get('desafio_id')
        resposta = data.get('resposta')
        
        # Lógica de correção simplificada
        correta = True  # Em produção, implementar lógica real
        pontuacao = 10  # Pontuação base
        
        db_manager.registrar_resposta_desafio(
            aluno_id, sala_id, desafio_id, resposta, correta, pontuacao
        )
        
        return jsonify({'success': True, 'pontuacao': pontuacao})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def criar_desafios_padrao(destino):
    """Cria desafios padrão baseados no destino"""
    if destino == 'lua':
        return [
            {
                'id': 'desafio_1',
                'titulo': 'Seleção de Módulos Essenciais',
                'descricao': 'Quais módulos são absolutamente necessários para uma missão lunar de 15 dias?',
                'tipo': 'multipla_escolha',
                'opcoes': ['Suporte à Vida', 'Habitacional', 'Exercícios', 'Todos os anteriores'],
                'resposta_correta': 3
            },
            {
                'id': 'desafio_2', 
                'titulo': 'Cálculo de Massa',
                'descricao': 'Se você adicionar 3 módulos de 200kg cada, qual será a massa total?',
                'tipo': 'numerico',
                'resposta_correta': 600
            }
        ]
    elif destino == 'marte':
        return [
            {
                'id': 'desafio_1',
                'titulo': 'Desafios de Longa Duração',
                'descricao': 'Quais são os principais desafios de uma missão a Marte comparada à Lua?',
                'tipo': 'texto',
                'dica': 'Considere duração, radiação e comunicação.'
            }
        ]
    else:
        return [
            {
                'id': 'desafio_1',
                'titulo': 'Tecnologias do Futuro',
                'descricao': 'Que tecnologias seriam necessárias para uma missão interestelar?',
                'tipo': 'texto'
            }
        ]

# --- EXECUÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host=host, port=port, debug=debug)