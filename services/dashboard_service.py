from datetime import date

from database.connection import obtener_conexion


def obtener_resumen_inicio(fecha_referencia=None):
    """Obtiene métricas reales y acotadas para la pantalla principal."""
    fecha = fecha_referencia or date.today()
    fecha_iso = fecha.isoformat()
    mes_actual = fecha.strftime("%Y-%m")
    nombres_meses = (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    )

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

        filas_urgentes = cursor.execute(
            """
            SELECT ch.numero,
                   COALESCE(c.nom_cli, ch.cliente, 'Sin cliente') AS cliente,
                   ch.banco,
                   ch.fecha_pago,
                   ch.importe,
                   CASE WHEN date(ch.fecha_pago) < date(?) THEN 1 ELSE 0 END AS vencido
            FROM cheques ch
            LEFT JOIN clientes c ON c.id_cliente = ch.id_cliente
            WHERE ch.estado = 'Pendiente'
              AND ch.fecha_pago IS NOT NULL
              AND date(ch.fecha_pago) <= date(?, '+7 days')
            ORDER BY date(ch.fecha_pago) ASC
            LIMIT 5
            """,
            (fecha_iso, fecha_iso),
        ).fetchall()

        cheques_por_vencer_7d = cursor.execute(
            """
            SELECT COUNT(*)
            FROM cheques
            WHERE estado = 'Pendiente'
              AND fecha_pago IS NOT NULL
              AND date(fecha_pago) <= date(?, '+7 days')
            """,
            (fecha_iso,),
        ).fetchone()[0]

        return {
            "remitos_pendientes": remitos_pendientes,
            "total_mes": float(total_mes or 0),
            "cheques_por_vencer": cheques_por_vencer,
            "cheques_por_vencer_7d": cheques_por_vencer_7d,
            "cheques_urgentes": [dict(f) for f in filas_urgentes],
            "periodo_mes": f"{nombres_meses[fecha.month - 1]} {fecha.year}",
        }
    finally:
        conexion.close()


def obtener_resumen_caja_diaria(fecha_referencia=None):
    """Obtiene el resumen de movimientos del día (remitos, cheques y gomeros)."""
    if isinstance(fecha_referencia, str) and fecha_referencia.strip():
        fecha_iso = fecha_referencia.strip()
    elif isinstance(fecha_referencia, date):
        fecha_iso = fecha_referencia.isoformat()
    else:
        fecha_iso = date.today().isoformat()

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        remitos = [
            dict(f)
            for f in cursor.execute(
                """
                SELECT t.id_trabajo, t.tipo, t.remito, t.fecha, t.total, t.estado, t.detalle,
                       COALESCE(c.nom_cli, 'Sin cliente') AS nom_cli
                FROM trabajos t
                LEFT JOIN clientes c ON c.id_cliente = t.id_cliente
                WHERE date(t.fecha) = date(?)
                ORDER BY t.id_trabajo DESC
                """,
                (fecha_iso,),
            ).fetchall()
        ]

        total_facturado = sum(float(r["total"] or 0) for r in remitos)
        total_pagado = sum(
            float(r["total"] or 0) for r in remitos if r["estado"] == "PAGADO"
        )
        total_pendiente = total_facturado - total_pagado

        cheques_dia = [
            dict(f)
            for f in cursor.execute(
                """
                SELECT ch.numero, ch.banco, ch.importe, ch.estado,
                       COALESCE(c.nom_cli, ch.cliente, 'Sin cliente') AS cliente
                FROM cheques ch
                LEFT JOIN clientes c ON c.id_cliente = ch.id_cliente
                WHERE date(ch.fecha_pago) = date(?)
                ORDER BY ch.id_cheque DESC
                """,
                (fecha_iso,),
            ).fetchall()
        ]

        movimientos_gomeros = [
            dict(f)
            for f in cursor.execute(
                """
                SELECT m.tipo, m.importe, m.concepto,
                       COALESCE(g.nombre, 'Gasto general') AS gomero
                FROM movimientos_gomeros m
                LEFT JOIN gomeros g ON g.id_gomero = m.id_gomero
                WHERE date(m.fecha) = date(?)
                ORDER BY m.id_movimiento DESC
                """,
                (fecha_iso,),
            ).fetchall()
        ]
        total_gastos_gomeros = sum(float(m["importe"] or 0) for m in movimientos_gomeros)

        return {
            "fecha": fecha_iso,
            "remitos": remitos,
            "cantidad_remitos": len(remitos),
            "total_facturado": total_facturado,
            "total_pagado": total_pagado,
            "total_pendiente": total_pendiente,
            "cheques_dia": cheques_dia,
            "total_cheques_dia": sum(float(c["importe"] or 0) for c in cheques_dia),
            "movimientos_gomeros": movimientos_gomeros,
            "total_gastos_gomeros": total_gastos_gomeros,
        }
    finally:
        conexion.close()
