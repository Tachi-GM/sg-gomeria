"""Importa a la base los remitos de 2026 desde Ctas_Corrientes.xls.

Uso (con la app cerrada):
    python scripts/importar_remitos.py                 # PRUEBA: no toca la base
    python scripts/importar_remitos.py --aplicar       # guarda en la base (con backup previo)
    python scripts/importar_remitos.py --aplicar --crear-clientes

Se puede correr todas las veces que haga falta: los remitos que ya están
en la base se saltean, así que no se duplican.

Clientes con otro nombre en el Excel: se completa datos_privados/mapeo_clientes.txt
con líneas del tipo   Nombre en el Excel => Nombre exacto en la base
(la prueba genera mapeo_clientes_pendiente.txt con los que no encontró).
"""

import argparse
import difflib
import re
import sqlite3
import sys
import unicodedata
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

# La raíz del proyecto es la carpeta que contiene utils/ (sirve si el script está en la raíz o en scripts/)
BASE = Path(__file__).resolve().parent
if not (BASE / "utils").exists():
    BASE = BASE.parent
sys.path.insert(0, str(BASE))  # así Python encuentra utils/

from utils.formateadores import validar_y_formatear_remito  # noqa: E402

warnings.filterwarnings("ignore", message="Could not infer format")

RUTA_EXCEL = BASE / "datos_privados" / "Ctas Corrientes.xls"
RUTA_DB = BASE / "sg_gomeria.db"
RUTA_MAPEO = BASE / "datos_privados" / "mapeo_clientes.txt"
RUTA_PENDIENTES = BASE / "datos_privados" / "mapeo_clientes_pendiente.txt"
ANIO = 2026

# Posición de cada dato en las hojas del Excel (columna A = 0, B = 1, ...)
COLUMNAS = ["comp", "numero", "fecha", "cliente", "obs", "importe", "total", "pagado", "resto"]
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
SUFIJOS_EMPRESA = {"sa", "srl", "sacif", "sas"}
SINONIMOS = {"transporte": "transp", "expreso": "exp"}


def normalizar(texto):
    """'¨Transp  Gabriel' -> 'transp gabriel' (sin tildes, símbolos ni mayúsculas)."""
    texto = str(texto).replace("&", " y ")
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-z0-9 ]", "", texto.lower())
    return " ".join(texto.split())


def clave(nombre):
    """Clave para comparar clientes: 'Ba&Lu', 'Ba y Lu' y 'BAYLU' dan todas 'baylu'."""
    palabras = [SINONIMOS.get(p, p) for p in normalizar(nombre).split() if p not in SUFIJOS_EMPRESA]
    return "".join(palabras)


def calcular_estado(pagado, resto):
    if pagado > 0 and resto <= 0:
        return "PAGADO"
    if pagado > 0:
        return "EN PROCESO"  # pagó una parte
    return "PENDIENTE"


def leer_remitos(ruta_excel):
    """Devuelve (remitos_validos, descartados, advertencias) de todas las hojas XXX26."""
    xls = pd.ExcelFile(ruta_excel, engine="xlrd")
    hojas = [h for h in xls.sheet_names if re.fullmatch(rf"[A-Za-z]{{3}}{ANIO % 100}", h.strip())]
    if not hojas:
        raise SystemExit(f"No encontré hojas del {ANIO} (ej. 'Ene{ANIO % 100}') en el Excel.")

    remitos, descartados, advertencias, vistos = [], {}, [], {}

    def descartar(motivo, hoja, fila, detalle=""):
        descartados.setdefault(motivo, []).append(f"{hoja} fila {fila}: {detalle}".strip(": "))

    for hoja in hojas:
        df = xls.parse(hoja, header=None, usecols=list(range(len(COLUMNAS))))
        df.columns = COLUMNAS
        df["numero"] = pd.to_numeric(df["numero"], errors="coerce")
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        for col in ("importe", "pagado", "resto"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        for i, f in df.iterrows():
            fila = i + 1  # fila tal cual se ve en Excel
            if pd.isna(f["numero"]):
                continue  # encabezados, títulos, totales y filas vacías: no son remitos

            comp = "" if pd.isna(f["comp"]) else str(f["comp"]).strip().upper()
            numero = int(f["numero"])
            if comp.startswith("FACT"):
                descartar("facturas (no son remitos)", hoja, fila, f"{comp} {numero}")
                continue
            if comp in ("OI", "OIB"):
                tipo = comp
            elif comp == "" and numero >= 10000:
                tipo = "OI"  # celda de tipo vacía dentro del bloque de OI
            else:
                descartar("tipo de comprobante desconocido", hoja, fila, f"{comp!r} {numero}")
                continue

            cliente = "" if pd.isna(f["cliente"]) else str(f["cliente"]).strip()
            if not clave(cliente) or pd.isna(f["fecha"]):
                descartar("sin cliente o sin fecha (números sin usar)", hoja, fila, f"{tipo} {numero}")
                continue
            if clave(cliente).startswith("anulad"):
                descartar("anulados", hoja, fila, f"{tipo} {numero}")
                continue
            if f["fecha"].year != ANIO:
                descartar(f"fecha fuera de {ANIO}", hoja, fila, f"{tipo} {numero} ({f['fecha']:%Y-%m-%d})")
                continue
            if f["fecha"].month != MESES.get(hoja.strip()[:3].lower()):
                advertencias.append(f"{hoja} fila {fila}: {tipo} {numero} ({cliente}) tiene fecha {f['fecha']:%Y-%m-%d}, de otro mes que la hoja")

            valido, remito = validar_y_formatear_remito(tipo, str(numero))
            if not valido:
                descartar("número de remito inválido", hoja, fila, f"{tipo} {numero}: {remito}")
                continue

            fecha = f["fecha"].strftime("%Y-%m-%d")
            total = round(float(f["importe"]), 2)
            previo = vistos.get((tipo, remito))
            if previo:
                if previo["clave"] == clave(cliente) and previo["fecha"] == fecha and previo["total"] == total:
                    descartar("repetidos idénticos (se ignoran)", hoja, fila, f"{tipo} {remito}")
                else:
                    descartar("CONFLICTO: mismo número con otros datos (se importó el primero)", hoja, fila,
                              f"{tipo} {remito} {cliente} ${total:,.0f} {fecha}  <->  ya cargado en {previo['donde']}: "
                              f"{previo['cliente']} ${previo['total']:,.0f} {previo['fecha']}")
                continue
            vistos[(tipo, remito)] = {"clave": clave(cliente), "fecha": fecha, "total": total,
                                      "cliente": cliente, "donde": f"{hoja} fila {fila}"}

            remitos.append({
                "tipo": tipo,
                "remito": remito,
                "fecha": fecha,
                "cliente": cliente,
                "total": total,
                "detalle": "" if pd.isna(f["obs"]) else str(f["obs"]).strip(),
                "estado": calcular_estado(f["pagado"], f["resto"]),
            })
    return remitos, descartados, advertencias


def cargar_mapeo(ruta):
    """Lee 'Nombre en Excel => Nombre en la base' (ignora vacíos y comentarios con #)."""
    mapeo = {}
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if "=>" not in linea or linea.lstrip().startswith("#"):
                continue
            excel, base = linea.split("=>", 1)
            base = base.split("#")[0].strip()
            if excel.strip() and base:
                mapeo[clave(excel)] = clave(base)
    return mapeo


def cargar_clientes(con):
    """Arma {clave: (id, nombre_real)} y {clave_alias: id}."""
    clientes = {clave(n): (i, n) for i, n in con.execute("SELECT id_cliente, nom_cli FROM clientes")}
    try:  # esta tabla la creó importar_clientes.py; puede no existir
        alias = {clave(a): i for a, i in con.execute("SELECT alias, id_cliente FROM alias_clientes")}
    except sqlite3.OperationalError:
        alias = {}
    return clientes, alias


def buscar_cliente(nombre, clientes, alias, manual):
    k = clave(nombre)
    k = manual.get(k, k)
    if k in alias:
        return alias[k]
    return clientes[k][0] if k in clientes else None


def hacer_backup(ruta_db):
    carpeta = BASE / "backups"
    carpeta.mkdir(exist_ok=True)
    destino_ruta = carpeta / f"antes_import_remitos_{datetime.now():%Y-%m-%d_%H-%M}.db"
    origen, destino = sqlite3.connect(ruta_db), sqlite3.connect(destino_ruta)
    try:
        origen.backup(destino)  # copia consistente aunque la base esté en uso
    finally:
        destino.close()
        origen.close()
    return destino_ruta


def importar(ruta_excel, ruta_db, aplicar, crear_clientes):
    remitos, descartados, advertencias = leer_remitos(ruta_excel)
    manual = cargar_mapeo(RUTA_MAPEO)

    if aplicar:
        print(f"Backup guardado en: {hacer_backup(ruta_db)}")

    con = sqlite3.connect(ruta_db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    nuevos = ya_existian = 0
    sin_cliente = {}  # clave -> {"nombre": primera grafía, "cant": remitos que quedaron afuera}
    creados = {}
    clientes = {}

    try:
        clientes, alias = cargar_clientes(con)
        for r in remitos:
            id_cliente = buscar_cliente(r["cliente"], clientes, alias, manual)

            if id_cliente is None and crear_clientes:
                k = clave(r["cliente"])
                k = manual.get(k, k)
                nombre = re.sub(r"^[^\w]+", "", r["cliente"]).strip()  # saca símbolos sueltos del inicio
                id_cliente = con.execute("INSERT INTO clientes (nom_cli) VALUES (?)", (nombre,)).lastrowid if aplicar else -1
                clientes[k] = (id_cliente, nombre)  # los próximos remitos del mismo cliente lo encuentran
                creados[k] = nombre

            if id_cliente is None:
                datos = sin_cliente.setdefault(clave(r["cliente"]), {"nombre": r["cliente"], "cant": 0})
                datos["cant"] += 1
                continue

            if con.execute("SELECT 1 FROM trabajos WHERE tipo = ? AND remito = ?", (r["tipo"], r["remito"])).fetchone():
                ya_existian += 1
                continue

            if aplicar:
                try:
                    con.execute(
                        """INSERT INTO trabajos (remito, tipo, fecha, id_cliente, total, detalle, estado)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (r["remito"], r["tipo"], r["fecha"], id_cliente, r["total"], r["detalle"], r["estado"]),
                    )
                except sqlite3.IntegrityError:  # ej. el número ya existe con otro tipo
                    ya_existian += 1
                    continue
            nuevos += 1

        if aplicar:
            con.commit()
    except Exception:
        con.rollback()  # si algo falla, no queda nada a medias
        raise
    finally:
        con.close()

    # ---------- Resumen ----------
    print(f"\n{'' if aplicar else '[PRUEBA - no se tocó la base] '}Remitos {ANIO} leídos del Excel: {len(remitos)}")
    print(f"  Nuevos {'guardados' if aplicar else 'a guardar'}: {nuevos}")
    print(f"  Ya existían en la base: {ya_existian}")
    if creados:
        print(f"  Clientes {'creados' if aplicar else 'a crear'}: {len(creados)}")
    for motivo, lista in descartados.items():
        print(f"  Salteados por '{motivo}': {len(lista)}")

    for motivo, lista in descartados.items():
        if motivo.startswith(("CONFLICTO", "tipo", "fecha", "número")):
            print(f"\n{motivo}:")
            for linea in lista:
                print(f"  - {linea}")
    if advertencias:
        print("\nFechas de otro mes que la hoja (se importaron igual; si es un error de tipeo, corregilo en el Excel ANTES de aplicar):")
        for a in advertencias:
            print(f"  - {a}")

    if sin_cliente:
        base = {k: v[1] for k, v in clientes.items()}
        lineas = []
        for k, d in sorted(sin_cliente.items(), key=lambda x: -x[1]["cant"]):
            cerca = difflib.get_close_matches(k, base, n=2, cutoff=0.6)
            tip = f"  ¿{' / '.join(base[c] for c in cerca)}?" if cerca else ""
            lineas.append(f"{d['nombre']} =>   # {d['cant']} remitos{tip}")
        RUTA_PENDIENTES.write_text(
            "# Copiá a mapeo_clientes.txt las líneas que quieras y escribí a la derecha de => el nombre EXACTO de la base.\n"
            + "\n".join(lineas) + "\n", encoding="utf-8")
        total = sum(d["cant"] for d in sin_cliente.values())
        print(f"\n{len(sin_cliente)} clientes del Excel no están en la base ({total} remitos sin importar). Los 15 con más remitos:")
        for linea in lineas[:15]:
            print(f"  {linea}")
        print(f"  Lista completa en: {RUTA_PENDIENTES}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--excel", default=RUTA_EXCEL, help="ruta del Ctas_Corrientes.xls")
    ap.add_argument("--db", default=RUTA_DB, help="ruta de la base SQLite")
    ap.add_argument("--aplicar", action="store_true", help="guardar en la base (sin esto es solo una prueba)")
    ap.add_argument("--crear-clientes", action="store_true", help="dar de alta los clientes que no existan")
    args = ap.parse_args()
    importar(args.excel, args.db, args.aplicar, args.crear_clientes)
