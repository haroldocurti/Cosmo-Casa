# app.py
from flask import Flask, render_template
import random
from flask import Flask, render_template, request
# Inicializa a aplicação Flask
app = Flask(__name__)

# --- DEFINIÇÃO DAS ROTAS ---

# --- BANCO DE DADOS DAS NAVES (baseado na imagem fornecida) ---
# Os atributos foram adaptados para a mecânica do jogo.
NAVES_ESPACIAIS = {
    'falcon9': {
        'nome': 'Falcon 9 (Block 5)',
        'operador': 'EUA / SpaceX', #
        'imagem': 'falcon9.png',
        'descricao': 'Foguete de dois estágios com autonomia limitada pelo consumo de propelente. Excelente para cargas pesadas em órbita baixa.', #
        'capacidade_carga': 22.8, # Em toneladas, para LEO
        'perfil_missao': 'Dois Estágios' #
    },
    'pslv': {
        'nome': 'PSLV (variante XL)',
        'operador': 'Índia / ISRO', #
        'imagem': 'pslv.png',
        'descricao': 'Perfil de missão versátil com múltiplas queimas de estágio, ideal para destinos variados como órbitas polares.', #
        'capacidade_carga': 3.8, # Em toneladas, para LEO (versão XL)
        'perfil_missao': 'Múltiplas Queimas' #
    },
    'longmarch8a': {
        'nome': 'Long March-8A',
        'operador': 'China', #
        'imagem': 'longmarch8a.png',
        'descricao': 'Projetado para uma gama diversificada de órbitas, com longos períodos de inércia entre as queimas de estágio.', #
        'capacidade_carga': 9.8, # Em toneladas, para LEO
        'perfil_missao': 'Coasting Estendido' #
    },
    'gslv': {
        'nome': 'GSLV (Mk II)',
        'operador': 'Índia / ISRO', #
        'imagem': 'gslv.png',
        'descricao': 'Inclui estágio criogênico para inserção em órbitas mais altas, definindo uma autonomia complexa.', #
        'capacidade_carga': 2.5, # Em toneladas, para GTO
        'perfil_missao': 'Estágio Criogênico' #
    }
}

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
                'Distância': '~225 milhões km',
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