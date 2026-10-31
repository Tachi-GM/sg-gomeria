document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".selector-asistencia").forEach((selector) => {
    selector.addEventListener("change", async () => {
      const celda = selector.closest("td");
      const estadoAnterior = selector.dataset.estadoAnterior;
      const datos = new URLSearchParams({
        gomero_id: selector.dataset.gomeroId,
        fecha: selector.dataset.fecha,
        ausente: selector.value,
      });

      selector.disabled = true;
      try {
        const respuesta = await fetch("/gomeros/ausencia", {
          method: "POST",
          headers: {"Content-Type": "application/x-www-form-urlencoded"},
          body: datos,
        });
        const resultado = await respuesta.json();
        if (!respuesta.ok || !resultado.exito) {
          throw new Error(resultado.mensaje || "No se pudo actualizar la asistencia.");
        }
        selector.dataset.estadoAnterior = selector.value;
        celda.classList.toggle("dia-ausente", resultado.ausente);
        const saldo = document.querySelector(
          `[data-saldo-gomero="${resultado.gomero_id}"]`
        );
        const descuento = document.querySelector(
          `[data-descuento-gomero="${resultado.gomero_id}"]`
        );
        if (saldo) saldo.textContent = `$${resultado.saldo.toLocaleString("es-AR")}`;
        if (descuento) {
          descuento.textContent = `$${resultado.descuento_ausencias.toLocaleString("es-AR")}`;
        }
      } catch (error) {
        selector.value = estadoAnterior;
        window.alert(error.message);
      } finally {
        selector.disabled = false;
      }
    });
  });

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

  function actualizarFormulario() {
    const esGasto = tipo.value === "GASTO_GENERAL";
    const esDescuento = tipo.value === "DESCUENTO_AGUINALDO";
    if (esGasto) destino.value = "NO_APLICA";
    else if (destino.value === "NO_APLICA" || !destino.value) destino.value = "SUELDO";
    if (esDescuento) destino.value = "AGUINALDO";
    if (tipo.value === "PAGO_SEMANAL") destino.value = "SUELDO";
    campoGomero.classList.toggle("d-none", esGasto);
    campoDestino.classList.toggle("d-none", esGasto || esDescuento);
    campoAguinaldo.classList.toggle("d-none", esGasto || (destino.value !== "AGUINALDO" && !esDescuento));
    selectorGomero.required = !esGasto;
    selectorGomero.disabled = esGasto;
    destino.required = !esGasto;
    periodo.required = !esGasto && (destino.value === "AGUINALDO" || esDescuento);
    if (esGasto) {
      ayuda.textContent = "El gasto queda en la cuenta general y no modifica ningún sueldo.";
    } else if (esDescuento) {
      ayuda.textContent = "Registrá un descuento efectivamente aplicado al aguinaldo. No puede superar el saldo pendiente.";
    } else if (destino.value === "AGUINALDO") {
      ayuda.textContent = "El adelanto queda pendiente para el aguinaldo y no reduce el saldo semanal.";
    } else if (tipo.value === "PAGO_SEMANAL") {
      ayuda.textContent = "Registrá el pago del sábado. Se resta del saldo pendiente de esta semana.";
    } else {
      ayuda.textContent = "El adelanto se descuenta del sueldo de la semana correspondiente a la fecha del movimiento.";
    }
  }

  tipo.addEventListener("change", actualizarFormulario);
  destino.addEventListener("change", actualizarFormulario);
  document.getElementById("form-movimiento").addEventListener("submit", (evento) => {
    if (!fecha.value || !Number.isInteger(Number(importe.value)) || Number(importe.value) <= 0) {
      evento.preventDefault();
      window.alert("Completá una fecha válida y un importe entero mayor que cero.");
    }
  });
  actualizarFormulario();
});
