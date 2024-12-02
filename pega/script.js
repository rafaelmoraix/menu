function carregarFormulario(url, containerId) {
    const container = document.getElementById(containerId);
    fetch(url)
        .then(response => response.text())
        .then(html => {
            container.innerHTML = html;
            container.style.display = 'block';
            container.querySelectorAll('.cancelbtn').forEach(btn => {
                btn.addEventListener('click', () => (container.style.display = 'none'));
            });
        })
        .catch(err => console.error('Erro ao carregar o formulário:', err));
}

document.querySelectorAll('[data-target]').forEach(item => {
    item.addEventListener('click', function (event) {
        event.preventDefault();
        const target = this.dataset.target;
        const url = `views/forms/${target}.html`;
        carregarFormulario(url, 'formulario-container');
    });
});

// Seleciona o link "Migrar Aluno"
const migrarAlunoLink = document.querySelector('a[data-target="formulario-mig-aluno"]');

// Adiciona um evento de clique ao link
migrarAlunoLink.addEventListener('click', (event) => {
  event.preventDefault(); // Impede o comportamento padrão do link

  // Chama a função carregarFormulario para carregar o formulário de migração de aluno
  carregarFormulario('views/f_migracao_aluno.html', 'formulario-container');
});