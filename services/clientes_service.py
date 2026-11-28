"""Operaciones sobre clientes que tocan varias tablas a la vez."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from database.connection import get_db_path, obtener_conexion

logger = logging.getLogger("SG_Gomeria")

# Datos de contacto que se completan en el cliente principal si los tiene vacíos.
CAMPOS_A_COMPLETAR = (
    "cuit", "tel", "mail", "direccion", "localidad",
    "condicion_iva", "tipo_factura", "contacto", "codigo",
)


class ErrorClientes(Exception):
    """Problema esperable con un mensaje que se puede mostrar al usuario."""


def _hacer_backup(carpeta):
    """Copia la base con la API de backup de SQLite (segura aunque la app la esté usando)."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"antes_unificar_clientes_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    origen = sqlite3.connect(str(get_db_path()))
    copia = sqlite3.connect(str(destino))
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    return destino


def _columnas(conexion, tabla):
    return {fila["name"] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')}


def _referencias_a_clientes(conexion):
    """[(tabla, columna)] de todas las tablas con clave foránea hacia clientes."""
    referencias = []
    tablas = [
        f["name"] for f in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
    ]
    for tabla in tablas:
        if tabla == "clientes":
            continue
        for fk in conexion.execute(f'PRAGMA foreign_key_list("{tabla}")'):
            if fk["table"] == "clientes":
                referencias.append((tabla, fk["from"]))
    return referencias


def _vacio(valor):
    return valor is None or not str(valor).strip()


def unificar_clientes(id_duplicado, id_principal, carpeta_backups):
    """Mueve todo lo del cliente duplicado al principal y elimina el duplicado.

    Todo ocurre en una sola transacción (si algo falla, no se cambia nada) y antes se guarda un
    backup. El nombre del duplicado queda como alias del principal, así los importadores lo
    reconocen. Del duplicado solo se copian los datos de contacto que el principal tenga vacíos;
    la condición de IVA y la lista de precios del principal no se tocan, y los remitos ya
    cargados no se recalculan.

    Devuelve un resumen con lo que se movió.
    """
    if not id_duplicado or not id_principal:
        raise ErrorClientes("Elegí el cliente principal con el que se va a unificar.")
    if id_duplicado == id_principal:
        raise ErrorClientes("El cliente duplicado y el principal no pueden ser el mismo.")

    conexion = obtener_conexion()
    try:
        duplicado = conexion.execute("SELECT * FROM clientes WHERE id_cliente = ?", (id_duplicado,)).fetchone()
        principal = conexion.execute("SELECT * FROM clientes WHERE id_cliente = ?", (id_principal,)).fetchone()
        if duplicado is None or principal is None:
            raise ErrorClientes("Alguno de los clientes ya no existe.")
    finally:
        conexion.close()

    backup = _hacer_backup(carpeta_backups)

    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        # Se vuelven a leer dentro de la transacción: otra persona pudo cambiar algo mientras tanto.
        duplicado = conexion.execute("SELECT * FROM clientes WHERE id_cliente = ?", (id_duplicado,)).fetchone()
        principal = conexion.execute("SELECT * FROM clientes WHERE id_cliente = ?", (id_principal,)).fetchone()
        if duplicado is None or principal is None:
            raise ErrorClientes("Alguno de los clientes ya no existe.")

        nombre_duplicado, nombre_principal = duplicado["nom_cli"], principal["nom_cli"]
        columnas_clientes = _columnas(conexion, "clientes")
        movidos = {}

        # 1) Textos que dependen del nombre (antes de mover, mientras se puede filtrar por el duplicado).
        if "cliente_alias" in _columnas(conexion, "trabajos"):
            conexion.execute(
                "UPDATE trabajos SET cliente_alias = ? WHERE id_cliente = ? "
                "AND (cliente_alias IS NULL OR TRIM(cliente_alias) = '')",
                (nombre_duplicado, id_duplicado))
        if "cliente" in _columnas(conexion, "cheques"):
            conexion.execute("UPDATE cheques SET cliente = ? WHERE id_cliente = ?", (nombre_principal, id_duplicado))

        # 2) Mover todo lo que apunta al duplicado (remitos, cheques, vehículos, alias...).
        referencias = _referencias_a_clientes(conexion)
        for tabla, columna in referencias:
            cursor = conexion.execute(
                f'UPDATE "{tabla}" SET "{columna}" = ? WHERE "{columna}" = ?', (id_principal, id_duplicado))
            if cursor.rowcount:
                movidos[tabla] = movidos.get(tabla, 0) + cursor.rowcount

        # 3) Alias: los que ya tenía el duplicado pasan al principal y se suma su nombre.
        conexion.execute(
            "CREATE TABLE IF NOT EXISTS alias_clientes ("
            "alias TEXT PRIMARY KEY, id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente))")
        conexion.execute("UPDATE alias_clientes SET id_cliente = ? WHERE id_cliente = ?", (id_principal, id_duplicado))
        alias_nuevo = " ".join(nombre_duplicado.lower().split())
        if alias_nuevo != " ".join(nombre_principal.lower().split()):
            conexion.execute(
                "INSERT OR IGNORE INTO alias_clientes (alias, id_cliente) VALUES (?, ?)", (alias_nuevo, id_principal))

        # 4) Comprobar que no quedó nada apuntando al duplicado y recién ahí eliminarlo.
        for tabla, columna in referencias:
            restantes = conexion.execute(
                f'SELECT COUNT(*) FROM "{tabla}" WHERE "{columna}" = ?', (id_duplicado,)).fetchone()[0]
            if restantes:
                raise ErrorClientes(
                    f"Quedaron {restantes} registros de «{tabla}» sin mover. No se hizo ningún cambio.")
        conexion.execute("DELETE FROM clientes WHERE id_cliente = ?", (id_duplicado,))

        # 5) Completar datos de contacto vacíos del principal (después de borrar el duplicado,
        #    así un CUIT único no choca consigo mismo).
        completados = []
        for campo in CAMPOS_A_COMPLETAR:
            if campo in columnas_clientes and _vacio(principal[campo]) and not _vacio(duplicado[campo]):
                conexion.execute(
                    f'UPDATE clientes SET "{campo}" = ? WHERE id_cliente = ?', (duplicado[campo], id_principal))
                completados.append(campo)

        conexion.commit()
        return {
            "duplicado": nombre_duplicado, "principal": nombre_principal,
            "remitos": movidos.get("trabajos", 0), "cheques": movidos.get("cheques", 0),
            "vehiculos": movidos.get("vehiculos", 0), "completados": completados,
            "backup": backup,
        }
    except ErrorClientes:
        conexion.rollback()
        raise
    except sqlite3.Error as error:
        conexion.rollback()
        logger.exception("Error al unificar clientes %s -> %s", id_duplicado, id_principal)
        raise ErrorClientes("La base rechazó la operación. No se hizo ningún cambio.") from error
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
