def parse_int_seguro(valor, por_defecto=0):
    """Convierte texto a entero sin lanzar excepciones."""
    try:
        if valor is None or str(valor).strip() == '':
            return por_defecto
        return int(valor)
    except (ValueError, TypeError):
        return por_defecto

def parse_float_seguro(valor, por_defecto=0.0):
    """Convierte texto a número decimal flotante con soporte para comas."""
    try:
        if valor is None or str(valor).strip() == '':
            return por_defecto
        limpio = str(valor).strip().replace(',', '.')
        return float(limpio)
    except (ValueError, TypeError):
        return por_defecto
    
MESES_ABREVIADOS = {
    '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
    '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
    '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'
}

def formatear_periodo(periodo):
    """Convierte 'YYYY-MM' (ej: '2026-09') en 'Sep 26' para mostrar en las pestañas."""
    anio, mes = periodo.split('-')
    return f"{MESES_ABREVIADOS[mes]} {anio[2:]}"

def obtener_meses_disponibles(cursor, id_cliente=None):
    """
    Devuelve la lista de meses con trabajos registrados, listos para las pestañas.
    Si se pasa id_cliente, filtra solo los meses de ese cliente.
    Si no, trae los meses de TODOS los clientes (para el historial general).
    """
    if id_cliente:
        filas = cursor.execute("""
            SELECT DISTINCT strftime('%Y-%m', fecha) AS periodo
            FROM trabajos
            WHERE id_cliente = ?
            ORDER BY periodo DESC
        """, (id_cliente,)).fetchall()
    else:
        filas = cursor.execute("""
            SELECT DISTINCT strftime('%Y-%m', fecha) AS periodo
            FROM trabajos
            ORDER BY periodo DESC
        """).fetchall()

    return [
        {'periodo': fila['periodo'], 'etiqueta': formatear_periodo(fila['periodo'])}
        for fila in filas
    ]