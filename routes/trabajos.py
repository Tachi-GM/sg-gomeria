import sqlite3
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.connection import obtener_conexion
from utils.seguridad import login_requerido, registrar_auditoria, modo_activo
from utils.formateadores import parse_int_seguro, parse_float_seguro
from services.trabajos_service import crear_trabajo_completo

logger = logging.getLogger("SG_Gomeria")
trabajos_bp = Blueprint("trabajos_bp", __name__)


# Pantalla Mataburros
@trabajos_bp.route("/mataburros")
@login_requerido
def mataburros():
    conexion = obtener_conexion()

    empresas = conexion.execute(
        "SELECT id_cliente, nom_cli, cuit, con_iva FROM clientes"
    ).fetchall()
    tareas = conexion.execute(
        "SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas"
    ).fetchall()
    clientes_json = [dict(e) for e in empresas]
    tareas_json = [dict(t) for t in tareas]

    conexion.close()
    return render_template(
        "mataburros.html",
        empresas=empresas,
        tareas=tareas,
        tareas_json=tareas_json,
        clientes_json=clientes_json,
        milagritos=modo_activo(),
    )


# Funcion de enviar trabajos
@trabajos_bp.route("/enviar-trabajo", methods=["POST"])
@login_requerido
def enviar_trabajo():
    remito = request.form.get("remito", "").strip()
    id_cliente = request.form.get("empresa")
    tipo_lista = request.form.get("tipo_lista", "1")
    detalle = request.form.get("detalles") or request.form.get("detalle", "")
    tipo = request.form.get("tipo", "OI").strip()
    if not remito:
        flash("Error: El número de remito es obligatorio", "danger")
        return redirect(url_for("trabajos_bp.mataburros"))
    if not id_cliente:
        flash("Error: Debes seleccionar una empresa", "danger")
        return redirect(url_for("trabajos_bp.mataburros"))
    # Delegamos toda la lógica y el cálculo al servicio
    exito, mensaje = crear_trabajo_completo(
        remito=remito,
        id_cliente=id_cliente,
        tipo_lista=tipo_lista,
        tipo=tipo,
        detalle=detalle,
        tareas_raw=request.form.getlist("tareas"),
        cantidades_raw=request.form.getlist("cantidades"),
    )
    flash(mensaje, "success" if exito else "danger")
    return redirect(url_for("trabajos_bp.mataburros"))


# Pantalla Precios
@trabajos_bp.route("/precios")
@login_requerido
def precios():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    tareas = cursor.execute(
        "SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas"
    ).fetchall()

    conexion.close()
    return render_template("precios.html", tareas=tareas, milagritos=modo_activo())


# Funciones de Agregar y Modificar Tareas
@trabajos_bp.route("/agregar-tarea", methods=["POST"])
@login_requerido
def agregar_tarea():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    nom_tar = request.form.get("nombre", "").strip()
    precio1 = parse_float_seguro(request.form.get("precio1-form"), 0.0)
    precio2 = parse_float_seguro(request.form.get("precio2-form"), 0.0)
    precio3 = parse_float_seguro(request.form.get("precio3-form"), 0.0)

    if not nom_tar:
        flash("El nombre de la tarea no puede estar vacío", "danger")
        return redirect(url_for("trabajos_bp.mataburros"))

    # Advertencias de coherencia comercial
    if not (precio1 <= precio2 <= precio3):
        flash(
            f'⚠️ Revisa los precios de "{nom_tar}": los valores no siguen el orden habitual L1 <= L2 <= L3.',
            "warning",
        )

    try:
        cursor.execute(
            """
            INSERT INTO tareas (nom_tar, precio, precio2, precio3)
            VALUES (?, ?, ?, ?)
        """,
            (nom_tar, precio1, precio2, precio3),
        )
        conexion.commit()
        registrar_auditoria(
            "ALTA_TAREA",
            f"Tarea '{nom_tar}' creada (L1: ${precio1}, L2: ${precio2}, L3: ${precio3})",
        )
        flash(f"Tarea '{nom_tar}' agregada correctamente.", "success")
    except sqlite3.IntegrityError:
        flash(f"Error: La tarea '{nom_tar}' ya existe en el tarifario.", "danger")
    except Exception as e:
        logger.exception(f"Error inesperado al agregar tarea: {e}")
        flash("Ocurrió un error al registrar la tarea.", "danger")
    finally:
        conexion.close()

    return redirect(url_for("trabajos_bp.mataburros"))


@trabajos_bp.route("/modificar-tarea", methods=["POST"])
@login_requerido
def modificar_tarea():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    id_tarea = parse_int_seguro(request.form.get("id_tarea"))
    nom_tar = request.form.get("nombre", "").strip()
    precio1 = parse_float_seguro(request.form.get("precio1"), 0.0)
    precio2 = parse_float_seguro(request.form.get("precio2"), 0.0)
    precio3 = parse_float_seguro(request.form.get("precio3"), 0.0)

    try:
        cursor.execute(
            """
            UPDATE tareas
            SET nom_tar = ?, precio = ?, precio2 = ?, precio3 = ?
            WHERE id_tarea = ?
        """,
            (nom_tar, precio1, precio2, precio3, id_tarea),
        )
        conexion.commit()
        registrar_auditoria(
            "MODIFICACION_TAREA", f"Tarea ID {id_tarea} ('{nom_tar}') actualizada"
        )
        flash(f"Tarifas de '{nom_tar}' actualizadas con éxito.", "success")
    except Exception as e:
        logger.exception(f"Error al modificar tarea ID {id_tarea}: {e}")
        flash("Ocurrió un error al actualizar las tarifas.", "danger")
    finally:
        conexion.close()

    return redirect(url_for("trabajos_bp.precios"))
