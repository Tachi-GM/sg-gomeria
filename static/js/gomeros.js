document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-movimiento");
  const formActionNuevo = form.action;
  const tipo = document.getElementById("tipo");
  const campoGomero = document.querySelector(".campo-gomero");
  const campoDestino = document.querySelector(".campo-destino");
  const campoAguinaldo = document.querySelector(".campo-aguinaldo");
  const selectorGomero = document.getElementById("id_gomero");
  const destino = document.getElementById("destino");
  const periodo = document.getElementById("periodo_aguinaldo");
  const ayuda = document.getElementById("ayuda-movimiento");
  const importe = document.getElementById("importe");
  const fecha = document.getElementById("fecha");
  const concepto = document.getElementById("concepto");
  const hiddenId = document.getElementById("id_movimiento");
  const botonGuardar = form.querySelector('button[type="submit"], button:not([type])');
  let botonCancelar = document.getElementById("cancelar-edicion-movimiento");
  if (!botonCancelar) {
    botonCancelar = document.createElement("button");
    botonCancelar.type = "button";
    botonCancelar.id = "cancelar-edicion-movimiento";
    botonCancelar.className = "btn btn-outline-secondary rounded-pill px-4 d-none";
    botonCancelar.textContent = "Cancelar edición";
    botonGuardar.parentElement.appendChild(botonCancelar);
  }

  // Sábados y domingos no se piden adelantos del sueldo: solo del aguinaldo.
  function esFinDeSemana() {
    if (!fecha.value) return false;
    const dia = new Date(fecha.value + "T00:00:00").getDay();  // 0 = domingo, 6 = sábado
    return dia === 0 || dia === 6;
  }

  function actualizarFormulario() {
    const esGasto = tipo.value === "GASTO_GENERAL";
    const esDescuento = tipo.value === "DESCUENTO_AGUINALDO";
    if (esGasto) destino.value = "NO_APLICA";
    else if (destino.value === "NO_APLICA" || !destino.value) destino.value = "SUELDO";
    if (esDescuento) destino.value = "AGUINALDO";
    if (tipo.value === "PAGO_SEMANAL") destino.value = "SUELDO";
    // Al corregir un movimiento (hiddenId con valor) no se toca el destino.
    const sinSueldo = hiddenId.value === "" && tipo.value === "ADELANTO" && esFinDeSemana();
    destino.querySelector('option[value="SUELDO"]').disabled = sinSueldo;
    if (sinSueldo) destino.value = "AGUINALDO";
    campoGomero.classList.toggle("d-none", esGasto);
    campoDestino.classList.toggle("d-none", esGasto || esDescuento);
    campoAguinaldo.classList.toggle("d-none", esGasto || (destino.value !== "AGUINALDO" && !esDescuento));
    selectorGomero.required = !esGasto;
    selectorGomero.disabled = esGasto;
    destino.required = !esGasto;
    periodo.required = !esGasto && (destino.value === "AGUINALDO" || esDescuento);
    if (esGasto) ayuda.textContent = "El gasto queda en la cuenta general y no modifica ningún sueldo.";
    else if (esDescuento) ayuda.textContent = "Registrá un descuento efectivamente aplicado al aguinaldo. No puede superar el saldo pendiente.";
    else if (sinSueldo) ayuda.textContent = "Los sábados y domingos solo se pide del aguinaldo: el sueldo se cobra completo el sábado.";
    else if (destino.value === "AGUINALDO") ayuda.textContent = "El adelanto queda pendiente para el aguinaldo y no reduce el saldo semanal.";
    else if (tipo.value === "PAGO_SEMANAL") ayuda.textContent = "Registrá el pago del sábado. Se resta del saldo pendiente de esta semana.";
    else ayuda.textContent = "El adelanto se descuenta del sueldo de la semana correspondiente a la fecha del movimiento.";
  }

  async function cambiarAsistencia(boton) {
    const celda = boton.closest("td");
    const estadoAnterior = boton.dataset.estadoAnterior === "true";
    const ausente = !estadoAnterior;
    boton.disabled = true;
    try {
      const datos = new URLSearchParams({
        gomero_id: boton.dataset.gomeroId,
        fecha: boton.dataset.fecha,
        ausente: String(ausente),
      });
      const respuesta = await fetch("/gomeros/ausencia", {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: datos,
      });
      const resultado = await respuesta.json();
      if (!respuesta.ok || !resultado.exito) throw new Error(resultado.mensaje || "No se pudo actualizar la asistencia.");
      boton.dataset.estadoAnterior = String(ausente);
      boton.setAttribute("aria-pressed", String(ausente));
      boton.setAttribute("aria-label", ausente ? "Marcar asistencia" : "Marcar ausencia");
      boton.title = ausente ? "Ausente" : "Asistió";
      boton.querySelector("span").textContent = ausente ? "✕" : "✓";
      celda.classList.toggle("dia-ausente", ausente);
      const saldo = document.querySelector(`[data-saldo-gomero="${resultado.gomero_id}"]`);
      const descuento = document.querySelector(`[data-descuento-gomero="${resultado.gomero_id}"]`);
      if (saldo) saldo.textContent = `$${resultado.saldo.toLocaleString("es-AR")}`;
      if (descuento) descuento.textContent = `$${resultado.descuento_ausencias.toLocaleString("es-AR")}`;
    } catch (error) {
      window.alert(error.message);
    } finally {
      boton.disabled = false;
    }
  }

  document.querySelectorAll(".selector-asistencia").forEach((boton) => {
    boton.addEventListener("click", (evento) => {
      evento.stopPropagation();
      cambiarAsistencia(boton);
    });
  });

  function cargarCelda(celda) {
    if (hiddenId.value) cancelarEdicion();
    tipo.value = "ADELANTO";
    destino.value = "SUELDO";
    selectorGomero.value = celda.dataset.gomeroId;
    fecha.value = celda.dataset.fecha;
    actualizarFormulario();
    form.scrollIntoView({behavior: "smooth", block: "center"});
    importe.focus({preventScroll: true});
  }
  document.querySelectorAll(".js-celda-movimiento").forEach((celda) => {
    celda.addEventListener("click", (evento) => {
      if (evento.target.closest(".selector-asistencia")) return;
      cargarCelda(celda);
    });
    celda.addEventListener("keydown", (evento) => {
      if (evento.key === "Enter" || evento.key === " ") {
        evento.preventDefault();
        cargarCelda(celda);
      }
    });
  });

  function cancelarEdicion() {
    hiddenId.value = "";
    form.action = formActionNuevo;
    tipo.disabled = false;
    selectorGomero.disabled = false;
    destino.disabled = false;
    periodo.disabled = false;
    botonGuardar.textContent = "Guardar movimiento";
    botonCancelar.classList.add("d-none");
    ayuda.textContent = "El adelanto al sueldo reduce el saldo semanal.";
    actualizarFormulario();
  }

  document.querySelectorAll(".js-editar-movimiento").forEach((boton) => {
    boton.addEventListener("click", () => {
      const id = boton.dataset.id;
      hiddenId.value = id;
      form.action = `/gomeros/movimiento/editar/${id}`;
      tipo.value = boton.dataset.tipo;
      fecha.value = boton.dataset.fecha;
      importe.value = window.ImporteAR.formatear(boton.dataset.importe);
      concepto.value = boton.dataset.concepto;
      if (boton.dataset.gomeroId) selectorGomero.value = boton.dataset.gomeroId;
      destino.value = boton.dataset.destino;
      if (boton.dataset.periodo) periodo.value = boton.dataset.periodo;
      tipo.disabled = true;
      selectorGomero.disabled = true;
      destino.disabled = true;
      periodo.disabled = true;
      actualizarFormulario();
      botonGuardar.textContent = "Guardar corrección";
      botonCancelar.classList.remove("d-none");
      form.scrollIntoView({behavior: "smooth", block: "center"});
      importe.focus({preventScroll: true});
    });
  });
  botonCancelar.addEventListener("click", cancelarEdicion);

  tipo.addEventListener("change", actualizarFormulario);
  fecha.addEventListener("change", actualizarFormulario);
  destino.addEventListener("change", actualizarFormulario);
  form.addEventListener("submit", (evento) => {
    const monto = window.ImporteAR.parse(importe.value);
    if (!fecha.value || !Number.isInteger(monto) || monto <= 0) {
      evento.preventDefault();
      window.alert("Completá una fecha válida y un importe entero mayor que cero.");
    }
  });
  actualizarFormulario();
});