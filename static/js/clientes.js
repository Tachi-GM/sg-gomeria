// === UTILIDADES ===

function toggleDetalle(fila) {
    const filaDetalle = fila.nextElementSibling;
    if (filaDetalle && filaDetalle.classList.contains('fila-detalle')) {
        filaDetalle.classList.toggle('d-none');
    }
}

function cambiarEstado(select, idTrabajo) {
    const nuevoEstado = select.value;
    fetch('/actualizar-estado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `id_trabajo=${idTrabajo}&estado=${encodeURIComponent(nuevoEstado)}`
    })
    .then(respuesta => {
        if (!respuesta.ok) throw new Error('No se pudo actualizar');
        select.classList.remove('select-pendiente', 'select-proceso', 'select-pagado');
        if (nuevoEstado === 'PENDIENTE') select.classList.add('select-pendiente');
        else if (nuevoEstado === 'EN PROCESO') select.classList.add('select-proceso');
        else select.classList.add('select-pagado');
    })
    .catch(err => {
        alert('Hubo un error al actualizar el estado. Probá de nuevo.');
        console.error(err);
    });
}

// === CHECKBOXES DE PAGO ===

function aplicarEstiloCheckPago(chk) {
    const fila = chk.closest('tr.fila-remito');
    if (!fila) return;
    if (chk.checked) {
        fila.classList.add('table-success');
        fila.classList.remove('table-warning');
    } else {
        fila.classList.remove('table-success');
    }
}

function inicializarCheckboxesPago() {
    document.querySelectorAll('.check-pago').forEach(chk => {
        aplicarEstiloCheckPago(chk);
        chk.addEventListener('change', function () {
            const idTrabajo = this.dataset.id;
            const nuevoEstado = this.checked ? 'PAGADO' : 'PENDIENTE';
            fetch('/actualizar-estado', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `id_trabajo=${idTrabajo}&estado=${encodeURIComponent(nuevoEstado)}`
            })
            .then(res => {
                if (!res.ok) throw new Error('Error del servidor');
                return res.json();
            })
            .then(data => {
                if (data.exito) {
                    this.dataset.estado = nuevoEstado;
                    this.title = nuevoEstado;
                    aplicarEstiloCheckPago(this);
                } else {
                    this.checked = !this.checked;
                    alert('No se pudo actualizar el estado. Intentá de nuevo.');
                }
            })
            .catch(err => {
                console.error(err);
                this.checked = !this.checked;
                alert('Error de comunicación. Intentá de nuevo.');
            });
        });
    });
}

// === ORDENAR TABLA ===

let ordenAscendente = true;
let ultimaColumna = -1;

function ordenarTabla(nColumna, esNumero = false) {
    const tabla = document.querySelector('.tabla-remitos table');
    if (!tabla) return;
    const tbody = tabla.querySelector('tbody');
    const filasRemito = Array.from(tbody.querySelectorAll('tr.fila-remito'));
    if (filasRemito.length <= 1) return;

    if (ultimaColumna === nColumna) {
        ordenAscendente = !ordenAscendente;
    } else {
        ordenAscendente = true;
        ultimaColumna = nColumna;
    }

    const pares = filasRemito.map(fila => ({
        remito: fila,
        detalle: fila.nextElementSibling
    }));

    pares.sort((a, b) => {
        const celdaA = a.remito.children[nColumna];
        const celdaB = b.remito.children[nColumna];
        if (!celdaA || !celdaB) return 0;
        const selectA = celdaA.querySelector('select');
        const selectB = celdaB.querySelector('select');
        const textoA = selectA ? selectA.value : celdaA.innerText.trim();
        const textoB = selectB ? selectB.value : celdaB.innerText.trim();
        if (esNumero) {
            const numA = parseFloat(textoA.replace(/[^0-9,-]+/g, '').replace(',', '.')) || 0;
            const numB = parseFloat(textoB.replace(/[^0-9,-]+/g, '').replace(',', '.')) || 0;
            return ordenAscendente ? numA - numB : numB - numA;
        }
        return ordenAscendente ? textoA.localeCompare(textoB) : textoB.localeCompare(textoA);
    });

    pares.forEach(par => {
        tbody.appendChild(par.remito);
        if (par.detalle) tbody.appendChild(par.detalle);
    });
}

// === MODAL EDITAR REMITO ===

function inicializarModalRemito() {
    const modalElement = document.getElementById('modalEditarRemito');
    if (!modalElement) return;

    const modalInstance = new bootstrap.Modal(modalElement);
    const formEditar = document.getElementById('form-editar-remito');
    const inputId = document.getElementById('edit-id-trabajo');
    const inputFecha = document.getElementById('edit-fecha');
    const selectTipo = document.getElementById('edit-tipo');
    const inputRemito = document.getElementById('edit-remito');
    const hintRemito = document.getElementById('edit-remito-hint');
    const alertaError = document.getElementById('alerta-error-modal');

    function actualizarHint() {
        if (!hintRemito) return;
        if (selectTipo.value === 'OI') {
            hintRemito.textContent = 'OI: 5 dígitos numéricos (ej. 12345). Si ingresás menos, se completará con ceros.';
        } else {
            hintRemito.textContent = 'OIB: Formato 00XXXX (4 dígitos tras el 00, ej. 001234).';
        }
    }

    if (selectTipo) selectTipo.addEventListener('change', actualizarHint);

    document.querySelectorAll('.btn-editar-remito').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            inputId.value = btn.dataset.id || '';
            selectTipo.value = btn.dataset.tipo || 'OI';
            inputRemito.value = btn.dataset.remito || '';
            inputFecha.value = btn.dataset.fecha || '';
            actualizarHint();
            alertaError.classList.add('d-none');
            alertaError.textContent = '';
            modalInstance.show();
        });
    });

    if (formEditar) {
        formEditar.addEventListener('submit', e => {
            e.preventDefault();
            alertaError.classList.add('d-none');
            alertaError.textContent = '';
            fetch('/editar-remito', { method: 'POST', body: new FormData(formEditar) })
            .then(res => res.json().then(data => ({ ok: res.ok, data })))
            .then(resultado => {
                if (!resultado.ok) {
                    alertaError.textContent = resultado.data.mensaje || 'Error al actualizar remito.';
                    alertaError.classList.remove('d-none');
                    return;
                }
                modalInstance.hide();
                location.reload();
            })
            .catch(() => {
                alertaError.textContent = 'Error de comunicación. Intentá de nuevo.';
                alertaError.classList.remove('d-none');
            });
        });
    }
}

// === VALIDACIÓN CUIT EN TIEMPO REAL ===

function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

function validarCuit(input) {
    const cuit = input.value.trim();
    const errDiv = input.parentElement.querySelector('.cuit-error');

    if (!cuit) {
        input.classList.remove('is-invalid');
        if (errDiv) errDiv.classList.add('d-none');
        return;
    }

    const payload = { cuit };
    const idCliente = input.dataset.idcliente;
    if (idCliente) payload.id_cliente = Number(idCliente);

    fetch('/clientes/validar-cuit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.exists) {
            input.classList.add('is-invalid');
            if (errDiv) {
                errDiv.textContent = data.message;
                errDiv.classList.remove('d-none');
            }
        } else {
            input.classList.remove('is-invalid');
            if (errDiv) errDiv.classList.add('d-none');
        }
    })
    .catch(err => console.error('Error validando CUIT:', err));
}

// === INICIALIZACIÓN GENERAL ===

document.addEventListener('DOMContentLoaded', () => {
    inicializarCheckboxesPago();
    inicializarModalRemito();

    // Validación CUIT en tiempo real (modales de edición)
    document.querySelectorAll('.cuit-input').forEach(inp => {
        inp.addEventListener('input', debounce(() => validarCuit(inp), 300));
    });
});
