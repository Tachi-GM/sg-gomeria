from datetime import date

from database.connection import obtener_conexion


def obtener_resumen_inicio(fecha_referencia=None):
    """Obtiene métricas reales y acotadas para la pantalla principal."""
    fecha = fecha_referencia or date.today()
    fecha_iso = fecha.isoformat()
    mes_actual = fecha.strftime("%Y-%m")

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        remitos_pendientes = cursor.execute(
            """
            SELECT COUNT(*)
            FROM trabajos
            WHERE estado IN ('PENDIENTE', 'EN PROCESO')
            """
        ).fetchone()[0]

        total_mes = cursor.execute(
            """
            SELECT COALESCE(SUM(total), 0)
            FROM trabajos
            WHERE substr(fecha, 1, 7) = ?
            """,
            (mes_actual,),
        ).fetchone()[0]

        cheques_por_vencer = cursor.execute(
            """
            SELECT COUNT(*)
            FROM cheques
            WHERE estado = 'Pendiente'
              AND fecha_pago IS NOT NULL
              AND date(fecha_pago) BETWEEN date(?) AND date(?, '+30 days')
            """,
            (fecha_iso, fecha_iso),
        ).fetchone()[0]

        return {
            "remitos_pendientes": remitos_pendientes,
            "total_mes": float(total_mes or 0),
            "cheques_por_vencer": cheques_por_vencer,
        }
    finally:
        conexion.close()
