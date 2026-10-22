"""Administración de usuarios del sistema, exclusiva para administradores."""

import logging
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from database.connection import obtener_conexion
from utils.seguridad import login_requerido, solo_admin, registrar_auditoria

logger = logging.getLogger("SG_Gomeria")
usuarios_bp = Blueprint("usuarios_bp", __name__)

ROLES_VALIDOS = {"admin", "usuario"}
LONGITUD_MINIMA_CLAVE = 8


def _cantidad_administradores(conexion):
    fila = conexion.execute(
        "SELECT COUNT(*) AS total FROM usuarios WHERE rol = ?", ("admin",)
    ).fetchone()
    return fila["total"]


@usuarios_bp.route("/usuarios", methods=["GET"])
@login_requerido
@solo_admin
def listar_usuarios():
    conexion = obtener_conexion()
    try:
        usuarios = conexion.execute(
            "SELECT id_usuario, usuario, rol FROM usuarios ORDER BY usuario COLLATE NOCASE"
        ).fetchall()
    finally:
        conexion.close()

    return render_template("usuarios.html", usuarios=usuarios)


@usuarios_bp.route("/usuarios/crear", methods=["POST"])
@login_requerido
@solo_admin
def crear_usuario():
    usuario = request.form.get("usuario", "").strip()
    clave = request.form.get("password", "")
    rol = request.form.get("rol", "usuario").strip()

    if not usuario or len(usuario) > 50:
        flash("El usuario es obligatorio y no puede superar los 50 caracteres.", "danger")
        return redirect(url_for("usuarios_bp.listar_usuarios"))
    if len(clave) < LONGITUD_MINIMA_CLAVE:
        flash("La contraseña debe tener al menos 8 caracteres.", "danger")
        return redirect(url_for("usuarios_bp.listar_usuarios"))
    if rol not in ROLES_VALIDOS:
        flash("El rol seleccionado no es válido.", "danger")
        return redirect(url_for("usuarios_bp.listar_usuarios"))

    conexion = obtener_conexion()
    try:
        conexion.execute(
            "INSERT INTO usuarios (usuario, contraseña, rol) VALUES (?, ?, ?)",
            (usuario, generate_password_hash(clave), rol),
        )
        conexion.commit()
        registrar_auditoria("ALTA_USUARIO", f"Usuario '{usuario}' creado con rol '{rol}'")
        flash(f"El usuario '{usuario}' fue creado correctamente.", "success")
    except sqlite3.IntegrityError:
        conexion.rollback()
        flash("No se pudo crear el usuario. El nombre ya existe o los datos no son válidos.", "danger")
    except Exception:
        conexion.rollback()
        logger.exception("Error al crear usuario")
        flash("Ocurrió un error al crear el usuario.", "danger")
    finally:
        conexion.close()

    return redirect(url_for("usuarios_bp.listar_usuarios"))


@usuarios_bp.route("/usuarios/editar/<int:id_usuario>", methods=["POST"])
@login_requerido
@solo_admin
def editar_usuario(id_usuario):
    nuevo_usuario = request.form.get("usuario", "").strip()
    nuevo_rol = request.form.get("rol", "").strip()
    nueva_clave = request.form.get("password", "")

    if not nuevo_usuario or len(nuevo_usuario) > 50:
        flash("El usuario es obligatorio y no puede superar los 50 caracteres.", "danger")
        return redirect(url_for("usuarios_bp.listar_usuarios"))
    if nuevo_rol not in ROLES_VALIDOS:
        flash("El rol seleccionado no es válido.", "danger")
        return redirect(url_for("usuarios_bp.listar_usuarios"))
    if nueva_clave and len(nueva_clave) < LONGITUD_MINIMA_CLAVE:
        flash("La nueva contraseña debe tener al menos 8 caracteres.", "danger")
        return redirect(url_for("usuarios_bp.listar_usuarios"))

    conexion = obtener_conexion()
    try:
        actual = conexion.execute(
            "SELECT id_usuario, usuario, rol FROM usuarios WHERE id_usuario = ?",
            (id_usuario,),
        ).fetchone()
        if actual is None:
            flash("El usuario que intentás editar no existe.", "warning")
            return redirect(url_for("usuarios_bp.listar_usuarios"))

        if actual["rol"] == "admin" and nuevo_rol != "admin":
            if _cantidad_administradores(conexion) <= 1:
                flash("No podés quitar el rol de administrador al último administrador.", "danger")
                return redirect(url_for("usuarios_bp.listar_usuarios"))

        if nueva_clave:
            conexion.execute(
                """UPDATE usuarios
                   SET usuario = ?, rol = ?, contraseña = ?
                   WHERE id_usuario = ?""",
                (nuevo_usuario, nuevo_rol, generate_password_hash(nueva_clave), id_usuario),
            )
        else:
            conexion.execute(
                "UPDATE usuarios SET usuario = ?, rol = ? WHERE id_usuario = ?",
                (nuevo_usuario, nuevo_rol, id_usuario),
            )
        conexion.commit()

        if session.get("usuario") == actual["usuario"]:
            session["usuario"] = nuevo_usuario
            session["rol"] = nuevo_rol

        registrar_auditoria(
            "MODIFICACION_USUARIO",
            f"Usuario ID {id_usuario}: '{actual['usuario']}' actualizado a '{nuevo_usuario}' con rol '{nuevo_rol}'",
        )
        flash(f"El usuario '{nuevo_usuario}' fue actualizado correctamente.", "success")
    except sqlite3.IntegrityError:
        conexion.rollback()
        flash("No se pudo actualizar. El nombre de usuario ya está en uso.", "danger")
    except Exception:
        conexion.rollback()
        logger.exception("Error al editar usuario ID %s", id_usuario)
        flash("Ocurrió un error al actualizar el usuario.", "danger")
    finally:
        conexion.close()

    return redirect(url_for("usuarios_bp.listar_usuarios"))


@usuarios_bp.route("/usuarios/eliminar/<int:id_usuario>", methods=["POST"])
@login_requerido
@solo_admin
def eliminar_usuario(id_usuario):
    conexion = obtener_conexion()
    cerrar_sesion = False
    try:
        objetivo = conexion.execute(
            "SELECT id_usuario, usuario, rol FROM usuarios WHERE id_usuario = ?",
            (id_usuario,),
        ).fetchone()
        if objetivo is None:
            flash("El usuario que intentás eliminar no existe.", "warning")
            return redirect(url_for("usuarios_bp.listar_usuarios"))

        if objetivo["rol"] == "admin" and _cantidad_administradores(conexion) <= 1:
            flash("No podés eliminar al último administrador del sistema.", "danger")
            return redirect(url_for("usuarios_bp.listar_usuarios"))

        cerrar_sesion = session.get("usuario") == objetivo["usuario"]
        conexion.execute("DELETE FROM usuarios WHERE id_usuario = ?", (id_usuario,))
        conexion.commit()
        registrar_auditoria("BAJA_USUARIO", f"Usuario '{objetivo['usuario']}' eliminado")
        if cerrar_sesion:
            session.clear()
            flash("Tu usuario fue eliminado. La sesión se cerró.", "info")
        else:
            flash(f"El usuario '{objetivo['usuario']}' fue eliminado correctamente.", "success")
    except Exception:
        conexion.rollback()
        logger.exception("Error al eliminar usuario ID %s", id_usuario)
        flash("Ocurrió un error al eliminar el usuario.", "danger")
    finally:
        conexion.close()

    if cerrar_sesion:
        return redirect(url_for("auth_bp.login"))
    return redirect(url_for("usuarios_bp.listar_usuarios"))
