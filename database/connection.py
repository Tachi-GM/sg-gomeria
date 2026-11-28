"""
Módulo de Conexión a la Base de Datos SQLite para 'Gomería El Puente'.

Centraliza la conexión a la base de datos para toda la aplicación (app.py, scripts, etc.),
respetando la variable DATABASE_PATH del archivo .env o usando 'sg_gomeria.db' por defecto.
"""

import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import shutil  # junto a los otros imports

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
ENV_EJEMPLO = BASE_DIR / ".env.example"

# Si todavía no existe .env, se crea copiando la plantilla .env.example
if not ENV_PATH.exists() and ENV_EJEMPLO.exists():
    shutil.copyfile(ENV_EJEMPLO, ENV_PATH)
    print("[INFO] No existía .env: se creó a partir de .env.example. Revisá SECRET_KEY y FLASK_DEBUG.")

load_dotenv(ENV_PATH)

# Obtener ruta configurada o usar %APPDATA%\SG-Gomeria\sg_gomeria.db por defecto en Windows
db_env = os.getenv("DATABASE_PATH")
if db_env:
    DB_PATH = Path(db_env) if os.path.isabs(db_env) else BASE_DIR / db_env
elif os.getenv("APPDATA"):
    DB_PATH = Path(os.getenv("APPDATA")) / "SG-Gomeria" / "sg_gomeria.db"
    # Migración automática segura si la base estaba en la raíz del proyecto
    db_legacy = BASE_DIR / "sg_gomeria.db"
    if not DB_PATH.exists() and db_legacy.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_legacy, DB_PATH)
else:
    DB_PATH = BASE_DIR / "sg_gomeria.db"


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

    # Tablas nuevas para gestionar aguinaldos sin reconstruir movimientos_gomeros.
    # Esto funciona como migración compatible con bases existentes.
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS aguinaldos (
            id_aguinaldo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_gomero INTEGER NOT NULL,
            periodo_aguinaldo TEXT NOT NULL
                CHECK (periodo_aguinaldo GLOB '[0-9][0-9][0-9][0-9]-[12]'),
            importe INTEGER NOT NULL CHECK (importe > 0),
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_gomero) REFERENCES gomeros(id_gomero) ON DELETE RESTRICT,
            UNIQUE (id_gomero, periodo_aguinaldo)
        )
        """
    )
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS pagos_aguinaldo (
            id_pago_aguinaldo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_aguinaldo INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            importe INTEGER NOT NULL CHECK (importe > 0),
            concepto TEXT,
            usuario TEXT,
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_aguinaldo)
                REFERENCES aguinaldos(id_aguinaldo) ON DELETE RESTRICT
        )
        """
    )
    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pagos_aguinaldo_id_fecha
        ON pagos_aguinaldo(id_aguinaldo, fecha)
        """
    )
    conexion.commit()

    # Migración transparente para clientes.activo si no existe en la base actual
    try:
        columnas = [
            col[1] for col in conexion.execute("PRAGMA table_info(clientes)").fetchall()
        ]
        if columnas and "activo" not in columnas:
            conexion.execute(
                "ALTER TABLE clientes ADD COLUMN activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1));"
            )
            conexion.commit()
    except Exception:
        pass

    # Migración transparente para trabajos.cliente_alias si no existe en la base actual
    try:
        cols = [c[1] for c in conexion.execute("PRAGMA table_info(trabajos)").fetchall()]
        if cols and "cliente_alias" not in cols:
            conexion.execute("ALTER TABLE trabajos ADD COLUMN cliente_alias TEXT;")
            conexion.commit()
    except Exception:
        pass

    return conexion


# Alias de conveniencia
def get_db_connection() -> sqlite3.Connection:
    return obtener_conexion()


def get_db_path() -> Path:
    """Devuelve la ruta absoluta al archivo SQLite."""
    return DB_PATH
