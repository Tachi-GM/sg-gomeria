// === UTILIDADES ===

function toggleDetalle(fila) {
    const filaDetalle = fila.nextElementSibling;
    if (filaDetalle && filaDetalle.classList.contains('fila-detalle')) {
        filaDetalle.classList.toggle('d-none');
        if (!filaDetalle.classList.contains('d-none')) {
            filaDetalle.querySelectorAll('img[data-src]').forEach(img => {
                img.src = img.dataset.src;
                delete img.dataset.src;
            });
        }
    }
}

function cambiarEstado(select, idTrabajo) {
    const nuevoEstado = select.value;
    fetch('/actualizar-estado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'id_trabajo=' + encodeURIComponent(idTrabajo) + '&estado=' + encodeURIComponent(nuevoEstado)
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

// === CHECKBOXES DE PAGO: delegación para incluir filas cargadas por AJAX ===

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
    document.querySelectorAll('.check-pago').forEach(aplicarEstiloCheckPago);
    document.addEventListener('change', function (event) {
        const chk = event.target.closest('.check-pago');
        if (!chk) return;

        const idTrabajo = chk.dataset.id;
        const nuevoEstado = chk.checked ? 'PAGADO' : 'PENDIENTE';
        fetch('/actualizar-estado', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'id_trabajo=' + encodeURIComponent(idTrabajo) + '&estado=' + encodeURIComponent(nuevoEstado)
        })
        .then(res => {
            if (!res.ok) throw new Error('Error del servidor');
            return res.json();
        })
        .then(data => {
            if (data.exito) {
                chk.dataset.estado = nuevoEstado;
                chk.title = nuevoEstado;
                aplicarEstiloCheckPago(chk);
            } else {
                chk.checked = !chk.checked;
                alert('No se pudo actualizar el estado. Intentá de nuevo.');
            }
        })
        .catch(err => {
            console.error(err);
            chk.checked = !chk.checked;
            alert('Error de comunicación. Intentá de nuevo.');
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

    if (ultimaColumna === nColumna) ordenAscendente = !ordenAscendente;
    else {
        ordenAscendente = true;
        ultimaColumna = nColumna;
    }

    const pares = filasRemito.map(fila => ({ remito: fila, detalle: fila.nextElementSibling }));
    pares.sort((a, b) => {
        const celdaA = a.remito.children[nColumna];
        const celdaB = b.remito.children[nColumna];
        if (!celdaA || !celdaB) return 0;
        const textoA = celdaA.innerText.trim();
        const textoB = celdaB.innerText.trim();
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

// === CARGA PROGRESIVA DE REMITOS ===

function inicializarCargaRemitos() {
    document.addEventListener('click', async event => {
        const boton = event.target.closest('.btn-cargar-remitos');
        if (!boton) return;

        const offset = Number.parseInt(boton.dataset.offset || '0', 10);
        if (!Number.isInteger(offset) || offset < 0) return;

        const parametros = new URLSearchParams({
            offset: String(offset),
            periodo: boton.dataset.periodo || 'todos'
        });
        if (boton.dataset.idCliente) parametros.set('id_cliente', boton.dataset.idCliente);

        const textoOriginal = boton.textContent;
        boton.disabled = true;
        boton.textContent = 'Cargando...';

        try {
            const respuesta = await fetch('/clientes/remitos-pagina?' + parametros.toString());
            const datos = await respuesta.json();
            if (!respuesta.ok) throw new Error(datos.error || 'No se pudieron cargar los remitos.');

            const tbody = document.querySelector('.tabla-remitos tbody');
            if (!tbody) throw new Error('No se encontró la tabla de remitos.');
            tbody.insertAdjacentHTML('beforeend', datos.html);
            boton.dataset.offset = String(offset + datos.cantidad_cargada);

            if (!datos.hay_mas || datos.cantidad_cargada === 0) {
                boton.closest('.text-center').remove();
            } else {
                boton.disabled = false;
                boton.textContent = textoOriginal;
            }
        } catch (error) {
            console.error(error);
            boton.disabled = false;
            boton.textContent = textoOriginal;
            alert(error.message || 'Error de comunicación al cargar remitos.');
        }
    });
}

// === MODAL EDITAR REMITO: delegación para filas agregadas dinámicamente ===

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
        hintRemito.textContent = selectTipo.value === 'OI'
            ? 'OI: 5 dígitos numéricos (ej. 12345). Si ingresás menos, se completará con ceros.'
            : 'OIB: Formato 00XXXX (4 dígitos tras el 00, ej. 001234).';
    }

    if (selectTipo) selectTipo.addEventListener('change', actualizarHint);

    document.addEventListener('click', event => {
        const btn = event.target.closest('.btn-editar-remito');
        if (!btn) return;
        event.stopPropagation();
        inputId.value = btn.dataset.id || '';
        selectTipo.value = btn.dataset.tipo || 'OI';
        inputRemito.value = btn.dataset.remito || '';
        inputFecha.value = btn.dataset.fecha || '';
        actualizarHint();
        alertaError.classList.add('d-none');
        alertaError.textContent = '';
        modalInstance.show();
    });

    if (formEditar) {
        formEditar.addEventListener('submit', event => {
            event.preventDefault();
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
    inicializarCargaRemitos();

    document.querySelectorAll('.cuit-input').forEach(inp => {
        inp.addEventListener('input', debounce(() => validarCuit(inp), 300));
    });
});
