import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

from routes.general import general_bp
from routes.auth import auth_bp
from routes.trabajos import trabajos_bp
from routes.clientes import clientes_bp
from routes.cheques import cheques_bp

# 1. Configuración de variables de entorno
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
    ),
)
logger = logging.getLogger("SG_Gomeria")

# 3. Creación y configuración de la app Flask
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-gomeria-2026-cambiar-en-prod")


def modo_activo():
    return session.get("modo_milagritos", False)


@app.context_processor
def inject_global_vars():
    return {
        "milagritos": session.get("modo_milagritos", False),
        "modo_activo": modo_activo,
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
app.register_blueprint(cheques_bp)

# 6. Arranque del servidor local
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode)
