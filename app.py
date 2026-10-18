from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, jsonify
import sqlite3
from datetime import date, datetime
import shutil
import os
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import logging
from database.connection import obtener_conexion, DB_PATH

# Configuración del sistema de Logs y Auditoría profesional:
# Muestra los mensajes en la terminal y además los guarda en sistema.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('sistema.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SG_Gomeria')

def registrar_auditoria(accion, detalle=""):
    """Registra en el log de auditoría la acción realizada y el usuario responsable."""
    usuario = session.get('usuario', 'ANONIMO')
    rol = session.get('rol', '-')
    logger.info(f"AUDITORIA | Usuario: {usuario} ({rol}) | Accion: {accion} | {detalle}")

def parse_int_seguro(valor, por_defecto=0):
    """Convierte texto a entero sin lanzar excepciones."""
    try:
        if valor is None or str(valor).strip() == '':
            return por_defecto
        return int(valor)
    except (ValueError, TypeError):
        return por_defecto

def parse_float_seguro(valor, por_defecto=0.0):
    """Convierte texto a número decimal flotante con soporte para comas."""
    try:
        if valor is None or str(valor).strip() == '':
            return por_defecto
        limpio = str(valor).strip().replace(',', '.')
        return float(limpio)
    except (ValueError, TypeError):
        return por_defecto

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

load_dotenv()  # Carga el archivo .env

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-gomeria-2026-cambiar-en-prod")

def modo_activo():
    return session.get('modo_milagritos', False)

# Decoradores de autenticación y autorización
def login_requerido(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        if not session.get('usuario'):
            flash("Debes iniciar sesión para acceder al sistema", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return funcion_decorada

def solo_admin(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        if session.get('rol') != 'admin':
            flash("Acceso restringido: requiere permisos de Administrador", "danger")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return funcion_decorada

# Autenticación: Login y Logout
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('usuario'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        clave = request.form.get('password', '')

        conexion = obtener_conexion()
        user = conexion.execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()
        conexion.close()

        if user and check_password_hash(user['contraseña'], clave):
            session['usuario'] = user['usuario']
            session['rol'] = user['rol']
            registrar_auditoria("LOGIN_EXITOSO", f"Acceso correcto al sistema")
            flash(f"¡Bienvenido/a, {user['usuario']}!", "success")
            return redirect(url_for('home'))
        else:
            logger.warning(f"AUDITORIA | Intento fallido de inicio de sesion para usuario: '{usuario}'")
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html', milagritos=modo_activo())

@app.route('/logout')
def logout():
    usuario_desconectado = session.pop('usuario', None)
    session.pop('rol', None)
    if usuario_desconectado:
        logger.info(f"AUDITORIA | Usuario: {usuario_desconectado} | Accion: LOGOUT | Cierre de sesion voluntario")
        flash("Has cerrado sesión exitosamente", "info")
    return redirect(url_for('login'))

# Ruta para prender/apagar el modo, y volver a donde estabas
@app.route('/toggle-milagritos')
def toggle_milagritos():
    session['modo_milagritos'] = not session.get('modo_milagritos', False)
    # request.referrer = la página desde la que vino el usuario
    return redirect(request.referrer or url_for('home'))

@app.after_request
def registrar_errores(respuesta):
    if respuesta.status_code >= 400:
        logging.warning(f"{request.method} {request.path} -> {respuesta.status_code}")
    return respuesta

#Errores
def pagina_error(codigo, mensaje):
    return render_template('error.html',
                           codigo=codigo,
                           mensaje=mensaje,
                           milagritos=modo_activo()), codigo

@app.errorhandler(401)
def error_401(e):
    logger.warning(f"AUDITORIA | Acceso no autorizado (401) a {request.path}")
    return pagina_error(401, "No tienes autorización para acceder a esta pantalla. Por favor, inicia sesión."), 401

@app.errorhandler(403)
def error_403(e):
    logger.warning(f"AUDITORIA | Permisos insuficientes (403) a {request.path} | Usuario: {session.get('usuario')}")
    return pagina_error(403, "Acceso restringido: no cuentas con los permisos de Administrador necesarios."), 403

@app.errorhandler(404)
def error_404(e):
    return pagina_error(404, "No encontramos esa página")

@app.errorhandler(500)
def error_500(e):
    return pagina_error(500, "Algo salió mal de nuestro lado. Probá de nuevo en un rato")

@app.route('/probar-error')
def probar_error():
    return 1 / 0  #Fuerza un ZeroDivisionError a propósito

# Pantallas
@app.route('/')
@login_requerido
def home():
    return render_template('index.html', milagritos=modo_activo())

@app.route('/salir')
def salir():
    return render_template('salir.html', milagritos=modo_activo())

@app.route('/acerca-de')
def acerca_de():
    return render_template('acerca-de.html', milagritos=modo_activo())

# Pantalla de Gestión de Clientes y Dashboard General
@app.route('/clientes')
@login_requerido
def clientes():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    buscar = request.args.get('buscar', '').strip()
    periodo_seleccionado = request.args.get('periodo', 'todos')

    if buscar:
        empresas = cursor.execute("""
            SELECT id_cliente, nom_cli, cuit, tel, mail 
            FROM clientes 
            WHERE nom_cli LIKE ? OR cuit LIKE ? OR tel LIKE ?
            ORDER BY nom_cli
        """, (f'%{buscar}%', f'%{buscar}%', f'%{buscar}%')).fetchall()
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

    if periodo_seleccionado and periodo_seleccionado != 'todos':
        query_remitos += " WHERE strftime('%Y-%m', t.fecha) = ?"
        parametros_remitos.append(periodo_seleccionado)

    query_remitos += " ORDER BY t.fecha DESC, t.id_trabajo DESC"

    remitos = cursor.execute(query_remitos, parametros_remitos).fetchall()

    meses_disponibles = obtener_meses_disponibles(cursor)  # sin id_cliente = todos los clientes

    detalles_raw = cursor.execute("""
        SELECT dt.id_trabajo, tar.nom_tar, dt.cantidad, dt.subtotal
        FROM detalle_trabajos dt
        JOIN tareas tar ON dt.id_tarea = tar.id_tarea
        ORDER BY dt.id_trabajo
    """).fetchall()

    detalles_por_trabajo = {}
    for d in detalles_raw:
        detalles_por_trabajo.setdefault(d['id_trabajo'], []).append(d)

    conexion.close()
    return render_template('clientes.html',
                        empresas=empresas,
                        remitos=remitos,
                        buscar=buscar,
                        periodo_seleccionado=periodo_seleccionado,
                        meses_disponibles=meses_disponibles,
                        detalles_por_trabajo=detalles_por_trabajo,
                        milagritos=modo_activo())

# Pantalla del Formulario Mataburros
@app.route('/mataburros')
@login_requerido
def mataburros():
    conexion = obtener_conexion()
    
    empresas = conexion.execute("SELECT id_cliente, nom_cli, cuit, con_iva FROM clientes").fetchall()
    tareas = conexion.execute("SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas").fetchall()
    clientes_json = [dict(e) for e in empresas]
    tareas_json=[dict(t) for t in tareas]
    
    conexion.close()
    return render_template('mataburros.html', empresas=empresas, tareas=tareas, tareas_json=tareas_json, clientes_json=clientes_json,milagritos=modo_activo())

@app.route('/precios')
@login_requerido
def precios():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    tareas = cursor.execute("SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas").fetchall()
    
    conexion.close()
    return render_template('precios.html', tareas=tareas , milagritos=modo_activo())

@app.route('/historial-cliente')
@login_requerido
def historial_cliente():
    id_cliente = request.args.get('id_cliente')
    periodo_seleccionado = request.args.get('periodo', 'todos')

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cliente = cursor.execute("SELECT id_cliente, nom_cli, cuit FROM clientes WHERE id_cliente = ?", (id_cliente,)).fetchone()
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
    if periodo_seleccionado and periodo_seleccionado != 'todos':
        query += " AND strftime('%Y-%m', t.fecha) = ?"
        parametros.append(periodo_seleccionado)

    # 3. Le agregamos el cierre obligatorio (agrupar y ordenar por fecha)
    query += " GROUP BY t.id_trabajo ORDER BY t.fecha DESC"

    # 4. Ejecutamos la consulta con sus parámetros
    remitos = cursor.execute(query, parametros).fetchall()

    # 5. Obtenemos el total y el total por mes
    total_mes = sum(r['total'] for r in remitos)

    # NUEVO: traemos el detalle solo de los trabajos que aparecen en `remitos`
    ids_trabajo = [r['id_trabajo'] for r in remitos]
    detalles_por_trabajo = {}
    
    if ids_trabajo:
        # Generamos "?, ?, ?" según cuántos ids haya, para el IN de SQL
        placeholders = ','.join('?' for _ in ids_trabajo)
        detalles_raw = cursor.execute(f"""
            SELECT dt.id_trabajo, tar.nom_tar, dt.cantidad, dt.subtotal
            FROM detalle_trabajos dt
            JOIN tareas tar ON dt.id_tarea = tar.id_tarea
            WHERE dt.id_trabajo IN ({placeholders})
            ORDER BY dt.id_trabajo
        """, ids_trabajo).fetchall()
        
        for d in detalles_raw:
            detalles_por_trabajo.setdefault(d['id_trabajo'], []).append(d)

    cursor.close()
    return render_template('historial-cliente.html',
                        cliente=cliente,
                        remitos=remitos, 
                        total_mes=total_mes,
                        meses_disponibles=meses_disponibles,
                        detalles_por_trabajo= detalles_por_trabajo,
                        periodo_seleccionado=periodo_seleccionado)
    
@app.route('/cheques')
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
    clientes = cursor.execute("SELECT nom_cli FROM clientes ORDER BY nom_cli ASC").fetchall()
    conexion.close()
    return render_template('cheques.html', cheques=lista_cheques, clientes=clientes, milagritos=modo_activo())

@app.route('/agregar-cheque', methods=['POST'])
@login_requerido
def agregar_cheque():
    numero = request.form.get('numero', '').strip()
    cliente = request.form.get('cliente', '').strip()
    banco = request.form.get('banco', '').strip()
    fecha_emision = request.form.get('fecha_emision', '')
    fecha_pago = request.form.get('fecha_pago', '')
    importe = parse_float_seguro(request.form.get('importe'), 0.0)
    estado = request.form.get('estado', 'Pendiente')
    endosado = request.form.get('endosado', '').strip()

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO cheques (numero, cliente, banco, fecha_emision, fecha_pago, importe, estado, endosado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (numero, cliente, banco, fecha_emision, fecha_pago, importe, estado, endosado))
    conexion.commit()
    id_nuevo = cursor.lastrowid
    conexion.close()

    registrar_auditoria("ALTA_CHEQUE", f"Cheque N° {numero} ({banco}) por ${importe:,.2f} para '{cliente}'")

    return jsonify({
        'id_cheque': id_nuevo,
        'numero': numero,
        'cliente': cliente,
        'banco': banco,
        'fecha_emision': fecha_emision,
        'fecha_pago': fecha_pago,
        'importe': importe,
        'estado': estado,
        'endosado': endosado
    })

@app.route('/actualizar-estado-cheque', methods=['POST'])
@login_requerido
def actualizar_estado_cheque():
    id_cheque = request.form.get('id_cheque')
    nuevo_estado = request.form.get('estado')
    estados_validos = ['Pendiente', 'Cobrado', 'Rechazado']
    if nuevo_estado not in estados_validos:
        return "Estado inválido", 400

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("UPDATE cheques SET estado = ? WHERE id_cheque = ?", (nuevo_estado, id_cheque))
    conexion.commit()
    conexion.close()

    registrar_auditoria("ESTADO_CHEQUE", f"Cheque ID {id_cheque} actualizado a estado '{nuevo_estado}'")
    return "OK", 200

@app.route('/eliminar-cheque', methods=['POST'])
@login_requerido
def eliminar_cheque():
    id_cheque = request.form.get('id_cheque')
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM cheques WHERE id_cheque = ?", (id_cheque,))
    conexion.commit()
    conexion.close()

    registrar_auditoria("BAJA_CHEQUE", f"Cheque ID {id_cheque} eliminado")
    return "OK", 200

MESES_ABREVIADOS = {
    '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
    '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
    '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'
}

def formatear_periodo(periodo):
    """Convierte 'YYYY-MM' (ej: '2026-09') en 'Sep 26' para mostrar en las pestañas."""
    anio, mes = periodo.split('-')
    return f"{MESES_ABREVIADOS[mes]} {anio[2:]}"

def obtener_meses_disponibles(cursor, id_cliente=None):
    """
    Devuelve la lista de meses con trabajos registrados, listos para las pestañas.
    Si se pasa id_cliente, filtra solo los meses de ese cliente.
    Si no, trae los meses de TODOS los clientes (para el historial general).
    """
    if id_cliente:
        filas = cursor.execute("""
            SELECT DISTINCT strftime('%Y-%m', fecha) AS periodo
            FROM trabajos
            WHERE id_cliente = ?
            ORDER BY periodo DESC
        """, (id_cliente,)).fetchall()
    else:
        filas = cursor.execute("""
            SELECT DISTINCT strftime('%Y-%m', fecha) AS periodo
            FROM trabajos
            ORDER BY periodo DESC
        """).fetchall()

    return [
        {'periodo': fila['periodo'], 'etiqueta': formatear_periodo(fila['periodo'])}
        for fila in filas
    ]

@app.route('/backup')
@login_requerido
@solo_admin
def hacer_backup():
    # 1. Armamos un nombre único con fecha y hora
    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombre_archivo = f"backup_gomeria_{fecha_hora}.db"

    # 2. Creamos una carpeta para guardar copias (si no existe)
    os.makedirs("backups", exist_ok=True)
    ruta_copia = os.path.join("backups", nombre_archivo)

    # 3. Copiamos la base de datos actual a esa carpeta
    shutil.copy("sg_gomeria.db", ruta_copia)

    registrar_auditoria("BACKUP_BD", f"Generado resguardo de base de datos: {nombre_archivo}")

    # 4. Le mandamos el archivo al navegador para que lo descargue
    return send_file(ruta_copia, as_attachment=True, download_name=nombre_archivo)


@app.route('/enviar-trabajo', methods=['POST'])
@login_requerido
def enviar_trabajo():
    # 1. Capturamos los datos del formulario
    remito = request.form.get('remito', '').strip()
    id_cliente = request.form.get('empresa')
    tipo_lista = request.form.get('tipo_lista', '1')  # 1, 2 o 3
    detalle = request.form.get('detalles') or request.form.get('detalle', '')

    if not remito:
        flash("Error: El número de remito es obligatorio", "danger")
        return redirect(url_for('mataburros'))

    if not id_cliente:
        flash("Error: Debes seleccionar una empresa", "danger")
        return redirect(url_for('mataburros'))
    
    columnas_precio = {'1': 'precio', '2': 'precio2', '3': 'precio3'}
    columna_elegida = columnas_precio.get(tipo_lista, 'precio')  # Por defecto, 'precio'

    # Capturamos todas las tareas y cantidades que agregó el usuario con getlist
    tareas_elegidas = request.form.getlist('tareas')
    cantidades = request.form.getlist('cantidades')
    
    # Filtramos de forma segura por si alguna quedó sin seleccionar o no es número
    ids_tareas = [parse_int_seguro(t) for t in tareas_elegidas if parse_int_seguro(t) > 0]
    
    if not ids_tareas:
        flash("Error: Debes seleccionar al menos una tarea válida", "danger")
        return redirect(url_for('mataburros'))

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
            return redirect(url_for('mataburros'))

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
        return redirect(url_for('mataburros'))
        
    except sqlite3.IntegrityError:
        logger.warning(f"AUDITORIA | Intento de registrar remito duplicado: N° {remito}")
        flash(f"Error: El remito N° {remito} ya fue registrado anteriormente.", "danger")
        return redirect(url_for('mataburros'))
    except Exception as e:
        logger.exception(f"Error inesperado al emitir remito #{remito}: {e}")
        flash("Ocurrió un error inesperado al procesar el remito. Intente nuevamente.", "danger")
        return redirect(url_for('mataburros'))
    finally:
        conexion.close()

@app.route('/agregar-cliente', methods=['POST'])
@login_requerido
def agregar_cliente():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    nom_cli = request.form.get('nombre', '').strip()
    cuit = request.form.get('cuit', '').strip()
    tel = request.form.get('tel', '').strip()
    mail = request.form.get('mail', '').strip()

    if not nom_cli:
        flash("El nombre o razón social del cliente es obligatorio", "danger")
        return redirect(url_for('clientes'))

    try:
        cursor.execute("""
            INSERT INTO clientes (nom_cli, cuit, tel, mail)
            VALUES (?, ?, ?, ?)
        """, (nom_cli, cuit, tel, mail))
        conexion.commit()
        registrar_auditoria("ALTA_CLIENTE", f"Empresa '{nom_cli}' (CUIT: {cuit}) agregada")
        flash(f"Cliente '{nom_cli}' registrado correctamente.", "success")
    except sqlite3.IntegrityError:
        logger.warning(f"AUDITORIA | Intento de registrar cliente duplicado: '{nom_cli}' (CUIT: {cuit})")
        flash(f"Error: Ya existe un cliente con ese CUIT o razón social.", "danger")
    except Exception as e:
        logger.exception(f"Error inesperado al agregar cliente: {e}")
        flash("Ocurrió un error inesperado al registrar el cliente.", "danger")
    finally:
        conexion.close()

    return redirect(url_for('clientes'))

@app.route('/agregar-tarea', methods=['POST'])
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
        return redirect(url_for('mataburros'))

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

    return redirect(url_for('mataburros'))

@app.route('/modificar-tarea', methods=['POST'])
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

    return redirect(url_for('precios'))


if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode)
