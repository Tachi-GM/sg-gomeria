/* Unificar clientes (solo administradores): completa el modal con el cliente duplicado,
   filtra la lista del cliente principal y pide una última confirmación. */
document.addEventListener("DOMContentLoaded", () => {
  const formulario = document.getElementById("form-unificar-cliente");
  if (!formulario) return;
  const lista = document.getElementById("unificar-principal");
  const filtro = document.getElementById("unificar-filtro");

  // El botón de cada tarjeta lleva el cliente duplicado en data-*.
  document.addEventListener("click", (evento) => {
    const boton = evento.target.closest(".js-unificar-cliente");
    if (!boton) return;
    document.getElementById("unificar-id-duplicado").value = boton.dataset.id;
    document.getElementById("unificar-nombre-duplicado").textContent = boton.dataset.nombre;
    filtro.value = "";
    lista.selectedIndex = -1;
    Array.from(lista.options).forEach((opcion) => {
      opcion.hidden = false;
      // El duplicado no puede ser su propio principal.
      opcion.disabled = opcion.value === boton.dataset.id;
    });
  });

  // Filtro de texto sobre la lista (nombre o CUIT), sin distinguir mayúsculas.
  filtro.addEventListener("input", () => {
    const texto = filtro.value.trim().toLowerCase();
    Array.from(lista.options).forEach((opcion) => {
      opcion.hidden = texto !== "" && !opcion.textContent.toLowerCase().includes(texto);
    });
  });

  formulario.addEventListener("submit", (evento) => {
    const elegido = lista.options[lista.selectedIndex];
    if (!elegido) {
      evento.preventDefault();
      window.alert("Elegí el cliente principal de la lista.");
      return;
    }
    const duplicado = document.getElementById("unificar-nombre-duplicado").textContent;
    const pregunta =
      `¿Unificar "${duplicado}" dentro de "${elegido.dataset.nombre}"?\n\n` +
      "Sus remitos, cheques y vehículos pasan al cliente principal y el duplicado se elimina. " +
      "Se guarda una copia de seguridad antes.";
    if (!window.confirm(pregunta)) evento.preventDefault();
  });
});
