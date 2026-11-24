/* Importar precios desde Excel: pide confirmación y evita enviar dos veces. */
document.addEventListener("DOMContentLoaded", () => {
  const formulario = document.getElementById("form-importar-precios");
  if (!formulario) return;

  formulario.addEventListener("submit", (evento) => {
    const archivo = formulario.elements["archivo"].files[0];
    if (!archivo) return;  // el navegador ya avisa que falta elegir uno (required)

    const pregunta =
      `¿Actualizar los precios con el archivo "${archivo.name}"?\n\n` +
      "Se van a modificar los precios existentes y agregar las tareas nuevas. " +
      "Antes se guarda una copia de seguridad automática.";
    if (!window.confirm(pregunta)) {
      evento.preventDefault();
      return;
    }

    // Una vez confirmado, se bloquea el botón para que un doble clic no importe dos veces.
    const boton = document.getElementById("btn-importar-precios");
    boton.disabled = true;
    boton.textContent = "Procesando…";
  });
});
