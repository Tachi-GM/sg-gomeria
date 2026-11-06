"""Validación y almacenamiento seguro de fotos asociadas a remitos."""

import os
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

MAX_FOTO_REMITO_BYTES = 5 * 1024 * 1024
CARPETA_FOTOS_REMITOS = "fotos_remitos"

_FIRMAS_FORMATOS = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),
}


def validar_foto_remito(archivo):
    """Valida una imagen subida sin confiar en el MIME enviado por el cliente."""
    if archivo is None or not archivo.filename:
        return False, "No se seleccionó una foto."

    nombre_seguro = secure_filename(archivo.filename)
    extension = Path(nombre_seguro).suffix.lower()
    firmas = _FIRMAS_FORMATOS.get(extension)
    if not nombre_seguro or not firmas:
        return False, "La foto debe tener extensión JPG, JPEG, PNG, GIF o WEBP."

    contenido = archivo.stream.read(MAX_FOTO_REMITO_BYTES + 1)
    archivo.stream.seek(0)
    if len(contenido) > MAX_FOTO_REMITO_BYTES:
        return False, "La foto no puede superar los 5 MB."

    if not any(contenido.startswith(firma) for firma in firmas):
        return False, "El contenido del archivo no coincide con una imagen válida."

    if extension == ".webp" and contenido[8:12] != b"WEBP":
        return False, "El contenido del archivo no coincide con una imagen WEBP válida."

    return True, extension


def guardar_foto_remito(archivo, carpeta_uploads):
    """Guarda la foto con un nombre generado por el servidor y devuelve su ruta relativa."""
    valido, resultado = validar_foto_remito(archivo)
    if not valido:
        raise ValueError(resultado)

    carpeta_raiz = Path(carpeta_uploads).resolve()
    carpeta_fotos = carpeta_raiz / CARPETA_FOTOS_REMITOS
    carpeta_fotos.mkdir(parents=True, exist_ok=True)

    nombre_archivo = f"{uuid4().hex}{resultado}"
    ruta_final = carpeta_fotos / nombre_archivo
    ruta_temporal = carpeta_fotos / f".{nombre_archivo}.tmp"
    try:
        archivo.save(ruta_temporal)
        os.replace(ruta_temporal, ruta_final)
    except Exception:
        ruta_temporal.unlink(missing_ok=True)
        raise

    return f"{CARPETA_FOTOS_REMITOS}/{nombre_archivo}"


def ruta_foto_segura(ruta_relativa, carpeta_uploads):
    """Resuelve únicamente rutas de fotos administradas por la aplicación."""
    if not ruta_relativa or Path(ruta_relativa).is_absolute():
        return None

    ruta = Path(ruta_relativa)
    if ruta.parts[:1] != (CARPETA_FOTOS_REMITOS,) or ".." in ruta.parts:
        return None

    raiz = Path(carpeta_uploads).resolve()
    candidata = (raiz / ruta).resolve()
    try:
        candidata.relative_to(raiz / CARPETA_FOTOS_REMITOS)
    except ValueError:
        return None
    return candidata


def eliminar_foto_remito(ruta_relativa, carpeta_uploads):
    """Elimina una foto solo si pertenece a la carpeta administrada."""
    ruta = ruta_foto_segura(ruta_relativa, carpeta_uploads)
    if ruta is not None and ruta.is_file():
        ruta.unlink()
