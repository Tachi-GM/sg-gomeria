import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from flask import (
    Blueprint,
    current_app,
    render_template,
    send_file,
    send_from_directory,
)
from database.connection import get_db_path
from services.dashboard_service import obtener_resumen_inicio
from config.empresa_loader import obtener_datos_empresa
from utils.seguridad import (
    login_requerido,
    solo_admin,
    registrar_auditoria,
    modo_activo,
)

general_bp = Blueprint("general_bp", __name__)


# Pantallas Principales
@general_bp.route("/")
@login_requerido
def home():
    return render_template(
        "index.html",
        milagritos=modo_activo(),
        resumen=obtener_resumen_inicio(),
    )


@general_bp.route("/empresa")
@login_requerido
@solo_admin
def datos_empresa():
    """Muestra los datos comerciales; el acceso está limitado a administradores."""
    return render_template(
        "empresa.html",
        empresa=obtener_datos_empresa(),
        milagritos=modo_activo(),
    )


@general_bp.route("/salir")
def salir():
    return render_template("salir.html", milagritos=modo_activo())


@general_bp.route("/acerca-de")
def acerca_de():
    return render_template("acerca-de.html", milagritos=modo_activo())


@general_bp.route("/manual")
@login_requerido
def manual_usuario():
    """Abre el manual PDF incluido en docs sin exponer el directorio completo."""
    carpeta_docs = Path(current_app.root_path) / "docs"
    return send_from_directory(
        carpeta_docs,
        "MANUAL_DE_USUARIO_SG_GOMERIA.pdf",
        mimetype="application/pdf",
        as_attachment=False,
    )


@general_bp.route("/backup")
@login_requerido
@solo_admin
def hacer_backup():
    from services.backup_service import generar_backup, obtener_carpeta_backups

    carpeta_backups = obtener_carpeta_backups(current_app.config)
    carpeta_uploads = current_app.config.get("UPLOAD_DIR", "uploads")
    ruta_copia = generar_backup(carpeta_backups, carpeta_uploads)

    registrar_auditoria(
        "BACKUP_BD", f"Generado resguardo de base de datos: {ruta_copia.name}"
    )

    # Le mandamos el archivo al navegador para que lo descargue
    return send_file(ruta_copia, as_attachment=True, download_name=ruta_copia.name)
