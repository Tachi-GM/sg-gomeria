import logging
from flask import Blueprint, request, jsonify, current_app
from utils.seguridad import login_requerido
from database.connection import obtener_conexion

logger = logging.getLogger("SG_Gomeria")

# Blueprint para la API de clientes (rutas ligeras JSON)
clientes_api_bp = Blueprint('clientes_api_bp', __name__, url_prefix='/clientes')

@clientes_api_bp.route('/validar-cuit', methods=['POST'])
@login_requerido
def validar_cuit():
    """Endpoint para validar en tiempo real si un CUIT ya está registrado.

    Recibe JSON con los campos:
        - cuit: string (obligatorio)
        - id_cliente: entero (opcional, se usa al editar para excluir el propio registro)

    Responde JSON:
        - exists: bool
        - message: string (solo cuando exists=True)
    """
    data = request.get_json(silent=True) or {}
    cuit = data.get('cuit', '').strip()
    id_cliente = data.get('id_cliente')

    if not cuit:
        # Si el campo está vacío, consideramos que no hay colisión
        return jsonify({"exists": False})

    # Opcionalmente podríamos validar el formato del CUIT usando la función existente
    # if not validar_y_formatear_cuit(cuit):
    #     return jsonify({"exists": True, "message": "Formato de CUIT no válido"}), 400

    db = obtener_conexion()
    cur = db.cursor()
    if id_cliente:
        cur.execute(
            "SELECT id_cliente FROM clientes WHERE cuit = ? AND id_cliente != ?",
            (cuit, id_cliente),
        )
    else:
        cur.execute(
            "SELECT id_cliente FROM clientes WHERE cuit = ?",
            (cuit,),
        )
    row = cur.fetchone()
    db.close()

    if row:
        return jsonify({"exists": True, "message": "CUIT ya pertenece a otra empresa"})
    else:
        return jsonify({"exists": False})
