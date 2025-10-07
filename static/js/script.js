// static/js/script.js (versão atualizada)

// Sistema de Gerenciamento de Módulos
class GerenciadorModulos {
    constructor() {
        this.modulosSelecionados = new Map(); // id -> quantidade
        this.massaTotal = 0;
        this.recursos = {
            energia: 0,
            agua: 0,
            capacidade: 0
        };
        this.eventHandlers = new Map();
    }
    
    // Adicionar módulo
    adicionarModulo(id, moduloData) {
        const quantidadeAtual = this.modulosSelecionados.get(id) || 0;
        this.modulosSelecionados.set(id, quantidadeAtual + 1);
        
        // Atualizar recursos
        this.massaTotal += moduloData.massa;
        this.recursos.energia += moduloData.energia;
        this.recursos.agua += moduloData.agua;
        
        this.notificarMudancas('moduloAdicionado', { id, moduloData, quantidade: quantidadeAtual + 1 });
        return quantidadeAtual + 1;
    }
    
    // Remover módulo
    removerModulo(id, moduloData) {
        const quantidadeAtual = this.modulosSelecionados.get(id) || 0;
        if (quantidadeAtual > 0) {
            this.modulosSelecionados.set(id, quantidadeAtual - 1);
            
            // Atualizar recursos
            this.massaTotal -= moduloData.massa;
            this.recursos.energia -= moduloData.energia;
            this.recursos.agua -= moduloData.agua;
            
            this.notificarMudancas('moduloRemovido', { id, moduloData, quantidade: quantidadeAtual - 1 });
            return quantidadeAtual - 1;
        }
        return 0;
    }
    
    // Obter quantidade de um módulo
    getQuantidade(id) {
        return this.modulosSelecionados.get(id) || 0;
    }
    
    // Obter todos os módulos selecionados
    getModulosSelecionados() {
        return Array.from(this.modulosSelecionados.entries()).map(([id, quantidade]) => ({
            id,
            quantidade
        }));
    }
    
    // Calcular utilização de capacidade
    getUtilizacaoCapacidade() {
        if (this.recursos.capacidade === 0) return 0;
        return (this.massaTotal / this.recursos.capacidade) * 100;
    }
    
    // Definir capacidade máxima
    setCapacidadeMaxima(capacidade) {
        this.recursos.capacidade = capacidade;
        this.notificarMudancas('capacidadeAtualizada', { capacidade });
    }
    
    // Sistema de eventos
    on(evento, callback) {
        if (!this.eventHandlers.has(evento)) {
            this.eventHandlers.set(evento, []);
        }
        this.eventHandlers.get(evento).push(callback);
    }
    
    notificarMudancas(evento, dados) {
        const handlers = this.eventHandlers.get(evento) || [];
        handlers.forEach(handler => handler(dados));
    }
    
    // Validar compatibilidade entre módulos
    validarCompatibilidade() {
        const problemas = [];
        
        // Verificar se há suporte de vida quando há módulos habitacionais
        const temHabitacional = this.getQuantidade('habitacional') > 0;
        const temSuporteVida = this.getQuantidade('suporte_vida') > 0;
        
        if (temHabitacional && !temSuporteVida) {
            problemas.push('Módulos habitacionais requerem Suporte à Vida');
        }
        
        // Verificar capacidade
        if (this.getUtilizacaoCapacidade() > 100) {
            problemas.push('Capacidade máxima excedida');
        }
        
        return problemas;
    }
}

// Instância global do gerenciador
const gerenciadorModulos = new GerenciadorModulos();
// Flag para habilitar/desabilitar a interface de monitoramento
const MONITORAMENTO_ATIVO = false;

document.addEventListener('DOMContentLoaded', function() {
    
    const spanMassaTotal = document.getElementById('massa-total');
    const spanCapacidadeCarga = document.getElementById('capacidade-carga');
    const barraProgresso = document.getElementById('barra-progresso');
    const hiddenInputsContainer = document.getElementById('modulos-selecionados-hidden');
    const botaoLancar = document.getElementById('botao-lancar');

    const capacidadeMaxima = parseInt(spanCapacidadeCarga.innerText.replace(' kg', ''));
    let massaAtual = 0;

    const modulosCards = document.querySelectorAll('.modulo-card');

    // Filtro por texto e expansão do container (somente na página de seleção de módulos)
    const filtroInput = document.getElementById('filtro-modulos');
    const containerModulos = document.getElementById('container-modulos');
    const toggleBtn = document.getElementById('toggle-modulos');

    if (filtroInput) {
        filtroInput.addEventListener('input', function() {
            const termo = this.value.trim().toLowerCase();
            modulosCards.forEach(card => {
                const nome = (card.querySelector('h4')?.textContent || '').toLowerCase();
                card.style.display = nome.includes(termo) ? '' : 'none';
            });
        });
    }

    if (toggleBtn && containerModulos) {
        toggleBtn.addEventListener('click', function() {
            containerModulos.classList.toggle('expanded');
            const expanded = containerModulos.classList.contains('expanded');
            this.innerText = expanded ? 'Reduzir' : 'Expandir';
            this.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        });
    }

function atualizarSumario() {
    calcularPerformanceMissao();
    spanMassaTotal.innerText = massaAtual;

    // CORREÇÃO: Usamos Math.min() para garantir que a porcentagem nunca passe de 100.
    const porcentagem = Math.min((massaAtual / capacidadeMaxima) * 100, 100);
    barraProgresso.style.width = porcentagem + '%';

    if (massaAtual > capacidadeMaxima) {
        spanMassaTotal.style.color = '#e74c3c'; // Vermelho (excesso)
        // A barra visualmente para em 100%, mas a cor indica o excesso.
        barraProgresso.style.backgroundColor = '#e74c3c';
        botaoLancar.disabled = true;
        botaoLancar.style.opacity = '0.5';
    } else if (massaAtual > capacidadeMaxima * 0.85) {
        spanMassaTotal.style.color = '#f39c12'; // Laranja (aviso)
        barraProgresso.style.backgroundColor = '#f39c12';
        botaoLancar.disabled = false;
        botaoLancar.style.opacity = '1';
    } else {
        spanMassaTotal.style.color = '#2ecc71'; // Verde (seguro)
        barraProgresso.style.backgroundColor = '#2ecc71';
        botaoLancar.disabled = false;
        botaoLancar.style.opacity = '1';
    }
    
    // Calcular e exibir informações de performance da missão
    calcularPerformanceMissao(massaAtual, capacidadeMaxima);
}

function calcularPerformanceMissao() {
    // Usar massa total do gerenciador
    const massaAtual = gerenciadorModulos.massaTotal;
    const capacidadeMaxima = parseInt(document.getElementById('capacidade-carga').innerText.replace(' kg', ''));
    const capacidadeMaximaElement = document.getElementById('capacidade-maxima');
    const duracaoMissaoElement = document.getElementById('duracao-missao');
    const explicacaoDuracaoElement = document.getElementById('explicacao-duracao');
    
    if (!capacidadeMaximaElement || !duracaoMissaoElement) return;
    
    // Cálculo da capacidade máxima baseado na eficiência da nave
    const eficienciaNave = 0.85; // 85% de eficiência (considerando reservas de segurança)
    const capacidadeReal = Math.floor(capacidadeMaxima * eficienciaNave);
    
    // Cálculo da duração estimada baseado no peso da carga
    const massaToneladas = massaAtual / 1000;
    const diasBase = {
        'lua': 30,
        'marte': 180,
        'exoplaneta': 365,
        'leo': 7
    };
    
    // Obter destino atual da URL ou do contexto da página
    let destino = 'lua'; // padrão
    const pathDestino = window.location.pathname.split('/');
    
    if (pathDestino.length >= 3) {
        destino = pathDestino[2]; // /selecao-modulos/lua/falcon9
    }
    
    const diasBaseMissao = diasBase[destino] || 30;
    const fatorAumento = 2.0; // cada tonelada aumenta 2 dias na missão
    
    const duracaoEstimada = Math.max(
        3, // mínimo de 3 dias para qualquer missão
        diasBaseMissao + (massaToneladas * fatorAumento)
    );
    
    // Calcular aumento percentual
    const aumentoPercentual = ((duracaoEstimada - diasBaseMissao) / diasBaseMissao * 100).toFixed(1);
    
    // Gerar explicação da alteração dos dias
    let explicacao = '';
    if (massaToneladas === 0) {
        explicacao = `Duração base para ${capitalizeFirst(destino)}: ${diasBaseMissao} dias (carga zero)`;
    } else if (duracaoEstimada > diasBaseMissao * 2) {
        explicacao = `Duração máxima atingida devido ao excesso de carga (${massaToneladas.toFixed(1)} ton)`;
    } else {
        explicacao = `Aumento de ${aumentoPercentual}% na duração devido ao peso da carga (${massaToneladas.toFixed(1)} ton)`;
    }
    
    // Atualizar os elementos com os cálculos
    capacidadeMaximaElement.textContent = `${capacidadeReal.toLocaleString()} kg (${(capacidadeReal / 1000).toFixed(1)} ton)`;
    
    if (massaAtual > capacidadeReal) {
        capacidadeMaximaElement.style.color = '#e74c3c';
    } else if (massaAtual > capacidadeReal * 0.8) {
        capacidadeMaximaElement.style.color = '#f39c12';
    } else {
        capacidadeMaximaElement.style.color = '#2ecc71';
    }
    
    duracaoMissaoElement.textContent = `${Math.round(duracaoEstimada)} dias`;
    
    // Atualizar explicação se o elemento existir
    if (explicacaoDuracaoElement) {
        explicacaoDuracaoElement.textContent = explicacao;
        explicacaoDuracaoElement.style.fontSize = '0.8em';
        explicacaoDuracaoElement.style.color = '#888';
        explicacaoDuracaoElement.style.marginTop = '2px';
    }
    
    // Cor da duração baseada na relação massa/duração
    const relacaoMassaDuracao = massaToneladas / (diasBaseMissao / 10);
    if (relacaoMassaDuracao > 0.8) {
        duracaoMissaoElement.style.color = '#e74c3c';
    } else if (relacaoMassaDuracao > 0.5) {
        duracaoMissaoElement.style.color = '#f39c12';
    } else {
        duracaoMissaoElement.style.color = '#2ecc71';
    }
}

    // Sistema para permitir múltiplos módulos do mesmo tipo (usando novo sistema)
    modulosCards.forEach(card => {
        const botao = card.querySelector('.botao-modulo');
        const massaModulo = parseInt(card.dataset.massa);
        const energiaModulo = parseInt(card.dataset.energia || 0);
        const aguaModulo = parseInt(card.dataset.agua || 0);
        const idModulo = card.dataset.id;
        const contadorElement = document.createElement('span');
        contadorElement.className = 'contador-modulo';
        contadorElement.style.marginLeft = '8px';
        contadorElement.style.fontSize = '0.9em';
        contadorElement.style.color = '#888';
        
        let quantidade = 0;
        
        // Adicionar contador ao botão
        botao.parentNode.insertBefore(contadorElement, botao.nextSibling);
        
        // Função para adicionar módulo
        function adicionarModuloHandler() {
            const moduloData = { massa: massaModulo, energia: energiaModulo, agua: aguaModulo };
            
            gerenciadorModulos.adicionarModulo(idModulo, moduloData);
            quantidade++;
            massaAtual = gerenciadorModulos.massaTotal;
            
            // Marcar card como selecionado e mostrar controles avançados
            card.classList.add('selecionado');
            
            // Cria um input escondido para enviar o ID do módulo
            const newInput = document.createElement('input');
            newInput.type = 'hidden';
            newInput.name = 'modulos_selecionados';
            newInput.value = idModulo;
            hiddenInputsContainer.appendChild(newInput);
            
            // Atualizar contador
            contadorElement.textContent = quantidade > 1 ? `×${quantidade}` : '';
            
            atualizarSumario();
        }
        
        // Função para remover módulo
        function removerModuloHandler() {
            if (quantidade > 0) {
                const moduloData = { massa: massaModulo, energia: energiaModulo, agua: aguaModulo };
                gerenciadorModulos.removerModulo(idModulo, moduloData);
                quantidade--;
                massaAtual = gerenciadorModulos.massaTotal;
                
                // Remover um input escondido correspondente
                const inputs = hiddenInputsContainer.querySelectorAll(`input[value="${idModulo}"]`);
                if (inputs.length > 0) {
                    hiddenInputsContainer.removeChild(inputs[inputs.length - 1]);
                }
                
                if (quantidade === 0) {
                    card.classList.remove('selecionado');
                }
                
                // Atualizar contador
                contadorElement.textContent = quantidade > 1 ? `×${quantidade}` : '';
                
                atualizarSumario();
            }
        }
        
        // Adicionar event listeners
        botao.addEventListener('click', adicionarModuloHandler);
        
        const botaoAdicionar = card.querySelector('.botao-adicionar');
        const botaoRemover = card.querySelector('.botao-remover');
        
        botaoAdicionar.addEventListener('click', adicionarModuloHandler);
        botaoRemover.addEventListener('click', removerModuloHandler);
    });

    atualizarSumario();
    
    // Monitoramento desativado por solicitação
    if (MONITORAMENTO_ATIVO) {
        if (!document.querySelector('.monitoramento-section')) {
            criarInterfaceMonitoramento();
        }
        atualizarMonitoramento();
    }
});

// Função para criar interface de monitoramento
function criarInterfaceMonitoramento() {
    // Compatível com o HTML atual: usa .sumario-carga; fallback para container principal
    let sumarioContainer = document.querySelector('.sumario-carga');
    if (!sumarioContainer) {
        sumarioContainer = document.querySelector('.container-grande') || document.body;
    }
    
    // Criar seção de monitoramento
    const monitoramentoSection = document.createElement('div');
    monitoramentoSection.className = 'monitoramento-section';
    monitoramentoSection.innerHTML = `
        <h3>Monitoramento de Recursos</h3>
        <div class="recursos-grid">
            <div class="recurso-item">
                <span class="recurso-label">Energia Total:</span>
                <span class="recurso-valor" id="energia-total">0 kWh</span>
            </div>
            <div class="recurso-item">
                <span class="recurso-label">Água Total:</span>
                <span class="recurso-valor" id="agua-total">0 L</span>
            </div>
            <div class="recurso-item">
                <span class="recurso-label">Capacidade:</span>
                <span class="recurso-valor" id="utilizacao-capacidade">0%</span>
            </div>
        </div>
        
        <h4>Módulos Ativos</h4>
        <div class="modulos-ativos" id="modulos-ativos">
            <p class="nenhum-modulo">Nenhum módulo ativo</p>
        </div>
        
        <h4>Status do Sistema</h4>
        <div class="status-sistema" id="status-sistema">
            <div class="status-item status-ok">
                <span class="status-icon">✓</span>
                <span>Sistema OK</span>
            </div>
        </div>
    `;
    
    // Garantir que o container exista antes de anexar
    if (sumarioContainer && typeof sumarioContainer.appendChild === 'function') {
        sumarioContainer.appendChild(monitoramentoSection);
    }
}

// Função para atualizar monitoramento
function atualizarMonitoramento() {
    if (!MONITORAMENTO_ATIVO) return;
    // Atualizar recursos
    document.getElementById('energia-total').textContent = `${gerenciadorModulos.recursos.energia} kWh`;
    document.getElementById('agua-total').textContent = `${gerenciadorModulos.recursos.agua} L`;
    
    const utilizacao = gerenciadorModulos.getUtilizacaoCapacidade();
    document.getElementById('utilizacao-capacidade').textContent = `${utilizacao.toFixed(1)}%`;
    
    // Atualizar módulos ativos
    const modulosAtivos = document.getElementById('modulos-ativos');
    const modulos = gerenciadorModulos.getModulosSelecionados();
    
    if (modulos.length === 0) {
        modulosAtivos.innerHTML = '<p class="nenhum-modulo">Nenhum módulo ativo</p>';
    } else {
        modulosAtivos.innerHTML = modulos.map(modulo => 
            `<div class="modulo-ativo">
                <span class="modulo-nome">${modulo.id.replace('_', ' ').toUpperCase()}</span>
                <span class="modulo-quantidade">x${modulo.quantidade}</span>
            </div>`
        ).join('');
    }
    
    // Atualizar status do sistema
    atualizarStatusSistema();
}

// Função para atualizar status do sistema
function atualizarStatusSistema() {
    const statusSistema = document.getElementById('status-sistema');
    const problemas = gerenciadorModulos.validarCompatibilidade();
    
    if (problemas.length === 0) {
        statusSistema.innerHTML = `
            <div class="status-item status-ok">
                <span class="status-icon">✓</span>
                <span>Sistema OK - Todos os módulos compatíveis</span>
            </div>
        `;
    } else {
        statusSistema.innerHTML = problemas.map(problema => 
            `<div class="status-item status-erro">
                <span class="status-icon">⚠</span>
                <span>${problema}</span>
            </div>`
        ).join('');
    }
}

// Função auxiliar para capitalizar a primeira letra
function capitalizeFirst(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}