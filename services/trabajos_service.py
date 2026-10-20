import sqlite3
import logging
from datetime import date, datetime
from database.connection import obtener_conexion
from utils.seguridad import registrar_auditoria
from utils.formateadores import (
    parse_int_seguro,
    parse_float_seguro,
    validar_y_formatear_remito,
)

logger = logging.getLogger("SG_Gomeria")


def crear_trabajo_completo(
    remito,
    id_cliente,
    tipo_lista,
    tipo,
    detalle,
    tareas_raw,
    cantidades_raw,
    fecha=None,
):
    """
    Procesa y registra un remito y sus renglones en la base de datos.
    Aplica validación de formato (OI: 5 dígitos, OIB: 00XXXX), fecha manual y
    descuento de IVA por cada tarea si el cliente no lleva IVA.
    Retorna una tupla: (exito: bool, mensaje: str)
    """
    if tipo not in ("OI", "OIB"):
        tipo = "OI"

    # Validación y estandarización del número de remito
    remito_valido, remito_formateado_o_err = validar_y_formatear_remito(tipo, remito)
    if not remito_valido:
        return False, f"Error: {remito_formateado_o_err}"
    remito = remito_formateado_o_err

    # Fecha: si no se especifica o viene vacía, usa la fecha de hoy
    if not fecha or not str(fecha).strip():
        fecha_final = date.today().strftime("%Y-%m-%d")
    else:
        try:
            # Validar formato ISO YYYY-MM-DD
            datetime.strptime(str(fecha).strip(), "%Y-%m-%d")
            fecha_final = str(fecha).strip()
        except ValueError:
            return False, "Error: Formato de fecha inválido (debe ser AAAA-MM-DD)"

    columnas_precio = {"1": "precio", "2": "precio2", "3": "precio3"}
    columna_elegida = columnas_precio.get(tipo_lista, "precio")

    # Filtrar solo tareas con id numérico válido
    ids_tareas = [parse_int_seguro(t) for t in tareas_raw if parse_int_seguro(t) > 0]
    if not ids_tareas:
        return False, "Error: Debes seleccionar al menos una tarea válida"

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # A. Verificar si el cliente existe y su condición de IVA
        cliente = cursor.execute(
            "SELECT con_iva FROM clientes WHERE id_cliente = ?", (id_cliente,)
        ).fetchone()
        if cliente is None:
            return False, "Error: Cliente inexistente"

        es_sin_iva = cliente["con_iva"] == 0

        # B. Calcular precios tarea por tarea
        total_trabajo = 0.0
        detalles_a_guardar = []

        for id_t, cant in zip(ids_tareas, cantidades_raw):
            cantidad = max(1, parse_int_seguro(cant, 1))
            cursor.execute(
                f"SELECT nom_tar, {columna_elegida} AS precio_final FROM tareas WHERE id_tarea = ?",
                (id_t,),
            )
            fila = cursor.fetchone()
            if fila:
                precio_lista = parse_float_seguro(fila["precio_final"], 0.0)

                # Descuento de IVA aplicado a cada renglón si corresponde
                if es_sin_iva:
                    precio_unitario = round(precio_lista / 1.21, 2)
                else:
                    precio_unitario = precio_lista

                subtotal = round(precio_unitario * cantidad, 2)
                total_trabajo += subtotal
                detalles_a_guardar.append((id_t, cantidad, precio_unitario, subtotal))

        # El total es la suma exacta de los renglones
        total_trabajo = round(total_trabajo, 2)

        # C. Guardar cabecera en 'trabajos'
        cursor.execute(
            """
            INSERT INTO trabajos (remito, tipo, fecha, id_cliente, total, detalle)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (remito, tipo, fecha_final, id_cliente, total_trabajo, detalle),
        )

        id_trabajo = cursor.lastrowid

        # D. Guardar renglones en 'detalle_trabajos'
        for id_t, cant, p_unit, sub in detalles_a_guardar:
            cursor.execute(
                """
                INSERT INTO detalle_trabajos (id_trabajo, id_tarea, cantidad, precio_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """,
                (id_trabajo, id_t, cant, p_unit, sub),
            )

        conexion.commit()
        registrar_auditoria(
            "EMISION_REMITO",
            f"Remito {tipo} #{remito} emitido para cliente ID {id_cliente}. Total: ${total_trabajo:,.2f}",
        )
        return (
            True,
            f"Remito {tipo} N° {remito} guardado. Total calculado: ${total_trabajo:,.2f}",
        )

    except sqlite3.IntegrityError:
        conexion.rollback()
        logger.warning(
            f"AUDITORIA | Intento de registrar remito duplicado: {tipo} #{remito}"
        )
        return False, f"Error: El remito N° {remito} ya fue registrado anteriormente."
    except Exception as e:
        conexion.rollback()
        logger.exception(f"Error inesperado al emitir remito #{remito}: {e}")
        return (
            False,
            "Ocurrió un error inesperado al procesar el remito. Intente nuevamente.",
        )
    finally:
        conexion.close()


def editar_cabecera_remito(id_trabajo, nuevo_tipo, nuevo_remito, nueva_fecha):
    """
    Permite modificar la fecha, el tipo y el número de un remito existente.
    Valida el formato de remito (OI: 5 dígitos, OIB: 00XXXX) y la unicidad del número.
    Retorna una tupla: (exito: bool, mensaje: str, remito_formateado: str|None)
    """
    if nuevo_tipo not in ("OI", "OIB"):
        return False, "Tipo de comprobante inválido (debe ser OI u OIB)", None

    remito_valido, remito_formateado = validar_y_formatear_remito(
        nuevo_tipo, nuevo_remito
    )
    if not remito_valido:
        return False, remito_formateado, None

    try:
        datetime.strptime(str(nueva_fecha).strip(), "%Y-%m-%d")
        fecha_final = str(nueva_fecha).strip()
    except (ValueError, TypeError):
        return False, "Formato de fecha inválido (debe ser AAAA-MM-DD)", None

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        trabajo_actual = cursor.execute(
            "SELECT remito, tipo, fecha FROM trabajos WHERE id_trabajo = ?",
            (id_trabajo,),
        ).fetchone()

        if not trabajo_actual:
            return False, "El trabajo especificado no existe", None

        cursor.execute(
            """
            UPDATE trabajos
            SET tipo = ?, remito = ?, fecha = ?
            WHERE id_trabajo = ?
        """,
            (nuevo_tipo, remito_formateado, fecha_final, id_trabajo),
        )
        conexion.commit()

        detalle_auditoria = (
            f"Trabajo ID {id_trabajo} modificado: "
            f"{trabajo_actual['tipo']} #{trabajo_actual['remito']} ({trabajo_actual['fecha']}) -> "
            f"{nuevo_tipo} #{remito_formateado} ({fecha_final})"
        )
        registrar_auditoria("MODIFICACION_REMITO", detalle_auditoria)
        return True, "Remito actualizado correctamente", remito_formateado

    except sqlite3.IntegrityError:
        conexion.rollback()
        logger.warning(
            f"AUDITORIA | Intento de duplicar remito en edición: {nuevo_tipo} #{remito_formateado}"
        )
        return (
            False,
            f"Error: Ya existe otro trabajo registrado con el remito {nuevo_tipo} #{remito_formateado}",
            None,
        )
    except Exception as e:
        conexion.rollback()
        logger.exception(f"Error al editar remito ID {id_trabajo}: {e}")
        return False, "Error inesperado al actualizar el remito", None
    finally:
        conexion.close()
