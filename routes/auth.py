from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database.connection import obtener_conexion
from utils.seguridad import registrar_auditoria, modo_activo
import logging

logger = logging.getLogger('SG_Gomeria')

auth_bp = Blueprint('auth_bp', __name__)

# Autenticación: Login y Logout
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('usuario'):
        return redirect(url_for('general_bp.home'))

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        clave = request.form.get('password', '')

        conexion = obtener_conexion()
        user = conexion.execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()
        conexion.close()

        if user and check_password_hash(user['contraseña'], clave):
            session['usuario'] = user['usuario']
            session['rol'] = user['rol']
            registrar_auditoria("LOGIN_EXITOSO", f"Acceso correcto al sistema")
            flash(f"¡Bienvenido/a, {user['usuario']}!", "success")
            return redirect(url_for('general_bp.home'))
        else:
            logger.warning(f"AUDITORIA | Intento fallido de inicio de sesion para usuario: '{usuario}'")
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html', milagritos=modo_activo())

@auth_bp.route('/logout')
def logout():
    usuario_desconectado = session.pop('usuario', None)
    session.pop('rol', None)
    if usuario_desconectado:
        logger.info(f"AUDITORIA | Usuario: {usuario_desconectado} | Accion: LOGOUT | Cierre de sesion voluntario")
        flash("Has cerrado sesión exitosamente", "info")
    return redirect(url_for('auth_bp.login'))