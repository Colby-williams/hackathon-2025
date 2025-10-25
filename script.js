document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.querySelector('.sidebar-toggle');
    const header = document.querySelector('header');
    if (toggleButton && header) {
        toggleButton.addEventListener('click', () => {
            toggleButton.classList.toggle('change');
            header.classList.toggle('collapsed');
        });
    }
});