import sqlite3
import logging
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.connection import obtener_conexion
from utils.seguridad import login_requerido, registrar_auditoria, modo_activo
from utils.formateadores import parse_int_seguro, parse_float_seguro

logger = logging.getLogger('SG_Gomeria')
trabajos_bp = Blueprint('trabajos_bp', __name__)

#Pantalla Mataburros
@trabajos_bp.route('/mataburros')
@login_requerido
def mataburros():
    conexion = obtener_conexion()
    
    empresas = conexion.execute("SELECT id_cliente, nom_cli, cuit, con_iva FROM clientes").fetchall()
    tareas = conexion.execute("SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas").fetchall()
    clientes_json = [dict(e) for e in empresas]
    tareas_json=[dict(t) for t in tareas]
    
    conexion.close()
    return render_template('mataburros.html', empresas=empresas, tareas=tareas, tareas_json=tareas_json, clientes_json=clientes_json,milagritos=modo_activo())

#Funcion de enviar trabajos
@trabajos_bp.route('/enviar-trabajo', methods=['POST'])
@login_requerido
def enviar_trabajo():
    # 1. Capturamos los datos del formulario
    remito = request.form.get('remito', '').strip()
    id_cliente = request.form.get('empresa')
    tipo_lista = request.form.get('tipo_lista', '1')  # 1, 2 o 3
    detalle = request.form.get('detalles') or request.form.get('detalle', '')

    if not remito:
        flash("Error: El número de remito es obligatorio", "danger")
        return redirect(url_for('trabajos_bp.mataburros'))

    if not id_cliente:
        flash("Error: Debes seleccionar una empresa", "danger")
        return redirect(url_for('trabajos_bp.mataburros'))
    
    columnas_precio = {'1': 'precio', '2': 'precio2', '3': 'precio3'}
    columna_elegida = columnas_precio.get(tipo_lista, 'precio')  # Por defecto, 'precio'

    # Capturamos todas las tareas y cantidades que agregó el usuario con getlist
    tareas_elegidas = request.form.getlist('tareas')
    cantidades = request.form.getlist('cantidades')
    
    # Filtramos de forma segura por si alguna quedó sin seleccionar o no es número
    ids_tareas = [parse_int_seguro(t) for t in tareas_elegidas if parse_int_seguro(t) > 0]
    
    if not ids_tareas:
        flash("Error: Debes seleccionar al menos una tarea válida", "danger")
        return redirect(url_for('trabajos_bp.mataburros'))

    fecha_hoy = date.today().strftime("%Y-%m-%d") # Fecha en formato YYYY-MM-DD
    
    # 2. Conectamos a SQLite
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # A. EL MATABURROS: Buscamos el precio real de cada tarea y calculamos el total
        total_trabajo = 0.0
        detalles_a_guardar = [] # Guardará tuplas: (id_tarea, cantidad, precio, subtotal)
        
        for id_t, cant in zip(ids_tareas, cantidades):
            cantidad = max(1, parse_int_seguro(cant, 1))
            cursor.execute(f"SELECT nom_tar, {columna_elegida} AS precio_final FROM tareas WHERE id_tarea = ?", (id_t,))
            fila = cursor.fetchone()
            if fila:
                precio = parse_float_seguro(fila['precio_final'], 0.0)
                subtotal = precio * cantidad
                total_trabajo += subtotal
                detalles_a_guardar.append((id_t, cantidad, precio, subtotal))
        
        # B. GUARDAR CABECERA en 'trabajos'
        tipo = request.form.get('tipo', 'OI').strip()
        if tipo not in ('OI', 'OIB'):
            tipo = 'OI'

        cliente = cursor.execute("SELECT con_iva FROM clientes WHERE id_cliente = ?", (id_cliente,)).fetchone()
        if cliente is None:
            flash("Error: Cliente inexistente", "danger")
            return redirect(url_for('trabajos_bp.mataburros'))

        if cliente['con_iva'] == 0:
            total_trabajo = round(total_trabajo / 1.21, 2)
        
        cursor.execute("""
            INSERT INTO trabajos (remito, tipo, fecha, id_cliente, total, detalle)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (remito, tipo, fecha_hoy, id_cliente, total_trabajo, detalle))
        
        # Obtenemos el id del trabajo recién insertado
        id_trabajo = cursor.lastrowid
        
        # C. GUARDAR RENGLONES en 'detalle_trabajos'
        for id_t, cant, p_unit, sub in detalles_a_guardar:
            cursor.execute("""
                INSERT INTO detalle_trabajos (id_trabajo, id_tarea, cantidad, precio_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (id_trabajo, id_t, cant, p_unit, sub))
        
        # D. CONFIRMAMOS LA TRANSACCIÓN
        conexion.commit()
        registrar_auditoria("EMISION_REMITO", f"Remito {tipo} #{remito} emitido para cliente ID {id_cliente}. Total: ${total_trabajo:,.2f}")
        flash(f"Remito N° {remito} guardado. Total calculado: ${total_trabajo:,.2f}", "success")
        return redirect(url_for('trabajos_bp.mataburros'))
        
    except sqlite3.IntegrityError:
        logger.warning(f"AUDITORIA | Intento de registrar remito duplicado: N° {remito}")
        flash(f"Error: El remito N° {remito} ya fue registrado anteriormente.", "danger")
        return redirect(url_for('trabajos_bp.mataburros'))
    except Exception as e:
        logger.exception(f"Error inesperado al emitir remito #{remito}: {e}")
        flash("Ocurrió un error inesperado al procesar el remito. Intente nuevamente.", "danger")
        return redirect(url_for('trabajos_bp.mataburros'))
    finally:
        conexion.close()
        
#Pantalla Precios
@trabajos_bp.route('/precios')
@login_requerido
def precios():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    tareas = cursor.execute("SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas").fetchall()
    
    conexion.close()
    return render_template('precios.html', tareas=tareas , milagritos=modo_activo())

#Funciones de Agregar y Modificar Tareas
@trabajos_bp.route('/agregar-tarea', methods=['POST'])
@login_requerido
def agregar_tarea():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    nom_tar = request.form.get('nombre', '').strip()
    precio1 = parse_float_seguro(request.form.get('precio1-form'), 0.0)
    precio2 = parse_float_seguro(request.form.get('precio2-form'), 0.0)
    precio3 = parse_float_seguro(request.form.get('precio3-form'), 0.0)

    if not nom_tar:
        flash("El nombre de la tarea no puede estar vacío", "danger")
        return redirect(url_for('trabajos_bp.mataburros'))

    # Advertencias de coherencia comercial
    if not (precio1 <= precio2 <= precio3):
        flash(f"⚠️ Revisa los precios de \"{nom_tar}\": los valores no siguen el orden habitual L1 <= L2 <= L3.", "warning")

    try:
        cursor.execute("""
            INSERT INTO tareas (nom_tar, precio, precio2, precio3)
            VALUES (?, ?, ?, ?)
        """, (nom_tar, precio1, precio2, precio3))
        conexion.commit()
        registrar_auditoria("ALTA_TAREA", f"Tarea '{nom_tar}' creada (L1: ${precio1}, L2: ${precio2}, L3: ${precio3})")
        flash(f"Tarea '{nom_tar}' agregada correctamente.", "success")
    except sqlite3.IntegrityError:
        flash(f"Error: La tarea '{nom_tar}' ya existe en el tarifario.", "danger")
    except Exception as e:
        logger.exception(f"Error inesperado al agregar tarea: {e}")
        flash("Ocurrió un error al registrar la tarea.", "danger")
    finally:
        conexion.close()

    return redirect(url_for('trabajos_bp.mataburros'))

@trabajos_bp.route('/modificar-tarea', methods=['POST'])
@login_requerido
def modificar_tarea():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    id_tarea = parse_int_seguro(request.form.get('id_tarea'))
    nom_tar = request.form.get('nombre', '').strip()
    precio1 = parse_float_seguro(request.form.get('precio1'), 0.0)
    precio2 = parse_float_seguro(request.form.get('precio2'), 0.0)
    precio3 = parse_float_seguro(request.form.get('precio3'), 0.0)

    try:
        cursor.execute("""
            UPDATE tareas
            SET nom_tar = ?, precio = ?, precio2 = ?, precio3 = ?
            WHERE id_tarea = ?
        """, (nom_tar, precio1, precio2, precio3, id_tarea))
        conexion.commit()
        registrar_auditoria("MODIFICACION_TAREA", f"Tarea ID {id_tarea} ('{nom_tar}') actualizada")
        flash(f"Tarifas de '{nom_tar}' actualizadas con éxito.", "success")
    except Exception as e:
        logger.exception(f"Error al modificar tarea ID {id_tarea}: {e}")
        flash("Ocurrió un error al actualizar las tarifas.", "danger")
    finally:
        conexion.close()

    return redirect(url_for('trabajos_bp.precios'))