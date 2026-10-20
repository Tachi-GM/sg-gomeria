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

// Variable para recordar la dirección del orden (ascendente o descendente)
let ordenAscendente = true;
let ultimaColumna = -1;

function ordenarTabla(nColumna, esNumero = false) {
    const tabla = document.querySelector(".tabla-remitos table");
    if (!tabla) return;
    const tbody = tabla.querySelector("tbody");
    
    // 1. Buscamos solo las filas de remito principales
    const filasRemito = Array.from(tbody.querySelectorAll("tr.fila-remito"));
    if (filasRemito.length <= 1) return;

    // 2. Alternamos dirección
    if (ultimaColumna === nColumna) {
        ordenAscendente = !ordenAscendente;
    } else {
        ordenAscendente = true;
        ultimaColumna = nColumna;
    }

    // 3. Emparejamos cada remito con su fila de detalle siguiente
    const pares = filasRemito.map(fila => ({
        remito: fila,
        detalle: fila.nextElementSibling
    }));

    // 4. Ordenamos las parejas basándonos en la fila de remito
    pares.sort((a, b) => {
        let celdaA = a.remito.children[nColumna];
        let celdaB = b.remito.children[nColumna];
        if (!celdaA || !celdaB) return 0;

        let selectA = celdaA.querySelector("select");
        let selectB = celdaB.querySelector("select");
        let textoA = selectA ? selectA.value : celdaA.innerText.trim();
        let textoB = selectB ? selectB.value : celdaB.innerText.trim();

        if (esNumero) {
            let numA = parseFloat(textoA.replace(/[^0-9,-]+/g, "").replace(",", ".")) || 0;
            let numB = parseFloat(textoB.replace(/[^0-9,-]+/g, "").replace(",", ".")) || 0;
            return ordenAscendente ? numA - numB : numB - numA;
        } else {
            return ordenAscendente 
                ? textoA.localeCompare(textoB) 
                : textoB.localeCompare(textoA);
        }
    });

    // 5. Volvemos a insertar ambos en orden: remito y luego su detalle
    pares.forEach(par => {
        tbody.appendChild(par.remito);
        if (par.detalle) tbody.appendChild(par.detalle);
    });
}

// Inicialización de la edición modal de remitos
document.addEventListener("DOMContentLoaded", () => {
    const modalElement = document.getElementById("modalEditarRemito");
    if (!modalElement) return;

    const modalInstance = new bootstrap.Modal(modalElement);
    const formEditar = document.getElementById("form-editar-remito");
    const inputId = document.getElementById("edit-id-trabajo");
    const inputFecha = document.getElementById("edit-fecha");
    const selectTipo = document.getElementById("edit-tipo");
    const inputRemito = document.getElementById("edit-remito");
    const hintRemito = document.getElementById("edit-remito-hint");
    const alertaError = document.getElementById("alerta-error-modal");

    let filaActual = null;

    function actualizarHint() {
        if (!hintRemito) return;
        if (selectTipo.value === "OI") {
            hintRemito.textContent = "OI: 5 dígitos numéricos (ej. 12345). Si ingresás menos, se completará con ceros.";
        } else {
            hintRemito.textContent = "OIB: Formato 00XXXX (4 dígitos tras el 00, ej. 001234).";
        }
    }

    if (selectTipo) {
        selectTipo.addEventListener("change", actualizarHint);
    }

    document.querySelectorAll(".btn-editar-remito").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            filaActual = btn.closest(".fila-remito");
            inputId.value = btn.dataset.id || "";
            selectTipo.value = btn.dataset.tipo || "OI";
            inputRemito.value = btn.dataset.remito || "";
            inputFecha.value = btn.dataset.fecha || "";
            actualizarHint();

            alertaError.classList.add("d-none");
            alertaError.textContent = "";
            modalInstance.show();
        });
    });

    if (formEditar) {
        formEditar.addEventListener("submit", (e) => {
            e.preventDefault();
            alertaError.classList.add("d-none");
            alertaError.textContent = "";

            const formData = new FormData(formEditar);

            fetch("/editar-remito", {
                method: "POST",
                body: formData
            })
            .then(res => res.json().then(data => ({ status: res.status, ok: res.ok, data })))
            .then(resultado => {
                if (!resultado.ok) {
                    alertaError.textContent = resultado.data.mensaje || "Error al actualizar remito.";
                    alertaError.classList.remove("d-none");
                    return;
                }

                // Actualizar la fila en el DOM
                if (filaActual) {
                    const btn = filaActual.querySelector(".btn-editar-remito");
                    if (btn) {
                        btn.dataset.tipo = resultado.data.tipo;
                        btn.dataset.remito = resultado.data.remito;
                        btn.dataset.fecha = resultado.data.fecha;
                    }
                    const celdaFecha = filaActual.querySelector(".celda-fecha");
                    const celdaRemito = filaActual.querySelector(".celda-remito");
                    if (celdaFecha) celdaFecha.textContent = resultado.data.fecha;
                    if (celdaRemito) celdaRemito.textContent = `${resultado.data.tipo} #${resultado.data.remito}`;
                }

                modalInstance.hide();
            })
            .catch(err => {
                console.error(err);
                alertaError.textContent = "Error de comunicación con el servidor. Intente nuevamente.";
                alertaError.classList.remove("d-none");
            });
        });
    }
});
