"""Generadores de archivos para exportaciones mensuales."""

from io import BytesIO
from textwrap import wrap

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError


def _texto_tareas(remito):
    return "; ".join(
        f"{detalle['nombre_tarea']} x {detalle['cantidad']}"
        for detalle in remito["detalles"]
    )


MESES = {
    "01": "Enero",
    "02": "Febrero",
    "03": "Marzo",
    "04": "Abril",
    "05": "Mayo",
    "06": "Junio",
    "07": "Julio",
    "08": "Agosto",
    "09": "Septiembre",
    "10": "Octubre",
    "11": "Noviembre",
    "12": "Diciembre",
}


def _calcular_importes(remito, con_iva):
    if con_iva:
        total = round(remito["total"], 2)
        importe = round(total / 1.21, 2)
    else:
        importe = round(remito["total"], 2)
        total = round(importe * 1.21, 2)
    return importe, round(total - importe, 2), total


def generar_excel_general(datos):
    """Genera un XLSX general, con una pestaña de formato mensual por mes."""
    libro = Workbook()
    cliente = datos["cliente"]
    hoja_resumen = libro.active
    hoja_resumen.title = "Resumen"
    hoja_resumen["A1"] = f"{cliente['nom_cli']} - Resumen"
    hoja_resumen["A1"].font = Font(bold=True, size=14)
    hoja_resumen["A2"] = "CUIT"
    hoja_resumen["B2"] = cliente["cuit"] or "Sin registrar"
    hoja_resumen["A4"] = "Mes"
    hoja_resumen["B4"] = "Subtotal"
    hoja_resumen["C4"] = "IVA"
    hoja_resumen["D4"] = "Total"
    for celda in hoja_resumen[4]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1A42B8")

    nombres_usados = set()
    for fila, mes in enumerate(datos["meses"], start=5):
        nombre_mes = _nombre_pestana(mes["periodo"], nombres_usados)
        hoja_resumen.cell(fila, 1, nombre_mes)
        hoja_resumen.cell(fila, 2, f"='{nombre_mes}'!E{len(mes['remitos']) + 4}")
        hoja_resumen.cell(fila, 3, f"='{nombre_mes}'!E{len(mes['remitos']) + 5}")
        hoja_resumen.cell(fila, 4, f"='{nombre_mes}'!E{len(mes['remitos']) + 6}")
        _generar_hoja_mensual(
            libro, mes, cliente["con_iva"], nombre_mes, cliente["nom_cli"]
        )

    fila_total = 5 + len(datos["meses"])
    hoja_resumen.cell(fila_total, 1, "TOTAL GENERAL").font = Font(bold=True)
    for columna in range(2, 5):
        letra = chr(64 + columna)
        hoja_resumen.cell(
            fila_total, columna, f"=SUM({letra}5:{letra}{fila_total - 1})"
        )
        hoja_resumen.cell(fila_total, columna).font = Font(bold=True)
    for columna, ancho in {"A": 20, "B": 16, "C": 16, "D": 16}.items():
        hoja_resumen.column_dimensions[columna].width = ancho

    for hoja in libro.worksheets:
        hoja.sheet_view.showGridLines = True

    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)
    return salida


def _nombre_pestana(periodo, nombres_usados):
    nombre_base = MESES[periodo[5:7]]
    nombre = nombre_base
    if nombre in nombres_usados:
        nombre = f"{nombre_base} {periodo[:4]}"
    nombres_usados.add(nombre)
    return nombre


def _generar_hoja_mensual(libro, datos, con_iva, nombre, nombre_cliente):
    hoja = libro.create_sheet(nombre)
    hoja.merge_cells("A1:G1")
    hoja["A1"] = f"{nombre_cliente} - {nombre}"
    hoja["A1"].font = Font(bold=True, size=14)
    hoja["A1"].alignment = Alignment(horizontal="center")
    encabezados = [
        "OI N°",
        "Fecha",
        "Detalle",
        "Importe",
        "Total",
        "Pagado",
        "Saldo",
    ]
    for columna, encabezado in enumerate(encabezados, start=1):
        celda = hoja.cell(2, columna, encabezado)
        celda.font = Font(bold=True)
        celda.border = Border(bottom=Side(style="thin", color="000000"))

    saldo_anterior = 0
    for fila, remito in enumerate(datos["remitos"], start=3):
        importe, iva, total = _calcular_importes(remito, con_iva)
        pagado = importe if remito["estado"] == "PAGADO" else 0
        hoja.cell(fila, 1, remito["remito"])
        hoja.cell(fila, 2, remito["fecha"])
        hoja.cell(fila, 3, remito["detalle"] or _texto_tareas(remito))
        if con_iva:
            hoja.cell(fila, 4, f"=E{fila}/1.21")
            hoja.cell(fila, 5, total)
        else:
            hoja.cell(fila, 4, importe)
            hoja.cell(fila, 5, f"=D{fila}*1.21")
        hoja.cell(
            fila,
            6,
            f"=D{fila}" if remito["estado"] == "PAGADO" else 0,
        )
        hoja.cell(
            fila,
            7,
            f"=G{fila - 1}+D{fila}-F{fila}" if fila > 3 else f"=D{fila}-F{fila}",
        )
        for columna in range(4, 8):
            hoja.cell(fila, columna).number_format = "#,##0.00"
        saldo_anterior += importe - pagado

    primera = 3
    ultima = 2 + len(datos["remitos"])
    fila_subtotal = ultima + 2
    fila_iva = ultima + 3
    fila_total = ultima + 4
    hoja.cell(fila_subtotal, 4, "subtotal").font = Font(bold=True)
    hoja.cell(fila_subtotal, 5, f"=SUM(D{primera}:D{ultima})")
    hoja.cell(fila_iva, 4, "IVA").font = Font(bold=True)
    hoja.cell(fila_iva, 5, f"=E{fila_total}-E{fila_subtotal}")
    hoja.cell(fila_total, 4, "Total").font = Font(bold=True)
    hoja.cell(fila_total, 5, f"=SUM(E{primera}:E{ultima})")
    for fila in (fila_subtotal, fila_iva, fila_total):
        hoja.cell(fila, 5).number_format = "#,##0.00"
    for columna, ancho in {
        "A": 14,
        "B": 14,
        "C": 42,
        "D": 16,
        "E": 16,
        "F": 16,
        "G": 16,
    }.items():
        hoja.column_dimensions[columna].width = ancho
    hoja.freeze_panes = "A3"


def generar_imagen(datos):
    """Genera una imagen legible con el resumen mensual y miniaturas seguras."""
    ancho = 1500
    margen = 40
    alto_fila = 72
    alto_foto = 190
    alto = (
        190
        + sum(
            alto_foto if remito["foto_path"] else alto_fila
            for remito in datos["remitos"]
        )
        + 100
    )
    imagen = Image.new("RGB", (ancho, max(alto, 300)), "white")
    dibujo = ImageDraw.Draw(imagen)
    fuente = ImageFont.load_default()

    cliente = datos["cliente"]
    dibujo.text(
        (margen, 30),
        f"Remitos de {cliente['nom_cli']} | CUIT: {cliente['cuit'] or 'Sin registrar'}",
        fill="black",
        font=fuente,
    )
    dibujo.text((margen, 55), f"Período: {datos['periodo']}", fill="black", font=fuente)
    dibujo.text(
        (margen, 80),
        "Fecha | Remito | Tareas | Total | Estado",
        fill="black",
        font=fuente,
    )

    y = 120
    for remito in datos["remitos"]:
        tareas = _texto_tareas(remito) or "Sin tareas"
        texto = (
            f"{remito['fecha']} | {remito['tipo']} #{remito['remito']} | "
            f"{tareas} | ${remito['total']:,.2f} | {remito['estado']}"
        )
        lineas = wrap(texto, width=125)
        dibujo.multiline_text((margen, y), "\n".join(lineas), fill="black", font=fuente)
        if remito["foto_path"]:
            try:
                with Image.open(remito["foto_path"]) as foto_original:
                    foto = foto_original.convert("RGB")
            except (OSError, UnidentifiedImageError):
                foto = None
            if foto is not None:
                foto.thumbnail((260, 160))
                imagen.paste(foto, (ancho - margen - foto.width, y))
            y += alto_foto
        else:
            y += alto_fila

    dibujo.text(
        (margen, y + 15),
        f"TOTAL DEL PERÍODO: ${datos['total']:,.2f}",
        fill="black",
        font=fuente,
    )
    salida = BytesIO()
    imagen.save(salida, format="PNG")
    salida.seek(0)
    return salida
