"""Importa las tres listas de precios de un Excel al catálogo de tareas."""

import argparse
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from openpyxl import load_workbook

IVA = Decimal("1.21")
CENTAVOS = Decimal("0.01")
TOLERANCIA = CENTAVOS
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


def normalizar_descripcion(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def parsear_importe(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))

    texto = str(valor).strip().replace("$", "").replace(" ", "")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return Decimal(texto)
    except InvalidOperation as error:
        raise ValueError(f"Importe inválido: {valor!r}") from error


def calcular_sin_iva(precio_final):
    return (parsear_importe(precio_final) / IVA).quantize(
        CENTAVOS, rounding=ROUND_HALF_UP
    )


def comparar_importes(primero, segundo):
    return abs(parsear_importe(primero) - parsear_importe(segundo)) <= TOLERANCIA


def _nombre_hoja_lista(nombre):
    coincidencia = re.search(r"(?:^|[\s_-])([123])\s*$", nombre)
    return int(coincidencia.group(1)) if coincidencia else None


def detectar_hojas_listas(libro):
    hojas = {}
    for nombre in libro.sheetnames:
        numero = _nombre_hoja_lista(nombre)
        if numero is not None:
            if numero in hojas:
                raise ValueError(f"Hay más de una hoja para la lista {numero}")
            hojas[numero] = libro[nombre]

    faltantes = sorted(set((1, 2, 3)) - set(hojas))
    if faltantes:
        raise ValueError(f"Faltan hojas de listas: {', '.join(map(str, faltantes))}")
    return hojas


def _buscar_encabezados(hoja):
    requeridos = {
        "descripcion": "descripcion",
        "precio sin iva": "precio_sin_iva",
        "precio s/iva": "precio_sin_iva",
        "precio final": "precio_final",
    }

    for numero_fila, fila in enumerate(hoja.iter_rows(values_only=True), start=1):
        encontrados = {}
        for numero_columna, valor in enumerate(fila, start=1):
            clave = normalizar_descripcion(valor)
            if clave in requeridos:
                encontrados[requeridos[clave]] = numero_columna
        if len(encontrados) == len(set(requeridos.values())):
            return numero_fila, encontrados

    raise ValueError(f"No se encontraron encabezados válidos en {hoja.title}")


def leer_lista(hoja, numero_lista):
    fila_encabezados, columnas = _buscar_encabezados(hoja)
    filas = []
    advertencias = []

    for numero_fila, fila in enumerate(
        hoja.iter_rows(min_row=fila_encabezados + 1, values_only=True),
        start=fila_encabezados + 1,
    ):
        descripcion = fila[columnas["descripcion"] - 1]
        if descripcion is None or not str(descripcion).strip():
            continue

        try:
            precio_sin_iva = parsear_importe(fila[columnas["precio_sin_iva"] - 1])
            precio_final = parsear_importe(fila[columnas["precio_final"] - 1])
        except ValueError as error:
            advertencias.append(f"Hoja {numero_lista}, fila {numero_fila}: {error}")
            continue

        if precio_sin_iva is None or precio_final is None:
            advertencias.append(
                f"Hoja {numero_lista}, fila {numero_fila}: falta un precio"
            )
            continue

        filas.append(
            {
                "fila_excel": numero_fila,
                "descripcion": str(descripcion).strip(),
                "clave": normalizar_descripcion(descripcion),
                "precio_sin_iva": precio_sin_iva,
                "precio_final": precio_final,
            }
        )

    return filas, advertencias


def leer_excel(ruta_excel):
    libro = load_workbook(ruta_excel, read_only=True, data_only=True)
    try:
        hojas = detectar_hojas_listas(libro)
        listas = {}
        advertencias = []
        for numero, hoja in hojas.items():
            listas[numero], avisos = leer_lista(hoja, numero)
            advertencias.extend(avisos)
        return listas, advertencias
    finally:
        libro.close()


def comparar_con_base(listas, conexion):
    tareas = {}
    duplicadas = set()
    for tarea in conexion.execute(
        "SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas"
    ):
        clave = normalizar_descripcion(tarea["nom_tar"])
        if clave in tareas:
            duplicadas.add(clave)
        else:
            tareas[clave] = tarea

    resultados = []
    for numero_lista, filas in sorted(listas.items()):
        campo = {1: "precio", 2: "precio2", 3: "precio3"}[numero_lista]
        for fila in filas:
            tarea = tareas.get(fila["clave"])
            calculado = calcular_sin_iva(fila["precio_final"])
            resultado = {
                **fila,
                "lista": numero_lista,
                "campo": campo,
                "tarea": tarea,
                "calculo_iva_ok": comparar_importes(fila["precio_sin_iva"], calculado),
                "precio_actual": None if tarea is None else tarea[campo],
                "precio_distinto": (
                    None
                    if tarea is None
                    else not comparar_importes(tarea[campo], fila["precio_final"])
                ),
            }
            if fila["clave"] in duplicadas:
                resultado["estado"] = "duplicada"
            elif tarea is None:
                resultado["estado"] = "faltante"
            else:
                resultado["estado"] = (
                    "diferente" if resultado["precio_distinto"] else "igual"
                )
            resultados.append(resultado)
    return resultados


def crear_backup(ruta_db):
    carpeta = RAIZ_PROYECTO / "backups"
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / f"antes_import_precios_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    shutil.copy2(ruta_db, destino)
    return destino


def preparar_tareas_nuevas(resultados):
    nuevas = {}
    for resultado in resultados:
        if resultado["estado"] != "faltante":
            continue
        nueva = nuevas.setdefault(
            resultado["clave"],
            {
                "nom_tar": resultado["descripcion"],
                "precio": Decimal("0"),
                "precio2": Decimal("0"),
                "precio3": Decimal("0"),
            },
        )
        nueva[resultado["campo"]] = resultado["precio_final"]
    return list(nuevas.values())


def ejecutar(ruta_excel, ruta_db, actualizar=False):
    listas, advertencias = leer_excel(ruta_excel)
    conexion = sqlite3.connect(ruta_db)
    conexion.row_factory = sqlite3.Row
    try:
        resultados = comparar_con_base(listas, conexion)
        if actualizar:
            backup = crear_backup(ruta_db)
            nuevas = preparar_tareas_nuevas(resultados)
            actualizados = 0
            try:
                for nueva in nuevas:
                    conexion.execute(
                        """
                        INSERT INTO tareas (nom_tar, precio, precio2, precio3)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            nueva["nom_tar"],
                            float(nueva["precio"]),
                            float(nueva["precio2"]),
                            float(nueva["precio3"]),
                        ),
                    )
                for resultado in resultados:
                    if resultado["tarea"] is None:
                        continue
                    if resultado["precio_distinto"]:
                        conexion.execute(
                            f"UPDATE tareas SET {resultado['campo']} = ? WHERE id_tarea = ?",
                            (
                                float(resultado["precio_final"]),
                                resultado["tarea"]["id_tarea"],
                            ),
                        )
                        actualizados += 1
                conexion.commit()
            except Exception:
                conexion.rollback()
                raise
            print(f"Backup creado: {backup}")
            print(f"Tareas creadas: {len(nuevas)}")
            print(f"Precios actualizados: {actualizados}")

        resumen = {
            "igual": sum(r["estado"] == "igual" for r in resultados),
            "diferente": sum(r["estado"] == "diferente" for r in resultados),
            "faltantes_detectadas": sum(r["estado"] == "faltante" for r in resultados),
            "duplicada": sum(r["estado"] == "duplicada" for r in resultados),
            "iva_distinto": sum(not r["calculo_iva_ok"] for r in resultados),
        }
        print(
            "Resumen: "
            + " | ".join(f"{clave}={valor}" for clave, valor in resumen.items())
        )
        for advertencia in advertencias:
            print(f"Advertencia: {advertencia}")
        for resultado in resultados:
            if resultado["estado"] == "duplicada" or (
                resultado["estado"] == "faltante" and not actualizar
            ):
                print(
                    f"{resultado['estado'].capitalize()}: "
                    f"lista {resultado['lista']} - {resultado['descripcion']}"
                )
        return resultados, advertencias
    finally:
        conexion.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("excel", type=Path, help="Archivo Excel de listas de precios")
    parser.add_argument(
        "--db",
        type=Path,
        default=RAIZ_PROYECTO / "sg_gomeria.db",
        help="Base SQLite a revisar (por defecto, sg_gomeria.db)",
    )
    parser.add_argument(
        "--actualizar",
        action="store_true",
        help="Crear backup y guardar los precios diferentes",
    )
    args = parser.parse_args()

    if not args.excel.exists():
        parser.error(f"No existe el Excel: {args.excel}")
    if not args.db.exists():
        parser.error(f"No existe la base: {args.db}")

    ejecutar(args.excel, args.db, actualizar=args.actualizar)


if __name__ == "__main__":
    main()
