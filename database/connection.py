"""
Módulo de Conexión a la Base de Datos SQLite para 'Gomería El Puente'.

Centraliza la conexión a la base de datos para toda la aplicación (app.py, scripts, etc.),
respetando la variable DATABASE_PATH del archivo .env o usando 'sg_gomeria.db' por defecto.
"""

import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Ubicación base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Obtener ruta configurada o usar 'sg_gomeria.db' por defecto
db_env = os.getenv("DATABASE_PATH", "sg_gomeria.db")
if os.path.isabs(db_env):
    DB_PATH = Path(db_env)
else:
    DB_PATH = BASE_DIR / db_env


def obtener_conexion() -> sqlite3.Connection:
    """
    Abre y retorna una conexión a la base de datos SQLite con:
    - row_factory = sqlite3.Row (acceso a columnas por nombre: fila['nom_cli'])
    - foreign_keys activadas (integridad referencial)
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(str(DB_PATH))
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON;")
    return conexion


# Alias de conveniencia
def get_db_connection() -> sqlite3.Connection:
    return obtener_conexion()


def get_db_path() -> Path:
    """Devuelve la ruta absoluta al archivo SQLite."""
    return DB_PATH
