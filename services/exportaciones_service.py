"""Consulta y preparación de datos para exportaciones mensuales de remitos."""

import re

from database.connection import obtener_conexion
from utils.fotos import ruta_foto_segura

PERIODO_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validar_periodo(periodo):
    """Valida el formato AAAA-MM sin aceptar períodos ambiguos."""
    return bool(PERIODO_RE.fullmatch(str(periodo or "")))


def obtener_datos_exportacion(id_cliente, periodo, carpeta_uploads):
    """Devuelve cliente, remitos, detalles y fotos seguras para un período."""
    if not validar_periodo(periodo):
        raise ValueError("El período debe tener formato AAAA-MM.")

    conexion = obtener_conexion()
    try:
        cliente = conexion.execute(
            "SELECT id_cliente, nom_cli, cuit, con_iva FROM clientes WHERE id_cliente = ?",
            (id_cliente,),
        ).fetchone()
        if cliente is None:
            raise ValueError("El cliente indicado no existe.")

        remitos = conexion.execute(
            """
            SELECT id_trabajo, remito, tipo, fecha, detalle, total, estado,
                   foto_remito
            FROM trabajos
            WHERE id_cliente = ? AND strftime('%Y-%m', fecha) = ?
            ORDER BY fecha ASC, id_trabajo ASC
            """,
            (id_cliente, periodo),
        ).fetchall()

        ids_trabajo = [remito["id_trabajo"] for remito in remitos]
        detalles_por_trabajo = {}
        if ids_trabajo:
            placeholders = ",".join("?" for _ in ids_trabajo)
            detalles = conexion.execute(
                f"""
                SELECT dt.id_trabajo, tar.nom_tar AS nombre_tarea,
                       dt.cantidad, dt.subtotal
                FROM detalle_trabajos dt
                JOIN tareas tar ON dt.id_tarea = tar.id_tarea
                WHERE dt.id_trabajo IN ({placeholders})
                UNION ALL
                SELECT dtt.id_trabajo, dtt.nombre_tarea AS nombre_tarea,
                       dtt.cantidad, dtt.subtotal
                FROM detalle_temporal_trabajos dtt
                WHERE dtt.id_trabajo IN ({placeholders})
                ORDER BY id_trabajo
                """,
                ids_trabajo + ids_trabajo,
            ).fetchall()
            for detalle in detalles:
                detalles_por_trabajo.setdefault(detalle["id_trabajo"], []).append(
                    dict(detalle)
                )

        resultado_remitos = []
        for remito in remitos:
            foto_path = ruta_foto_segura(remito["foto_remito"], carpeta_uploads)
            resultado_remitos.append(
                {
                    **dict(remito),
                    "detalles": detalles_por_trabajo.get(remito["id_trabajo"], []),
                    "foto_path": (
                        foto_path if foto_path and foto_path.is_file() else None
                    ),
                }
            )

        return {
            "cliente": dict(cliente),
            "periodo": periodo,
            "remitos": resultado_remitos,
            "total": round(sum(r["total"] for r in resultado_remitos), 2),
        }
    finally:
        conexion.close()


def obtener_datos_exportacion_general(id_cliente, carpeta_uploads):
    """Devuelve todos los remitos del cliente agrupables en pestañas mensuales."""
    conexion = obtener_conexion()
    try:
        cliente = conexion.execute(
            """
            SELECT id_cliente, nom_cli, cuit, con_iva
            FROM clientes
            WHERE id_cliente = ?
            """,
            (id_cliente,),
        ).fetchone()
        if cliente is None:
            raise ValueError("El cliente indicado no existe.")

        periodos = conexion.execute(
            """
            SELECT DISTINCT strftime('%Y-%m', fecha) AS periodo
            FROM trabajos
            WHERE id_cliente = ?
            ORDER BY periodo
            """,
            (id_cliente,),
        ).fetchall()

        meses = [
            obtener_datos_exportacion(id_cliente, fila["periodo"], carpeta_uploads)
            for fila in periodos
        ]
        return {
            "cliente": dict(cliente),
            "meses": meses,
            "total": round(sum(mes["total"] for mes in meses), 2),
        }
    finally:
        conexion.close()
