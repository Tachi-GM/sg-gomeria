"""Importación de las listas de precios desde un Excel subido por la pantalla web.

Reutiliza el núcleo de `scripts/importar_precios.py` (el mismo que se usa por consola)
y le suma lo que necesita una pantalla: validar el archivo subido, hacer un backup
consistente de la base y devolver un resumen legible.
"""

import logging
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from scripts.importar_precios import importar

logger = logging.getLogger("SG_Gomeria")

TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB sobran para una lista de precios


class ErrorImportacionPrecios(Exception):
    """Problema esperable (archivo inválido, formato distinto...) con mensaje para el usuario."""


def _backup_consistente(ruta_db, carpeta):
    """Copia la base con la API de backup de SQLite (segura aunque la app la esté usando)."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"antes_import_precios_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    origen = sqlite3.connect(str(ruta_db))
    copia = sqlite3.connect(str(destino))
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    return destino


def importar_precios_desde_archivo(archivo, ruta_db, carpeta_backups):
    """Valida el archivo subido, actualiza la base y devuelve el resultado de `importar`.

    `archivo` es el FileStorage de Flask. Lanza ErrorImportacionPrecios con un
    mensaje claro si algo no está bien; en ese caso la base no se modifica.
    """
    nombre = (getattr(archivo, "filename", "") or "").strip()
    if not nombre:
        raise ErrorImportacionPrecios("Elegí un archivo de Excel para importar.")
    if Path(nombre).suffix.lower() != ".xlsx":
        raise ErrorImportacionPrecios(
            "El archivo tiene que ser un Excel .xlsx. Si es un .xls, abrilo y usá "
            "«Guardar como» → «Libro de Excel (.xlsx)»."
        )

    contenido = archivo.read(TAMANO_MAXIMO_BYTES + 1)
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ErrorImportacionPrecios("El archivo es demasiado grande (máximo 5 MB).")
    if not contenido.startswith(b"PK"):  # un .xlsx es un zip: arranca con «PK»
        raise ErrorImportacionPrecios(
            "El archivo no parece un Excel .xlsx válido. ¿Está dañado o es de otro formato?"
        )

    with tempfile.TemporaryDirectory(prefix="sg-precios-") as carpeta_temporal:
        ruta_excel = Path(carpeta_temporal) / "precios.xlsx"
        ruta_excel.write_bytes(contenido)
        try:
            return importar(
                ruta_excel,
                ruta_db,
                actualizar=True,
                funcion_backup=lambda ruta: _backup_consistente(ruta, carpeta_backups),
            )
        except ValueError as error:
            # Mensajes propios del importador: "Faltan hojas de listas: 2, 3", etc.
            raise ErrorImportacionPrecios(
                f"{error}. Revisá que el Excel tenga las hojas «Lista 1», «Lista 2» y "
                "«Lista 3», con las columnas «Descripción», «Precio sin IVA» y «Precio final»."
            ) from error
        except (BadZipFile, InvalidFileException, KeyError) as error:
            raise ErrorImportacionPrecios(
                "No se pudo leer el archivo como Excel. ¿Está dañado?"
            ) from error
        except sqlite3.IntegrityError as error:
            logger.warning("Importación de precios rechazada por la base: %s", error)
            raise ErrorImportacionPrecios(
                "La base rechazó algún dato del Excel (por ejemplo, un nombre repetido). "
                "No se guardó ningún cambio."
            ) from error
