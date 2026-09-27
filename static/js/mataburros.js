// Guardamos referencias a las instancias de Choices para poder actualizarlas o destruirlas después
let instanciaChoicesEmpresa = null;
let instanciasChoicesTareas = [];

// Función auxiliar: convierte cualquier <select> en un combobox buscable
function crearChoicesParaSelect(select) {
    return new Choices(select, {
        searchEnabled: true,
        searchPlaceholderValue: 'Escribí para buscar...',
        noResultsText: 'No se encontró ninguna coincidencia',
        shouldSort: false // respeta el orden en el que vienen de la base de datos
    });
}

function agregarFilaTarea() {
    const contenedor = document.getElementById('contenedor-tareas');
    const plantilla = document.getElementById('plantilla-fila-tarea');

    // 1️⃣ Clonamos el contenido de la plantilla (nunca de una fila ya existente)
    const fragmento = plantilla.content.cloneNode(true);
    const nuevaFila = fragmento.querySelector('.fila-tarea');

    // 2️⃣ PRIMERO la insertamos en la página
    contenedor.appendChild(nuevaFila);

    // 3️⃣ RECIÉN AHORA tocamos su valor, cuando ya está "conectada" y visible
    const inputCantidad = nuevaFila.querySelector('.input-cantidad');
    inputCantidad.value = 1;

    // 4️⃣ Convertimos el <select> de esta fila en un combobox buscable
    const selectNuevo = nuevaFila.querySelector('select');
    const instancia = crearChoicesParaSelect(selectNuevo);
    instanciasChoicesTareas.push(instancia);

    calcularTotal();
}

function quitarFilaTarea() {
    const contenedor = document.getElementById('contenedor-tareas');
    const filas = contenedor.querySelectorAll('.fila-tarea');

    if (filas.length > 1) {
        // Destruimos la instancia de Choices de la última fila antes de borrarla del DOM
        const instanciaAEliminar = instanciasChoicesTareas.pop();
        if (instanciaAEliminar) instanciaAEliminar.destroy();

        contenedor.removeChild(filas[filas.length - 1]);
    }

    calcularTotal();
}

const COLUMNA_PRECIO = { 1: 'precio', 2: 'precio2', 3: 'precio3' };

function cambiarLista(numeroLista) {
    document.getElementById('tipo_lista').value = numeroLista;
    const columna = COLUMNA_PRECIO[numeroLista];

    instanciasChoicesTareas.forEach(instancia => {
        const selectOriginal = instancia.passedElement.element;
        const valorActual = selectOriginal.value.trim(); // .trim() por si quedó algún espacio de más

        const nuevasOpciones = [
            {
                value: "",
                label: "Selecciona una tarea realizada...",
                disabled: true,
                selected: valorActual === ""
            },
            ...TAREAS_DATA.map(tarea => {
                const precio = tarea[columna] || 0;
                return {
                    value: String(tarea.id_tarea),
                    label: `${tarea.nom_tar} — $${precio.toFixed(2)}`,
                    selected: String(tarea.id_tarea) === valorActual
                };
            })
        ];

        instancia.setChoices(nuevasOpciones, 'value', 'label', true);
    });

    document.querySelectorAll('.btn-lista').forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline-primary');
    });
    const botonActivo = document.getElementById(`btn-l${numeroLista}`);
    botonActivo.classList.remove('btn-outline-primary');
    botonActivo.classList.add('btn-primary');

    calcularTotal();
}

function modificarCantidad(boton, cambio) {
    const input = boton.parentElement.querySelector('.input-cantidad');
    let valorActual = parseInt(input.value) || 1;
    let nuevoValor = valorActual + cambio;
    if (nuevoValor >= 1) {
        input.value = nuevoValor;
    }
    calcularTotal();
}

function calcularTotal() {
    const filas = document.querySelectorAll('#contenedor-tareas .fila-tarea');
    const listaActual = document.getElementById('tipo_lista').value;
    const columna = COLUMNA_PRECIO[listaActual];
    let total = 0;

    filas.forEach(fila => {
        const select = fila.querySelector('select');
        const cantidadInput = fila.querySelector('.input-cantidad');

        const idSeleccionado = select.value.trim();
        const tarea = TAREAS_DATA.find(t => String(t.id_tarea) === idSeleccionado);

        const precio = tarea ? (tarea[columna] || 0) : 0;
        const cantidad = parseInt(cantidadInput.value) || 0;

        total += precio * cantidad;
    });

    document.getElementById('total-parcial').textContent =
        `$${total.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// Todo lo que necesita que la página ya esté cargada, va acá adentro
document.addEventListener('DOMContentLoaded', function () {
    // Combobox buscable para Empresa
    const selectEmpresa = document.getElementById('select-empresa');
    if (selectEmpresa) {
        instanciaChoicesEmpresa = crearChoicesParaSelect(selectEmpresa);
    }

    // Creamos la primera fila de tareas (antes estaba escrita a mano en el HTML)
    agregarFilaTarea();

    // Escuchamos cambios en cualquier select de tarea (incluidos los clonados)
    document.getElementById('contenedor-tareas').addEventListener('change', function (e) {
        if (e.target.tagName === 'SELECT') {
            calcularTotal();
        }
    });
});