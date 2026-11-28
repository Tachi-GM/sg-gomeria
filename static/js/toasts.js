/**
 * Helper global para mostrar notificaciones Toast flotantes (arriba a la derecha).
 */
(function () {
    function normalizarTipo(categoria) {
        if (categoria === 'error' || categoria === 'danger') return 'danger';
        if (categoria === 'warning') return 'warning';
        if (categoria === 'info') return 'info';
        return 'success';
    }

    function iconoPorTipo(tipo) {
        if (tipo === 'danger') return '❌';
        if (tipo === 'warning') return '⚠️';
        if (tipo === 'info') return 'ℹ️';
        return '✅';
    }

    window.mostrarToast = function (mensaje, tipo = 'success') {
        const contenedor = document.getElementById('toast-container-global');
        if (!contenedor || typeof bootstrap === 'undefined') return;

        const tipoBs = normalizarTipo(tipo);
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-bg-${tipoBs} border-0 shadow`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');

        const cuerpo = document.createElement('div');
        cuerpo.className = 'd-flex';

        const texto = document.createElement('div');
        texto.className = 'toast-body fw-medium';
        texto.textContent = `${iconoPorTipo(tipoBs)} ${mensaje}`;

        const btnCerrar = document.createElement('button');
        btnCerrar.type = 'button';
        btnCerrar.className = `btn-close ${tipoBs === 'warning' ? '' : 'btn-close-white'} me-2 m-auto`;
        btnCerrar.setAttribute('data-bs-dismiss', 'toast');
        btnCerrar.setAttribute('aria-label', 'Cerrar');

        cuerpo.appendChild(texto);
        cuerpo.appendChild(btnCerrar);
        toastEl.appendChild(cuerpo);
        contenedor.appendChild(toastEl);

        const instancia = new bootstrap.Toast(toastEl, { delay: 3500 });
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
        instancia.show();
    };

    document.addEventListener('DOMContentLoaded', () => {
        const scriptFlash = document.getElementById('flash-messages-data');
        if (!scriptFlash) return;
        try {
            const mensajes = JSON.parse(scriptFlash.textContent || '[]');
            mensajes.forEach(([categoria, texto]) => {
                window.mostrarToast(texto, categoria);
            });
        } catch (err) {
            console.error('Error al leer mensajes flash:', err);
        }
    });
})();
