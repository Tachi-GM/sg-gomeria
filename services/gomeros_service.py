"""Lógica de negocio para sueldos semanales, adelantos y gastos de gomeros."""
from datetime import date, timedelta
import re
import sqlite3
from database.connection import obtener_conexion


class ErrorGomeros(ValueError):
    """Error de validación del módulo."""


def inicio_semana(fecha):
    fecha = date.fromisoformat(fecha) if isinstance(fecha, str) else fecha
    return fecha - timedelta(days=fecha.weekday())


def _importe(valor):
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError) as exc:
        raise ErrorGomeros("El importe debe ser un número entero de pesos.") from exc
    if numero <= 0:
        raise ErrorGomeros("El importe debe ser mayor que cero.")
    return numero


def _fecha_valida(fecha):
    try:
        return date.fromisoformat((fecha or "").strip())
    except (TypeError, ValueError) as exc:
        raise ErrorGomeros("La fecha no es válida.") from exc


def _obtener_ausencias(conexion, id_gomero, lunes, sabado):
    filas = conexion.execute(
        """
        SELECT fecha
        FROM ausencias_gomeros
        WHERE gomero_id = ? AND fecha BETWEEN ? AND ?
        ORDER BY fecha
        """,
        (id_gomero, lunes.isoformat(), sabado.isoformat()),
    ).fetchall()
    return {fila["fecha"] for fila in filas}


def _calcular_descuento_ausencias(sueldo_semanal, cantidad_ausencias):
    return round(sueldo_semanal * cantidad_ausencias / 6)


def _validar_gomero(conexion, id_gomero):
    try:
        id_gomero = int(id_gomero)
    except (TypeError, ValueError) as exc:
        raise ErrorGomeros("Seleccioná un gomero válido.") from exc
    gomero = conexion.execute(
        "SELECT id_gomero, sueldo_semanal FROM gomeros WHERE id_gomero = ?",
        (id_gomero,),
    ).fetchone()
    if gomero is None:
        raise ErrorGomeros("El gomero no existe.")
    return gomero


def registrar_ausencia(gomero_id, fecha):
    """Registra una ausencia idempotente para un gomero y una fecha."""
    fecha_obj = _fecha_valida(fecha)
    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        _validar_gomero(conexion, gomero_id)
        conexion.execute(
            """
            INSERT INTO ausencias_gomeros (gomero_id, fecha)
            VALUES (?, ?)
            ON CONFLICT(gomero_id, fecha) DO NOTHING
            """,
            (int(gomero_id), fecha_obj.isoformat()),
        )
        conexion.commit()
    except ErrorGomeros:
        conexion.rollback()
        raise
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def eliminar_ausencia(gomero_id, fecha):
    """Elimina únicamente la ausencia indicada, sin afectar otras fechas."""
    fecha_obj = _fecha_valida(fecha)
    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        _validar_gomero(conexion, gomero_id)
        conexion.execute(
            "DELETE FROM ausencias_gomeros WHERE gomero_id = ? AND fecha = ?",
            (int(gomero_id), fecha_obj.isoformat()),
        )
        conexion.commit()
    except ErrorGomeros:
        conexion.rollback()
        raise
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def listar_gomeros():
    conexion = obtener_conexion()
    try:
        return conexion.execute(
            """SELECT id_gomero, nombre, sueldo_semanal FROM gomeros
               WHERE activo = 1 ORDER BY nombre COLLATE NOCASE"""
        ).fetchall()
    finally:
        conexion.close()


def guardar_gomero(nombre, sueldo_semanal="260000", id_gomero=None):
    nombre = (nombre or "").strip()
    if not nombre or len(nombre) > 80:
        raise ErrorGomeros("El nombre es obligatorio y no puede superar los 80 caracteres.")
    sueldo = _importe(sueldo_semanal)
    conexion = obtener_conexion()
    try:
        if id_gomero:
            cursor = conexion.execute(
                """UPDATE gomeros SET nombre = ?, sueldo_semanal = ?
                   WHERE id_gomero = ? AND activo = 1""",
                (nombre, sueldo, id_gomero),
            )
            if cursor.rowcount != 1:
                raise ErrorGomeros("No se encontró el gomero activo.")
        else:
            conexion.execute(
                "INSERT INTO gomeros (nombre, sueldo_semanal) VALUES (?, ?)",
                (nombre, sueldo),
            )
        conexion.commit()
    except sqlite3.IntegrityError as exc:
        conexion.rollback()
        raise ErrorGomeros("Ya existe un gomero con ese nombre.") from exc
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def desactivar_gomero(id_gomero):
    """Baja lógica: conserva al empleado y sus movimientos históricos."""
    conexion = obtener_conexion()
    try:
        cursor = conexion.execute(
            "UPDATE gomeros SET activo = 0 WHERE id_gomero = ? AND activo = 1",
            (id_gomero,),
        )
        if cursor.rowcount != 1:
            raise ErrorGomeros("No se encontró el gomero activo.")
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def registrar_movimiento(tipo, fecha, importe, id_gomero=None, destino="NO_APLICA",
                         periodo_aguinaldo=None, concepto="", usuario=""):
    """Valida y registra un movimiento completo dentro de una transacción."""
    tipos = {"ADELANTO", "PAGO_SEMANAL", "GASTO_GENERAL", "DESCUENTO_AGUINALDO"}
    if tipo not in tipos:
        raise ErrorGomeros("El tipo de movimiento no es válido.")
    fecha_obj = _fecha_valida(fecha)

    valor = _importe(importe)
    concepto = (concepto or "").strip()[:200]
    usuario = (usuario or "").strip()[:50]

    if tipo == "PAGO_SEMANAL" and fecha_obj.weekday() != 5:
        raise ErrorGomeros("El pago semanal se registra el sábado.")

    if tipo == "GASTO_GENERAL":
        if id_gomero not in (None, ""):
            raise ErrorGomeros("Los gastos generales no se asocian a un gomero.")
        id_gomero, destino, periodo_aguinaldo = None, "NO_APLICA", None
    else:
        try:
            id_gomero = int(id_gomero)
        except (TypeError, ValueError) as exc:
            raise ErrorGomeros("Seleccioná un gomero.") from exc
        if tipo == "DESCUENTO_AGUINALDO":
            destino = "AGUINALDO"
        if tipo == "PAGO_SEMANAL":
            destino = "SUELDO"
        if destino not in {"SUELDO", "AGUINALDO"}:
            raise ErrorGomeros("Elegí si el adelanto se descuenta del sueldo o del aguinaldo.")
        if destino == "AGUINALDO":
            if not re.fullmatch(r"\d{4}-[12]", str(periodo_aguinaldo or "")):
                raise ErrorGomeros("Elegí el período de aguinaldo (año y semestre).")
        else:
            periodo_aguinaldo = None

    conexion = obtener_conexion()
    try:
        # Serializa validación + INSERT para evitar superar el saldo por concurrencia.
        conexion.execute("BEGIN IMMEDIATE")
        if tipo != "GASTO_GENERAL":
            gomero = conexion.execute(
                """SELECT id_gomero, sueldo_semanal FROM gomeros
                   WHERE id_gomero = ? AND activo = 1""",
                (id_gomero,),
            ).fetchone()
            if gomero is None:
                raise ErrorGomeros("El gomero no existe o está inactivo.")

            if destino == "SUELDO" and tipo in {"ADELANTO", "PAGO_SEMANAL"}:
                lunes = inicio_semana(fecha_obj)
                sabado = lunes + timedelta(days=5)
                usado = conexion.execute(
                    """SELECT COALESCE(SUM(importe), 0) AS total
                       FROM movimientos_gomeros
                       WHERE id_gomero = ? AND fecha BETWEEN ? AND ?
                         AND destino = 'SUELDO'
                         AND tipo IN ('ADELANTO', 'PAGO_SEMANAL')""",
                    (id_gomero, lunes.isoformat(), sabado.isoformat()),
                ).fetchone()["total"]
                ausencias = _obtener_ausencias(conexion, id_gomero, lunes, sabado)
                descuento = _calcular_descuento_ausencias(
                    gomero["sueldo_semanal"], len(ausencias)
                )
                sueldo_disponible = max(gomero["sueldo_semanal"] - descuento, 0)
                if usado + valor > sueldo_disponible:
                    disponible = max(sueldo_disponible - usado, 0)
                    importe_formateado = format(disponible, ",.0f").replace(",", ".")
                    raise ErrorGomeros(
                        "El movimiento supera el saldo semanal disponible: $" + importe_formateado + "."
                    )

            if tipo == "DESCUENTO_AGUINALDO":
                pendiente = conexion.execute(
                    """SELECT COALESCE(SUM(
                           CASE WHEN tipo = 'ADELANTO' THEN importe
                                WHEN tipo = 'DESCUENTO_AGUINALDO' THEN -importe
                                ELSE 0 END
                       ), 0) AS total
                       FROM movimientos_gomeros
                       WHERE id_gomero = ? AND destino = 'AGUINALDO'
                         AND periodo_aguinaldo = ?""",
                    (id_gomero, periodo_aguinaldo),
                ).fetchone()["total"]
                if valor > pendiente:
                    raise ErrorGomeros(
                        "El descuento supera los adelantos pendientes de ese aguinaldo."
                    )

        conexion.execute(
            """INSERT INTO movimientos_gomeros
               (id_gomero, tipo, fecha, importe, destino, periodo_aguinaldo, concepto, usuario)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (id_gomero, tipo, fecha_obj.isoformat(), valor, destino,
             periodo_aguinaldo, concepto or None, usuario or None),
        )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def obtener_resumen(fecha_referencia=None):
    """Calcula los totales de la semana que contiene la fecha indicada."""
    try:
        fecha = date.fromisoformat(fecha_referencia) if fecha_referencia else date.today()
    except (TypeError, ValueError) as exc:
        raise ErrorGomeros("La fecha seleccionada no es válida.") from exc
    lunes = inicio_semana(fecha)
    domingo = lunes + timedelta(days=6)
    conexion = obtener_conexion()
    try:
        empleados = conexion.execute(
            """SELECT id_gomero, nombre, sueldo_semanal FROM gomeros
               WHERE activo = 1 ORDER BY nombre COLLATE NOCASE"""
        ).fetchall()
        movimientos = conexion.execute(
            """SELECT m.*, g.nombre AS nombre_gomero
               FROM movimientos_gomeros m
               LEFT JOIN gomeros g ON g.id_gomero = m.id_gomero
               WHERE m.fecha BETWEEN ? AND ?
               ORDER BY m.fecha DESC, m.id_movimiento DESC""",
            (lunes.isoformat(), domingo.isoformat()),
        ).fetchall()
        resumen = []
        for empleado in empleados:
            propios = [m for m in movimientos if m["id_gomero"] == empleado["id_gomero"]]
            ausencias = _obtener_ausencias(conexion, empleado["id_gomero"], lunes, lunes + timedelta(days=5))
            descuento_ausencias = _calcular_descuento_ausencias(
                empleado["sueldo_semanal"], len(ausencias)
            )
            adelantos = sum(
                m["importe"] for m in propios
                if m["tipo"] == "ADELANTO" and m["destino"] == "SUELDO"
            )
            pagos = sum(m["importe"] for m in propios if m["tipo"] == "PAGO_SEMANAL")
            por_dia = {}
            for numero_dia in range(6):
                dia = (lunes + timedelta(days=numero_dia)).isoformat()
                por_dia[dia] = sum(
                    m["importe"] for m in propios
                    if m["fecha"] == dia
                    and m["tipo"] in {"ADELANTO", "PAGO_SEMANAL"}
                    and m["destino"] == "SUELDO"
                )
            resumen.append({
                "id_gomero": empleado["id_gomero"], "nombre": empleado["nombre"],
                "sueldo": empleado["sueldo_semanal"], "adelantos": adelantos,
                "pagos": pagos, "ausencias": len(ausencias),
                "ausencias_por_dia": {
                    dia: dia in ausencias
                    for dia in (
                        (lunes + timedelta(days=n)).isoformat() for n in range(6)
                    )
                },
                "descuento_ausencias": descuento_ausencias,
                "saldo": max(
                    empleado["sueldo_semanal"]
                    - descuento_ausencias
                    - adelantos
                    - pagos,
                    0,
                ),
                "por_dia": por_dia,
            })
        gastos = [m for m in movimientos if m["tipo"] == "GASTO_GENERAL"]
        return {
            "lunes": lunes, "sabado": lunes + timedelta(days=5), "domingo": domingo,
            "anterior": (lunes - timedelta(days=7)).isoformat(),
            "siguiente": (lunes + timedelta(days=7)).isoformat(),
            "dias": [lunes + timedelta(days=n) for n in range(6)],
            "gomeros": resumen, "movimientos": movimientos, "gastos": gastos,
            "total_sueldos": sum(g["sueldo"] for g in resumen),
            "total_adelantos": sum(g["adelantos"] for g in resumen),
            "total_saldo": sum(max(g["saldo"], 0) for g in resumen),
            "total_gastos": sum(g["importe"] for g in gastos),
        }
    finally:
        conexion.close()


def obtener_saldos_aguinaldo():
    """Lista períodos de aguinaldo con adelantos todavía pendientes."""
    conexion = obtener_conexion()
    try:
        return conexion.execute(
            """SELECT g.id_gomero, g.nombre, m.periodo_aguinaldo,
                      SUM(CASE WHEN m.tipo = 'ADELANTO' THEN m.importe
                               WHEN m.tipo = 'DESCUENTO_AGUINALDO' THEN -m.importe
                               ELSE 0 END) AS pendiente
               FROM movimientos_gomeros m
               JOIN gomeros g ON g.id_gomero = m.id_gomero
               WHERE m.destino = 'AGUINALDO'
               GROUP BY g.id_gomero, g.nombre, m.periodo_aguinaldo
               HAVING pendiente > 0
               ORDER BY m.periodo_aguinaldo DESC, g.nombre COLLATE NOCASE"""
        ).fetchall()
    finally:
        conexion.close()
