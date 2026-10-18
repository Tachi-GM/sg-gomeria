from flask import Blueprint, render_template, request, jsonify
from database.connection import obtener_conexion
from utils.seguridad import login_requerido, registrar_auditoria, modo_activo
from utils.formateadores import parse_float_seguro

cheques_bp = Blueprint("cheques_bp", __name__)


@cheques_bp.route("/cheques")
@login_requerido
def cheques():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    filas = cursor.execute("""
        SELECT id_cheque, numero, cliente, banco, fecha_emision, fecha_pago, importe, estado, endosado
        FROM cheques
        ORDER BY fecha_pago ASC, id_cheque DESC
    """).fetchall()

    lista_cheques = [dict(f) for f in filas]

    # También obtenemos la lista de clientes para facilitar sugerencias de endosado si se quiere
    clientes = cursor.execute(
        "SELECT nom_cli FROM clientes ORDER BY nom_cli ASC"
    ).fetchall()
    conexion.close()
    return render_template(
        "cheques.html",
        cheques=lista_cheques,
        clientes=clientes,
        milagritos=modo_activo(),
    )


@cheques_bp.route("/agregar-cheque", methods=["POST"])
@login_requerido
def agregar_cheque():
    numero = request.form.get("numero", "").strip()
    cliente = request.form.get("cliente", "").strip()
    banco = request.form.get("banco", "").strip()
    fecha_emision = request.form.get("fecha_emision", "")
    fecha_pago = request.form.get("fecha_pago", "")
    importe = parse_float_seguro(request.form.get("importe"), 0.0)
    estado = request.form.get("estado", "Pendiente")
    endosado = request.form.get("endosado", "").strip()

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # Vincular id_cliente obligatorio (si el cliente no existe, se registra)
    cliente_fila = cursor.execute(
        "SELECT id_cliente FROM clientes WHERE nom_cli = ?", (cliente,)
    ).fetchone()

    if cliente_fila:
        id_cliente = cliente_fila["id_cliente"]
    else:
        cursor.execute("INSERT INTO clientes (nom_cli) VALUES (?)", (cliente,))
        id_cliente = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO cheques (
            numero, cliente, banco, fecha_emision, fecha_pago, importe, estado, endosado, id_cliente
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            numero,
            cliente,
            banco,
            fecha_emision,
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
        f"Cheque N° {numero} ({banco}) por ${importe:,.2f} para '{cliente}'",
    )

    return jsonify(
        {
            "id_cheque": id_nuevo,
            "numero": numero,
            "cliente": cliente,
            "banco": banco,
            "fecha_emision": fecha_emision,
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
