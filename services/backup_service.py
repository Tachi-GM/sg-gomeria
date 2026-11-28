"""
Servicio de copias de seguridad para 'Gomería El Puente'.

Centraliza la generación de backups consistentes en ZIP (SQLite Backup API + fotos)
y el respaldo automático diario con rotación.
"""

import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from database.connection import BASE_DIR, get_db_path


def obtener_carpeta_backups(config=None) -> Path:
    """Devuelve la carpeta de backups configurada o %APPDATA%\\SG-Gomeria\\backups."""
    if config and config.get("BACKUP_DIR"):
        return Path(config["BACKUP_DIR"])

    env_dir = os.getenv("BACKUP_DIR")
    if env_dir:
        ruta = Path(env_dir)
        return ruta if ruta.is_absolute() else BASE_DIR / ruta

    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "SG-Gomeria" / "backups"

    return BASE_DIR / "backups"


def generar_backup(carpeta_backups: Path | str, carpeta_uploads: Path | str) -> Path:
    """Genera un archivo ZIP con la base de datos y las fotos de remitos."""
    carpeta_backups = Path(carpeta_backups)
    carpeta_backups.mkdir(parents=True, exist_ok=True)

    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombre_archivo = f"backup_gomeria_{fecha_hora}.zip"
    ruta_copia = carpeta_backups / nombre_archivo
    ruta_db_temporal = None

    origen = sqlite3.connect(str(get_db_path()))
    try:
        with tempfile.NamedTemporaryFile(
            prefix="backup_db_", suffix=".db", dir=carpeta_backups, delete=False
        ) as archivo_temporal:
            ruta_db_temporal = archivo_temporal.name

        destino = sqlite3.connect(ruta_db_temporal)
        try:
            origen.backup(destino)
        finally:
            destino.close()

        uploads_path = Path(carpeta_uploads).resolve()
        with zipfile.ZipFile(
            ruta_copia, "w", compression=zipfile.ZIP_DEFLATED
        ) as paquete:
            paquete.write(ruta_db_temporal, arcname="sg_gomeria.db")
            carpeta_fotos = uploads_path / "fotos_remitos"
            if carpeta_fotos.is_dir():
                for ruta_foto in carpeta_fotos.rglob("*"):
                    if ruta_foto.is_file():
                        paquete.write(
                            ruta_foto,
                            arcname=str(ruta_foto.relative_to(uploads_path)),
                        )
    finally:
        origen.close()
        if ruta_db_temporal:
            Path(ruta_db_temporal).unlink(missing_ok=True)

    return ruta_copia


def backup_automatico_diario(
    carpeta_backups: Path | str,
    carpeta_uploads: Path | str,
    max_backups: int = 20,
) -> Path | None:
    """
    Si hoy todavía no se generó un backup, crea uno automáticamente
    y conserva como máximo los últimos `max_backups` archivos.
    """
    db_path = get_db_path()
    if not db_path.exists():
        return None

    carpeta = Path(carpeta_backups)
    carpeta.mkdir(parents=True, exist_ok=True)

    hoy = datetime.now().strftime("%Y-%m-%d")
    if any(carpeta.glob(f"backup_gomeria_{hoy}_*.zip")):
        return None

    nuevo_backup = generar_backup(carpeta, carpeta_uploads)

    # Rotación: eliminar los backups más antiguos si se supera el límite
    backups = sorted(
        carpeta.glob("backup_gomeria_*.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for viejo in backups[max_backups:]:
        viejo.unlink(missing_ok=True)

    return nuevo_backup
