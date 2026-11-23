"""Rutas del control semanal de gomeros para usuarios autenticados."""
from datetime import date
import logging
import re

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for,
)

from services.gomeros_service import (
    ErrorGomeros, guardar_gomero, desactivar_gomero, registrar_movimiento, actualizar_movimiento,
    obtener_resumen, listar_gomeros, obtener_saldos_aguinaldo,
    registrar_ausencia, eliminar_ausencia, guardar_aguinaldo,
    registrar_pago_aguinaldo, obtener_resumen_aguinaldos, obtener_pagos_aguinaldo,
    eliminar_movimiento as eliminar_movimiento_servicio,
    actualizar_aguinaldo, eliminar_aguinaldo,
    actualizar_pago_aguinaldo, eliminar_pago_aguinaldo,
    obtener_ficha_gomero, obtener_planilla_semanal, obtener_planilla_aguinaldo,
)
from utils.seguridad import login_requerido, registrar_auditoria

logger = logging.getLogger("SG_Gomeria")
gomeros_bp = Blueprint("gomeros_bp", __name__)


def _booleano_formulario(valor):
    return str(valor).strip().lower() in {"1", "true", "si", "sí", "on"}


def _volver_a_semana(ancla_defecto=""):
    """Redirige al lugar de origen: la ficha de un gomero o la semana general.

    `volver_a` y `ancla` vienen de campos ocultos del formulario, por eso se
    validan: solo se aceptan destinos propios (nunca una URL cualquiera) y un
    ancla con letras, números y guiones. Así evitamos un "open redirect".
    """
    volver_a = request.form.get("volver_a", "")
    if re.fullmatch(r"ficha:\d+", volver_a):
        destino = url_for("gomeros_bp.ficha_gomero", id_gomero=int(volver_a[6:]))
    else:
        semana = request.form.get("semana", "")
        destino = url_for("gomeros_bp.control_gomeros", semana=semana or None)
    ancla = request.form.get("ancla") or ancla_defecto
    if re.fullmatch(r"[A-Za-z0-9_-]{1,40}", ancla or ""):
        destino += "#" + ancla
    return redirect(destino)


@gomeros_bp.route("/gomeros")
@login_requerido
def control_gomeros():
    referencia = request.args.get("semana") or date.today().isoformat()
    try:
        resumen = obtener_resumen(referencia)
    except ValueError:
        flash("La fecha seleccionada no es válida; se muestra la semana actual.", "warning")
        resumen = obtener_resumen(date.today().isoformat())
    return render_template(
        "gomeros.html", resumen=resumen, gomeros=listar_gomeros(),
        saldos_aguinaldo=obtener_saldos_aguinaldo(),
        aguinaldos=obtener_resumen_aguinaldos(),
        pagos_aguinaldo=obtener_pagos_aguinaldo(),
        hoy=date.today().isoformat(),
    )



@gomeros_bp.route("/gomeros/aguinaldo/guardar", methods=["POST"])
@login_requerido
def guardar_aguinaldo_ruta():
    try:
        guardar_aguinaldo(
            request.form.get("id_gomero"),
            request.form.get("periodo_aguinaldo"),
            request.form.get("importe"),
        )
        registrar_auditoria(
            "AGUINALDO_CONFIGURADO",
            f"Gomero {request.form.get('id_gomero')}; "
            f"período {request.form.get('periodo_aguinaldo')}; "
            f"importe {request.form.get('importe')}",
        )
        flash("Aguinaldo guardado correctamente.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al guardar aguinaldo")
        flash("No se pudo guardar el aguinaldo.", "danger")
    return _volver_a_semana("gestion-aguinaldos")


@gomeros_bp.route("/gomeros/aguinaldo/pagar", methods=["POST"])
@login_requerido
def pagar_aguinaldo_ruta():
    try:
        registrar_pago_aguinaldo(
            request.form.get("id_aguinaldo"),
            request.form.get("fecha"),
            request.form.get("importe"),
            request.form.get("concepto"),
            session.get("usuario", ""),
        )
        registrar_auditoria(
            "PAGO_AGUINALDO",
            f"Aguinaldo ID {request.form.get('id_aguinaldo')}; "
            f"importe {request.form.get('importe')}",
        )
        flash("Pago de aguinaldo registrado correctamente.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al registrar pago de aguinaldo")
        flash("No se pudo registrar el pago de aguinaldo.", "danger")
    return _volver_a_semana("gestion-aguinaldos")

@gomeros_bp.route("/gomeros/crear", methods=["POST"])
@login_requerido
def crear_gomero():
    nombre = request.form.get("nombre", "").strip()
    try:
        guardar_gomero(nombre, request.form.get("sueldo_semanal", "260000"))
        registrar_auditoria("ALTA_GOMERO", f"Gomero creado: {nombre}")
        flash("Gomero agregado correctamente.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al crear gomero")
        flash("No se pudo guardar el gomero.", "danger")
    return _volver_a_semana()


@gomeros_bp.route("/gomeros/editar/<int:id_gomero>", methods=["POST"])
@login_requerido
def editar_gomero(id_gomero):
    try:
        guardar_gomero(request.form.get("nombre"), request.form.get("sueldo_semanal", "260000"), id_gomero)
        registrar_auditoria("EDICION_GOMERO", f"Gomero ID {id_gomero} actualizado")
        flash("Datos del gomero actualizados.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al editar gomero ID %s", id_gomero)
        flash("No se pudieron actualizar los datos.", "danger")
    return _volver_a_semana()


@gomeros_bp.route("/gomeros/desactivar/<int:id_gomero>", methods=["POST"])
@login_requerido
def desactivar(id_gomero):
    try:
        desactivar_gomero(id_gomero)
        registrar_auditoria("BAJA_GOMERO", f"Gomero ID {id_gomero} desactivado")
        flash("Gomero desactivado. Su historial se conserva.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al desactivar gomero ID %s", id_gomero)
        flash("No se pudo desactivar el gomero.", "danger")
    return _volver_a_semana()


@gomeros_bp.route("/gomeros/movimiento", methods=["POST"])
@login_requerido
def nuevo_movimiento():
    try:
        registrar_movimiento(
            tipo=request.form.get("tipo"), fecha=request.form.get("fecha"),
            importe=request.form.get("importe"), id_gomero=request.form.get("id_gomero") or None,
            destino=request.form.get("destino", "NO_APLICA"),
            periodo_aguinaldo=request.form.get("periodo_aguinaldo") or None,
            concepto=request.form.get("concepto"), usuario=session.get("usuario", ""),
        )
        registrar_auditoria(
            "MOVIMIENTO_GOMEROS",
            f"Tipo {request.form.get('tipo')}; "
            f"importe {request.form.get('importe')}",
        )
        flash("Movimiento registrado correctamente.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al registrar movimiento de gomeros")
        flash("No se pudo registrar el movimiento.", "danger")
    return _volver_a_semana()


@gomeros_bp.route("/gomeros/movimiento/editar/<int:id_movimiento>", methods=["POST"])
@login_requerido
def editar_movimiento(id_movimiento):
    try:
        actualizar_movimiento(
            id_movimiento,
            fecha=request.form.get("fecha"),
            importe=request.form.get("importe"),
            concepto=request.form.get("concepto"),
        )
        registrar_auditoria(
            "CORRECCION_MOVIMIENTO_GOMEROS",
            f"ID {id_movimiento}; importe corregido a {request.form.get('importe')}",
        )
        flash("Movimiento corregido. Los saldos fueron recalculados.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al corregir movimiento %s", id_movimiento)
        flash("No se pudo corregir el movimiento.", "danger")
    return _volver_a_semana()


@gomeros_bp.route("/gomeros/ausencia", methods=["POST"])
@login_requerido
def cambiar_ausencia():
    datos_json = request.get_json(silent=True) or {}
    gomero_id = request.form.get("gomero_id") or datos_json.get("gomero_id")
    fecha = request.form.get("fecha") or datos_json.get("fecha")
    ausente = _booleano_formulario(
        request.form.get("ausente", datos_json.get("ausente", False))
    )
    try:
        if ausente:
            registrar_ausencia(gomero_id, fecha)
        else:
            eliminar_ausencia(gomero_id, fecha)
        resumen = obtener_resumen(fecha)
        fila = next(
            gomero for gomero in resumen["gomeros"]
            if gomero["id_gomero"] == int(gomero_id)
        )
        return jsonify({
            "exito": True,
            "gomero_id": int(gomero_id),
            "fecha": fecha,
            "ausente": ausente,
            "saldo": fila["saldo"],
            "descuento_ausencias": fila["descuento_ausencias"],
            "ausencias": fila["ausencias"],
        })
    except (ErrorGomeros, ValueError) as exc:
        return jsonify({"exito": False, "mensaje": str(exc)}), 400
    except Exception:
        logger.exception("Error al cambiar asistencia de gomero")
        return jsonify({
            "exito": False,
            "mensaje": "No se pudo actualizar la asistencia.",
        }), 500


@gomeros_bp.route("/gomeros/movimiento/eliminar/<int:id_movimiento>", methods=["POST"])
@login_requerido
def eliminar_movimiento(id_movimiento):
    try:
        fila = eliminar_movimiento_servicio(id_movimiento)
        registrar_auditoria(
            "ELIMINACION_MOVIMIENTO_GOMEROS",
            f"ID {id_movimiento}; tipo {fila['tipo']}; importe {fila['importe']}",
        )
        flash("Movimiento eliminado.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al eliminar movimiento %s", id_movimiento)
        flash("No se pudo eliminar el movimiento.", "danger")
    return _volver_a_semana()


# ---------------------------------------------------------------------------
# Corrección y baja de aguinaldos y pagos
# ---------------------------------------------------------------------------
def _ejecutar_aguinaldo(accion, auditoria, detalle, mensaje_ok, mensaje_error):
    """Ejecuta una acción de aguinaldo, avisa con flash y vuelve a la sección."""
    try:
        resultado = accion()
        registrar_auditoria(auditoria, detalle(resultado))
        flash(mensaje_ok, "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception(mensaje_error)
        flash(mensaje_error, "danger")
    return _volver_a_semana("gestion-aguinaldos")


@gomeros_bp.route("/gomeros/aguinaldo/editar/<int:id_aguinaldo>", methods=["POST"])
@login_requerido
def editar_aguinaldo(id_aguinaldo):
    importe = request.form.get("importe")
    return _ejecutar_aguinaldo(
        lambda: actualizar_aguinaldo(id_aguinaldo, importe),
        "CORRECCION_AGUINALDO",
        lambda fila: f"Aguinaldo ID {id_aguinaldo} ({fila['periodo_aguinaldo']}): "
                     f"importe {fila['importe']} -> {importe}",
        "Aguinaldo corregido.",
        "No se pudo corregir el aguinaldo.",
    )


@gomeros_bp.route("/gomeros/aguinaldo/eliminar/<int:id_aguinaldo>", methods=["POST"])
@login_requerido
def borrar_aguinaldo(id_aguinaldo):
    return _ejecutar_aguinaldo(
        lambda: eliminar_aguinaldo(id_aguinaldo),
        "ELIMINACION_AGUINALDO",
        lambda fila: f"Aguinaldo ID {id_aguinaldo} ({fila['periodo_aguinaldo']}) "
                     f"por ${fila['importe']} eliminado",
        "Aguinaldo eliminado.",
        "No se pudo eliminar el aguinaldo.",
    )


@gomeros_bp.route("/gomeros/aguinaldo/pago/editar/<int:id_pago>", methods=["POST"])
@login_requerido
def editar_pago_aguinaldo(id_pago):
    importe = request.form.get("importe")
    return _ejecutar_aguinaldo(
        lambda: actualizar_pago_aguinaldo(
            id_pago, request.form.get("fecha"), importe, request.form.get("concepto")
        ),
        "CORRECCION_PAGO_AGUINALDO",
        lambda fila: f"Pago ID {id_pago}; importe corregido a {importe}",
        "Pago de aguinaldo corregido.",
        "No se pudo corregir el pago de aguinaldo.",
    )


@gomeros_bp.route("/gomeros/aguinaldo/pago/eliminar/<int:id_pago>", methods=["POST"])
@login_requerido
def borrar_pago_aguinaldo(id_pago):
    return _ejecutar_aguinaldo(
        lambda: eliminar_pago_aguinaldo(id_pago),
        "ELIMINACION_PAGO_AGUINALDO",
        lambda fila: f"Pago ID {id_pago} por ${fila['importe']} eliminado",
        "Pago de aguinaldo eliminado.",
        "No se pudo eliminar el pago de aguinaldo.",
    )


# ---------------------------------------------------------------------------
# Pestaña por gomero y hojas imprimibles
# ---------------------------------------------------------------------------
@gomeros_bp.route("/gomeros/<int:id_gomero>")
@login_requerido
def ficha_gomero(id_gomero):
    try:
        ficha = obtener_ficha_gomero(id_gomero)
    except ErrorGomeros:
        abort(404)
    return render_template("gomero_ficha.html", ficha=ficha, hoy=date.today().isoformat())


@gomeros_bp.route("/gomeros/<int:id_gomero>/imprimir/semana")
@login_requerido
def imprimir_semana(id_gomero):
    try:
        planilla = obtener_planilla_semanal(id_gomero, request.args.get("semana"))
    except ErrorGomeros as exc:
        if "no existe" in str(exc):
            abort(404)
        flash(str(exc), "danger")
        return redirect(url_for("gomeros_bp.ficha_gomero", id_gomero=id_gomero))
    return render_template("gomero_planilla_semana.html", p=planilla)


@gomeros_bp.route("/gomeros/<int:id_gomero>/imprimir/aguinaldo")
@login_requerido
def imprimir_aguinaldo(id_gomero):
    try:
        planilla = obtener_planilla_aguinaldo(id_gomero, request.args.get("periodo"))
    except ErrorGomeros as exc:
        if "no existe" in str(exc):
            abort(404)
        flash(str(exc), "danger")
        return redirect(url_for("gomeros_bp.ficha_gomero", id_gomero=id_gomero))
    return render_template("gomero_planilla_aguinaldo.html", p=planilla)
