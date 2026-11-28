"""Lógica de negocio para sueldos semanales, adelantos y gastos de gomeros."""
from datetime import date, timedelta
import re
import sqlite3
from database.connection import obtener_conexion
from utils.formateadores import parse_importe_ar


class ErrorGomeros(ValueError):
    """Error de validación del módulo."""


def inicio_semana(fecha):
    fecha = date.fromisoformat(fecha) if isinstance(fecha, str) else fecha
    return fecha - timedelta(days=fecha.weekday())


def _importe(valor):
    """Importe entero en pesos. Acepta el formato argentino: "1.250.000" o "1250000"."""
    numero = parse_importe_ar(valor, None)
    if numero is None or numero != int(numero):
        raise ErrorGomeros("El importe debe ser un número entero de pesos.")
    numero = int(numero)
    if numero <= 0:
        raise ErrorGomeros("El importe debe ser mayor que cero.")
    return numero


def _fecha_valida(fecha):
    try:
        return date.fromisoformat((fecha or "").strip())
    except (TypeError, ValueError) as exc:
        raise ErrorGomeros("La fecha no es válida.") from exc


def _validar_adelanto_sueldo_en_dia_habil(tipo, destino, fecha_obj):
    """Sábados y domingos no se piden adelantos del sueldo: solo del aguinaldo.

    El sábado se cobra directamente el resto del sueldo; y un adelanto de
    domingo quedaría fuera del tope semanal (que se calcula de lunes a sábado).
    """
    if tipo == "ADELANTO" and destino == "SUELDO" and fecha_obj.weekday() >= 5:
        raise ErrorGomeros(
            "Los sábados y domingos solo se pueden pedir adelantos del aguinaldo, "
            "no del sueldo."
        )


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

    _validar_adelanto_sueldo_en_dia_habil(tipo, destino, fecha_obj)

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



def actualizar_movimiento(id_movimiento, fecha, importe, concepto=""):
    """Corrige fecha, importe y concepto sin cambiar el tipo ni el destinatario."""
    fecha_obj = _fecha_valida(fecha)
    valor = _importe(importe)
    concepto = (concepto or "").strip()[:200]

    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        movimiento = conexion.execute(
            """SELECT id_movimiento, id_gomero, tipo, destino, periodo_aguinaldo
               FROM movimientos_gomeros WHERE id_movimiento = ?""",
            (id_movimiento,),
        ).fetchone()
        if movimiento is None:
            raise ErrorGomeros("El movimiento ya no existe.")

        if movimiento["tipo"] == "PAGO_SEMANAL" and fecha_obj.weekday() != 5:
            raise ErrorGomeros("El pago semanal se registra el sábado.")
        _validar_adelanto_sueldo_en_dia_habil(
            movimiento["tipo"], movimiento["destino"], fecha_obj
        )

        if movimiento["tipo"] in {"ADELANTO", "PAGO_SEMANAL"} and movimiento["destino"] == "SUELDO":
            lunes = inicio_semana(fecha_obj)
            sabado = lunes + timedelta(days=5)
            usado = conexion.execute(
                """SELECT COALESCE(SUM(importe), 0) AS total
                   FROM movimientos_gomeros
                   WHERE id_gomero = ? AND id_movimiento != ?
                     AND fecha BETWEEN ? AND ? AND destino = 'SUELDO'
                     AND tipo IN ('ADELANTO', 'PAGO_SEMANAL')""",
                (movimiento["id_gomero"], id_movimiento,
                 lunes.isoformat(), sabado.isoformat()),
            ).fetchone()["total"]
            gomero = conexion.execute(
                "SELECT sueldo_semanal FROM gomeros WHERE id_gomero = ?",
                (movimiento["id_gomero"],),
            ).fetchone()
            if gomero is None:
                raise ErrorGomeros("No se encontró el gomero asociado.")
            ausencias = _obtener_ausencias(conexion, movimiento["id_gomero"], lunes, sabado)
            descuento = _calcular_descuento_ausencias(gomero["sueldo_semanal"], len(ausencias))
            disponible = max(gomero["sueldo_semanal"] - descuento - usado, 0)
            if valor > disponible:
                raise ErrorGomeros(
                    "El importe corregido supera el saldo semanal disponible: $"
                    + format(disponible, ",.0f").replace(",", ".") + "."
                )

        if movimiento["tipo"] == "DESCUENTO_AGUINALDO":
            pendiente = conexion.execute(
                """SELECT COALESCE(SUM(
                       CASE WHEN tipo = 'ADELANTO' THEN importe
                            WHEN tipo = 'DESCUENTO_AGUINALDO' THEN -importe
                            ELSE 0 END
                   ), 0) AS total
                   FROM movimientos_gomeros
                   WHERE id_gomero = ? AND destino = 'AGUINALDO'
                     AND periodo_aguinaldo = ? AND id_movimiento != ?""",
                (movimiento["id_gomero"], movimiento["periodo_aguinaldo"], id_movimiento),
            ).fetchone()["total"]
            if valor > pendiente:
                raise ErrorGomeros("El importe corregido supera los adelantos pendientes de ese aguinaldo.")

        conexion.execute(
            """UPDATE movimientos_gomeros
               SET fecha = ?, importe = ?, concepto = ?
               WHERE id_movimiento = ?""",
            (fecha_obj.isoformat(), valor, concepto or None, id_movimiento),
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


def _validar_periodo_aguinaldo(periodo):
    periodo = str(periodo or "").strip()
    if not re.fullmatch(r"\d{4}-[12]", periodo):
        raise ErrorGomeros("Elegí un período válido de aguinaldo (por ejemplo, 2026-2).")
    return periodo


def guardar_aguinaldo(id_gomero, periodo_aguinaldo, importe):
    """Crea o actualiza el importe correspondiente a un gomero y semestre."""
    periodo = _validar_periodo_aguinaldo(periodo_aguinaldo)
    valor = _importe(importe)
    try:
        id_gomero = int(id_gomero)
    except (TypeError, ValueError) as exc:
        raise ErrorGomeros("Seleccioná un gomero válido.") from exc

    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        gomero = conexion.execute(
            "SELECT id_gomero FROM gomeros WHERE id_gomero = ? AND activo = 1",
            (id_gomero,),
        ).fetchone()
        if gomero is None:
            raise ErrorGomeros("El gomero no existe o está inactivo.")

        comprometido = conexion.execute(
            """
            SELECT
                COALESCE((
                    SELECT SUM(importe) FROM movimientos_gomeros
                    WHERE id_gomero = ? AND destino = 'AGUINALDO'
                      AND periodo_aguinaldo = ? AND tipo = 'ADELANTO'
                ), 0)
                +
                COALESCE((
                    SELECT SUM(p.importe)
                    FROM pagos_aguinaldo p
                    JOIN aguinaldos a ON a.id_aguinaldo = p.id_aguinaldo
                    WHERE a.id_gomero = ? AND a.periodo_aguinaldo = ?
                ), 0) AS total
            """,
            (id_gomero, periodo, id_gomero, periodo),
        ).fetchone()["total"]
        if valor < comprometido:
            raise ErrorGomeros(
                "El importe no puede ser menor que los adelantos y pagos ya registrados."
            )

        conexion.execute(
            """
            INSERT INTO aguinaldos (id_gomero, periodo_aguinaldo, importe)
            VALUES (?, ?, ?)
            ON CONFLICT(id_gomero, periodo_aguinaldo) DO UPDATE SET
                importe = excluded.importe,
                actualizado_en = CURRENT_TIMESTAMP
            """,
            (id_gomero, periodo, valor),
        )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def registrar_pago_aguinaldo(id_aguinaldo, fecha, importe, concepto="", usuario=""):
    """Registra un pago real y evita superar el saldo todavía adeudado."""
    fecha_obj = _fecha_valida(fecha)
    valor = _importe(importe)
    concepto = (concepto or "").strip()[:200]
    usuario = (usuario or "").strip()[:50]

    try:
        id_aguinaldo = int(id_aguinaldo)
    except (TypeError, ValueError) as exc:
        raise ErrorGomeros("Seleccioná un aguinaldo válido.") from exc

    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        aguinaldo = conexion.execute(
            """
            SELECT id_aguinaldo, id_gomero, periodo_aguinaldo, importe
            FROM aguinaldos
            WHERE id_aguinaldo = ?
            """,
            (id_aguinaldo,),
        ).fetchone()
        if aguinaldo is None:
            raise ErrorGomeros("El aguinaldo no existe.")

        adelantos = conexion.execute(
            """
            SELECT COALESCE(SUM(importe), 0) AS total
            FROM movimientos_gomeros
            WHERE id_gomero = ? AND destino = 'AGUINALDO'
              AND periodo_aguinaldo = ? AND tipo = 'ADELANTO'
            """,
            (aguinaldo["id_gomero"], aguinaldo["periodo_aguinaldo"]),
        ).fetchone()["total"]
        pagos = conexion.execute(
            """
            SELECT COALESCE(SUM(importe), 0) AS total
            FROM pagos_aguinaldo
            WHERE id_aguinaldo = ?
            """,
            (id_aguinaldo,),
        ).fetchone()["total"]
        saldo = max(aguinaldo["importe"] - adelantos - pagos, 0)
        if valor > saldo:
            raise ErrorGomeros(
                "El pago supera el saldo de aguinaldo disponible: $"
                + format(saldo, ",.0f").replace(",", ".") + "."
            )

        conexion.execute(
            """
            INSERT INTO pagos_aguinaldo
                (id_aguinaldo, fecha, importe, concepto, usuario)
            VALUES (?, ?, ?, ?, ?)
            """,
            (id_aguinaldo, fecha_obj.isoformat(), valor, concepto or None, usuario or None),
        )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def obtener_resumen_aguinaldos():
    """Devuelve el aguinaldo, adelantos, aplicaciones, pagos y saldo por gomero/período."""
    conexion = obtener_conexion()
    try:
        filas = conexion.execute(
            """
            SELECT
                a.id_aguinaldo,
                a.id_gomero,
                g.nombre,
                a.periodo_aguinaldo,
                a.importe,
                COALESCE((
                    SELECT SUM(m.importe)
                    FROM movimientos_gomeros m
                    WHERE m.id_gomero = a.id_gomero
                      AND m.destino = 'AGUINALDO'
                      AND m.periodo_aguinaldo = a.periodo_aguinaldo
                      AND m.tipo = 'ADELANTO'
                ), 0) AS adelantos,
                COALESCE((
                    SELECT SUM(m.importe)
                    FROM movimientos_gomeros m
                    WHERE m.id_gomero = a.id_gomero
                      AND m.destino = 'AGUINALDO'
                      AND m.periodo_aguinaldo = a.periodo_aguinaldo
                      AND m.tipo = 'DESCUENTO_AGUINALDO'
                ), 0) AS descuentos_aplicados,
                COALESCE((
                    SELECT SUM(p.importe)
                    FROM pagos_aguinaldo p
                    WHERE p.id_aguinaldo = a.id_aguinaldo
                ), 0) AS pagos
            FROM aguinaldos a
            JOIN gomeros g ON g.id_gomero = a.id_gomero
            ORDER BY a.periodo_aguinaldo DESC, g.nombre COLLATE NOCASE
            """
        ).fetchall()

        resumen = []
        for fila in filas:
            item = dict(fila)
            item["adelantos_pendientes"] = max(
                item["adelantos"] - item["descuentos_aplicados"], 0
            )
            comprometido = item["adelantos"] + item["pagos"]
            item["saldo"] = max(item["importe"] - comprometido, 0)
            item["excedente"] = max(comprometido - item["importe"], 0)
            resumen.append(item)
        return resumen
    finally:
        conexion.close()


def obtener_pagos_aguinaldo():
    """Lista los pagos reales de aguinaldo para su consulta histórica."""
    conexion = obtener_conexion()
    try:
        return conexion.execute(
            """
            SELECT p.id_pago_aguinaldo, p.fecha, p.importe, p.concepto, p.usuario,
                   a.periodo_aguinaldo, g.nombre
            FROM pagos_aguinaldo p
            JOIN aguinaldos a ON a.id_aguinaldo = p.id_aguinaldo
            JOIN gomeros g ON g.id_gomero = a.id_gomero
            ORDER BY p.fecha DESC, p.id_pago_aguinaldo DESC
            """
        ).fetchall()
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# Eliminación de movimientos (antes vivía dentro de la ruta)
# ---------------------------------------------------------------------------
def eliminar_movimiento(id_movimiento):
    """Elimina un movimiento y devuelve sus datos para dejarlos en la auditoría.

    Si es un adelanto de aguinaldo, no deja borrarlo cuando ya hay descuentos
    aplicados que dependen de él (el pendiente quedaría negativo).
    """
    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        fila = conexion.execute(
            """SELECT id_movimiento, id_gomero, tipo, destino, periodo_aguinaldo, importe
               FROM movimientos_gomeros WHERE id_movimiento = ?""",
            (id_movimiento,),
        ).fetchone()
        if fila is None:
            raise ErrorGomeros("El movimiento ya no existe.")

        if fila["tipo"] == "ADELANTO" and fila["destino"] == "AGUINALDO":
            totales = conexion.execute(
                """SELECT
                       COALESCE(SUM(CASE WHEN tipo = 'ADELANTO' THEN importe END), 0) AS adelantos,
                       COALESCE(SUM(CASE WHEN tipo = 'DESCUENTO_AGUINALDO' THEN importe END), 0) AS descuentos
                   FROM movimientos_gomeros
                   WHERE id_gomero = ? AND destino = 'AGUINALDO' AND periodo_aguinaldo = ?""",
                (fila["id_gomero"], fila["periodo_aguinaldo"]),
            ).fetchone()
            if totales["adelantos"] - fila["importe"] < totales["descuentos"]:
                raise ErrorGomeros(
                    "No se puede eliminar este adelanto: ya hay descuentos aplicados "
                    "al aguinaldo que dependen de él. Eliminá primero esos descuentos."
                )

        conexion.execute(
            "DELETE FROM movimientos_gomeros WHERE id_movimiento = ?", (id_movimiento,)
        )
        conexion.commit()
        return dict(fila)
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# Corrección y baja de aguinaldos y de sus pagos
# ---------------------------------------------------------------------------
def _sumas_aguinaldo(conexion, id_gomero, periodo, id_aguinaldo, excluir_pago=None):
    """Adelantos y pagos ya comprometidos de un aguinaldo (opcionalmente sin un pago)."""
    adelantos = conexion.execute(
        """SELECT COALESCE(SUM(importe), 0) AS total FROM movimientos_gomeros
           WHERE id_gomero = ? AND destino = 'AGUINALDO'
             AND periodo_aguinaldo = ? AND tipo = 'ADELANTO'""",
        (id_gomero, periodo),
    ).fetchone()["total"]
    pagos = conexion.execute(
        """SELECT COALESCE(SUM(importe), 0) AS total FROM pagos_aguinaldo
           WHERE id_aguinaldo = ? AND id_pago_aguinaldo != ?""",
        (id_aguinaldo, excluir_pago or 0),
    ).fetchone()["total"]
    return adelantos, pagos


def actualizar_aguinaldo(id_aguinaldo, importe):
    """Corrige el importe de un aguinaldo ya cargado (ej.: 60.000 en vez de 600.000)."""
    valor = _importe(importe)
    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        fila = conexion.execute(
            """SELECT id_aguinaldo, id_gomero, periodo_aguinaldo, importe
               FROM aguinaldos WHERE id_aguinaldo = ?""",
            (id_aguinaldo,),
        ).fetchone()
        if fila is None:
            raise ErrorGomeros("El aguinaldo ya no existe.")
        adelantos, pagos = _sumas_aguinaldo(
            conexion, fila["id_gomero"], fila["periodo_aguinaldo"], id_aguinaldo
        )
        if valor < adelantos + pagos:
            raise ErrorGomeros(
                "El importe no puede ser menor que los adelantos y pagos ya "
                "registrados ($" + format(adelantos + pagos, ",.0f").replace(",", ".") + ")."
            )
        conexion.execute(
            """UPDATE aguinaldos SET importe = ?, actualizado_en = CURRENT_TIMESTAMP
               WHERE id_aguinaldo = ?""",
            (valor, id_aguinaldo),
        )
        conexion.commit()
        return dict(fila)
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def eliminar_aguinaldo(id_aguinaldo):
    """Elimina un aguinaldo solo si no tiene adelantos ni pagos registrados."""
    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        fila = conexion.execute(
            """SELECT id_aguinaldo, id_gomero, periodo_aguinaldo, importe
               FROM aguinaldos WHERE id_aguinaldo = ?""",
            (id_aguinaldo,),
        ).fetchone()
        if fila is None:
            raise ErrorGomeros("El aguinaldo ya no existe.")
        adelantos, pagos = _sumas_aguinaldo(
            conexion, fila["id_gomero"], fila["periodo_aguinaldo"], id_aguinaldo
        )
        movimientos = conexion.execute(
            """SELECT COUNT(*) AS n FROM movimientos_gomeros
               WHERE id_gomero = ? AND destino = 'AGUINALDO' AND periodo_aguinaldo = ?""",
            (fila["id_gomero"], fila["periodo_aguinaldo"]),
        ).fetchone()["n"]
        if adelantos or pagos or movimientos:
            raise ErrorGomeros(
                "Este aguinaldo ya tiene adelantos o pagos. Primero eliminá "
                "esos registros y después podrás borrarlo."
            )
        conexion.execute("DELETE FROM aguinaldos WHERE id_aguinaldo = ?", (id_aguinaldo,))
        conexion.commit()
        return dict(fila)
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def actualizar_pago_aguinaldo(id_pago, fecha, importe, concepto=""):
    """Corrige fecha, importe y concepto de un pago de aguinaldo."""
    fecha_obj = _fecha_valida(fecha)
    valor = _importe(importe)
    concepto = (concepto or "").strip()[:200]
    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        fila = conexion.execute(
            """SELECT p.id_pago_aguinaldo, p.id_aguinaldo, a.id_gomero,
                      a.periodo_aguinaldo, a.importe AS importe_aguinaldo
               FROM pagos_aguinaldo p
               JOIN aguinaldos a ON a.id_aguinaldo = p.id_aguinaldo
               WHERE p.id_pago_aguinaldo = ?""",
            (id_pago,),
        ).fetchone()
        if fila is None:
            raise ErrorGomeros("El pago ya no existe.")
        adelantos, otros_pagos = _sumas_aguinaldo(
            conexion, fila["id_gomero"], fila["periodo_aguinaldo"],
            fila["id_aguinaldo"], excluir_pago=id_pago,
        )
        disponible = max(fila["importe_aguinaldo"] - adelantos - otros_pagos, 0)
        if valor > disponible:
            raise ErrorGomeros(
                "El pago corregido supera el saldo de aguinaldo disponible: $"
                + format(disponible, ",.0f").replace(",", ".") + "."
            )
        conexion.execute(
            """UPDATE pagos_aguinaldo SET fecha = ?, importe = ?, concepto = ?
               WHERE id_pago_aguinaldo = ?""",
            (fecha_obj.isoformat(), valor, concepto or None, id_pago),
        )
        conexion.commit()
        return dict(fila)
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def eliminar_pago_aguinaldo(id_pago):
    """Elimina un pago de aguinaldo mal cargado (el saldo se recalcula solo)."""
    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        fila = conexion.execute(
            "SELECT id_pago_aguinaldo, importe FROM pagos_aguinaldo WHERE id_pago_aguinaldo = ?",
            (id_pago,),
        ).fetchone()
        if fila is None:
            raise ErrorGomeros("El pago ya no existe.")
        conexion.execute(
            "DELETE FROM pagos_aguinaldo WHERE id_pago_aguinaldo = ?", (id_pago,)
        )
        conexion.commit()
        return dict(fila)
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# Ficha por gomero y planillas imprimibles
# ---------------------------------------------------------------------------
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def rango_periodo_aguinaldo(periodo):
    """'2026-1' -> (2026-01-01, 2026-06-30); '2026-2' -> (2026-07-01, 2026-12-31)."""
    periodo = _validar_periodo_aguinaldo(periodo)
    anio, semestre = periodo.split("-")
    anio = int(anio)
    if semestre == "1":
        return date(anio, 1, 1), date(anio, 6, 30)
    return date(anio, 7, 1), date(anio, 12, 31)


def _obtener_gomero(conexion, id_gomero):
    fila = conexion.execute(
        "SELECT id_gomero, nombre, sueldo_semanal, activo FROM gomeros WHERE id_gomero = ?",
        (id_gomero,),
    ).fetchone()
    if fila is None:
        raise ErrorGomeros("El gomero no existe.")
    return fila


def obtener_ficha_gomero(id_gomero, hoy=None):
    """Datos de la pestaña de un gomero: adelantos de sueldo por semana y aguinaldos.

    Todo viene ordenado con lo más reciente primero.
    """
    hoy = hoy or date.today()
    conexion = obtener_conexion()
    try:
        gomero = _obtener_gomero(conexion, id_gomero)
        sueldo = gomero["sueldo_semanal"]

        adelantos = conexion.execute(
            """SELECT id_movimiento, fecha, importe, concepto, usuario
               FROM movimientos_gomeros
               WHERE id_gomero = ? AND tipo = 'ADELANTO' AND destino = 'SUELDO'
               ORDER BY fecha DESC, id_movimiento DESC""",
            (id_gomero,),
        ).fetchall()
        ausencias = conexion.execute(
            "SELECT fecha FROM ausencias_gomeros WHERE gomero_id = ? ORDER BY fecha DESC",
            (id_gomero,),
        ).fetchall()

        # Agrupamos por semana (clave = lunes de esa semana).
        semanas = {}

        def semana(fecha_texto):
            lunes = inicio_semana(fecha_texto)
            return semanas.setdefault(lunes, {
                "lunes": lunes, "sabado": lunes + timedelta(days=5),
                "eventos": [], "total_adelantos": 0, "cantidad_ausencias": 0,
            })

        for a in adelantos:
            s = semana(a["fecha"])
            s["eventos"].append({
                "clase": "adelanto", **dict(a),
                "dia": DIAS_SEMANA[date.fromisoformat(a["fecha"]).weekday()],
            })
            s["total_adelantos"] += a["importe"]
        for a in ausencias:
            s = semana(a["fecha"])
            s["eventos"].append({
                "clase": "ausencia", "fecha": a["fecha"],
                "dia": DIAS_SEMANA[date.fromisoformat(a["fecha"]).weekday()],
            })
            s["cantidad_ausencias"] += 1

        lista_semanas = []
        for lunes in sorted(semanas, reverse=True):
            s = semanas[lunes]
            # Dentro de la semana: fecha descendente; a igual fecha, adelantos primero.
            s["eventos"].sort(key=lambda e: (e["fecha"], e.get("id_movimiento", 0)), reverse=True)
            s["descuento_ausencias"] = _calcular_descuento_ausencias(
                sueldo, s["cantidad_ausencias"]
            )
            s["resto"] = max(sueldo - s["descuento_ausencias"] - s["total_adelantos"], 0)
            s["iso"] = lunes.isoformat()
            lista_semanas.append(s)

        # ----- Aguinaldos: por período (aunque todavía no tengan importe cargado)
        cargados = {
            f["periodo_aguinaldo"]: f for f in conexion.execute(
                """SELECT id_aguinaldo, periodo_aguinaldo, importe
                   FROM aguinaldos WHERE id_gomero = ?""", (id_gomero,)
            ).fetchall()
        }
        movs = conexion.execute(
            """SELECT id_movimiento, tipo, fecha, importe, concepto, periodo_aguinaldo
               FROM movimientos_gomeros
               WHERE id_gomero = ? AND destino = 'AGUINALDO'
               ORDER BY fecha DESC, id_movimiento DESC""",
            (id_gomero,),
        ).fetchall()
        pagos = conexion.execute(
            """SELECT p.id_pago_aguinaldo, p.fecha, p.importe, p.concepto,
                      a.periodo_aguinaldo
               FROM pagos_aguinaldo p
               JOIN aguinaldos a ON a.id_aguinaldo = p.id_aguinaldo
               WHERE a.id_gomero = ?
               ORDER BY p.fecha DESC, p.id_pago_aguinaldo DESC""",
            (id_gomero,),
        ).fetchall()

        periodos = sorted(
            set(cargados) | {m["periodo_aguinaldo"] for m in movs}, reverse=True
        )
        aguinaldos = []
        for periodo in periodos:
            propios_movs = [dict(m) for m in movs if m["periodo_aguinaldo"] == periodo]
            propios_pagos = [dict(p) for p in pagos if p["periodo_aguinaldo"] == periodo]
            # Una sola lista (adelantos, descuentos y pagos), lo más nuevo primero.
            lineas = (
                [{"clase": "adelanto" if m["tipo"] == "ADELANTO" else "descuento",
                  "id": m["id_movimiento"], **m} for m in propios_movs]
                + [{"clase": "pago", "id": p["id_pago_aguinaldo"], **p} for p in propios_pagos]
            )
            lineas.sort(key=lambda l: (l["fecha"], l["clase"] == "pago", l["id"]), reverse=True)
            total_adelantos = sum(m["importe"] for m in propios_movs if m["tipo"] == "ADELANTO")
            total_descuentos = sum(
                m["importe"] for m in propios_movs if m["tipo"] == "DESCUENTO_AGUINALDO"
            )
            total_pagos = sum(p["importe"] for p in propios_pagos)
            cargado = cargados.get(periodo)
            importe = cargado["importe"] if cargado else None
            aguinaldos.append({
                "periodo": periodo,
                "id_aguinaldo": cargado["id_aguinaldo"] if cargado else None,
                "importe": importe,
                "adelantos": total_adelantos,
                "descuentos": total_descuentos,
                "pagos": total_pagos,
                "saldo": max(importe - total_adelantos - total_pagos, 0) if importe else None,
                "lineas": lineas,
            })

        # Semana actual, para las tarjetas de arriba.
        lunes_actual = inicio_semana(hoy)
        actual = semanas.get(lunes_actual)
        adelantado_actual = actual["total_adelantos"] if actual else 0
        ausencias_actual = actual["cantidad_ausencias"] if actual else 0
        descuento_actual = _calcular_descuento_ausencias(sueldo, ausencias_actual)
        return {
            "gomero": dict(gomero),
            "semanas": lista_semanas,
            "aguinaldos": aguinaldos,
            "semana_actual_iso": lunes_actual.isoformat(),
            "adelantado_actual": adelantado_actual,
            "resto_actual": max(sueldo - descuento_actual - adelantado_actual, 0),
            "periodo_actual": f"{hoy.year}-{1 if hoy.month <= 6 else 2}",
        }
    finally:
        conexion.close()


def obtener_planilla_semanal(id_gomero, semana_ref=None):
    """Datos de la hoja 'Control de adelantos semanales' (lunes a viernes).

    El resto a cobrar = sueldo - descuento por ausencias - adelantos al sueldo.
    No se resta el pago del sábado: la hoja sirve justamente para saber cuánto
    corresponde pagar ese día.
    """
    try:
        referencia = date.fromisoformat(semana_ref) if semana_ref else date.today()
    except (TypeError, ValueError) as exc:
        raise ErrorGomeros("La fecha seleccionada no es válida.") from exc
    lunes = inicio_semana(referencia)
    sabado = lunes + timedelta(days=5)
    domingo = lunes + timedelta(days=6)

    conexion = obtener_conexion()
    try:
        gomero = _obtener_gomero(conexion, id_gomero)
        sueldo = gomero["sueldo_semanal"]
        adelantos = conexion.execute(
            """SELECT fecha, importe, concepto FROM movimientos_gomeros
               WHERE id_gomero = ? AND tipo = 'ADELANTO' AND destino = 'SUELDO'
                 AND fecha BETWEEN ? AND ?
               ORDER BY fecha, id_movimiento""",
            (id_gomero, lunes.isoformat(), domingo.isoformat()),
        ).fetchall()
        ausencias = sorted(_obtener_ausencias(conexion, id_gomero, lunes, sabado))
    finally:
        conexion.close()

    dias = []
    for n in range(5):  # lunes a viernes
        dia = lunes + timedelta(days=n)
        dias.append({
            "nombre": DIAS_SEMANA[n], "fecha": dia,
            "importe": sum(a["importe"] for a in adelantos if a["fecha"] == dia.isoformat()),
        })

    total_adelantado = sum(a["importe"] for a in adelantos)
    descuento = _calcular_descuento_ausencias(sueldo, len(ausencias))

    observaciones = []
    for a in adelantos:
        fecha_a = date.fromisoformat(a["fecha"])
        fuera_de_tabla = fecha_a.weekday() >= 5  # no debería pasar, pero se avisa
        if a["concepto"] or fuera_de_tabla:
            texto = f"{DIAS_SEMANA[fecha_a.weekday()]} {fecha_a:%d/%m}: ${a['importe']:,.0f}".replace(",", ".")
            if a["concepto"]:
                texto += f" — {a['concepto']}"
            observaciones.append(texto)
    for f in ausencias:
        fecha_f = date.fromisoformat(f)
        observaciones.append(f"Faltó el {DIAS_SEMANA[fecha_f.weekday()].lower()} {fecha_f:%d/%m}")
    if ausencias:
        observaciones.append(
            "Descuento por ausencias: $" + format(descuento, ",.0f").replace(",", ".")
        )

    return {
        "gomero": dict(gomero), "lunes": lunes, "sabado": sabado, "dias": dias,
        "sueldo": sueldo, "total_adelantado": total_adelantado,
        "descuento_ausencias": descuento, "cantidad_ausencias": len(ausencias),
        "resto": max(sueldo - descuento - total_adelantado, 0),
        "observaciones": observaciones,
    }


def obtener_planilla_aguinaldo(id_gomero, periodo):
    """Datos de la hoja de aguinaldo de un semestre (adelantos y pagos, más nuevo primero)."""
    desde, hasta = rango_periodo_aguinaldo(periodo)
    conexion = obtener_conexion()
    try:
        gomero = _obtener_gomero(conexion, id_gomero)
        aguinaldo = conexion.execute(
            """SELECT id_aguinaldo, importe FROM aguinaldos
               WHERE id_gomero = ? AND periodo_aguinaldo = ?""",
            (id_gomero, periodo),
        ).fetchone()
        adelantos = conexion.execute(
            """SELECT fecha, importe, concepto FROM movimientos_gomeros
               WHERE id_gomero = ? AND destino = 'AGUINALDO' AND tipo = 'ADELANTO'
                 AND periodo_aguinaldo = ?
               ORDER BY fecha DESC, id_movimiento DESC""",
            (id_gomero, periodo),
        ).fetchall()
        pagos = []
        if aguinaldo:
            pagos = conexion.execute(
                """SELECT fecha, importe, concepto FROM pagos_aguinaldo
                   WHERE id_aguinaldo = ?
                   ORDER BY fecha DESC, id_pago_aguinaldo DESC""",
                (aguinaldo["id_aguinaldo"],),
            ).fetchall()
    finally:
        conexion.close()

    total_adelantos = sum(a["importe"] for a in adelantos)
    total_pagos = sum(p["importe"] for p in pagos)
    importe = aguinaldo["importe"] if aguinaldo else None
    return {
        "gomero": dict(gomero), "periodo": periodo, "desde": desde, "hasta": hasta,
        "importe": importe,
        "adelantos": [dict(a) for a in adelantos], "pagos": [dict(p) for p in pagos],
        "total_adelantos": total_adelantos, "total_pagos": total_pagos,
        "resto": max(importe - total_adelantos - total_pagos, 0) if importe else None,
    }
