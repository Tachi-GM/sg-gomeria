"""Importa cheques desde el Excel «Cheques-Echeqs» a la tabla `cheques`.

Qué hace con los datos (que vienen "a mano" y con errores de tipeo):
- Fechas: acepta fechas reales y texto en castellano ("Viernes 26 de junio de 2026"). Se toma
  día, mes y año e IGNORA el nombre del día; si no coincide con el día real del calendario, se
  importa igual y queda anotado en el informe para revisar.
- Importes: acepta números y texto roto como "600,000,00" o "250 000 00" (los dos últimos
  dígitos son centavos).
- Bancos: unifica mayúsculas/minúsculas ("CREDICOOP" = "Credicoop"). "Echeq" se deja tal cual.
- Destino: va al campo «endosado» como texto plano. "Anulado/No aceptado" marca el cheque como
  Rechazado.
- Librador (el cliente): se busca primero entre los clientes y sus alias (también por lo que
  figura entre paréntesis). Si no existe, se crea y se guardan los alias.
- Sin número: se carga con un número provisional «SIN-N°-001», «SIN-N°-002»...
- Repetidos: un cheque se identifica por número + banco + importe + fecha de pago. Si ya existe
  (en el Excel o en la base) no se duplica; así se puede volver a correr sin problemas.
- La fecha de emisión no se usa (queda vacía).

Uso por consola (por defecto solo prueba, no guarda nada):
    python scripts/importar_cheques.py "Cheques-Echeqs.xlsx" [--db sg_gomeria.db] [--aplicar]
"""

import argparse
import re
import shutil
import sqlite3
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from utils.formateadores import parse_importe_ar  # noqa: E402

PREFIJO_SIN_NUMERO = "SIN-N°-"
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_ABREVIADOS = {"lun": 0, "mar": 1, "mie": 2, "jue": 3, "vie": 4, "sab": 5, "dom": 6}
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
         "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}
SUFIJOS_EMPRESA = {"sa", "srl", "sacif", "sas"}
SINONIMOS = {"transporte": "transp", "expreso": "exp"}
COLUMNAS_OBLIGATORIAS = ("numero", "banco", "librador", "importe", "fecha")


# --------------------------------------------------------------------------- textos
def sin_tildes(texto):
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def normalizar(texto):
    """'¨Transp  Gabriel' -> 'transp gabriel' (sin tildes, símbolos ni mayúsculas)."""
    texto = sin_tildes(str(texto).replace("&", " y ")).lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", "", texto).split())


def clave(nombre):
    """Clave para comparar clientes: 'Transporte Cuadra S.A.' y 'Transp Cuadra' coinciden."""
    palabras = [SINONIMOS.get(p, p) for p in normalizar(nombre).split() if p not in SUFIJOS_EMPRESA]
    return "".join(palabras)


def limpiar_nombre(nombre):
    return " ".join(re.sub(r"^[^\w(]+", "", str(nombre)).split())


# --------------------------------------------------------------------------- fechas
def parsear_fecha(valor):
    """Devuelve (fecha | None, dia_escrito | None, motivo_error | None).

    `dia_escrito` es el día de la semana (0 = lunes) que figuraba en el texto, solo para el informe.
    """
    if isinstance(valor, datetime):
        return valor.date(), None, None
    if isinstance(valor, date):
        return valor, None, None
    if valor is None or not str(valor).strip():
        return None, None, "sin fecha"

    texto = sin_tildes(str(valor)).lower()
    coincidencia = re.search(r"(\d{1,2})\s*(?:de\s*)?([a-z]{3,})\s*(?:de\s*)?(\d{4})", texto)
    if not coincidencia:
        return None, None, f"no se entiende la fecha «{str(valor).strip()}»"
    dia, palabra_mes, anio = int(coincidencia.group(1)), coincidencia.group(2), int(coincidencia.group(3))
    mes = MESES.get(palabra_mes[:3])
    if not mes:
        return None, None, f"mes desconocido en «{str(valor).strip()}»"

    primera = re.match(r"\s*([a-z]+)", texto)
    dia_escrito = DIAS_ABREVIADOS.get(primera.group(1)[:3]) if primera else None
    try:
        return date(anio, mes, dia), dia_escrito, None
    except ValueError:
        return None, dia_escrito, f"la fecha «{str(valor).strip()}» no existe en el calendario"


# --------------------------------------------------------------------------- importes
def parsear_importe(valor):
    """Devuelve (importe | None, fue_corregido).

    "600,000,00" -> 600000.0 (corregido) · 181500 -> 181500.0 · "1.234,50" -> 1234.5
    """
    if valor is None or isinstance(valor, bool):
        return None, False
    if isinstance(valor, (int, float)):
        return round(float(valor), 2), False

    texto = str(valor).strip().replace("$", "")
    if not texto or not re.fullmatch(r"[\d.,\s]+", texto):
        return None, False
    partes = [p for p in re.split(r"[.,\s]+", texto) if p != ""]
    # Miles y centavos con el mismo símbolo: "600,000,00" / "250 000 00" -> 600000.00 / 250000.00
    if len(partes) >= 3 and len(partes[-1]) == 2 and all(len(p) == 3 for p in partes[1:-1]):
        return round(float("".join(partes[:-1]) + "." + partes[-1]), 2), True
    importe = parse_importe_ar(texto, None)
    if importe is None:
        return None, False
    return round(importe, 2), not re.fullmatch(r"\d+", texto)


def normalizar_numero(valor):
    if valor is None:
        return None
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    texto = str(valor).strip()
    return texto or None


def unificar_bancos(nombres):
    """Devuelve {nombre original: nombre unificado}, ignorando mayúsculas y espacios de más."""
    variantes = {}
    for nombre in nombres:
        limpio = " ".join(str(nombre).split())
        variantes.setdefault(limpio.casefold(), Counter())[limpio] += 1
    elegido = {}
    for clave_banco, contador in variantes.items():
        ordenadas = [v for v, _ in contador.most_common()]
        # Se prefiere una grafía que no esté toda en mayúsculas ("Credicoop" y no "CREDICOOP").
        no_gritadas = [v for v in ordenadas if not (v.isupper() and len(v) > 5)]
        elegido[clave_banco] = (no_gritadas or ordenadas)[0]
    return {n: elegido[" ".join(str(n).split()).casefold()] for n in nombres}


# --------------------------------------------------------------------------- lectura del Excel
def leer_excel(ruta_excel):
    """Lee la primera hoja y devuelve una lista de filas crudas (dicts) con su número de fila."""
    libro = load_workbook(ruta_excel, data_only=True, read_only=True)
    try:
        hoja = libro.worksheets[0]
        filas = list(hoja.iter_rows(values_only=True))
    finally:
        libro.close()

    encabezado, indice_encabezado = None, None
    for i, fila in enumerate(filas[:15]):
        nombres = [normalizar(c) if c is not None else "" for c in fila]
        if "numero" in nombres and "importe" in nombres:
            encabezado, indice_encabezado = {n: j for j, n in enumerate(nombres) if n}, i
            break
    if encabezado is None:
        raise ValueError("No encontré la fila de encabezados (Numero, Banco, Librador, Destino, Importe, Fecha)")
    faltan = [c for c in COLUMNAS_OBLIGATORIAS if c not in encabezado]
    if faltan:
        raise ValueError("Faltan columnas en el Excel: " + ", ".join(faltan))

    datos = []
    for i, fila in enumerate(filas[indice_encabezado + 1:], start=indice_encabezado + 2):
        if not any(c is not None and str(c).strip() for c in fila):
            continue

        def celda(nombre):
            j = encabezado.get(nombre)
            return fila[j] if j is not None and j < len(fila) else None

        datos.append({
            "fila": i, "numero": celda("numero"), "banco": celda("banco"),
            "librador": celda("librador"), "destino": celda("destino"),
            "importe": celda("importe"), "fecha": celda("fecha"),
        })
    return datos


# --------------------------------------------------------------------------- clientes
def _asegurar_alias(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS alias_clientes (
            alias TEXT PRIMARY KEY,
            id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente)
        )
    """)


def _cargar_indice_clientes(conexion):
    """{clave: (id_cliente, nombre_del_cliente)}: primero los nombres, después los alias."""
    indice = {}
    for fila in conexion.execute("SELECT id_cliente, nom_cli FROM clientes"):
        indice.setdefault(clave(fila["nom_cli"]), (fila["id_cliente"], fila["nom_cli"]))
    for fila in conexion.execute(
        "SELECT a.alias, c.id_cliente, c.nom_cli FROM alias_clientes a "
        "JOIN clientes c ON c.id_cliente = a.id_cliente"
    ):
        indice.setdefault(clave(fila["alias"]), (fila["id_cliente"], fila["nom_cli"]))
    return indice


def _candidatos_cliente(librador):
    """Textos a probar, de más a menos específico: completo, sin paréntesis y lo de adentro.

    Devuelve ([(texto, esta_entre_parentesis)], nombre_para_crear_si_no_existe).
    """
    texto = limpiar_nombre(librador)
    sin_parentesis = limpiar_nombre(re.sub(r"\([^)]*\)", " ", texto))
    entre_parentesis = [limpiar_nombre(p) for p in re.findall(r"\(([^)]*)\)", texto)]
    vistos, resultado = set(), []
    for candidato, entre in [(texto, False), (sin_parentesis, False), *[(p, True) for p in entre_parentesis]]:
        k = clave(candidato)
        if len(k) >= 2 and k not in vistos:
            vistos.add(k)
            resultado.append((candidato, entre))
    return resultado, sin_parentesis or texto


# --------------------------------------------------------------------------- importación
def importar(ruta_excel, ruta_db, actualizar=False, funcion_backup=None):
    """Núcleo de la importación: no imprime nada y devuelve un diccionario con el informe.

    actualizar=False: solo analiza y arma el informe (no toca la base).
    actualizar=True: backup (solo si hay algo para guardar) + inserción en una transacción.
    """
    crudas = leer_excel(ruta_excel)
    conexion = sqlite3.connect(ruta_db)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    try:
        _asegurar_alias(conexion)
        conexion.commit()
        indice = _cargar_indice_clientes(conexion)
        # Clientes que se crean en esta misma corrida: solo se reutilizan si el texto completo
        # (o el nombre sin paréntesis) coincide; lo que va entre paréntesis nunca une dos clientes nuevos.
        nuevos = {}

        # Cheques que ya están en la base (para no duplicar si se vuelve a importar).
        con_numero, sin_numero, max_sin_numero = set(), set(), 0
        for f in conexion.execute("SELECT numero, banco, importe, fecha_pago, id_cliente FROM cheques"):
            importe = round(float(f["importe"]), 2)
            banco = " ".join(str(f["banco"]).split()).casefold()
            if str(f["numero"]).startswith(PREFIJO_SIN_NUMERO):
                sin_numero.add((banco, importe, f["fecha_pago"], f["id_cliente"]))
                try:
                    max_sin_numero = max(max_sin_numero, int(str(f["numero"])[len(PREFIJO_SIN_NUMERO):]))
                except ValueError:
                    pass
            else:
                con_numero.add((str(f["numero"]), banco, importe, f["fecha_pago"]))

        bancos = unificar_bancos([c["banco"] for c in crudas if c["banco"]])
        informe = {
            "importados": [], "ya_existian": [], "duplicados_en_excel": [], "invalidas": [],
            "fechas_a_revisar": [], "importes_corregidos": [], "sin_numero": [],
            "clientes_creados": [], "clientes_asociados": [], "rechazados": [],
            "bancos_unificados": sorted({f"{o} → {u}" for o, u in bancos.items() if o.strip() != u}),
            "backup": None,
        }
        a_insertar, vistos_excel, contador_sin_numero = [], set(), max_sin_numero

        for c in crudas:
            fila = c["fila"]
            fecha, dia_escrito, error_fecha = parsear_fecha(c["fecha"])
            importe, corregido = parsear_importe(c["importe"])
            librador = limpiar_nombre(c["librador"] or "")
            banco = bancos.get(c["banco"], "") if c["banco"] else ""
            motivo = None
            if error_fecha:
                motivo = error_fecha
            elif importe is None or importe <= 0:
                motivo = f"importe no válido («{c['importe']}»)"
            elif not librador:
                motivo = "falta el librador (cliente)"
            elif not banco:
                motivo = "falta el banco"
            if motivo:
                informe["invalidas"].append({"fila": fila, "motivo": motivo, "numero": c["numero"], "librador": librador})
                continue

            if corregido and not isinstance(c["importe"], (int, float)):
                informe["importes_corregidos"].append(
                    {"fila": fila, "original": str(c["importe"]).strip(), "importe": importe})
            if dia_escrito is not None and dia_escrito != fecha.weekday():
                informe["fechas_a_revisar"].append({
                    "fila": fila, "original": str(c["fecha"]).strip(), "fecha": fecha,
                    "dia_real": DIAS_SEMANA[fecha.weekday()], "librador": librador,
                    "numero": normalizar_numero(c["numero"]), "importe": importe,
                })

            # ---- cliente (alias primero; si no existe, se creará)
            candidatos, nombre_nuevo = _candidatos_cliente(librador)
            encontrado = None
            for texto_candidato, entre_parentesis in candidatos:
                k = clave(texto_candidato)
                if k in indice:
                    encontrado = indice[k]
                    break
                if not entre_parentesis and k in nuevos:
                    encontrado = nuevos[k]
                    break
            id_cliente, nombre_cliente = encontrado if encontrado else (None, nombre_nuevo)

            numero = normalizar_numero(c["numero"])
            fecha_iso = fecha.isoformat()
            banco_k = banco.casefold()
            if numero:
                identidad = (numero, banco_k, importe, fecha_iso)
                existe_en_base = identidad in con_numero
            else:
                identidad = (None, banco_k, importe, fecha_iso, clave(nombre_cliente))
                existe_en_base = id_cliente is not None and (banco_k, importe, fecha_iso, id_cliente) in sin_numero

            resumen_fila = {"fila": fila, "numero": numero, "banco": banco, "cliente": nombre_cliente,
                            "importe": importe, "fecha": fecha}
            if identidad in vistos_excel:
                informe["duplicados_en_excel"].append(resumen_fila)
                continue
            vistos_excel.add(identidad)
            if existe_en_base:
                informe["ya_existian"].append(resumen_fila)
                continue

            if not numero:
                contador_sin_numero += 1
                numero = f"{PREFIJO_SIN_NUMERO}{contador_sin_numero:03d}"
                resumen_fila["numero"] = numero
                informe["sin_numero"].append({**resumen_fila, "librador": librador})

            if id_cliente is None:
                # Se crea una sola vez; las filas siguientes del mismo cliente lo reutilizan.
                id_cliente = ("nuevo", clave(nombre_nuevo))
                informe["clientes_creados"].append({"fila": fila, "nombre": nombre_nuevo, "librador": librador})
                for texto_candidato, entre_parentesis in candidatos:
                    if not entre_parentesis:
                        nuevos.setdefault(clave(texto_candidato), (id_cliente, nombre_nuevo))
            elif encontrado and clave(librador) != clave(nombre_cliente) and not any(
                    a["librador"] == librador for a in informe["clientes_asociados"]):
                informe["clientes_asociados"].append(
                    {"fila": fila, "librador": librador, "cliente": nombre_cliente})

            estado = "Pendiente"
            destino = " ".join(str(c["destino"] or "").split())
            if "anulado" in normalizar(destino) or "no aceptado" in normalizar(destino):
                estado = "Rechazado"
                informe["rechazados"].append(resumen_fila)

            a_insertar.append({**resumen_fila, "id_cliente": id_cliente, "estado": estado,
                               "endosado": destino, "fecha_iso": fecha_iso, "librador": librador})
            informe["importados"].append({**resumen_fila, "estado": estado, "endosado": destino})

        if actualizar and a_insertar:
            informe["backup"] = (funcion_backup or crear_backup)(ruta_db)
            try:
                creados = {}
                for nuevo in informe["clientes_creados"]:
                    k = clave(nuevo["nombre"])
                    cursor = conexion.execute("INSERT INTO clientes (nom_cli) VALUES (?)", (nuevo["nombre"],))
                    creados[("nuevo", k)] = cursor.lastrowid
                    # Alias: el texto completo tal como figuraba en el Excel (si difiere del nombre).
                    alias = normalizar(nuevo["librador"])
                    if alias and alias != normalizar(nuevo["nombre"]):
                        conexion.execute(
                            "INSERT OR IGNORE INTO alias_clientes (alias, id_cliente) VALUES (?, ?)",
                            (alias, cursor.lastrowid))
                for fila in a_insertar:
                    id_final = creados.get(fila["id_cliente"], fila["id_cliente"])
                    conexion.execute(
                        """INSERT INTO cheques (numero, cliente, banco, fecha_pago, importe, estado, endosado, id_cliente)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (fila["numero"], fila["cliente"], fila["banco"], fila["fecha_iso"], fila["importe"],
                         fila["estado"], fila["endosado"], id_final))
                conexion.commit()
            except Exception:
                conexion.rollback()
                raise
        informe["resumen"] = {
            "filas_leidas": len(crudas), "importados": len(informe["importados"]),
            "ya_existian": len(informe["ya_existian"]), "duplicados_en_excel": len(informe["duplicados_en_excel"]),
            "invalidas": len(informe["invalidas"]), "clientes_creados": len(informe["clientes_creados"]),
            "sin_numero": len(informe["sin_numero"]), "fechas_a_revisar": len(informe["fechas_a_revisar"]),
            "importes_corregidos": len(informe["importes_corregidos"]),
        }
        informe["aplicado"] = bool(actualizar and a_insertar)
        return informe
    finally:
        conexion.close()


def crear_backup(ruta_db):
    carpeta = RAIZ_PROYECTO / "backups"
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / f"antes_import_cheques_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    shutil.copy2(ruta_db, destino)
    return destino


# --------------------------------------------------------------------------- consola
def ejecutar(ruta_excel, ruta_db, actualizar=False):
    informe = importar(ruta_excel, ruta_db, actualizar=actualizar)
    print(("IMPORTADO" if informe["aplicado"] else "PRUEBA (no se guardó nada)") + ":")
    for clave_r, valor in informe["resumen"].items():
        print(f"  {clave_r.replace('_', ' ')}: {valor}")
    if informe["backup"]:
        print(f"  backup: {informe['backup']}")
    secciones = [
        ("invalidas", "Filas NO importadas", lambda x: f"fila {x['fila']}: {x['motivo']}"),
        ("fechas_a_revisar", "Fechas para revisar (el día escrito no coincide)",
         lambda x: f"fila {x['fila']}: «{x['original']}» → {x['fecha']:%d/%m/%Y} ({x['dia_real']})"),
        ("importes_corregidos", "Importes corregidos", lambda x: f"fila {x['fila']}: «{x['original']}» → {x['importe']:,.2f}"),
        ("sin_numero", "Sin número (provisorio)", lambda x: f"fila {x['fila']}: {x['numero']} · {x['librador']}"),
        ("clientes_creados", "Clientes creados", lambda x: f"fila {x['fila']}: {x['nombre']}"),
        ("clientes_asociados", "Asociados a un cliente existente", lambda x: f"fila {x['fila']}: «{x['librador']}» → {x['cliente']}"),
        ("duplicados_en_excel", "Repetidos dentro del Excel", lambda x: f"fila {x['fila']}: {x['numero']} · {x['banco']}"),
        ("rechazados", "Marcados como Rechazado", lambda x: f"fila {x['fila']}: {x['numero']} · {x['cliente']}"),
    ]
    for campo, titulo, formato in secciones:
        if informe[campo]:
            print(f"\n{titulo} ({len(informe[campo])}):")
            for item in informe[campo]:
                print("  - " + formato(item))
    return informe


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("excel", type=Path, help="Excel de cheques")
    parser.add_argument("--db", type=Path, default=RAIZ_PROYECTO / "sg_gomeria.db", help="Base SQLite")
    parser.add_argument("--aplicar", action="store_true", help="Hacer backup y guardar (sin esto, solo prueba)")
    args = parser.parse_args()
    if not args.excel.exists():
        parser.error(f"No existe el Excel: {args.excel}")
    if not args.db.exists():
        parser.error(f"No existe la base: {args.db}")
    ejecutar(args.excel, args.db, actualizar=args.aplicar)


if __name__ == "__main__":
    main()
