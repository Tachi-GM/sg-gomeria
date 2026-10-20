import sqlite3
import logging
from datetime import date
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from database.connection import obtener_conexion
from utils.seguridad import login_requerido, registrar_auditoria, modo_activo
from utils.formateadores import parse_int_seguro, parse_float_seguro
from services.trabajos_service import (
    crear_trabajo_completo,
    editar_cabecera_remito,
)

logger = logging.getLogger("SG_Gomeria")
trabajos_bp = Blueprint("trabajos_bp", __name__)


# Pantalla Mataburros
@trabajos_bp.route("/mataburros")
@login_requerido
def mataburros():
    conexion = obtener_conexion()

    empresas = conexion.execute(
        "SELECT id_cliente, nom_cli, cuit, con_iva, lista_precios FROM clientes ORDER BY nom_cli ASC"
    ).fetchall()
    tareas = conexion.execute(
        "SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas WHERE activa = 1 ORDER BY nom_tar ASC"
    ).fetchall()
    clientes_json = [dict(e) for e in empresas]
    tareas_json = [dict(t) for t in tareas]
    fecha_hoy = date.today().strftime("%Y-%m-%d")

    conexion.close()
    return render_template(
        "mataburros.html",
        empresas=empresas,
        tareas=tareas,
        tareas_json=tareas_json,
        clientes_json=clientes_json,
        fecha_hoy=fecha_hoy,
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
    fecha = request.form.get("fecha", "").strip()

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
        fecha=fecha,
    )
    flash(mensaje, "success" if exito else "danger")
    return redirect(url_for("trabajos_bp.mataburros"))


# Endpoint asíncrono para editar remito desde el modal de clientes / historial
@trabajos_bp.route("/editar-remito", methods=["POST"])
@login_requerido
def editar_remito():
    id_trabajo = parse_int_seguro(request.form.get("id_trabajo"))
    nuevo_tipo = request.form.get("tipo", "OI").strip()
    nuevo_remito = request.form.get("remito", "").strip()
    nueva_fecha = request.form.get("fecha", "").strip()

    if not id_trabajo:
        return jsonify({"exito": False, "mensaje": "ID de trabajo inválido"}), 400

    exito, mensaje, remito_formateado = editar_cabecera_remito(
        id_trabajo, nuevo_tipo, nuevo_remito, nueva_fecha
    )

    status_code = 200 if exito else 400
    return (
        jsonify(
            {
                "exito": exito,
                "mensaje": mensaje,
                "id_trabajo": id_trabajo,
                "tipo": nuevo_tipo,
                "remito": remito_formateado or nuevo_remito,
                "fecha": nueva_fecha,
            }
        ),
        status_code,
    )


# Pantalla Precios
@trabajos_bp.route("/precios")
@login_requerido
def precios():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    tareas = cursor.execute(
        "SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas ORDER BY nom_tar ASC"
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


# Endpoint asíncrono para marcar/desmarcar remito como pagado
@trabajos_bp.route("/actualizar-estado", methods=["POST"])
@login_requerido
def actualizar_estado():
    id_trabajo = parse_int_seguro(request.form.get("id_trabajo"))
    nuevo_estado = request.form.get("estado", "").strip()

    estados_validos = ("PENDIENTE", "EN PROCESO", "PAGADO")
    if not id_trabajo or nuevo_estado not in estados_validos:
        return jsonify({"exito": False, "mensaje": "Datos inválidos"}), 400

    conexion = obtener_conexion()
    try:
        conexion.execute(
            "UPDATE trabajos SET estado = ? WHERE id_trabajo = ?",
            (nuevo_estado, id_trabajo),
        )
        conexion.commit()
        registrar_auditoria(
            "ESTADO_REMITO",
            f"Trabajo ID {id_trabajo} marcado como '{nuevo_estado}'",
        )
        return jsonify({"exito": True, "estado": nuevo_estado})
    except Exception as e:
        logger.exception(f"Error al actualizar estado del trabajo ID {id_trabajo}: {e}")
        return jsonify({"exito": False, "mensaje": "Error interno"}), 500
    finally:
        conexion.close()
