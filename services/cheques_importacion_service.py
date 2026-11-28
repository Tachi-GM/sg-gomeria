"""Importación de cheques desde el Excel «Cheques-Echeqs» subido por la pantalla web.

Reutiliza el núcleo de `scripts/importar_cheques.py` (el mismo que se usa por consola).
"""

import logging
import sqlite3
import tempfile
from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from scripts.importar_cheques import importar
from services.archivos_excel import ErrorArchivoExcel, backup_consistente, leer_xlsx_subido

logger = logging.getLogger("SG_Gomeria")


def importar_cheques_desde_archivo(archivo, ruta_db, carpeta_backups):
    """Valida el archivo, importa los cheques y devuelve el informe de `importar`.

    Lanza ErrorArchivoExcel con un mensaje claro si algo no está bien; en ese caso la base
    no se modifica (la inserción es una sola transacción).
    """
    contenido = leer_xlsx_subido(archivo)
    with tempfile.TemporaryDirectory(prefix="sg-cheques-") as carpeta_temporal:
        ruta_excel = Path(carpeta_temporal) / "cheques.xlsx"
        ruta_excel.write_bytes(contenido)
        try:
            return importar(
                ruta_excel,
                ruta_db,
                actualizar=True,
                funcion_backup=lambda ruta: backup_consistente(ruta, carpeta_backups, "antes_import_cheques"),
            )
        except ValueError as error:
            raise ErrorArchivoExcel(
                f"{error}. El Excel debe tener las columnas Numero, Banco, Librador, Destino, Importe y Fecha."
            ) from error
        except (BadZipFile, InvalidFileException, KeyError) as error:
            raise ErrorArchivoExcel("No se pudo leer el archivo como Excel. ¿Está dañado?") from error
        except sqlite3.IntegrityError as error:
            logger.warning("Importación de cheques rechazada por la base: %s", error)
            raise ErrorArchivoExcel(
                "La base rechazó algún dato del Excel. No se guardó ningún cheque."
            ) from error
