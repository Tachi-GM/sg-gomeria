import re


def parse_int_seguro(valor, por_defecto=0):
    """Convierte texto a entero sin lanzar excepciones."""
    try:
        if valor is None or str(valor).strip() == "":
            return por_defecto
        return int(valor)
    except (ValueError, TypeError):
        return por_defecto


def parse_float_seguro(valor, por_defecto=0.0):
    """Convierte texto a número decimal flotante con soporte para comas."""
    try:
        if valor is None or str(valor).strip() == "":
            return por_defecto
        limpio = str(valor).strip().replace(",", ".")
        return float(limpio)
    except (ValueError, TypeError):
        return por_defecto


def validar_y_formatear_cuit(cuit_raw):
    """
    Valida y formatea un CUIT argentino (11 dígitos, algoritmo módulo 11 de AFIP).
    Retorna (es_valido: bool, cuit_formateado_o_mensaje: str)
    """
    if not cuit_raw or not str(cuit_raw).strip():
        return False, "El CUIT es obligatorio"

    limpio = re.sub(r"\D", "", str(cuit_raw).strip())
    if len(limpio) != 11:
        return False, "El CUIT debe contener exactamente 11 dígitos"

    # Algoritmo Módulo 11 de AFIP
    multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(limpio[i]) * multiplicadores[i] for i in range(10))
    resto = 11 - (suma % 11)

    if resto == 11:
        digito_esperado = 0
    elif resto == 10:
        digito_esperado = 9
    else:
        digito_esperado = resto

    if digito_esperado != int(limpio[10]):
        return False, "El CUIT ingresado no es válido (dígito verificador incorrecto)"

    formateado = f"{limpio[:2]}-{limpio[2:10]}-{limpio[10]}"
    return True, formateado


def validar_y_formatear_remito(tipo, remito_raw):
    """
    Valida y estandariza el formato de remito según su tipo:
    - OI: Exactamente 5 dígitos (ej. 12345). Si ingresa menos dígitos numéricos,
      autocompleta con ceros a la izquierda.
    - OIB: Exactamente '00' seguido de 4 dígitos (ej. 001234). Si ingresa hasta 4 dígitos,
      antepone '00' y rellena con ceros.
    Retorna (es_valido: bool, remito_formateado_o_mensaje: str)
    """
    if tipo not in ("OI", "OIB"):
        return False, "Tipo de comprobante inválido (debe ser OI u OIB)"

    if not remito_raw or not str(remito_raw).strip():
        return False, "El número de remito es obligatorio"

    remito_limpio = str(remito_raw).strip()

    if tipo == "OI":
        if not remito_limpio.isdigit():
            return (
                False,
                "El remito OI debe ser estrictamente numérico (hasta 5 dígitos)",
            )
        if len(remito_limpio) > 5:
            return False, "El remito OI no puede superar los 5 dígitos (formato XXXXX)"
        return True, remito_limpio.zfill(5)

    if tipo == "OIB":
        if remito_limpio.startswith("00"):
            resto = remito_limpio[2:]
            if not resto.isdigit():
                return (
                    False,
                    "El remito OIB debe contener 4 dígitos luego del prefijo 00",
                )
            if len(resto) > 4:
                return (
                    False,
                    "El remito OIB no puede superar los 4 dígitos tras el 00 (formato 00XXXX)",
                )
            return True, f"00{resto.zfill(4)}"
        else:
            if not remito_limpio.isdigit():
                return (
                    False,
                    "El remito OIB debe contener solo dígitos (formato 00XXXX)",
                )
            if len(remito_limpio) > 4:
                return (
                    False,
                    "El remito OIB debe tener formato 00XXXX (máximo 4 dígitos precedidos por 00)",
                )
            return True, f"00{remito_limpio.zfill(4)}"


MESES_ABREVIADOS = {
    "01": "Ene",
    "02": "Feb",
    "03": "Mar",
    "04": "Abr",
    "05": "May",
    "06": "Jun",
    "07": "Jul",
    "08": "Ago",
    "09": "Sep",
    "10": "Oct",
    "11": "Nov",
    "12": "Dic",
}


def formatear_periodo(periodo):
    """Convierte 'YYYY-MM' (ej: '2026-09') en 'Sep 26' para mostrar en las pestañas."""
    anio, mes = periodo.split("-")
    return f"{MESES_ABREVIADOS[mes]} {anio[2:]}"


def obtener_meses_disponibles(cursor, id_cliente=None):
    """
    Devuelve la lista de meses con trabajos registrados, listos para las pestañas.
    Si se pasa id_cliente, filtra solo los meses de ese cliente.
    Si no, trae los meses de TODOS los clientes (para el historial general).
    """
    if id_cliente:
        filas = cursor.execute(
            """
            SELECT DISTINCT strftime('%Y-%m', fecha) AS periodo
            FROM trabajos
            WHERE id_cliente = ?
            ORDER BY periodo DESC
        """,
            (id_cliente,),
        ).fetchall()
    else:
        filas = cursor.execute("""
            SELECT DISTINCT strftime('%Y-%m', fecha) AS periodo
            FROM trabajos
            ORDER BY periodo DESC
        """).fetchall()

    return [
        {"periodo": fila["periodo"], "etiqueta": formatear_periodo(fila["periodo"])}
        for fila in filas
    ]
