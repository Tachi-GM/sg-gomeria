"""Infraestructura compartida para ejecutar las pruebas con una base SQLite temporal.

Este módulo debe importarse antes que cualquier módulo de la aplicación que importe
`database.connection`, porque ese módulo resuelve DATABASE_PATH al importarse.
"""
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# El directorio vive durante todo el proceso de pruebas y se elimina al finalizar.
_TEMP_DIR = tempfile.TemporaryDirectory(prefix="sg-gomeria-tests-")
TEST_DIR = Path(_TEMP_DIR.name)
TEST_DB_PATH = TEST_DIR / "sg_gomeria_tests.db"

# Debe configurarse antes de importar la conexión, los servicios o la app.
os.environ["DATABASE_PATH"] = str(TEST_DB_PATH)
os.environ["SG_TESTING"] = "1"

# Creamos el esquema real y los datos semilla que las pruebas existentes esperan.
from database.init_db import crear_tablas, sembrar_datos_prueba  # noqa: E402

crear_tablas()
sembrar_datos_prueba()

from app import app  # noqa: E402
from database.connection import get_db_path, obtener_conexion  # noqa: E402

app.config.update(
    TESTING=True,
    BACKUP_DIR=str(TEST_DIR / "backups"),
)

# Comprobación defensiva: si cambia la inicialización de conexión, no seguir
# ejecutando pruebas accidentalmente contra otra base.
if get_db_path().resolve() != TEST_DB_PATH.resolve():
    raise RuntimeError(
        "La suite de pruebas no está usando la base SQLite temporal configurada."
    )
