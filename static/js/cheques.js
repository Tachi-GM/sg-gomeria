// Cheques cargados desde el backend / base de datos
let checks = JSON.parse(document.getElementById('cheques-data').textContent);

const rows = document.getElementById('rows');
const modal = document.getElementById('modal');
const form = document.getElementById('form');

const money = n => new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n);
const esc = s => String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function claseSegunEstado(st) {
    if (st === 'Pendiente') return 'select-pendiente';
    if (st === 'Cobrado') return 'select-pagado';
    if (st === 'Rechazado') return 'bg-danger text-white';
    return '';
}

function render() {
    const q = document.getElementById('search').value.trim().toLowerCase();
    const status = document.getElementById('status-filter').value;
    const date = document.getElementById('date-filter').value;

    const shown = checks.filter(c => {
        const coincideTexto = !q || [c.numero, c.cliente, c.banco, c.endosado].some(v => (v || '').toLowerCase().includes(q));
        const coincideEstado = !status || c.estado === status;
        const coincideFecha = !date || c.fecha_pago === date;
        return coincideTexto && coincideEstado && coincideFecha;
    });

    rows.innerHTML = shown.map(c => {
        return `
        <tr>
            <td class="fw-bold text-primary">#${esc(c.numero)}</td>
            <td class="fw-bold">${esc(c.cliente)}</td>
            <td>${esc(c.banco)}</td>
            <td>${esc(c.fecha_emision)}</td>
            <td class="fw-medium">${esc(c.fecha_pago)}</td>
            <td class="text-end fw-bold text-dark">${money(Number(c.importe))}</td>
            <td class="text-secondary">${esc(c.endosado) || '<span class="text-muted small">&mdash;</span>'}</td>
            <td class="text-center">
                <select class="form-select form-select-sm select-estado ${claseSegunEstado(c.estado)}"
                        data-id="${c.id_cheque}"
                        onchange="cambiarEstadoCheque(this, ${c.id_cheque})">
                    <option value="Pendiente" ${c.estado === 'Pendiente' ? 'selected' : ''}>Pendiente</option>
                    <option value="Cobrado" ${c.estado === 'Cobrado' ? 'selected' : ''}>Cobrado</option>
                    <option value="Rechazado" ${c.estado === 'Rechazado' ? 'selected' : ''}>Rechazado</option>
                </select>
            </td>
            <td class="text-center">
                <button class="delete-btn" data-id="${c.id_cheque}" type="button" title="Eliminar cheque">
                    🗑️
                </button>
            </td>
        </tr>
        `;
    }).join('');

    document.getElementById('empty').style.display = shown.length ? 'none' : 'block';
    document.getElementById('count').textContent = `${shown.length} ${shown.length === 1 ? 'cheque' : 'cheques'}`;
    document.getElementById('total').textContent = checks.length;

    const pending = checks.filter(c => c.estado === 'Pendiente');
    document.getElementById('pending').textContent = pending.length;
    document.getElementById('amount').textContent = money(pending.reduce((sum, c) => sum + Number(c.importe), 0));
}

function cambiarEstadoCheque(select, idCheque) {
    const nuevoEstado = select.value;
    fetch('/actualizar-estado-cheque', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `id_cheque=${idCheque}&estado=${encodeURIComponent(nuevoEstado)}`
    })
    .then(res => {
        if (!res.ok) throw new Error('Error al actualizar');
        // Actualizar localmente en memoria
        const item = checks.find(c => c.id_cheque == idCheque);
        if (item) item.estado = nuevoEstado;
        // Repintar clase del select
        select.className = `form-select form-select-sm select-estado ${claseSegunEstado(nuevoEstado)}`;
        render();
    })
    .catch(err => {
        alert('No se pudo actualizar el estado del cheque.');
        console.error(err);
    });
}

// Eventos del modal
document.getElementById('new-check').onclick = () => modal.showModal();
document.getElementById('close').onclick = () => modal.close();
document.getElementById('cancel').onclick = () => modal.close();

// Filtros reactivos
['search', 'status-filter', 'date-filter'].forEach(id => {
    document.getElementById(id).addEventListener('input', render);
});

// Eliminar cheque
rows.addEventListener('click', e => {
    const btn = e.target.closest('[data-id].delete-btn');
    if (btn) {
        const idCheque = btn.dataset.id;
        if (!confirm('¿Estás seguro de que deseás eliminar este cheque?')) return;
        fetch('/eliminar-cheque', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `id_cheque=${idCheque}`
        })
        .then(res => {
            if (!res.ok) throw new Error('Error al eliminar');
            checks = checks.filter(c => c.id_cheque != idCheque);
            render();
        })
        .catch(err => alert('No se pudo eliminar el cheque.'));
    }
});

// Guardar nuevo cheque en BD
form.addEventListener('submit', e => {
    e.preventDefault();
    const formData = new FormData(form);
    fetch('/agregar-cheque', {
        method: 'POST',
        body: formData
    })
    .then(res => {
        if (!res.ok) throw new Error('Error al guardar');
        return res.json();
    })
    .then(nuevoCheque => {
        checks.unshift(nuevoCheque);
        form.reset();
        modal.close();
        render();
    })
    .catch(err => alert('Error al registrar el cheque en el sistema.'));
});

// Renderizado inicial
render();