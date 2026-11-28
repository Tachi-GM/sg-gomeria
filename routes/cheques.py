import logging
from flask import Blueprint, current_app, flash, redirect, render_template, request, jsonify, url_for
from database.connection import obtener_conexion, get_db_path
from services.archivos_excel import ErrorArchivoExcel
from services.cheques_importacion_service import importar_cheques_desde_archivo
from utils.seguridad import login_requerido, registrar_auditoria, modo_activo
from utils.formateadores import parse_int_seguro, parse_importe_ar

cheques_bp = Blueprint("cheques_bp", __name__)


@cheques_bp.route("/cheques")
@login_requerido
def cheques():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    filas = cursor.execute("""
        SELECT ch.id_cheque, ch.numero, ch.banco, ch.fecha_pago,
               ch.importe, ch.estado, ch.endosado, ch.id_cliente,
               COALESCE(c.nom_cli, ch.cliente) AS cliente,
               c.cuit AS cliente_cuit
        FROM cheques ch
        LEFT JOIN clientes c ON ch.id_cliente = c.id_cliente
        ORDER BY ch.fecha_pago ASC, ch.id_cheque DESC
    """).fetchall()

    lista_cheques = [dict(f) for f in filas]

    # Lista de clientes activos para el combobox Choices.js
    clientes = cursor.execute(
        """SELECT id_cliente, nom_cli, cuit
           FROM clientes
           WHERE COALESCE(activo, 1) = 1
           ORDER BY nom_cli ASC"""
    ).fetchall()

    # Sugerencias de endosados existentes en el sistema
    endosados_filas = cursor.execute(
        """SELECT DISTINCT endosado
           FROM cheques
           WHERE endosado IS NOT NULL AND TRIM(endosado) != ''
           ORDER BY endosado ASC"""
    ).fetchall()
    endosados = [f["endosado"] for f in endosados_filas]

    conexion.close()
    return render_template(
        "cheques.html",
        cheques=lista_cheques,
        clientes=clientes,
        endosados=endosados,
        milagritos=modo_activo(),
    )


@cheques_bp.route("/agregar-cheque", methods=["POST"])
@login_requerido
def agregar_cheque():
    numero = request.form.get("numero", "").strip()
    id_cliente_raw = request.form.get("id_cliente")
    cliente_texto = request.form.get("cliente", "").strip()
    banco = request.form.get("banco", "").strip()
    fecha_pago = request.form.get("fecha_pago", "")
    # El importe viene como lo escribe el usuario: "125.000,50" (puntos de miles, coma decimal).
    importe = parse_importe_ar(request.form.get("importe"), 0.0)
    estado = request.form.get("estado", "Pendiente")
    endosado = request.form.get("endosado", "").strip()

    if not numero or not banco or importe <= 0:
        return jsonify({"exito": False, "mensaje": "Datos obligatorios incompletos o importe inválido"}), 400

    id_cliente = parse_int_seguro(id_cliente_raw) if id_cliente_raw else None

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cliente_nom = cliente_texto
    if id_cliente:
        cliente_fila = cursor.execute(
            "SELECT id_cliente, nom_cli FROM clientes WHERE id_cliente = ?",
            (id_cliente,),
        ).fetchone()
        if cliente_fila:
            cliente_nom = cliente_fila["nom_cli"]
        else:
            id_cliente = None

    # Fallback si se envió texto directo en lugar de id_cliente
    if not id_cliente and cliente_texto:
        cliente_fila = cursor.execute(
            "SELECT id_cliente, nom_cli FROM clientes WHERE nom_cli = ?",
            (cliente_texto,),
        ).fetchone()
        if cliente_fila:
            id_cliente = cliente_fila["id_cliente"]
            cliente_nom = cliente_fila["nom_cli"]
        else:
            cursor.execute("INSERT INTO clientes (nom_cli) VALUES (?)", (cliente_texto,))
            id_cliente = cursor.lastrowid
            cliente_nom = cliente_texto

    if not id_cliente:
        conexion.close()
        return jsonify({"exito": False, "mensaje": "Debes seleccionar o ingresar un cliente válido"}), 400

    cursor.execute(
        """
        INSERT INTO cheques (
            numero, cliente, banco, fecha_pago, importe, estado, endosado, id_cliente
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            numero,
            cliente_nom,
            banco,
            fecha_pago,
            importe,
            estado,
            endosado,
            id_cliente,
        ),
    )
    conexion.commit()
    id_nuevo = cursor.lastrowid
    conexion.close()

    registrar_auditoria(
        "ALTA_CHEQUE",
        f"Cheque N° {numero} ({banco}) por ${importe:,.2f} para '{cliente_nom}'",
    )

    return jsonify(
        {
            "id_cheque": id_nuevo,
            "numero": numero,
            "cliente": cliente_nom,
            "banco": banco,
            "fecha_pago": fecha_pago,
            "importe": importe,
            "estado": estado,
            "endosado": endosado,
            "id_cliente": id_cliente,
        }
    )


@cheques_bp.route("/actualizar-estado-cheque", methods=["POST"])
@login_requerido
def actualizar_estado_cheque():
    id_cheque = request.form.get("id_cheque")
    nuevo_estado = request.form.get("estado")
    estados_validos = ["Pendiente", "Cobrado", "Rechazado"]
    if nuevo_estado not in estados_validos:
        return "Estado inválido", 400

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE cheques SET estado = ? WHERE id_cheque = ?", (nuevo_estado, id_cheque)
    )
    conexion.commit()
    conexion.close()

    registrar_auditoria(
        "ESTADO_CHEQUE", f"Cheque ID {id_cheque} actualizado a estado '{nuevo_estado}'"
    )
    return "OK", 200


@cheques_bp.route("/eliminar-cheque", methods=["POST"])
@login_requerido
def eliminar_cheque():
    id_cheque = request.form.get("id_cheque")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM cheques WHERE id_cheque = ?", (id_cheque,))
    conexion.commit()
    conexion.close()

    registrar_auditoria("BAJA_CHEQUE", f"Cheque ID {id_cheque} eliminado")
    return "OK", 200


@cheques_bp.route("/cheques/importar", methods=["POST"])
@login_requerido
def importar_cheques():
    """Importa los cheques de un Excel y muestra el informe de lo que se hizo."""
    try:
        informe = importar_cheques_desde_archivo(
            request.files.get("archivo"),
            get_db_path(),
            current_app.config.get("BACKUP_DIR", "backups"),
        )
    except ErrorArchivoExcel as error:
        flash(str(error), "danger")
        return redirect(url_for("cheques_bp.cheques"))
    except Exception:
        logging.getLogger("SG_Gomeria").exception("Error inesperado al importar cheques")
        flash("Ocurrió un error inesperado al importar los cheques. No se guardó nada.", "danger")
        return redirect(url_for("cheques_bp.cheques"))

    resumen = informe["resumen"]
    registrar_auditoria(
        "IMPORTACION_CHEQUES",
        f"{resumen['importados']} cheques importados, {resumen['clientes_creados']} clientes creados, "
        f"{resumen['ya_existian'] + resumen['duplicados_en_excel']} repetidos omitidos, "
        f"backup: {informe['backup'].name if informe['backup'] else 'no hizo falta'}",
    )
    return render_template("cheques_importacion.html", informe=informe, milagritos=modo_activo())
