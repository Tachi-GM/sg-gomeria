// Guardamos referencias a las instancias de Choices para poder actualizarlas o destruirlas después
let instanciaChoicesEmpresa = null;
let instanciasChoicesTareas = [];

// Constantes
const TAREAS_DATA = JSON.parse(document.getElementById('tareas-data').textContent);
const COLUMNA_PRECIO = { 1: 'precio', 2: 'precio2', 3: 'precio3' };
const TASA_IVA = 1.21;
const CLIENTES_DATA = JSON.parse(document.getElementById('clientes-data').textContent);
let clienteSinIva = false;

function formatearPesos(valor) {
    return `$${valor.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

document.getElementById('select-empresa').addEventListener('change', function () {
    const cliente = CLIENTES_DATA.find(c => String(c.id_cliente) === this.value);
    clienteSinIva = cliente ? cliente.con_iva === 0 : false;
    document.getElementById('aviso-sin-iva').classList.toggle('d-none', !clienteSinIva);

    // Auto-vincular lista de precios del cliente (L1, L2, L3)
    if (cliente && cliente.lista_precios) {
        cambiarLista(cliente.lista_precios);
    } else {
        calcularTotal();
    }
});

// Ayuda y placeholders dinámicos según tipo de comprobante (OI vs OIB)
const selectTipo = document.getElementById('select-tipo');
const inputRemito = document.getElementById('input-remito');
const ayudaRemito = document.getElementById('ayuda-remito');

if (selectTipo && inputRemito) {
    selectTipo.addEventListener('change', function () {
        if (this.value === 'OI') {
            inputRemito.placeholder = 'Ej: 20213 (5 dígitos)';
            if (ayudaRemito) ayudaRemito.textContent = 'OI: 5 dígitos numéricos (ej. 12345)';
        } else if (this.value === 'OIB') {
            inputRemito.placeholder = 'Ej: 001234 (00 + 4 dígitos)';
            if (ayudaRemito) ayudaRemito.textContent = 'OIB: Comienza con 00 y 4 dígitos adicionales';
        }
    });
}

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
    if (botonActivo) {
        botonActivo.classList.remove('btn-outline-primary');
        botonActivo.classList.add('btn-primary');
    }

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

    if (clienteSinIva) {
        const totalFinal = total / TASA_IVA;
        document.getElementById('subtotal-parcial').textContent = formatearPesos(total);
        document.getElementById('iva-parcial').textContent = '-' + formatearPesos(total - totalFinal);
        document.getElementById('total-parcial').textContent = formatearPesos(totalFinal);
    } else {
        const neto = total / TASA_IVA;
        document.getElementById('subtotal-parcial').textContent = formatearPesos(neto);
        document.getElementById('iva-parcial').textContent = formatearPesos(total - neto);
        document.getElementById('total-parcial').textContent = formatearPesos(total);
    }
}

function validarFormularioRemito(e) {
    const errores = [];
    const inputRem = document.querySelector('[name="remito"]').value.trim();
    const tipoVal = document.getElementById('select-tipo') ? document.getElementById('select-tipo').value : 'OI';

    if (!inputRem) {
        errores.push('Falta el número de remito.');
    } else {
        if (tipoVal === 'OI' && inputRem.replace(/\D/g, '').length > 5) {
            errores.push('El remito OI no puede superar los 5 dígitos.');
        }
        if (tipoVal === 'OIB' && inputRem.startsWith('00') && inputRem.replace(/\D/g, '').length > 6) {
            errores.push('El remito OIB no puede superar los 6 dígitos totales.');
        }
    }

    if (!document.getElementById('select-empresa').value) {
        errores.push('Elegí un cliente.');
    }
    document.querySelectorAll('#contenedor-tareas .fila-tarea').forEach((fila, i) => {
        if (!fila.querySelector('select').value) {
            errores.push(`Elegí la tarea de la fila ${i + 1}.`);
        }
    });

    const caja = document.getElementById('errores-form');
    if (errores.length > 0) {
        e.preventDefault(); // frena el envío del formulario
        caja.innerHTML = errores.map(t => `<div>${t}</div>`).join('');
        caja.classList.remove('d-none');
        caja.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Todo lo que necesita que la página ya esté cargada, va acá adentro
document.addEventListener('DOMContentLoaded', function () {
    // Combobox buscable para Empresa
    const selectEmpresa = document.getElementById('select-empresa');
    if (selectEmpresa) {
        instanciaChoicesEmpresa = crearChoicesParaSelect(selectEmpresa);
    }

    // Creamos la primera fila de tareas
    agregarFilaTarea();

    // Escuchamos cambios en cualquier select de tarea (incluidos los clonados)
    document.getElementById('contenedor-tareas').addEventListener('change', function (e) {
        if (e.target.tagName === 'SELECT') {
            calcularTotal();
        }
    });
    document.getElementById('form-remito').addEventListener('submit', validarFormularioRemito);
});
