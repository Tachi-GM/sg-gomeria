/* Importación desde Excel: pide confirmación y evita enviar dos veces.

   Se activa en cualquier <form data-importar-excel>. El texto de la pregunta sale de
   data-confirmar-importar ("¿Importar los cheques del archivo" + nombre del archivo + "?"). */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-importar-excel]").forEach((formulario) => {
    formulario.addEventListener("submit", (evento) => {
      const archivo = formulario.elements["archivo"].files[0];
      if (!archivo) return;  // el navegador ya avisa que falta elegir uno (required)

      const pregunta =
        `${formulario.dataset.confirmarImportar} "${archivo.name}"?\n\n` +
        "Antes se guarda una copia de seguridad automática.";
      if (!window.confirm(pregunta)) {
        evento.preventDefault();
        return;
      }
      // Confirmado: se bloquea el botón para que un doble clic no importe dos veces.
      const boton = formulario.querySelector("[data-boton-importar]");
      if (boton) {
        boton.disabled = true;
        boton.textContent = "Procesando…";
      }
    });
  });
});
