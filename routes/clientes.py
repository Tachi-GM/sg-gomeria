import sqlite3
import logging
from datetime import datetime
from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from database.connection import obtener_conexion
from services.clientes_service import ErrorClientes, unificar_clientes
from utils.seguridad import login_requerido, solo_admin, registrar_auditoria, modo_activo
from utils.formateadores import (
    obtener_meses_disponibles,
    validar_y_formatear_cuit,
    parse_int_seguro,
)

logger = logging.getLogger("SG_Gomeria")

clientes_bp = Blueprint("clientes_bp", __name__)


# Cantidad de remitos que se muestran inicialmente y por cada carga adicional.
REMITOS_POR_PAGINA = 10


def _rango_fechas_periodo(periodo):
    """Convierte YYYY-MM en un rango [inicio, fin) aprovechable por índices."""
    if not periodo or periodo == "todos":
        return None

    try:
        fecha = datetime.strptime(periodo, "%Y-%m")
    except ValueError:
        return None

    if fecha.month == 12:
        siguiente = fecha.replace(year=fecha.year + 1, month=1)
    else:
        siguiente = fecha.replace(month=fecha.month + 1)

    return fecha.strftime("%Y-%m-01"), siguiente.strftime("%Y-%m-01")


def _obtener_remitos(
    cursor,
    id_cliente=None,
    periodo="todos",
    limite=REMITOS_POR_PAGINA,
    offset=0,
):
    """Obtiene una página de cabeceras; trae un registro extra para saber si hay más."""
    condiciones = []
    parametros = []

    if id_cliente is not None:
        condiciones.append("t.id_cliente = ?")
        parametros.append(id_cliente)

    rango = _rango_fechas_periodo(periodo)
    if periodo and periodo != "todos":
        if not rango:
            return [], False
        condiciones.append("t.fecha >= ? AND t.fecha < ?")
        parametros.extend(rango)

    where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    query = f"""
        SELECT t.id_trabajo, t.remito, t.tipo, t.fecha,
               COALESCE(NULLIF(t.cliente_alias, ''), c.nom_cli) AS nom_cli,
               t.total, t.detalle, t.estado, t.foto_remito
        FROM trabajos t
        JOIN clientes c ON t.id_cliente = c.id_cliente
        {where_clause}
        ORDER BY t.fecha DESC, t.id_trabajo DESC
        LIMIT ? OFFSET ?
    """
    parametros.extend([limite + 1, offset])
    filas = cursor.execute(query, parametros).fetchall()
    hay_mas = len(filas) > limite
    return filas[:limite], hay_mas


def _obtener_detalles(cursor, remitos):
    """Consulta los detalles solo para los remitos de la página actual."""
    ids_trabajo = [r["id_trabajo"] for r in remitos]
    if not ids_trabajo:
        return {}

    placeholders = ",".join("?" for _ in ids_trabajo)
    query = f"""
        SELECT id_trabajo, nom_tar, cantidad, subtotal
        FROM (
            SELECT dt.id_trabajo, tar.nom_tar AS nom_tar, dt.cantidad, dt.subtotal
            FROM detalle_trabajos dt
            JOIN tareas tar ON dt.id_tarea = tar.id_tarea
            WHERE dt.id_trabajo IN ({placeholders})

            UNION ALL

            SELECT dtt.id_trabajo, dtt.nombre_tarea AS nom_tar,
                   dtt.cantidad, dtt.subtotal
            FROM detalle_temporal_trabajos dtt
            WHERE dtt.id_trabajo IN ({placeholders})
        )
        ORDER BY id_trabajo
    """
    detalles = cursor.execute(query, ids_trabajo + ids_trabajo).fetchall()

    detalles_por_trabajo = {}
    for detalle in detalles:
        detalles_por_trabajo.setdefault(detalle["id_trabajo"], []).append(detalle)
    return detalles_por_trabajo


def _obtener_resumen_remitos(cursor, id_cliente=None, periodo="todos"):
    """Devuelve cantidad e importe globales, sin depender de la página visible."""
    condiciones = []
    parametros = []

    if id_cliente is not None:
        condiciones.append("id_cliente = ?")
        parametros.append(id_cliente)

    rango = _rango_fechas_periodo(periodo)
    if periodo and periodo != "todos":
        if not rango:
            return 0, 0
        condiciones.append("fecha >= ? AND fecha < ?")
        parametros.extend(rango)

    where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    resumen = cursor.execute(
        f"""
        SELECT COUNT(*) AS cantidad, COALESCE(SUM(total), 0) AS total
        FROM trabajos
        {where_clause}
        """,
        parametros,
    ).fetchone()
    return resumen["cantidad"], resumen["total"]


# Pantalla Clientes y Dashboard General
@clientes_bp.route("/clientes")
@login_requerido
def clientes():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    buscar = request.args.get("buscar", "").strip()
    periodo_seleccionado = request.args.get("periodo", "todos")
    filtro_estado = request.args.get("estado", "activos").strip().lower()

    condiciones = []
    parametros_empresas = []

    if filtro_estado == "activos":
        condiciones.append("COALESCE(clientes.activo, 1) = 1")
    elif filtro_estado == "inactivos":
        condiciones.append("COALESCE(clientes.activo, 1) = 0")

    if buscar:
        condiciones.append("(nom_cli LIKE ? OR cuit LIKE ? OR tel LIKE ?)")
        busqueda_param = f"%{buscar}%"
        parametros_empresas.extend([busqueda_param, busqueda_param, busqueda_param])

    where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    # Una sola agregación evita ejecutar dos subconsultas por cada cliente.
    query_empresas = f"""
        SELECT clientes.id_cliente, clientes.nom_cli, clientes.cuit,
               clientes.tel, clientes.mail, clientes.con_iva,
               clientes.lista_precios, COALESCE(clientes.activo, 1) AS activo,
               COALESCE(resumen.cantidad_remitos, 0) AS cantidad_remitos,
               COALESCE(resumen.total_facturado, 0) AS total_facturado
        FROM clientes
        LEFT JOIN (
            SELECT id_cliente, COUNT(*) AS cantidad_remitos,
                   SUM(total) AS total_facturado
            FROM trabajos
            GROUP BY id_cliente
        ) resumen ON resumen.id_cliente = clientes.id_cliente
        {where_clause}
        ORDER BY cantidad_remitos DESC, clientes.nom_cli COLLATE NOCASE
    """
    # En la vista normal se muestran los seis clientes con más remitos.
    # La búsqueda conserva todos los resultados coincidentes para no ocultar empresas.
    if not buscar:
        query_empresas += " LIMIT 6"
    empresas = cursor.execute(query_empresas, parametros_empresas).fetchall()

    conteo_activos = cursor.execute(
        "SELECT COUNT(*) FROM clientes WHERE COALESCE(activo, 1) = 1"
    ).fetchone()[0]
    conteo_inactivos = cursor.execute(
        "SELECT COUNT(*) FROM clientes WHERE COALESCE(activo, 1) = 0"
    ).fetchone()[0]

    remitos, hay_mas_remitos = _obtener_remitos(
        cursor, periodo=periodo_seleccionado
    )
    total_remitos, _ = _obtener_resumen_remitos(
        cursor, periodo=periodo_seleccionado
    )
    meses_disponibles = obtener_meses_disponibles(cursor)
    detalles_por_trabajo = _obtener_detalles(cursor, remitos)

    # Solo los administradores ven el botón "Unificar": hace falta la lista completa de clientes.
    todos_clientes = []
    if session.get("rol") == "admin":
        todos_clientes = cursor.execute(
            """SELECT id_cliente, nom_cli, cuit, COALESCE(activo, 1) AS activo
               FROM clientes ORDER BY nom_cli COLLATE NOCASE"""
        ).fetchall()

    cursor.close()
    conexion.close()
    return render_template(
        "clientes.html",
        todos_clientes=todos_clientes,
        empresas=empresas,
        remitos=remitos,
        buscar=buscar,
        periodo_seleccionado=periodo_seleccionado,
        filtro_estado=filtro_estado,
        conteo_activos=conteo_activos,
        conteo_inactivos=conteo_inactivos,
        meses_disponibles=meses_disponibles,
        detalles_por_trabajo=detalles_por_trabajo,
        total_remitos=total_remitos,
        hay_mas_remitos=hay_mas_remitos,
        milagritos=modo_activo(),
    )


# Pantalla Historial-Clientes
@clientes_bp.route("/historial-cliente")
@login_requerido
def historial_cliente():
    id_cliente = parse_int_seguro(request.args.get("id_cliente"), 0)
    periodo_seleccionado = request.args.get("periodo", "todos")

    if id_cliente <= 0:
        flash("Seleccioná una empresa válida para ver su historial.", "warning")
        return redirect(url_for("clientes_bp.clientes"))

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cliente = cursor.execute(
        """SELECT id_cliente, nom_cli, cuit, tel, mail, con_iva, lista_precios,
                  COALESCE(activo, 1) AS activo
           FROM clientes WHERE id_cliente = ?""",
        (id_cliente,),
    ).fetchone()

    if not cliente:
        cursor.close()
        conexion.close()
        flash("El cliente solicitado no existe.", "danger")
        return redirect(url_for("clientes_bp.clientes"))

    meses_disponibles = obtener_meses_disponibles(cursor, id_cliente)
    remitos, hay_mas_remitos = _obtener_remitos(
        cursor, id_cliente=id_cliente, periodo=periodo_seleccionado
    )
    cantidad_remitos, total_mes = _obtener_resumen_remitos(
        cursor, id_cliente=id_cliente, periodo=periodo_seleccionado
    )
    detalles_por_trabajo = _obtener_detalles(cursor, remitos)

    cursor.close()
    conexion.close()
    return render_template(
        "historial-cliente.html",
        cliente=cliente,
        remitos=remitos,
        total_mes=total_mes,
        cantidad_remitos=cantidad_remitos,
        meses_disponibles=meses_disponibles,
        detalles_por_trabajo=detalles_por_trabajo,
        periodo_seleccionado=periodo_seleccionado,
        hay_mas_remitos=hay_mas_remitos,
    )


@clientes_bp.route("/clientes/remitos-pagina")
@login_requerido
def cargar_mas_remitos():
    """Devuelve como HTML seguro la siguiente página de remitos."""
    id_cliente_raw = request.args.get("id_cliente")
    id_cliente = None
    if id_cliente_raw:
        id_cliente = parse_int_seguro(id_cliente_raw, 0)
        if id_cliente <= 0:
            return jsonify({"error": "El cliente indicado no es válido."}), 400

    offset = parse_int_seguro(request.args.get("offset", "0"), -1)
    if offset < 0 or offset > 100000:
        return jsonify({"error": "La página solicitada no es válida."}), 400

    periodo = request.args.get("periodo", "todos")
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    if id_cliente is not None:
        existe = cursor.execute(
            "SELECT 1 FROM clientes WHERE id_cliente = ?", (id_cliente,)
        ).fetchone()
        if not existe:
            cursor.close()
            conexion.close()
            return jsonify({"error": "El cliente solicitado no existe."}), 404

    remitos, hay_mas = _obtener_remitos(
        cursor, id_cliente=id_cliente, periodo=periodo, offset=offset
    )
    detalles_por_trabajo = _obtener_detalles(cursor, remitos)

    html = render_template(
        "componentes/filas_remitos.html",
        remitos=remitos,
        detalles_por_trabajo=detalles_por_trabajo,
    )
    cursor.close()
    conexion.close()
    return jsonify(
        {
            "html": html,
            "hay_mas": hay_mas,
            "cantidad_cargada": len(remitos),
        }
    )


# Función para agregar clientes
@clientes_bp.route("/agregar-cliente", methods=["POST"])
@login_requerido
def agregar_cliente():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    nom_cli = request.form.get("nombre", "").strip()
    cuit_raw = request.form.get("cuit", "").strip()
    tel = request.form.get("tel", "").strip()
    mail = request.form.get("mail", "").strip()
    con_iva = 1 if request.form.get("con_iva", "1") == "1" else 0
    lista_precios = parse_int_seguro(request.form.get("lista_precios", 1), 1)
    if lista_precios not in (1, 2, 3):
        lista_precios = 1

    if not nom_cli:
        flash("El nombre o razón social del cliente es obligatorio.", "danger")
        return redirect(url_for("clientes_bp.clientes"))

    cuit_final = None
    if cuit_raw:
        cuit_valido, cuit_resultado = validar_y_formatear_cuit(cuit_raw)
        if not cuit_valido:
            flash(f"Error en CUIT: {cuit_resultado}", "danger")
            return redirect(url_for("clientes_bp.clientes"))
        cuit_final = cuit_resultado

    try:
        cursor.execute(
            """
            INSERT INTO clientes (nom_cli, cuit, tel, mail, con_iva, lista_precios, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
            (nom_cli, cuit_final, tel, mail, con_iva, lista_precios),
        )
        conexion.commit()
        registrar_auditoria(
            "ALTA_CLIENTE", f"Empresa '{nom_cli}' (CUIT: {cuit_final}) agregada"
        )
        flash(f"Cliente '{nom_cli}' registrado correctamente.", "success")
    except sqlite3.IntegrityError:
        logger.warning(
            f"AUDITORIA | Intento de registrar cliente duplicado: '{nom_cli}' (CUIT: {cuit_final})"
        )
        flash("Error: Ya existe un cliente con ese CUIT o razón social.", "danger")
    except Exception as e:
        logger.exception(f"Error inesperado al agregar cliente: {e}")
        flash("Ocurrió un error inesperado al registrar el cliente.", "danger")
    finally:
        conexion.close()

    return redirect(url_for("clientes_bp.clientes"))


# Función para editar clientes existentes
@clientes_bp.route("/editar-cliente/<int:id_cliente>", methods=["POST"])
@login_requerido
def editar_cliente(id_cliente):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cliente_existente = cursor.execute(
        "SELECT id_cliente, nom_cli, cuit FROM clientes WHERE id_cliente = ?",
        (id_cliente,),
    ).fetchone()

    if not cliente_existente:
        conexion.close()
        flash("El cliente que intentás editar no existe.", "danger")
        return redirect(url_for("clientes_bp.clientes"))

    nom_cli = request.form.get("nombre", "").strip()
    cuit_raw = request.form.get("cuit", "").strip()
    tel = request.form.get("tel", "").strip()
    mail = request.form.get("mail", "").strip()
    con_iva = 1 if request.form.get("con_iva", "1") == "1" else 0
    lista_precios = parse_int_seguro(request.form.get("lista_precios", 1), 1)
    if lista_precios not in (1, 2, 3):
        lista_precios = 1

    if not nom_cli:
        conexion.close()
        flash("El nombre o razón social no puede estar vacío.", "danger")
        return redirect(url_for("clientes_bp.clientes"))

    cuit_final = None
    if cuit_raw:
        cuit_valido, cuit_resultado = validar_y_formatear_cuit(cuit_raw)
        if not cuit_valido:
            conexion.close()
            flash(f"Error en CUIT: {cuit_resultado}", "danger")
            return redirect(url_for("clientes_bp.clientes"))
        cuit_final = cuit_resultado

        # Verificar unicidad de CUIT excluyendo al cliente actual
        duplicado = cursor.execute(
            "SELECT id_cliente, nom_cli FROM clientes WHERE cuit = ? AND id_cliente != ?",
            (cuit_final, id_cliente),
        ).fetchone()
        if duplicado:
            conexion.close()
            flash(
                f"El CUIT '{cuit_final}' ya pertenece a la empresa '{duplicado['nom_cli']}'.",
                "danger",
            )
            return redirect(url_for("clientes_bp.clientes"))

    try:
        cursor.execute(
            """
            UPDATE clientes
            SET nom_cli = ?, cuit = ?, tel = ?, mail = ?, con_iva = ?, lista_precios = ?
            WHERE id_cliente = ?
        """,
            (nom_cli, cuit_final, tel, mail, con_iva, lista_precios, id_cliente),
        )
        conexion.commit()
        registrar_auditoria(
            "MODIFICACION_CLIENTE",
            f"Cliente ID {id_cliente} actualizado a '{nom_cli}' (CUIT: {cuit_final}, L{lista_precios}, IVA:{con_iva})",
        )
        flash(f"Cliente '{nom_cli}' actualizado con éxito.", "success")
    except sqlite3.IntegrityError:
        flash(
            "Error de integridad: Ya existe un cliente con ese CUIT o nombre.", "danger"
        )
    except Exception as e:
        logger.exception(f"Error al editar cliente ID {id_cliente}: {e}")
        flash("Ocurrió un error inesperado al actualizar el cliente.", "danger")
    finally:
        conexion.close()

    return redirect(url_for("clientes_bp.clientes"))


# Función para conmutar estado Activo / Inactivo (Ocultar / Reactivar)
@clientes_bp.route("/alternar-cliente/<int:id_cliente>", methods=["POST"])
@login_requerido
def alternar_cliente(id_cliente):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cliente = cursor.execute(
        "SELECT id_cliente, nom_cli, COALESCE(activo, 1) AS activo FROM clientes WHERE id_cliente = ?",
        (id_cliente,),
    ).fetchone()

    if not cliente:
        conexion.close()
        flash("El cliente seleccionado no existe.", "danger")
        return redirect(url_for("clientes_bp.clientes"))

    nuevo_estado = 0 if cliente["activo"] == 1 else 1
    accion_texto = (
        "desactivado y ocultado del mostrador"
        if nuevo_estado == 0
        else "reactivado exitosamente"
    )

    try:
        cursor.execute(
            "UPDATE clientes SET activo = ? WHERE id_cliente = ?",
            (nuevo_estado, id_cliente),
        )
        conexion.commit()
        registrar_auditoria(
            "ESTADO_CLIENTE",
            f"Cliente ID {id_cliente} ('{cliente['nom_cli']}') marcado como activo={nuevo_estado}",
        )
        flash(f"Cliente '{cliente['nom_cli']}' {accion_texto}.", "success")
    except Exception as e:
        logger.exception(f"Error al cambiar estado de cliente ID {id_cliente}: {e}")
        flash("Ocurrió un error al cambiar el estado del cliente.", "danger")
    finally:
        conexion.close()

    return redirect(url_for("clientes_bp.clientes"))

@clientes_bp.route("/clientes/unificar", methods=["POST"])
@login_requerido
@solo_admin
def unificar_cliente():
    """Unifica un cliente duplicado dentro del principal (solo administradores)."""
    id_duplicado = parse_int_seguro(request.form.get("id_duplicado"))
    id_principal = parse_int_seguro(request.form.get("id_principal"))
    try:
        resultado = unificar_clientes(
            id_duplicado, id_principal, current_app.config.get("BACKUP_DIR", "backups")
        )
    except ErrorClientes as error:
        flash(str(error), "danger")
        return redirect(url_for("clientes_bp.clientes"))
    except Exception:
        logger.exception("Error inesperado al unificar clientes %s -> %s", id_duplicado, id_principal)
        flash("Ocurrió un error inesperado al unificar los clientes. No se cambió nada.", "danger")
        return redirect(url_for("clientes_bp.clientes"))

    registrar_auditoria(
        "UNIFICACION_CLIENTES",
        f"'{resultado['duplicado']}' (ID {id_duplicado}) unificado en '{resultado['principal']}' "
        f"(ID {id_principal}): {resultado['remitos']} remitos, {resultado['cheques']} cheques, "
        f"{resultado['vehiculos']} vehículos. Backup: {resultado['backup'].name}",
    )
    flash(
        f"«{resultado['duplicado']}» se unificó dentro de «{resultado['principal']}»: "
        f"{resultado['remitos']} remitos, {resultado['cheques']} cheques y "
        f"{resultado['vehiculos']} vehículos pasaron al cliente principal. "
        f"Copia de seguridad: {resultado['backup'].name}.",
        "success",
    )
    return redirect(url_for("clientes_bp.clientes"))
