import sqlite3
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.connection import obtener_conexion
from utils.seguridad import login_requerido, registrar_auditoria, modo_activo
from utils.formateadores import obtener_meses_disponibles

logger = logging.getLogger("SG_Gomeria")

clientes_bp = Blueprint("clientes_bp", __name__)


# Pantall Clientes y Dashboard General
@clientes_bp.route("/clientes")
@login_requerido
def clientes():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    buscar = request.args.get("buscar", "").strip()
    periodo_seleccionado = request.args.get("periodo", "todos")

    if buscar:
        empresas = cursor.execute(
            """
            SELECT id_cliente, nom_cli, cuit, tel, mail
            FROM clientes
            WHERE nom_cli LIKE ? OR cuit LIKE ? OR tel LIKE ?
            ORDER BY nom_cli
        """,
            (f"%{buscar}%", f"%{buscar}%", f"%{buscar}%"),
        ).fetchall()
    else:
        empresas = cursor.execute("""
            SELECT id_cliente, nom_cli, cuit, tel, mail
            FROM clientes
            ORDER BY nom_cli
        """).fetchall()

    # Armamos la consulta de remitos, sumando el filtro de mes si corresponde
    query_remitos = """
        SELECT t.id_trabajo, t.remito, t.tipo, t.fecha, c.nom_cli, t.total, t.detalle
        FROM trabajos t
        JOIN clientes c ON t.id_cliente = c.id_cliente
    """
    parametros_remitos = []

    if periodo_seleccionado and periodo_seleccionado != "todos":
        query_remitos += " WHERE strftime('%Y-%m', t.fecha) = ?"
        parametros_remitos.append(periodo_seleccionado)

    query_remitos += " ORDER BY t.fecha DESC, t.id_trabajo DESC"

    remitos = cursor.execute(query_remitos, parametros_remitos).fetchall()

    meses_disponibles = obtener_meses_disponibles(
        cursor
    )  # sin id_cliente = todos los clientes

    detalles_raw = cursor.execute("""
        SELECT dt.id_trabajo, tar.nom_tar, dt.cantidad, dt.subtotal
        FROM detalle_trabajos dt
        JOIN tareas tar ON dt.id_tarea = tar.id_tarea
        ORDER BY dt.id_trabajo
    """).fetchall()

    detalles_por_trabajo = {}
    for d in detalles_raw:
        detalles_por_trabajo.setdefault(d["id_trabajo"], []).append(d)

    conexion.close()
    return render_template(
        "clientes.html",
        empresas=empresas,
        remitos=remitos,
        buscar=buscar,
        periodo_seleccionado=periodo_seleccionado,
        meses_disponibles=meses_disponibles,
        detalles_por_trabajo=detalles_por_trabajo,
        milagritos=modo_activo(),
    )


# Pantalla Historial-Clientes
@clientes_bp.route("/historial-cliente")
@login_requerido
def historial_cliente():
    id_cliente = request.args.get("id_cliente")
    periodo_seleccionado = request.args.get("periodo", "todos")

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cliente = cursor.execute(
        "SELECT id_cliente, nom_cli, cuit FROM clientes WHERE id_cliente = ?",
        (id_cliente,),
    ).fetchone()
    # 1. Armamos la consulta base y la lista de parámetros
    query = """
        SELECT t.id_trabajo, t.remito, t.tipo, t.fecha, c.nom_cli, t.total, t.detalle,
               GROUP_CONCAT(tar.nom_tar, ', ') AS detalle_tareas
        FROM trabajos t
        LEFT JOIN detalle_trabajos dt ON t.id_trabajo = dt.id_trabajo
        LEFT JOIN tareas tar ON dt.id_tarea = tar.id_tarea
        LEFT JOIN clientes c ON t.id_cliente = c.id_cliente
        WHERE t.id_cliente = ?
    """
    parametros = [id_cliente]

    # Buscamos qué meses/años tienen trabajos para crear las pestañas
    meses_disponibles = obtener_meses_disponibles(cursor, id_cliente)

    # 2. Si eligió un mes específico (y no "todos"), le sumamos la condición:
    if periodo_seleccionado and periodo_seleccionado != "todos":
        query += " AND strftime('%Y-%m', t.fecha) = ?"
        parametros.append(periodo_seleccionado)

    # 3. Le agregamos el cierre obligatorio (agrupar y ordenar por fecha)
    query += " GROUP BY t.id_trabajo ORDER BY t.fecha DESC"

    # 4. Ejecutamos la consulta con sus parámetros
    remitos = cursor.execute(query, parametros).fetchall()

    # 5. Obtenemos el total y el total por mes
    total_mes = sum(r["total"] for r in remitos)

    # NUEVO: traemos el detalle solo de los trabajos que aparecen en `remitos`
    ids_trabajo = [r["id_trabajo"] for r in remitos]
    detalles_por_trabajo = {}

    if ids_trabajo:
        # Generamos "?, ?, ?" según cuántos ids haya, para el IN de SQL
        placeholders = ",".join("?" for _ in ids_trabajo)
        detalles_raw = cursor.execute(
            f"""
            SELECT dt.id_trabajo, tar.nom_tar, dt.cantidad, dt.subtotal
            FROM detalle_trabajos dt
            JOIN tareas tar ON dt.id_tarea = tar.id_tarea
            WHERE dt.id_trabajo IN ({placeholders})
            ORDER BY dt.id_trabajo
        """,
            ids_trabajo,
        ).fetchall()

        for d in detalles_raw:
            detalles_por_trabajo.setdefault(d["id_trabajo"], []).append(d)

    cursor.close()
    return render_template(
        "historial-cliente.html",
        cliente=cliente,
        remitos=remitos,
        total_mes=total_mes,
        meses_disponibles=meses_disponibles,
        detalles_por_trabajo=detalles_por_trabajo,
        periodo_seleccionado=periodo_seleccionado,
    )


# Funcion para agregar clientes
@clientes_bp.route("/agregar-cliente", methods=["POST"])
@login_requerido
def agregar_cliente():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    nom_cli = request.form.get("nombre", "").strip()
    cuit = request.form.get("cuit", "").strip()
    tel = request.form.get("tel", "").strip()
    mail = request.form.get("mail", "").strip()

    if not nom_cli:
        flash("El nombre o razón social del cliente es obligatorio", "danger")
        return redirect(url_for("clientes_bp.clientes"))

    try:
        cursor.execute(
            """
            INSERT INTO clientes (nom_cli, cuit, tel, mail)
            VALUES (?, ?, ?, ?)
        """,
            (nom_cli, cuit, tel, mail),
        )
        conexion.commit()
        registrar_auditoria(
            "ALTA_CLIENTE", f"Empresa '{nom_cli}' (CUIT: {cuit}) agregada"
        )
        flash(f"Cliente '{nom_cli}' registrado correctamente.", "success")
    except sqlite3.IntegrityError:
        logger.warning(
            f"AUDITORIA | Intento de registrar cliente duplicado: '{nom_cli}' (CUIT: {cuit})"
        )
        flash("Error: Ya existe un cliente con ese CUIT o razón social.", "danger")
    except Exception as e:
        logger.exception(f"Error inesperado al agregar cliente: {e}")
        flash("Ocurrió un error inesperado al registrar el cliente.", "danger")
    finally:
        conexion.close()

    return redirect(url_for("clientes_bp.clientes"))
