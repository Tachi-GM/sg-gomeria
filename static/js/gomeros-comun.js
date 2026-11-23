/* Comportamientos compartidos por la pestaña "Gomeros" y la ficha de cada gomero. */
document.addEventListener("DOMContentLoaded", () => {
  const formatoPesos = new Intl.NumberFormat("es-AR");
  const aPesos = (valor) => "$" + formatoPesos.format(Number(valor));

  // 1) Ruedita del mouse: en un <input type="number"> enfocado cambia el valor
  //    sin querer (60.000 -> 59.999...). Al scrollear le sacamos el foco al campo
  //    antes de que el navegador aplique el cambio. Las flechas del teclado siguen andando.
  document.addEventListener("wheel", () => {
    const activo = document.activeElement;
    if (activo && activo.tagName === "INPUT" && activo.type === "number") activo.blur();
  }, {passive: true});

  // 2) Eco del importe: debajo de cada importe/sueldo se muestra "= $600.000",
  //    para detectar al instante un cero de más o de menos.
  const NOMBRES_IMPORTE = ["importe", "sueldo_semanal"];
  document.querySelectorAll('input[type="number"]').forEach((campo) => {
    if (!NOMBRES_IMPORTE.includes(campo.name)) return;
    const eco = document.createElement("div");
    eco.className = "form-text fw-semibold text-primary eco-importe";
    eco.setAttribute("aria-live", "polite");
    campo.insertAdjacentElement("afterend", eco);
    const actualizar = () => {
      eco.textContent = campo.value ? "= " + aPesos(campo.value) : "";
    };
    campo.addEventListener("input", actualizar);
    actualizar();
  });

  // 3) Confirmación antes de guardar: los formularios con data-confirmar-importe
  //    preguntan "¿Guardar aguinaldo de $600.000?" antes de enviarse.
  document.addEventListener("submit", (evento) => {
    const formulario = evento.target;
    if (!formulario.dataset || formulario.dataset.confirmarImporte === undefined) return;
    const campo = formulario.querySelector('input[name="importe"]');
    if (!campo || !campo.value) return;
    const pregunta = `${formulario.dataset.confirmarImporte} ${aPesos(campo.value)}?`;
    if (!window.confirm(pregunta)) evento.preventDefault();
  });

  // 4) Modales de corrección: el botón "Editar" lleva los datos en data-*;
  //    acá los volcamos al formulario del modal y armamos su URL.
  function abrirModal(boton, idFormulario, campos) {
    const formulario = document.getElementById(idFormulario);
    if (!formulario) return;
    formulario.action = formulario.dataset.urlBase + boton.dataset.id;
    formulario.querySelector("[data-detalle-modal]").textContent = boton.dataset.detalle || "";
    Object.entries(campos).forEach(([nombre, valor]) => {
      const entrada = formulario.elements[nombre];
      if (!entrada) return;
      entrada.value = valor;
      entrada.dispatchEvent(new Event("input"));  // refresca el eco del importe
    });
  }
  document.addEventListener("click", (evento) => {
    const aguinaldo = evento.target.closest(".js-editar-aguinaldo");
    if (aguinaldo) {
      abrirModal(aguinaldo, "form-editar-aguinaldo", {importe: aguinaldo.dataset.importe});
      return;
    }
    const movimiento = evento.target.closest(".js-editar-mov-modal");
    if (movimiento) {
      abrirModal(movimiento, "form-editar-movimiento", {
        fecha: movimiento.dataset.fecha, importe: movimiento.dataset.importe,
        concepto: movimiento.dataset.concepto, ancla: movimiento.dataset.ancla,
      });
      return;
    }
    const pago = evento.target.closest(".js-editar-pago-aguinaldo");
    if (pago) {
      abrirModal(pago, "form-editar-pago-aguinaldo", {
        fecha: pago.dataset.fecha, importe: pago.dataset.importe, concepto: pago.dataset.concepto,
      });
    }
  });

  // 5) Pestañas con ancla: si la URL termina en #aguinaldo (o el id de una pestaña),
  //    se abre esa pestaña; y al cambiar de pestaña se actualiza el ancla.
  const disparadores = document.querySelectorAll('[data-bs-toggle="tab"]');
  if (disparadores.length && window.bootstrap) {
    const hash = window.location.hash;
    const pedido = hash && document.querySelector(`[data-bs-toggle="tab"][data-bs-target="${hash}"]`);
    if (pedido) window.bootstrap.Tab.getOrCreateInstance(pedido).show();
    disparadores.forEach((d) => d.addEventListener("shown.bs.tab", () => {
      history.replaceState(null, "", d.dataset.bsTarget);
    }));
  }
});
