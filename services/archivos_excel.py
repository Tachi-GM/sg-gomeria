"""Piezas compartidas por las importaciones desde Excel subidas por la web (precios, cheques, gomeros)."""

import sqlite3
from datetime import datetime
from pathlib import Path

TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB sobran para estos Excel


class ErrorArchivoExcel(Exception):
    """Problema esperable con el archivo subido; el mensaje se puede mostrar tal cual al usuario."""


def leer_xlsx_subido(archivo):
    """Valida el archivo subido (FileStorage de Flask) y devuelve su contenido en bytes."""
    nombre = (getattr(archivo, "filename", "") or "").strip()
    if not nombre:
        raise ErrorArchivoExcel("Elegí un archivo de Excel para importar.")
    if Path(nombre).suffix.lower() != ".xlsx":
        raise ErrorArchivoExcel(
            "El archivo tiene que ser un Excel .xlsx. Si es un .xls, abrilo y usá "
            "«Guardar como» → «Libro de Excel (.xlsx)»."
        )
    contenido = archivo.read(TAMANO_MAXIMO_BYTES + 1)
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ErrorArchivoExcel("El archivo es demasiado grande (máximo 5 MB).")
    if not contenido.startswith(b"PK"):  # un .xlsx es un zip: arranca con «PK»
        raise ErrorArchivoExcel(
            "El archivo no parece un Excel .xlsx válido. ¿Está dañado o es de otro formato?"
        )
    return contenido


def backup_consistente(ruta_db, carpeta, prefijo):
    """Copia la base con la API de backup de SQLite (segura aunque la app la esté usando)."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{prefijo}_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    origen = sqlite3.connect(str(ruta_db))
    copia = sqlite3.connect(str(destino))
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    return destino
