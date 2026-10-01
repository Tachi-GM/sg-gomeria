function toggleDetalle(fila) {
    const filaDetalle = fila.nextElementSibling;
    filaDetalle.classList.toggle('d-none');
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
        // Repintamos el color del select según el nuevo estado
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
        detalle: fila.nextElementSibling // Su fila-detalle correspondiente
    }));
    // 4. Ordenamos las parejas basándonos en la fila de remito
    pares.sort((a, b) => {
        let celdaA = a.remito.children[nColumna];
        let celdaB = b.remito.children[nColumna];
        // Si es la columna del select de Estado (columna 4):
        let selectA = celdaA.querySelector("select");
        let selectB = celdaB.querySelector("select");
        let textoA = selectA ? selectA.value : celdaA.innerText.trim();
        let textoB = selectB ? selectB.value : celdaB.innerText.trim();
        if (esNumero) {
            // Limpiamos $ , . y # para que quede solo el número
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