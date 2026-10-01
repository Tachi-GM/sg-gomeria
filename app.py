from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3
from datetime import date, datetime
import shutil
import os

app = Flask(__name__)
app.secret_key = "modo-milagritos-activo"

def obtener_conexion():
    conexion = sqlite3.connect("sg_gomeria.db")
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion

def modo_activo():
    return session.get('modo_milagritos', False)

# Ruta para prender/apagar el modo, y volver a donde estabas
@app.route('/toggle-milagritos')
def toggle_milagritos():
    session['modo_milagritos'] = not session.get('modo_milagritos', False)
    # request.referrer = la página desde la que vino el usuario
    return redirect(request.referrer or url_for('home'))

# Pantalla de inicio (Botones Mataburros / Clientes)
@app.route('/')
def home():
    return render_template('index.html', milagritos=modo_activo())

@app.route('/salir')
def salir():
    return render_template('salir.html', milagritos=modo_activo())

@app.route('/acerca-de')
def acerca_de():
    return render_template('acerca-de.html',milagritos=modo_activo())

# Pantalla de Gestión de Clientes y Dashboard General
@app.route('/clientes')
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
        SELECT t.id_trabajo, t.remito, t.tipo, t.fecha, c.nom_cli, t.total, t.estado
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
def mataburros():
    conexion = obtener_conexion()
    
    empresas = conexion.execute("SELECT id_cliente, nom_cli, cuit FROM clientes").fetchall()
    tareas = conexion.execute("SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas").fetchall()
    
    conexion.close()
    return render_template('mataburros.html', empresas=empresas, tareas=tareas, tareas_json=[dict(t) for t in tareas], milagritos=modo_activo())

@app.route('/precios')
def precios():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    tareas = cursor.execute("SELECT id_tarea, nom_tar, precio, precio2, precio3 FROM tareas").fetchall()
    
    conexion.close()
    return render_template('precios.html', tareas=tareas , milagritos=modo_activo())

@app.route('/historial-cliente')
def historial_cliente():
    id_cliente = request.args.get('id_cliente')
    periodo_seleccionado = request.args.get('periodo', 'todos')

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cliente = cursor.execute("SELECT id_cliente, nom_cli, cuit FROM clientes WHERE id_cliente = ?", (id_cliente,)).fetchone()
    # 1. Armamos la consulta base y la lista de parámetros
    query = """
        SELECT t.id_trabajo, t.remito, t.tipo, t.fecha, c.nom_cli, t.total, t.estado,
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
def cheques():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    conexion.close()
    return render_template('cheques.html', cheques=cheques, milagritos=modo_activo())

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
def hacer_backup():
    # 1. Armamos un nombre único con fecha y hora
    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombre_archivo = f"backup_gomeria_{fecha_hora}.db"

    # 2. Creamos una carpeta para guardar copias (si no existe)
    os.makedirs("backups", exist_ok=True)
    ruta_copia = os.path.join("backups", nombre_archivo)

    # 3. Copiamos la base de datos actual a esa carpeta
    shutil.copy("sg_gomeria.db", ruta_copia)

    # 4. Le mandamos el archivo al navegador para que lo descargue
    return send_file(ruta_copia, as_attachment=True, download_name=nombre_archivo)


@app.route('/actualizar-estado', methods=['POST'])
def actualizar_estado():
    id_trabajo = request.form.get('id_trabajo')
    nuevo_estado = request.form.get('estado')

    estados_validos=['PENDIENTE', 'EN PROCESO', 'PAGADO']

    if nuevo_estado not in estados_validos:
        return "Estado invalido", 400

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute('UPDATE trabajos SET estado = ? WHERE id_trabajo = ?', (nuevo_estado, id_trabajo))
    conexion.commit()
    conexion.close()

    return "OK", 200

@app.route('/enviar-trabajo', methods=['POST'])
def enviar_trabajo():
    # 1. Capturamos los datos del formulario
    remito = request.form.get('remito')
    id_cliente = request.form.get('empresa')
    tipo_lista = request.form.get('tipo_lista', '1')  # 1, 2 o 3

    if not id_cliente:
        return "Error: Debes seleccionar una empresa", 400
    
    columnas_precio = {'1': 'precio', '2': 'precio2', '3': 'precio3'}
    columna_elegida = columnas_precio.get(tipo_lista, 'precio')  # Por defecto, 'precio'

    # Capturamos todas las tareas y cantidades que agregó el usuario con getlist
    tareas_elegidas = request.form.getlist('tareas')
    cantidades = request.form.getlist('cantidades')
    
    # Filtramos por si alguna quedó sin seleccionar
    ids_tareas = [int(t) for t in tareas_elegidas if t]
    
    if not ids_tareas:
        return "Error: Debes seleccionar al menos una tarea", 400

    fecha_hoy = date.today().strftime("%Y-%m-%d") # Fecha en formato YYYY-MM-DD
    
    # 2. Conectamos a SQLite
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # A. EL MATABURROS: Buscamos el precio real de cada tarea y calculamos el total
        total_trabajo = 0.0
        detalles_a_guardar = [] # Guardará tuplas: (id_tarea, precio)
        
        for id_t, cant in zip(ids_tareas, cantidades):
            cantidad = int(cant) if cant else 1
            cursor.execute(f"SELECT nom_tar, {columna_elegida} AS precio_final FROM tareas WHERE id_tarea = ?", (id_t,))
            fila = cursor.fetchone()
            if fila:
                precio = fila['precio_final'] or 0.0 #Por si no tiene precio, lo ponemos en 0
                subtotal = precio * cantidad
                total_trabajo += subtotal
                detalles_a_guardar.append((id_t, cantidad, precio, subtotal))
        
        # B. GUARDAR CABECERA en 'trabajos'
        tipo = request.form.get('tipo', 'OI')
        if tipo not in ('OI', 'OIB'):
            return "Error: tipo de remito inválido", 400

        cursor.execute("""
            INSERT INTO trabajos (remito, tipo, fecha, id_cliente, total, estado)
            VALUES (?, ?, ?, ?, ?, 'PENDIENTE')
        """, (remito, tipo, fecha_hoy, id_cliente, total_trabajo))
        
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
        print(f"[EXITO] Remito N° {remito} guardado. Total calculado: ${total_trabajo:,.2f}")
        
    except sqlite3.IntegrityError as e:
        print(f"[ERROR] No se pudo guardar: el remito N° {remito} ya existe.")
        return f"Error: El remito N° {remito} ya fue registrado anteriormente.", 400
    finally:
        conexion.close()
        
    # Redirigimos al inicio
    return redirect(url_for('home'))

@app.route('/agregar-cliente', methods=['POST'])
def agregar_cliente():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # Capturamos los datos del formulario
    nom_cli = request.form.get('nombre')
    cuit = request.form.get('cuit')
    tel = request.form.get('tel')
    mail = request.form.get('mail')

    try:
        cursor.execute("""
            INSERT INTO clientes (nom_cli, cuit, tel, mail)
            VALUES (?, ?, ?, ?)
        """, (nom_cli, cuit, tel, mail))
        conexion.commit()
        print(f"[EXITO] Cliente '{nom_cli}' agregado correctamente.")
    except sqlite3.IntegrityError as e:
        print(f"[ERROR] No se pudo agregar el cliente: {e}")
        return f"Error: No se pudo agregar el cliente '{nom_cli}'.", 400
    finally:
        conexion.close()

    return redirect(url_for('clientes'))

@app.route('/agregar-tarea', methods=['POST'])
def agregar_tarea():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    #Capturamos datos de la nueva tarea
    nom_tar = request.form.get('nombre')
    precio1 = float(request.form.get('precio1-form') or 0)
    precio2 = float(request.form.get('precio2-form') or 0)
    precio3 = float(request.form.get('precio3-form') or 0)

    #Advertencia
    if not (precio1 <= precio2 <= precio3):
        flash(f"⚠️ Revisa los precios de \"{nom_tar}\", ya que algún precio no es el esperado. Se guardó igual.", "warning")

    if precio3 >= precio2*1.5 or precio2 >= precio1*1.5:
        flash(f"⚠️ Revisa los precios de \"{nom_tar}\", ya que algún precio no es el esperado. Se guardó igual.", "warning")


    try:
        cursor.execute("""
            INSERT INTO tareas (nom_tar, precio, precio2, precio3)
            VALUES (?, ?, ?, ?)
        """, (nom_tar, precio1, precio2, precio3))
        conexion.commit()
        print(f"[EXITO] Trea '{nom_tar}' agregada correctamente.")
    except sqlite3.IntegrityError as e:
        print(f"[ERROR] No se pudo agregar la tarea: {e}")
        return f"Error: No se pudo agregar la tarea '{nom_tar}'.", 400
    finally:
        conexion.close()

    return redirect(url_for('mataburros'))

@app.route('/modificar-tarea', methods=['POST'])
def modificar_tarea():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    id_tarea = request.form.get('id_tarea')
    nom_tar = request.form.get('nombre')
    precio1 = request.form.get('precio1')
    precio2 = request.form.get('precio2')
    precio3 = request.form.get('precio3')

    cursor.execute("""
        UPDATE tareas
        SET nom_tar = ?, precio = ?, precio2 = ?, precio3 = ?
        WHERE id_tarea = ?
    """, (nom_tar, precio1, precio2, precio3, id_tarea))
    conexion.commit()
    conexion.close()

    return redirect(url_for('precios'))


if __name__ == '__main__':
    app.run(debug=True)



