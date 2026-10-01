import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent  # la carpeta donde vive ESTE script
RUTA_EXCEL = BASE / "datos_privados" / "CUIT Clientes.xls"
RUTA_DB = BASE / "datos_privados" / "sg_gomeria2.db"
RUTA_REVISION = BASE / "datos_privados" / "clientes_a_revisar.xlsx"

CONDICION = {
    "resp. inscripto": "Responsable Inscripto",
    "resp inscripto": "Responsable Inscripto",
    "iva exento": "IVA Exento",
    "monotributista": "Monotributo",
    "monotributo": "Monotributo",
    "cons final": "Consumidor Final",
}

COLUMNAS_NUEVAS = {
    "codigo": "TEXT",
    "direccion": "TEXT",
    "localidad": "TEXT",
    "condicion_iva": "TEXT",
    "tipo_factura": "TEXT",
    "contacto": "TEXT",
    "sin_iva": "INTEGER NOT NULL DEFAULT 0",
    "tipo_remito": "TEXT NOT NULL DEFAULT 'OI'",
}


def limpiar_cuit(valor):
    """Devuelve el CUIT como XX-XXXXXXXX-X, o None si no tiene 11 dígitos."""
    digitos = re.sub(r"\D", "", str(valor or ""))
    if len(digitos) != 11:
        return None
    return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}"


def normalizar_nombre(nombre):
    return " ".join(str(nombre).lower().split())


def leer_clientes():
    df = pd.read_excel(RUTA_EXCEL, sheet_name="CUIT", header=1, dtype=str, engine="xlrd")
    df = df.dropna(subset=["Cliente"])
    df = df[~df["Cliente"].str.startswith("http")]
    df = df.apply(lambda col: col.str.strip()).replace("", pd.NA)

    df = df.rename(columns={
        "Codigo": "codigo", "Cliente": "nom_cli", "CUIT": "cuit_crudo",
        "Direccion": "direccion", "Localidad": "localidad", "Mail": "mail",
        "Telefono": "tel", "Fact.": "tipo_factura",
        "Condicion": "condicion_iva", "Contacto": "contacto",
    })
    df["fila_excel"] = df.index + 3  # para ubicar la fila en el Excel
    df["condicion_iva"] = df["condicion_iva"].str.lower().map(CONDICION)
    df["tipo_factura"] = df["tipo_factura"].str.upper()

    # CUIT: limpio o None. Guardamos los que venían con algo pero inválido.
    df["cuit"] = df["cuit_crudo"].apply(limpiar_cuit)
    invalidos = df[df["cuit_crudo"].notna() & df["cuit"].isna()]

    # Un cliente sin CUIT con el mismo nombre que otro que sí lo tiene hereda ese CUIT
    df["nombre_norm"] = df["nom_cli"].apply(normalizar_nombre)
    cuit_por_nombre = (df.dropna(subset=["cuit"])
                         .drop_duplicates("nombre_norm")
                         .set_index("nombre_norm")["cuit"])
    df["cuit"] = df["cuit"].fillna(df["nombre_norm"].map(cuit_por_nombre))

    # Primero las filas más completas: al fusionar, su nombre queda como principal
    df["completitud"] = df.notna().sum(axis=1)
    df = df.sort_values("completitud", ascending=False, kind="stable")

    con_cuit = df[df["cuit"].notna()]
    sin_cuit = df[df["cuit"].isna()].drop_duplicates("nombre_norm").copy()

    # .first() toma, por columna, el primer valor NO nulo de cada grupo => fusiona info
    fusionados = con_cuit.groupby("cuit", sort=False).first().reset_index()
    nombres = con_cuit.groupby("cuit", sort=False)["nom_cli"].agg(lambda s: list(dict.fromkeys(s)))
    fusionados["aliases"] = fusionados["cuit"].map(nombres)
    sin_cuit["aliases"] = sin_cuit["nom_cli"].apply(lambda n: [n])

    clientes = pd.concat([fusionados, sin_cuit], ignore_index=True)

    filas = con_cuit.groupby("cuit", sort=False).size()
    repetidos = filas[filas > 1].index  # CUIT que aparecían en más de una fila
    resumen_fusiones = pd.DataFrame({
        "cuit": repetidos,
        "filas_en_excel": filas[repetidos].values,
        "nombres_unificados": [" | ".join(nombres[c]) for c in repetidos],
    })
    return clientes, resumen_fusiones, invalidos


def preparar_tablas(con):
    existentes = {fila[1] for fila in con.execute("PRAGMA table_info(clientes)")}
    for columna, tipo in COLUMNAS_NUEVAS.items():
        if columna not in existentes:  # así se puede correr más de una vez
            con.execute(f"ALTER TABLE clientes ADD COLUMN {columna} {tipo}")
    con.execute("""
        CREATE TABLE IF NOT EXISTS alias_clientes (
            alias TEXT PRIMARY KEY,
            id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente)
        )
    """)


def importar(dry_run=True):
    for ruta in (RUTA_EXCEL, RUTA_DB):
        if not ruta.exists():
            raise FileNotFoundError(f"No encuentro: {ruta}")

    clientes, fusiones, invalidos = leer_clientes()
    RUTA_REVISION.parent.mkdir(exist_ok=True)
    with pd.ExcelWriter(RUTA_REVISION) as w:
        fusiones.to_excel(w, sheet_name="Fusionados", index=False)
        invalidos[["fila_excel", "nom_cli", "cuit_crudo"]].to_excel(
            w, sheet_name="CUIT invalido", index=False)

    if not dry_run:
        carpeta = BASE / "backups"
        carpeta.mkdir(exist_ok=True)
        shutil.copy(RUTA_DB, carpeta / f"antes_import_{datetime.now():%Y-%m-%d_%H-%M}.db")


    con = sqlite3.connect(RUTA_DB)
    limpio = lambda x: None if pd.isna(x) else x
    nuevos = omitidos = 0
    try:
        if not dry_run:
            preparar_tablas(con)
        cuits_db = {re.sub(r"\D", "", c) for (c,) in con.execute(
            "SELECT cuit FROM clientes WHERE cuit IS NOT NULL")}
        nombres_db = {normalizar_nombre(n) for (n,) in con.execute("SELECT nom_cli FROM clientes")}

        for _, f in clientes.iterrows():
            cuit = limpio(f["cuit"])
            ya_existe = (re.sub(r"\D", "", cuit) in cuits_db) if cuit \
                else (normalizar_nombre(f["nom_cli"]) in nombres_db)
            if ya_existe:
                omitidos += 1
                continue
            nuevos += 1
            if dry_run:
                continue
            cur = con.execute("""
                INSERT INTO clientes (nom_cli, cuit, tel, mail, codigo, direccion,
                                      localidad, condicion_iva, tipo_factura, contacto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(limpio(f[c]) for c in ["nom_cli", "cuit", "tel", "mail", "codigo",
                        "direccion", "localidad", "condicion_iva", "tipo_factura", "contacto"]))
            for alias in f["aliases"]:
                con.execute("INSERT OR IGNORE INTO alias_clientes (alias, id_cliente) VALUES (?, ?)",
                            (normalizar_nombre(alias), cur.lastrowid))
        if not dry_run:
            con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    print(f"{'[PRUEBA] ' if dry_run else ''}Nuevos: {nuevos} | Ya existían: {omitidos} | "
          f"Fusionados: {len(fusiones)} | CUIT inválidos (quedan NULL): {len(invalidos)}")


if __name__ == "__main__":
    importar(dry_run=False)