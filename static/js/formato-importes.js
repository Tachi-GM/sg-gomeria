/* Importes escritos a la argentina: mientras se escribe, el campo muestra puntos de
   miles (1.250.000) y la coma queda para los centavos (1.250.000,50).

   Uso: agregar el atributo data-importe-ar a un <input type="text" inputmode="decimal">.
   El servidor recibe el texto tal cual (con puntos y coma) y lo interpreta con
   `parse_importe_ar`; los puntos son solo comodidad visual para quien escribe.

   También expone window.ImporteAR.parse("1.250,50") -> 1250.5 para los cálculos en pantalla. */
(function () {
  // Deja solo dígitos y UNA coma (el punto lo pone el formato, no el usuario).
  function limpiar(texto) {
    texto = texto.replace(/[^\d,]/g, "");
    const primera = texto.indexOf(",");
    if (primera !== -1) {
      texto = texto.slice(0, primera + 1) + texto.slice(primera + 1).replace(/,/g, "");
    }
    return texto;
  }

  function formatear(textoLimpio) {
    const partes = textoLimpio.split(",");
    let entero = partes[0].replace(/^0+(?=\d)/, "");  // sin ceros a la izquierda
    const tieneComa = partes.length > 1;
    if (entero === "" && tieneComa) entero = "0";
    entero = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return tieneComa ? entero + "," + partes[1].slice(0, 2) : entero;
  }

  function parse(texto) {
    const numero = Number(String(texto || "").replace(/\./g, "").replace(",", "."));
    return Number.isFinite(numero) ? numero : 0;
  }

  function alEscribir(campo) {
    // Para no mover el cursor: se cuenta cuántos dígitos/comas había antes de él
    // y, tras darle formato, se lo coloca después de la misma cantidad.
    const cursor = campo.selectionStart ?? campo.value.length;
    const antes = (campo.value.slice(0, cursor).match(/[\d,]/g) || []).length;
    campo.value = formatear(limpiar(campo.value));

    let posicion = 0;
    let vistos = 0;
    while (posicion < campo.value.length && vistos < antes) {
      if (/[\d,]/.test(campo.value[posicion])) vistos += 1;
      posicion += 1;
    }
    campo.setSelectionRange(posicion, posicion);
  }

  function iniciar() {
    document.querySelectorAll("input[data-importe-ar]").forEach((campo) => {
      campo.addEventListener("input", () => alEscribir(campo));
      if (campo.value) campo.value = formatear(limpiar(campo.value));
    });
  }

  window.ImporteAR = { parse, formatear: (texto) => formatear(limpiar(texto)) };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
