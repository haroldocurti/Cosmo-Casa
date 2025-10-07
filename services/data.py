"""Dados estáticos da aplicação (naves, módulos e eventos).

Mantém separação de responsabilidades, evitando inchar app.py.
"""

# --- BANCO DE DADOS DAS NAVES ESPACIAIS ---
NAVES_ESPACIAIS = {
    'falcon9': {
        'nome': 'Falcon 9',
        'operador': 'EUA / SpaceX',
        'imagem': 'Falcon9.png',
        'descricao': 'Foguete de dois estágios reutilizável com excelente relação empuxo-peso. Ideal para cargas pesadas em órbita baixa.',
        'capacidade_carga': 22.8,
        'perfil_missao': 'Dois Estágios',
        'empuxo_total': 7607,
        'impulso_especifico': 282,
        'massa_seca': 28.2,
        'massa_combustivel': 433.1,
        'delta_v_total': 9300,
        'taxa_empuxo_peso': 1.8
    },
    'pslv': {
        'nome': 'PSLV',
        'operador': 'Índia / ISRO',
        'imagem': 'PSLV.jpg',
        'descricao': 'Foguete confiável com múltiplos estágios e capacidade de inserção em órbitas polares e sincronizadas com o sol.',
        'capacidade_carga': 3.8,
        'perfil_missao': 'Múltiplas Queimas',
        'empuxo_total': 4800,
        'impulso_especifico': 262,
        'massa_seca': 18.5,
        'massa_combustivel': 230.0,
        'delta_v_total': 8200,
        'taxa_empuxo_peso': 1.4
    },
    'longmarch8a': {
        'nome': 'Long-March8A',
        'operador': 'China',
        'imagem': 'foguete-longa-marcha.png',
        'descricao': 'Foguete de médio porte com capacidade para múltiplas órbitas e fases de coasting estendidas.',
        'capacidade_carga': 9.8,
        'perfil_missao': 'Coasting Estendido',
        'empuxo_total': 5800,
        'impulso_especifico': 275,
        'massa_seca': 22.1,
        'massa_combustivel': 320.5,
        'delta_v_total': 8800,
        'taxa_empuxo_peso': 1.6
    },
    'gslv': {
        'nome': 'GSLV',
        'operador': 'Índia / ISRO',
        'imagem': 'LVM3_M3.png',
        'descricao': 'Foguete com estágio criogênico superior para inserção precisa em órbitas de transferência geossíncronas.',
        'capacidade_carga': 2.5,
        'perfil_missao': 'Estágio Criogênico',
        'empuxo_total': 4200,
        'impulso_especifico': 295,
        'massa_seca': 16.8,
        'massa_combustivel': 198.7,
        'delta_v_total': 9500,
        'taxa_empuxo_peso': 1.3
    }
}

# --- BANCO DE DADOS DOS MÓDULOS (com imagens e observações para tooltips) ---
MODULOS_HABITAT = {
    'suporte_vida': {"nome": "Suporte à Vida", "massa": 800, "energia": 15, "agua": 50,
                     "imagem": "suporte_vida.svg", "obs": "Essencial. Conecta-se ao Habitacional, Sanitário e Produção de Alimentos."},
    'habitacional': {"nome": "Habitacional Privado", "massa": 200, "energia": 1, "agua": 5,
                     "imagem": "Privado.svg", "obs": "Acomodações para a tripulação. Pode ser integrado com Lazer."},
    'alimentacao': {"nome": "Alimentação e Refeições", "massa": 300, "energia": 3, "agua": 20,
                    "imagem": "Cultura.svg", "obs": "Área de preparo e consumo de alimentos."},
    'medico': {"nome": "Módulo Médico", "massa": 250, "energia": 2, "agua": 5,
               "imagem": "Medicina.svg", "obs": "Para emergências médicas e monitoramento da saúde da tripulação."},
    'exercicios': {"nome": "Exercícios", "massa": 400, "energia": 5, "agua": 2,
                   "imagem": "Exercicio.svg", "obs": "Equipamentos para mitigar a perda de massa muscular e óssea."},
    'pesquisa': {"nome": "Trabalho e Pesquisa", "massa": 350, "energia": 4, "agua": 2,
                 "imagem": "Pesquisa.svg", "obs": "Laboratório para condução de experimentos científicos."},
    'armazenamento': {"nome": "Armazenamento", "massa": 150, "energia": 0.5, "agua": 0,
                      "imagem": "Armazenagem.svg", "obs": "Estoque de suprimentos, ferramentas e amostras."},
    'sanitario': {"nome": "Sanitário e Higiene", "massa": 250, "energia": 2, "agua": 30,
                  "imagem": "Sanitário.svg", "obs": "Banheiro, chuveiro e sistemas de reciclagem de água."},
    'inflavel': {"nome": "Inflável Expansível", "massa": 500, "energia": 2, "agua": 5,
                 "imagem": "Inflavel.svg", "obs": "Módulo de grande volume quando inflado, altamente versátil."},
    'airlock': {"nome": "Airlock", "massa": 300, "energia": 2, "agua": 2,
                "imagem": "AirLock.svg", "obs": "Câmara de descompressão para atividades extraveiculares (EVAs)."},
    'hidroponia': {"nome": "Produção de Alimentos (Hidroponia)", "massa": 500, "energia": 8, "agua": 40,
                   "imagem": "Hidroponia.svg", "obs": "Cultivo de plantas em ambiente controlado para suplementar a dieta."},
    'impressao3d': {"nome": "Impressão 3D/Manufatura", "massa": 300, "energia": 5, "agua": 2,
                    "imagem": "Impressora.svg", "obs": "Fabricação de peças de reposição e ferramentas sob demanda."}
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
"""Dados estáticos utilizados pela UI e simulação do Cosmo-Casa.

- `NAVES_ESPACIAIS`: catálogo com nome, imagem e notas educativas;
- `MODULOS_HABITAT`: módulos do habitat com descrição e atributos;
- `EVENTOS_ALEATORIOS`: eventos para simulação em turnos com efeitos.

Mantém o conteúdo pedagógico separado da lógica, permitindo evoluções
independentes e eventual internacionalização.
"""