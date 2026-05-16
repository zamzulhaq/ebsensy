const header = document.querySelector('.site-header');
const menuToggle = document.querySelector('.menu-toggle');

if (header && menuToggle) {
    menuToggle.addEventListener('click', () => {
        const isOpen = header.classList.toggle('is-open');
        menuToggle.setAttribute('aria-expanded', String(isOpen));
    });

    header.querySelectorAll('.site-nav a').forEach((link) => {
        link.addEventListener('click', () => {
            header.classList.remove('is-open');
            menuToggle.setAttribute('aria-expanded', 'false');
        });
    });
}

document.querySelectorAll('.faq-list details').forEach((item) => {
    item.addEventListener('toggle', () => {
        if (!item.open) return;
        document.querySelectorAll('.faq-list details').forEach((other) => {
            if (other !== item) other.removeAttribute('open');
        });
    });
});
