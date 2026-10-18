import logging
from functools import wraps
from flask import session, flash, redirect, url_for

logger = logging.getLogger('SG_Gomeria')

def modo_activo():
    """Devuelve si el Modo Milagritos está activo en la sesión."""
    return session.get('modo_milagritos', False)

# Decoradores de autenticación y autorización
def login_requerido(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        if not session.get('usuario'):
            flash("Debes iniciar sesión para acceder al sistema", "warning")
            return redirect(url_for('auth_bp.login'))
        return f(*args, **kwargs)
    return funcion_decorada

def solo_admin(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        if session.get('rol') != 'admin':
            flash("Acceso restringido: requiere permisos de Administrador", "danger")
            return redirect(url_for('general_bp.home'))
        return f(*args, **kwargs)
    return funcion_decorada

def registrar_auditoria(accion, detalle=""):
    """Registra en el log de auditoría la acción realizada y el usuario responsable."""
    usuario = session.get('usuario', 'ANONIMO')
    rol = session.get('rol', '-')
    logger.info(f"AUDITORIA | Usuario: {usuario} ({rol}) | Accion: {accion} | {detalle}")
