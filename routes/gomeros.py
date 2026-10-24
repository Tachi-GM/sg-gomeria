"""Rutas del control semanal de gomeros para usuarios autenticados."""
from datetime import date
import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from services.gomeros_service import (
    ErrorGomeros, guardar_gomero, desactivar_gomero, registrar_movimiento,
    obtener_resumen, listar_gomeros, obtener_saldos_aguinaldo,
)
from utils.seguridad import login_requerido, registrar_auditoria

logger = logging.getLogger("SG_Gomeria")
gomeros_bp = Blueprint("gomeros_bp", __name__)


def _volver_a_semana():
    semana = request.form.get("semana", "")
    return redirect(url_for("gomeros_bp.control_gomeros", semana=semana or None))


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
        saldos_aguinaldo=obtener_saldos_aguinaldo(), hoy=date.today().isoformat(),
    )


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
        registrar_auditoria("MOVIMIENTO_GOMEROS", f"Tipo {request.form.get('tipo')}; importe {request.form.get('importe')}")
        flash("Movimiento registrado correctamente.", "success")
    except ErrorGomeros as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Error al registrar movimiento de gomeros")
        flash("No se pudo registrar el movimiento.", "danger")
    return _volver_a_semana()


@gomeros_bp.route("/gomeros/movimiento/eliminar/<int:id_movimiento>", methods=["POST"])
@login_requerido
def eliminar_movimiento(id_movimiento):
    from database.connection import obtener_conexion
    conexion = obtener_conexion()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        fila = conexion.execute(
            "SELECT id_movimiento, tipo, importe FROM movimientos_gomeros WHERE id_movimiento = ?",
            (id_movimiento,),
        ).fetchone()
        if fila is None:
            flash("El movimiento ya no existe.", "warning")
        else:
            conexion.execute("DELETE FROM movimientos_gomeros WHERE id_movimiento = ?", (id_movimiento,))
            conexion.commit()
            registrar_auditoria("ELIMINACION_MOVIMIENTO_GOMEROS", f"ID {id_movimiento}; tipo {fila['tipo']}; importe {fila['importe']}")
            flash("Movimiento eliminado.", "success")
    except Exception:
        conexion.rollback()
        logger.exception("Error al eliminar movimiento %s", id_movimiento)
        flash("No se pudo eliminar el movimiento.", "danger")
    finally:
        conexion.close()
    return _volver_a_semana()
