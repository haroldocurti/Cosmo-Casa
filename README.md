Cosmo-Casa — Projeto Educacional para Alunos e Professores

Resumo
- Simulador e ambiente didático para explorar missões espaciais, montagem de habitat e decisões de engenharia.
- Pensado para dois perfis: Professores (admin) gerenciam salas e desafios; Alunos participam com código e nome.
- Baseado em Flask + SQLite, com templates HTML e assets estáticos.

Arquitetura
- `app.py`: aplicação Flask principal, registra blueprints e rotas de apoio.
- `routes/`:
  - `professor.py`: dashboard, CRUD de salas, gestão de desafios, exportação CSV.
  - `aluno.py`: fluxo de entrada do aluno por código + nome e registro de respostas.
  - `missao.py`: seleção de nave/destino, montagem de módulos e simulação em turnos.
- `services/`:
  - `db.py`: camada de acesso a dados em SQLite (criar/buscar/atualizar entidades).
  - `data.py`: catálogos estáticos (naves, módulos, eventos aleatórios) usados na UI/simulação.
- `templates/`: páginas HTML para professor e aluno.
- `static/`: CSS/JS e imagens (`static/imagens`). Alias oferecido via `/static/images/*`.

Instalação e execução
1) Requisitos: Python 3.10+, pip.
2) Crie e ative um ambiente virtual (opcional):
   - Windows PowerShell: `python -m venv .venv && .venv\\Scripts\\Activate.ps1`
   - Linux/macOS: `python -m venv .venv && source .venv/bin/activate`
3) Instale dependências:
   - `pip install -r requirements.txt` (se disponível) ou `pip install flask werkzeug`
4) Execute o servidor:
   - `python app.py`
5) Acesse:
   - Professor: `http://localhost:5000/professor/dashboard`
   - Aluno: fluxo via código de sala (link fornecido pelo professor)

Perfis e fluxo
- Professor (admin):
  - Cria salas com lista de alunos e configura destino/nave.
  - Cria e edita desafios, seleciona o desafio em destaque.
  - Exporta CSV com cadastro e respostas.
  - Botão "Trocar senha" permanece visível para facilitar testes.
- Aluno:
  - Entra com código de sala e nome (normalização de acentos e espaços).
  - Responde desafios e acompanha progresso.

Banco de dados
- SQLite simples, mantido em `services/db.py`.
- Entidades típicas: salas_virtuais, alunos, respostas_desafios.
- Operações principais: criar/buscar/atualizar/excluir sala, adicionar aluno, ranking por sala.

Dados estáticos
- `services/data.py`: listas de naves (`NAVES_ESPACIAIS`), módulos (`MODULOS_HABITAT`) e eventos (`EVENTOS_ALEATORIOS`).
- Usados para construção de páginas e simulação.

Estilo e UI
- Top bar com fundo preto e botões de ação consistentes nas telas de professor.
- CSS centralizado em `static/css/style.css` para evitar estilos inline.

Desenvolvimento
- Estruture novas features em blueprints ou `services/*`.
- Mantenha `app.py` leve, apenas orquestrando.
- Use docstrings para explicar fluxos pedagógicos e responsabilidades.

Testes manuais rápidos
- Criar sala: dashboard → formulário → confirmar listagem.
- Selecionar destino/nave: registrar desafio → confirmar no detalhes da sala.
- Aluno entra: código + nome → página de módulo.
- Exportar CSV: detalhes da sala → exportar → verificar conteúdo.

Boas práticas
- Padronize nomes de variáveis e funções em português claro.
- Evite lógica pesada em templates; concentre no Python.
- Valide entradas de usuário (nome não vazio, código existente).

Sugestões de melhoria (UX alunos e professores)
- Alunos:
  - Barra de progresso por desafio e feedback visual de acertos/erros.
  - Dicas contextuais e exemplos práticos nos desafios.
  - Modo acessível: alto contraste e suporte a leitores de tela.
- Professores:
  - Clonar sala como template e reabrir com nova turma.
  - Banco de desafios reutilizáveis com tags (física, biologia, engenharia).
  - Painel de métricas: conclusão média, precisão, tempo por desafio.

Roadmap sugerido
- Autenticação de professor com múltiplos usuários (além de admin).
- Rubricas por desafio e comentários para alunos.
- Modo offline com sincronização posterior.
- Testes unitários para `services/db.py` e `routes/*`.

Contribuição
- Faça PRs pequenos e objetivos.
- Adicione docstrings e atualize este README quando alterar fluxos.