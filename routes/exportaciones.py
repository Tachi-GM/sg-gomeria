"""Rutas protegidas para exportaciones de clientes."""

from datetime import datetime

from flask import Blueprint, current_app, request, send_file
from werkzeug.utils import secure_filename

from services.exportaciones_service import (
    obtener_datos_exportacion,
    obtener_datos_exportacion_general,
    validar_periodo,
)
from utils.exportadores import MESES, generar_excel_general, generar_imagen
from utils.seguridad import login_requerido, registrar_auditoria

exportaciones_bp = Blueprint("exportaciones_bp", __name__)


def _obtener_datos(id_cliente):
    periodo = request.args.get("periodo", "").strip()
    if not validar_periodo(periodo):
        return None, ("El período debe tener formato AAAA-MM.", 400)
    try:
        datos = obtener_datos_exportacion(
            id_cliente,
            periodo,
            current_app.config.get("UPLOAD_DIR", "uploads"),
        )
    except ValueError as error:
        return None, (str(error), 404)
    if not datos["remitos"]:
        return None, ("No hay remitos para el período indicado.", 404)
    return datos, None


@exportaciones_bp.route("/exportar-cliente/<int:id_cliente>/excel")
@login_requerido
def exportar_excel(id_cliente):
    try:
        datos = obtener_datos_exportacion_general(
            id_cliente,
            current_app.config.get("UPLOAD_DIR", "uploads"),
        )
    except ValueError as error:
        return str(error), 404
    if not datos["meses"]:
        return "No hay remitos registrados para este cliente.", 404

    archivo = generar_excel_general(datos)
    cliente = secure_filename(datos["cliente"]["nom_cli"]) or "cliente"
    fecha_descarga = datetime.now()
    mes_descarga = MESES[fecha_descarga.strftime("%m")].lower()
    nombre = f"remitos_{cliente}_{mes_descarga}_{fecha_descarga.year}.xlsx"
    registrar_auditoria(
        "EXPORTACION_EXCEL",
        f"Cliente ID {id_cliente}, exportación general",
    )
    return send_file(
        archivo,
        as_attachment=True,
        download_name=nombre,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@exportaciones_bp.route("/exportar-cliente/<int:id_cliente>/imagen")
@login_requerido
def exportar_imagen(id_cliente):
    datos, error = _obtener_datos(id_cliente)
    if error:
        return error
    archivo = generar_imagen(datos)
    cliente = secure_filename(datos["cliente"]["nom_cli"]) or "cliente"
    nombre = f"remitos_{cliente}_{datos['periodo']}.png"
    registrar_auditoria(
        "EXPORTACION_IMAGEN",
        f"Cliente ID {id_cliente}, período {datos['periodo']}",
    )
    return send_file(
        archivo, as_attachment=True, download_name=nombre, mimetype="image/png"
    )
