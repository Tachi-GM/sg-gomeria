import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

from config.empresa_loader import obtener_datos_empresa
from routes.general import general_bp
from routes.auth import auth_bp
from routes.trabajos import trabajos_bp
from routes.clientes import clientes_bp
from routes.clientes_api import clientes_api_bp
from routes.cheques import cheques_bp
from routes.usuarios import usuarios_bp
from routes.gomeros import gomeros_bp
from routes.exportaciones import exportaciones_bp
from utils.seguridad import login_requerido, solo_admin
from utils.formateadores import etiqueta_estado_remito

import os
import logging
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

# Filtro para codificar URLs en plantillas
def url_encode(s):
    return urllib.parse.quote_plus(str(s))

# Registro del filtro en la aplicación (se hará después de crear app)
load_dotenv()

# 2. Configuración centralizada de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=(
        [logging.StreamHandler()]
        if os.getenv("SG_TESTING") == "1"
        else [
            logging.FileHandler("sistema.log", encoding="utf-8"),
            logging.StreamHandler(),
        ]
    )
)
logger = logging.getLogger("SG_Gomeria")

# 3. Creación y configuración de la app Flask
app = Flask(__name__)
# Registro del filtro URL‑encode para usar en plantillas Jinja
app.add_template_filter(url_encode, "url_encode")
app.jinja_env.filters["url_encode"] = url_encode
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-gomeria-2026-cambiar-en-prod")
app.config["UPLOAD_DIR"] = os.getenv("UPLOAD_DIR", "uploads")

if os.getenv("SG_TESTING") != "1":
    try:
        from services.backup_service import (
            backup_automatico_diario,
            obtener_carpeta_backups,
        )

        respaldo = backup_automatico_diario(
            obtener_carpeta_backups(app.config), app.config["UPLOAD_DIR"]
        )
        if respaldo:
            logger.info(f"Backup automático diario generado: {respaldo.name}")
    except Exception as exc:
        logger.warning(f"No se pudo generar el backup automático diario: {exc}")


def modo_activo():
    return session.get("modo_milagritos", False)


# Filtro de plantillas: {{ remito.estado | estado_remito }} -> "Aceptado" / "En proceso" / "Pagado".
app.add_template_filter(etiqueta_estado_remito, "estado_remito")


@app.context_processor
def inject_global_vars():
    return {
        "milagritos": session.get("modo_milagritos", False),
        "modo_activo": modo_activo,
        # Datos compartidos con Jinja2 para evitar repetir imports en cada ruta.
        "empresa": obtener_datos_empresa(),
    }


# 4. Manejadores globales de errores HTTP y modo-milagritos
def pagina_error(codigo, mensaje):
    return (
        render_template(
            "error.html", codigo=codigo, mensaje=mensaje, milagritos=modo_activo()
        ),
        codigo,
    )


@app.errorhandler(401)
def error_401(e):
    logger.warning(f"AUDITORIA | Acceso no autorizado (401) a {request.path}")
    return (
        pagina_error(
            401,
            "No tienes autorización para acceder a esta pantalla. Por favor, inicia sesión.",
        ),
        401,
    )


@app.errorhandler(403)
def error_403(e):
    logger.warning(
        f"AUDITORIA | Permisos insuficientes (403) a {request.path} | Usuario: {session.get('usuario')}"
    )
    return (
        pagina_error(
            403,
            "Acceso restringido: no cuentas con los permisos de Administrador necesarios.",
        ),
        403,
    )


@app.errorhandler(404)
def error_404(e):
    return pagina_error(404, "No encontramos esa página")


@app.errorhandler(500)
def error_500(e):
    return pagina_error(
        500, "Algo salió mal de nuestro lado. Probá de nuevo en un rato"
    )


@app.route("/probar-error")
@login_requerido
@solo_admin
def probar_error():
    return 1 / 0  # Fuerza un ZeroDivisionError a propósito


@app.after_request
def registrar_errores(respuesta):
    if respuesta.status_code >= 400:
        logging.warning(f"{request.method} {request.path} -> {respuesta.status_code}")
    return respuesta


# Ruta para prender/apagar el modo, y volver a donde estabas
@app.route("/toggle-milagritos")
def toggle_milagritos():
    session["modo_milagritos"] = not session.get("modo_milagritos", False)
    # request.referrer = la página desde la que vino el usuario
    return redirect(request.referrer or url_for("general_bp.home"))


# 5. REGISTRO DE BLUEPRINTS (Los módulos del sistema)
app.register_blueprint(general_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(trabajos_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(clientes_api_bp)
app.register_blueprint(cheques_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(gomeros_bp)
app.register_blueprint(exportaciones_bp)

# 6. Arranque del servidor local
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode)
