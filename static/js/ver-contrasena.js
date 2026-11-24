/* Ojo para mostrar/ocultar la contraseña mientras se escribe.

   Cada botón con data-ojo-clave="<id del input>" alterna ese campo entre
   type="password" (oculto) y type="text" (visible).

   Cuidados de seguridad:
   - Solo muestra lo que se está escribiendo: las contraseñas guardadas no se
     pueden ver porque en la base están hasheadas (y los campos de "nueva
     contraseña" arrancan vacíos).
   - Se vuelve a ocultar sola a los 10 segundos, al salir del campo, al enviar
     el formulario y al volver a la pestaña. Así no queda una clave a la vista
     en una PC compartida o con gente alrededor.
*/
(function () {
  const SEGUNDOS_VISIBLE = 10;

  function ocultar(campo, boton) {
    campo.type = "password";
    boton.setAttribute("aria-pressed", "false");
    boton.setAttribute("aria-label", "Mostrar contraseña");
    boton.title = "Mostrar contraseña";
    boton.classList.remove("activo");
    clearTimeout(boton._temporizador);
  }

  function mostrar(campo, boton) {
    campo.type = "text";
    boton.setAttribute("aria-pressed", "true");
    boton.setAttribute("aria-label", "Ocultar contraseña");
    boton.title = "Ocultar contraseña";
    boton.classList.add("activo");
    clearTimeout(boton._temporizador);
    boton._temporizador = setTimeout(() => ocultar(campo, boton), SEGUNDOS_VISIBLE * 1000);
  }

  document.querySelectorAll("[data-ojo-clave]").forEach((boton) => {
    const campo = document.getElementById(boton.dataset.ojoClave);
    if (!campo) return;

    // mousedown + preventDefault: al tocar el ojo el campo no pierde el foco.
    boton.addEventListener("mousedown", (evento) => evento.preventDefault());
    boton.addEventListener("click", () => {
      if (campo.type === "password") mostrar(campo, boton);
      else ocultar(campo, boton);
      campo.focus();
    });

    // Al salir del campo (salvo que se haya tocado el ojo) se vuelve a ocultar.
    campo.addEventListener("blur", () => ocultar(campo, boton));
    if (campo.form) campo.form.addEventListener("submit", () => ocultar(campo, boton));
  });

  // Al volver a la pestaña o recuperar la página desde el historial, todo oculto.
  const ocultarTodo = () => document.querySelectorAll("[data-ojo-clave]").forEach((boton) => {
    const campo = document.getElementById(boton.dataset.ojoClave);
    if (campo) ocultar(campo, boton);
  });
  document.addEventListener("visibilitychange", () => { if (document.hidden) ocultarTodo(); });
  window.addEventListener("pageshow", ocultarTodo);
})();
