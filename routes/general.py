import os
import shutil
from datetime import datetime
from flask import Blueprint, render_template, send_file, session
from utils.seguridad import login_requerido, solo_admin, registrar_auditoria, modo_activo

general_bp = Blueprint('general_bp', __name__)

# Pantallas Principales
@general_bp.route('/')
@login_requerido
def home():
    return render_template('index.html', milagritos=modo_activo())

@general_bp.route('/salir')
def salir():
    return render_template('salir.html', milagritos=modo_activo())

@general_bp.route('/acerca-de')
def acerca_de():
    return render_template('acerca-de.html', milagritos=modo_activo())

@general_bp.route('/backup')
@login_requerido
@solo_admin
def hacer_backup():
    # 1. Armamos un nombre único con fecha y hora
    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombre_archivo = f"backup_gomeria_{fecha_hora}.db"

    # 2. Creamos una carpeta para guardar copias (si no existe)
    os.makedirs("backups", exist_ok=True)
    ruta_copia = os.path.join("backups", nombre_archivo)

    # 3. Copiamos la base de datos actual a esa carpeta
    shutil.copy("sg_gomeria.db", ruta_copia)

    registrar_auditoria("BACKUP_BD", f"Generado resguardo de base de datos: {nombre_archivo}")

    # 4. Le mandamos el archivo al navegador para que lo descargue
    return send_file(ruta_copia, as_attachment=True, download_name=nombre_archivo)