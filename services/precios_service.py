"""Importación de las listas de precios desde un Excel subido por la pantalla web.

Reutiliza el núcleo de `scripts/importar_precios.py` (el mismo que se usa por consola)
y le suma lo que necesita una pantalla: validar el archivo subido, hacer un backup
consistente de la base y devolver un resumen legible.
"""

import logging
import sqlite3
import tempfile
from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from scripts.importar_precios import importar
from services.archivos_excel import ErrorArchivoExcel, backup_consistente, leer_xlsx_subido

logger = logging.getLogger("SG_Gomeria")


class ErrorImportacionPrecios(Exception):
    """Problema esperable (archivo inválido, formato distinto...) con mensaje para el usuario."""


def importar_precios_desde_archivo(archivo, ruta_db, carpeta_backups):
    """Valida el archivo subido, actualiza la base y devuelve el resultado de `importar`.

    `archivo` es el FileStorage de Flask. Lanza ErrorImportacionPrecios con un
    mensaje claro si algo no está bien; en ese caso la base no se modifica.
    """
    try:
        contenido = leer_xlsx_subido(archivo)
    except ErrorArchivoExcel as error:
        raise ErrorImportacionPrecios(str(error)) from error

    with tempfile.TemporaryDirectory(prefix="sg-precios-") as carpeta_temporal:
        ruta_excel = Path(carpeta_temporal) / "precios.xlsx"
        ruta_excel.write_bytes(contenido)
        try:
            return importar(
                ruta_excel,
                ruta_db,
                actualizar=True,
                funcion_backup=lambda ruta: backup_consistente(ruta, carpeta_backups, "antes_import_precios"),
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
