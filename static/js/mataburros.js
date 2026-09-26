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

function cambiarLista(numeroLista) {
    document.getElementById('tipo_lista').value = numeroLista;

    // Recorremos cada combobox de tarea y le reconstruimos la lista de opciones
    instanciasChoicesTareas.forEach(instancia => {
        const selectOriginal = instancia.passedElement.element; // el <select> real, escondido por Choices
        const valorActual = selectOriginal.value; // qué tenía elegido antes de redibujar

        const nuevasOpciones = Array.from(selectOriginal.querySelectorAll('option')).map(opcion => {
            const nombre = opcion.getAttribute('data-nombre');
            const esPlaceholder = opcion.value === "";
            const precio = parseFloat(opcion.getAttribute(`data-precio${numeroLista}`)) || 0;

            return {
                value: opcion.value,
                label: esPlaceholder ? nombre : `${nombre} — $${precio.toFixed(2)}`,
                disabled: esPlaceholder,
                selected: opcion.value === valorActual
            };
        });

        // Le pedimos a Choices que redibuje su lista con los nuevos precios
        instancia.setChoices(nuevasOpciones, 'value', 'label', true);
    });

    // Repintado de los botones L1/L2/L3 (esto no cambia)
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
    let total = 0;

    filas.forEach(fila => {
        const select = fila.querySelector('select');
        const cantidadInput = fila.querySelector('.input-cantidad');
        const opcionSeleccionada = select.options[select.selectedIndex];

        const precio = parseFloat(opcionSeleccionada.getAttribute(`data-precio${listaActual}`)) || 0;
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