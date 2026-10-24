document.addEventListener("DOMContentLoaded", () => {
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
