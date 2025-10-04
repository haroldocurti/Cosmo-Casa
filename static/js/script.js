// static/js/script.js (versão atualizada)

document.addEventListener('DOMContentLoaded', function() {
    
    const spanMassaTotal = document.getElementById('massa-total');
    const spanCapacidadeCarga = document.getElementById('capacidade-carga');
    const barraProgresso = document.getElementById('barra-progresso');
    const hiddenInputsContainer = document.getElementById('modulos-selecionados-hidden');
    const botaoLancar = document.getElementById('botao-lancar');

    const capacidadeMaxima = parseInt(spanCapacidadeCarga.innerText.replace(' kg', ''));
    let massaAtual = 0;

    const modulosCards = document.querySelectorAll('.modulo-card');

function atualizarSumario() {
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
}

    modulosCards.forEach(card => {
        const botao = card.querySelector('.botao-modulo');
        const massaModulo = parseInt(card.dataset.massa);
        const idModulo = card.dataset.id;

        botao.addEventListener('click', function() {
            if (this.classList.contains('selecionado')) {
                // REMOVER
                massaAtual -= massaModulo;
                this.classList.remove('selecionado');
                this.innerText = 'Adicionar';
                // Remove o input escondido
                const inputToRemove = hiddenInputsContainer.querySelector(`input[value="${idModulo}"]`);
                if (inputToRemove) {
                    hiddenInputsContainer.removeChild(inputToRemove);
                }
            } else {
                // ADICIONAR
                massaAtual += massaModulo;
                this.classList.add('selecionado');
                this.innerText = 'Remover';
                // Cria um input escondido para enviar o ID do módulo
                const newInput = document.createElement('input');
                newInput.type = 'hidden';
                newInput.name = 'modulos_selecionados';
                newInput.value = idModulo;
                hiddenInputsContainer.appendChild(newInput);
            }
            atualizarSumario();
        });
    });

    atualizarSumario();
});