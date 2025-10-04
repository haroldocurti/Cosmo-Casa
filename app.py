# app.py
from flask import Flask, render_template
import random
from flask import Flask, render_template, request
# Inicializa a aplicação Flask
app = Flask(__name__)

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

# Rota para a página inicial ('/')
@app.route('/')
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
    return render_template('selecao.html', missoes=missoes)

# NOVA ROTA: Tela para montar o transporte
@app.route('/montagem-transporte/<string:destino>')
def montagem_transporte(destino):
    """
    Renderiza a tela de seleção de naves, recebendo o destino como parâmetro.
    O destino pode ser 'lua' ou 'marte'.
    """
    print(f"Destino recebido: {destino.upper()}")
    # No futuro, o destino pode afetar quais naves estão disponíveis
    return render_template('montagem_transporte.html', naves=NAVES_ESPACIAIS, destino=destino)

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
                           modulos=MODULOS_HABITAT)
    
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

    return render_template('viagem.html', 
                           diario=diario_de_bordo,
                           destino=destino,
                           nave=nave,
                           modulos=modulos_a_bordo)

# --- EXECUÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    app.run(debug=True)

@app.route('/performance-foguetes')
def performance_foguetes():
    """
    Rota para visualizar os cálculos de performance dos foguetes
    """
    resultados = {}
    
    for nave_id, nave in NAVES_ESPACIAIS.items():
        # Calcular performance para cada destino
        performance = {}
        
        for destino in ['leo', 'gto', 'lua', 'marte']:
            distancia_max = calcular_distancia_maxima_sem_carga(nave, destino)
            
            # Distâncias dos destinos em km
            distancias_destino = {
                'leo': 400,
                'gto': 35786,
                'lua': 384400,
                'marte': 225e6
            }
            
            carga_maxima = calcular_carga_maxima_para_destino(nave, destino, distancias_destino[destino])
            
            performance[destino] = {
                'distancia_maxima_km': round(distancia_max, 2),
                'carga_maxima_kg': round(carga_maxima, 2),
                'carga_maxima_ton': round(carga_maxima / 1000, 2)
            }
        
        resultados[nave_id] = {
            'info': nave,
            'performance': performance,
            'delta_v_calculado': calcular_delta_v(nave['massa_seca'], nave['massa_combustivel'], nave['impulso_especifico'])
        }
    
    return render_template('performance_foguetes.html', resultados=resultados)