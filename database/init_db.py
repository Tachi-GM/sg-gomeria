"""
Script de Inicialización de la Base de Datos para 'Gomería El Puente'.

Crea la estructura relacional completa con todas las restricciones de integridad
(PRIMARY KEY, FOREIGN KEY, CHECK, UNIQUE) e inserta datos semilla iniciales
junto con los datos completos de demostración (clientes, tareas, remitos,
cheques, vehículos, movimientos de gomeros y usuarios).
"""

import sys
from pathlib import Path

# Asegurar que se pueda importar connection independientemente de donde se ejecute
sys.path.insert(0, str(Path(__file__).resolve().parent))
from connection import obtener_conexion, get_db_path


def crear_tablas():
    """Crea la estructura relacional completa si no existe."""
    ddl_script = """
    -- 1. Empresas / Clientes
    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_cli TEXT NOT NULL,
        cuit TEXT UNIQUE,
        tel TEXT,
        mail TEXT,
        con_iva INTEGER NOT NULL DEFAULT 1,
        lista_precios INTEGER NOT NULL DEFAULT 1 CHECK (lista_precios IN (1, 2, 3)),
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
    );

    -- 2. Vehículos de cada empresa
    CREATE TABLE IF NOT EXISTS vehiculos (
        id_vehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
        patente TEXT NOT NULL UNIQUE,
        id_cliente INTEGER NOT NULL,
        FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente) ON DELETE CASCADE
    );

    -- 3. Catálogo de Tareas y Tarifas (Con 3 listas de precios y estado activa)
    CREATE TABLE IF NOT EXISTS tareas (
        id_tarea INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_tar TEXT NOT NULL UNIQUE,
        precio REAL NOT NULL CHECK (precio >= 0),
        precio2 REAL DEFAULT 0 CHECK (precio2 >= 0),
        precio3 REAL DEFAULT 0 CHECK (precio3 >= 0),
        activa INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1))
    );

    -- 4. Cabecera de Trabajos / Remitos (Con tipo OI/OIB, detalle, foto e IVA)
    CREATE TABLE IF NOT EXISTS trabajos (
        id_trabajo INTEGER PRIMARY KEY AUTOINCREMENT,
        remito TEXT NOT NULL UNIQUE,
        fecha TEXT NOT NULL, -- Formato ISO YYYY-MM-DD
        id_cliente INTEGER NOT NULL,
        id_vehiculo INTEGER,
        total REAL NOT NULL DEFAULT 0 CHECK (total >= 0),
        estado TEXT NOT NULL DEFAULT 'PENDIENTE', -- PENDIENTE, EN PROCESO, PAGADO
        tipo TEXT NOT NULL DEFAULT 'OI',         -- OI, OIB
        detalle TEXT,
        foto_remito TEXT,
        con_iva INTEGER NOT NULL DEFAULT 1 CHECK (con_iva IN (0, 1)),
        FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente) ON DELETE RESTRICT,
        FOREIGN KEY (id_vehiculo) REFERENCES vehiculos (id_vehiculo) ON DELETE SET NULL
    );

    -- 5. Detalle de Tareas realizadas por cada Trabajo (Maestro-Detalle)
    CREATE TABLE IF NOT EXISTS detalle_trabajos (
        id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
        id_trabajo INTEGER NOT NULL,
        id_tarea INTEGER NOT NULL,
        cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0),
        precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
        subtotal REAL NOT NULL CHECK (subtotal >= 0),
        FOREIGN KEY (id_trabajo) REFERENCES trabajos (id_trabajo) ON DELETE CASCADE,
        FOREIGN KEY (id_tarea) REFERENCES tareas (id_tarea) ON DELETE RESTRICT
    );

    -- 6. Renglones temporales asociados a un remito, fuera del tarifario
    CREATE TABLE IF NOT EXISTS detalle_temporal_trabajos (
        id_detalle_temporal INTEGER PRIMARY KEY AUTOINCREMENT,
        id_trabajo INTEGER NOT NULL,
        nombre_tarea TEXT NOT NULL,
        cantidad INTEGER NOT NULL CHECK (cantidad > 0),
        precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
        subtotal REAL NOT NULL CHECK (subtotal >= 0),
        FOREIGN KEY (id_trabajo) REFERENCES trabajos (id_trabajo) ON DELETE CASCADE
    );

    -- 7. Cheques recibidos de clientes
    CREATE TABLE IF NOT EXISTS cheques (
        id_cheque INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL,
        cliente TEXT NOT NULL,
        banco TEXT NOT NULL,
        fecha_emision TEXT,
        fecha_pago TEXT,
        importe REAL NOT NULL CHECK (importe >= 0),
        estado TEXT NOT NULL DEFAULT 'Pendiente', -- Pendiente, Cobrado, Rechazado
        endosado TEXT DEFAULT '',
        id_cliente INTEGER NOT NULL,
        FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
    );

    -- 8. Usuarios del sistema
    CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL UNIQUE,
        contraseña TEXT NOT NULL,
        rol TEXT NOT NULL DEFAULT 'usuario' CHECK (rol IN ('usuario', 'admin'))
    );

    -- 8. Personal: gomeros y su sueldo semanal configurado
    CREATE TABLE IF NOT EXISTS gomeros (
        id_gomero INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL COLLATE NOCASE UNIQUE,
        sueldo_semanal INTEGER NOT NULL DEFAULT 260000 CHECK (sueldo_semanal > 0),
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- 9. Movimientos: adelantos, pagos de sueldo, gastos generales y descuentos de aguinaldo
    CREATE TABLE IF NOT EXISTS movimientos_gomeros (
        id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
        id_gomero INTEGER,
        tipo TEXT NOT NULL CHECK (tipo IN ('ADELANTO', 'PAGO_SEMANAL', 'GASTO_GENERAL', 'DESCUENTO_AGUINALDO')),
        fecha TEXT NOT NULL,
        importe INTEGER NOT NULL CHECK (importe > 0),
        destino TEXT NOT NULL CHECK (destino IN ('SUELDO', 'AGUINALDO', 'NO_APLICA')),
        periodo_aguinaldo TEXT,
        concepto TEXT,
        usuario TEXT,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_gomero) REFERENCES gomeros(id_gomero) ON DELETE RESTRICT,
        CHECK (
            (tipo = 'GASTO_GENERAL' AND id_gomero IS NULL AND destino = 'NO_APLICA')
            OR (tipo != 'GASTO_GENERAL' AND id_gomero IS NOT NULL AND destino IN ('SUELDO', 'AGUINALDO'))
        ),
        CHECK (
            (destino = 'AGUINALDO' AND periodo_aguinaldo IS NOT NULL)
            OR (destino != 'AGUINALDO' AND periodo_aguinaldo IS NULL)
        )
    );
    CREATE INDEX IF NOT EXISTS idx_movimientos_gomeros_fecha
        ON movimientos_gomeros(fecha);
    CREATE INDEX IF NOT EXISTS idx_movimientos_gomeros_gomero_fecha
        ON movimientos_gomeros(id_gomero, fecha);

    -- 10. Ausencias: registro de los días que no asistieron
    CREATE TABLE IF NOT EXISTS ausencias_gomeros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gomero_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (gomero_id)
            REFERENCES gomeros(id_gomero) ON DELETE RESTRICT,
        UNIQUE (gomero_id, fecha)
    );
    CREATE INDEX IF NOT EXISTS idx_ausencias_gomeros_gomero_fecha
        ON ausencias_gomeros(gomero_id, fecha);

    -- 11. Proveedores de insumos y mercadería (Borrador inicial)
    CREATE TABLE IF NOT EXISTS proveedores (
        id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL COLLATE NOCASE UNIQUE,
        cuit TEXT,
        telefono TEXT,
        contacto TEXT,
        rubro TEXT,
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- 12. Cuentas y gastos con proveedores
    CREATE TABLE IF NOT EXISTS cuentas_proveedores (
        id_cuenta INTEGER PRIMARY KEY AUTOINCREMENT,
        id_proveedor INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        detalle TEXT NOT NULL,
        total REAL NOT NULL DEFAULT 0 CHECK (total >= 0),
        estado TEXT NOT NULL DEFAULT 'Pendiente' CHECK (estado IN ('Pendiente', 'Pagado')),
        id_cheque INTEGER,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor) ON DELETE RESTRICT,
        FOREIGN KEY (id_cheque) REFERENCES cheques(id_cheque) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_cuentas_proveedores_proveedor_fecha
        ON cuentas_proveedores(id_proveedor, fecha);

    -- Índices para acelerar historial y carga paginada de remitos.
    CREATE INDEX IF NOT EXISTS idx_trabajos_fecha_id
        ON trabajos(fecha DESC, id_trabajo DESC);
    CREATE INDEX IF NOT EXISTS idx_trabajos_cliente_fecha_id
        ON trabajos(id_cliente, fecha DESC, id_trabajo DESC);
    CREATE INDEX IF NOT EXISTS idx_detalle_trabajos_id_trabajo
        ON detalle_trabajos(id_trabajo);
    CREATE INDEX IF NOT EXISTS idx_detalle_temporal_id_trabajo
        ON detalle_temporal_trabajos(id_trabajo);
    """

    conexion = obtener_conexion()
    try:
        conexion.executescript(ddl_script)
        # Gomeros iniciales solicitados; INSERT OR IGNORE no reactiva bajas lógicas.
        conexion.executemany(
            "INSERT OR IGNORE INTO gomeros (nombre, sueldo_semanal) VALUES (?, ?)",
            [
                ("Sebastián", 300000),
                ("Lucas", 300000),
                ("Marcelo", 350000),
                ("Braian", 300000),
                ("Javier", 400000),
            ],
        )
        conexion.commit()
        print(f"[OK] Estructura de tablas creada con exito en: {get_db_path()}")
    finally:
        conexion.close()


def cargar_datos_demo(conexion):
    """Carga los datos de demostración adicionales (clientes, tareas, remitos, cheques y movimientos)."""
    sql_demo = """
    -- 1. CLIENTES (3 nuevos)
    INSERT INTO clientes (nom_cli, cuit, tel, mail, con_iva, lista_precios) VALUES
      ('Expreso Horizonte SA',      '30-90000041-9', '011-5555-0141', 'flota@horizonte.example.com',   1, 3),
      ('Distribuidora Pampa SRL',   '30-90000052-5', '011-5555-0152', 'taller@pampa.example.com',      0, 2),
      ('Transportes Del Plata SA',  '30-90000063-0', '03487-55-0163', 'compras@delplata.example.com',  1, 1);

    -- 2. TAREAS (9 nuevas: quedan 14, de las cuales 13 activas)
    INSERT INTO tareas (nom_tar, precio, precio2, precio3, activa) VALUES
      ('Montaje y desmontaje',          20000, 18000, 16000, 1),
      ('Reparación con parche',         12000, 10800,  9600, 1),
      ('Balanceo de rueda',              8000,  7200,  6400, 1),
      ('Alineación de tren delantero',  25000, 22500, 20000, 1),
      ('Cambio de cubierta de camión',  90000, 81000, 72000, 1),
      ('Inflado con nitrógeno',          3000,  2700,  2400, 1),
      ('Auxilio en ruta',               45000, 40500, 36000, 1),
      ('Reparación de llanta',          18000, 16200, 14400, 1),
      ('Recapado (discontinuado)',      70000, 63000, 56000, 0);

    -- 3. VEHÍCULOS (7 nuevos)
    WITH v(patente, cuit) AS (VALUES
      ('AC101DE', '30-90000041-9'),
      ('AC102DE', '30-90000041-9'),
      ('AD201FG', '30-90000052-5'),
      ('AD202FG', '30-90000052-5'),
      ('AE301HI', '30-90000063-0'),
      ('AA401JK', '30-65498712-3'),
      ('AB501LM', '30-71239845-9')
    )
    INSERT INTO vehiculos (patente, id_cliente)
    SELECT v.patente, c.id_cliente
    FROM v
    JOIN clientes c ON c.cuit = v.cuit;

    -- 4. REMITOS (22 nuevos; con los 2 existentes quedan 24)
    WITH r(remito, tipo, fecha, cuit, patente, estado, detalle) AS (VALUES
      ('20440',  'OI',  '2026-08-24', '30-71239845-9', 'AE987ZA', 'PAGADO',     'Cambio de cubiertas del eje trasero'),
      ('20451',  'OI',  '2026-08-27', '30-65498712-3', 'AA401JK', 'PAGADO',     NULL),
      ('20468',  'OI',  '2026-08-31', '30-90000041-9', 'AC101DE', 'PAGADO',     'Servicio mensual de flota'),
      ('20503',  'OI',  '2026-09-02', '30-68312345-4', 'ABC123',  'PAGADO',     NULL),
      ('20517',  'OI',  '2026-09-04', '30-90000052-5', 'AD201FG', 'PAGADO',     NULL),
      ('20534',  'OI',  '2026-09-09', '30-71239845-9', 'AE987ZA', 'PAGADO',     'Camión con cubiertas gastadas'),
      ('20552',  'OI',  '2026-09-11', '30-90000063-0', 'AE301HI', 'PAGADO',     NULL),
      ('000141', 'OIB', '2026-09-15', '30-90000041-9', 'AC102DE', 'PAGADO',     'Trabajo adicional fuera del remito OI'),
      ('20589',  'OI',  '2026-09-18', '30-68312345-4', 'AF123JK', 'PAGADO',     NULL),
      ('20611',  'OI',  '2026-09-24', '30-65498712-3', 'AA401JK', 'PAGADO',     NULL),
      ('20640',  'OI',  '2026-09-29', '30-90000052-5', 'AD202FG', 'EN PROCESO', 'Pago parcial acordado con el cliente'),
      ('20672',  'OI',  '2026-10-02', '30-68312345-4', 'ABC123',  'PAGADO',     NULL),
      ('20693',  'OI',  '2026-10-07', '30-90000041-9', 'AC101DE', 'PENDIENTE',  'Cambio de cubiertas de camión'),
      ('000142', 'OIB', '2026-10-09', '30-90000063-0', 'AE301HI', 'PAGADO',     NULL),
      ('20718',  'OI',  '2026-10-14', '30-71239845-9', 'AE987ZA', 'EN PROCESO', NULL),
      ('20745',  'OI',  '2026-10-19', '30-65498712-3', 'AA401JK', 'PENDIENTE',  NULL),
      ('20771',  'OI',  '2026-10-23', '30-90000052-5', 'AD201FG', 'PENDIENTE',  NULL),
      ('20790',  'OI',  '2026-10-28', '30-68312345-4', 'AF123JK', 'PAGADO',     NULL),
      ('20812',  'OI',  '2026-11-03', '30-90000063-0', 'AE301HI', 'PENDIENTE',  'Auxilio en ruta, ruta 9'),
      ('000143', 'OIB', '2026-11-05', '30-71239845-9', 'AE987ZA', 'PENDIENTE',  NULL),
      ('20834',  'OI',  '2026-11-09', '30-90000041-9', 'AC102DE', 'PENDIENTE',  NULL),
      ('20851',  'OI',  '2026-11-12', '30-68312345-4', 'ABC123',  'PENDIENTE',  NULL)
    )
    INSERT INTO trabajos (remito, tipo, fecha, id_cliente, id_vehiculo, total, estado, detalle, con_iva)
    SELECT r.remito, r.tipo, r.fecha, c.id_cliente, v.id_vehiculo, 0, r.estado, r.detalle, c.con_iva
    FROM r
    JOIN clientes c ON c.cuit = r.cuit
    LEFT JOIN vehiculos v ON v.patente = r.patente
    ORDER BY r.fecha, r.remito;

    -- 5. RENGLONES DE CADA REMITO
    WITH d(remito, tarea, cantidad) AS (VALUES
      ('20440',  'Cambio de cubierta',            4), ('20440',  'Válvula nueva',                4),
      ('20451',  'Pinchadura',                    3), ('20451',  'Rotación de neumáticos',       1),
      ('20468',  'Alineación y balanceo',        2), ('20468',  'Inflado con nitrógeno',        6),
      ('20503',  'Cambio de cubierta',            2), ('20503',  'Balanceo de rueda',            2),
      ('20517',  'Reparación con parche',        3), ('20517',  'Pinchadura',                   2),
      ('20534',  'Cambio de cubierta de camión',  2), ('20534',  'Montaje y desmontaje',         2),
      ('20552',  'Alineación de tren delantero',  1),
      ('000141', 'Auxilio en ruta',               1),
      ('20589',  'Rotación de neumáticos',       1), ('20589',  'Válvula nueva',                2),
      ('20611',  'Cambio de cubierta',            3), ('20611',  'Alineación y balanceo',        1),
      ('20640',  'Reparación de llanta',          2), ('20640',  'Montaje y desmontaje',         2),
      ('20672',  'Pinchadura',                    1),
      ('20693',  'Cambio de cubierta de camión',  4), ('20693',  'Balanceo de rueda',            4),
      ('000142', 'Inflado con nitrógeno',        8),
      ('20718',  'Cambio de cubierta',            2), ('20718',  'Alineación de tren delantero', 1),
      ('20745',  'Pinchadura',                    4), ('20745',  'Válvula nueva',                4),
      ('20771',  'Rotación de neumáticos',       2), ('20771',  'Reparación con parche',        2),
      ('20790',  'Cambio de cubierta',            1), ('20790',  'Montaje y desmontaje',         1), ('20790', 'Balanceo de rueda', 1),
      ('20812',  'Auxilio en ruta',               1), ('20812',  'Cambio de cubierta',           2),
      ('000143', 'Reparación de llanta',          1),
      ('20834',  'Cambio de cubierta de camión',  2), ('20834',  'Alineación y balanceo',        2),
      ('20851',  'Alineación de tren delantero',  1), ('20851',  'Rotación de neumáticos',       1), ('20851', 'Válvula nueva', 1)
    )
    INSERT INTO detalle_trabajos (id_trabajo, id_tarea, cantidad, precio_unitario, subtotal)
    SELECT id_trabajo, id_tarea, cantidad, unitario, ROUND(unitario * cantidad, 2)
    FROM (
      SELECT t.id_trabajo, ta.id_tarea, d.cantidad,
             CASE WHEN c.con_iva = 0
                  THEN ROUND(CASE c.lista_precios WHEN 1 THEN ta.precio WHEN 2 THEN ta.precio2 ELSE ta.precio3 END / 1.21, 2)
                  ELSE CASE c.lista_precios WHEN 1 THEN ta.precio WHEN 2 THEN ta.precio2 ELSE ta.precio3 END
             END AS unitario
      FROM d
      JOIN trabajos t  ON t.remito = d.remito
      JOIN clientes c  ON c.id_cliente = t.id_cliente
      JOIN tareas   ta ON ta.nom_tar = d.tarea
    );

    -- Actualizar totales de los remitos nuevos
    UPDATE trabajos
    SET total = COALESCE((SELECT ROUND(SUM(subtotal), 2)
                          FROM detalle_trabajos dt
                          WHERE dt.id_trabajo = trabajos.id_trabajo), 0)
    WHERE total = 0;

    -- 6. CHEQUES (11 nuevos)
    INSERT INTO cheques (numero, cliente, banco, fecha_emision, fecha_pago, importe, estado, endosado, id_cliente)
    SELECT '13122333', nom_cli, 'Banco BBVA', '2026-11-13', '2026-11-20', 50000.0, 'Pendiente', '', id_cliente
    FROM clientes
    WHERE cuit = '30-68312345-4';

    WITH ch(numero, cuit, banco, fecha_emision, fecha_pago, importe, estado, endosado) AS (VALUES
      ('00412087', '30-71239845-9', 'Banco Santander', '2026-08-28', '2026-09-28', 185000.00, 'Cobrado',   ''),
      ('55210934', '30-65498712-3', 'Banco Nación',    '2026-09-01', '2026-10-01', 120000.00, 'Cobrado',   ''),
      ('77340218', '30-90000041-9', 'Banco Provincia', '2026-09-05', '2026-10-05', 310500.00, 'Cobrado',   'Proveedor Cubiertas SA'),
      ('00418855', '30-90000052-5', 'Banco Macro',     '2026-09-20', '2026-10-20',  96500.50, 'Rechazado', ''),
      ('88120045', '30-90000063-0', 'Banco Galicia',   '2026-10-02', '2026-11-02', 142000.00, 'Cobrado',   ''),
      ('66103377', '30-68312345-4', 'Banco ICBC',      '2026-10-10', '2026-11-10', 210000.00, 'Cobrado',   'Lubricantes del Centro SRL'),
      ('00419302', '30-71239845-9', 'Banco Credicoop', '2026-10-25', '2026-11-25', 240000.00, 'Pendiente', ''),
      ('99215566', '30-90000041-9', 'Banco BBVA',      '2026-11-02', '2026-12-02', 275000.00, 'Pendiente', 'Proveedor Cubiertas SA'),
      ('31405188', '30-65498712-3', 'Banco Santander', '2026-11-05', '2026-11-18',  88000.00, 'Pendiente', ''),
      ('00420011', '30-90000052-5', 'Banco Provincia', '2026-11-09', '2026-12-09', 130000.00, 'Pendiente', '')
    )
    INSERT INTO cheques (numero, cliente, banco, fecha_emision, fecha_pago, importe, estado, endosado, id_cliente)
    SELECT ch.numero, c.nom_cli, ch.banco, ch.fecha_emision, ch.fecha_pago, ch.importe, ch.estado, ch.endosado, c.id_cliente
    FROM ch
    JOIN clientes c ON c.cuit = ch.cuit
    ORDER BY ch.fecha_emision;

    -- 7. GOMEROS: ausencias y movimientos de la semana
    INSERT INTO ausencias_gomeros (gomero_id, fecha) VALUES
      (1, '2026-11-03'),
      (2, '2026-11-10'),
      (4, '2026-11-12');

    INSERT INTO movimientos_gomeros (id_gomero, tipo, fecha, importe, destino, concepto, usuario)
    SELECT id_gomero, 'PAGO_SEMANAL', '2026-11-07', sueldo_semanal, 'SUELDO', 'Pago semanal', 'admin'
    FROM gomeros;

    INSERT INTO movimientos_gomeros (id_gomero, tipo, fecha, importe, destino, concepto, usuario) VALUES
      (1, 'ADELANTO', '2026-11-10', 40000, 'SUELDO', 'Adelanto', 'admin'),
      (3, 'ADELANTO', '2026-11-11', 30000, 'SUELDO', 'Adelanto', 'admin'),
      (5, 'ADELANTO', '2026-11-12', 50000, 'SUELDO', 'Adelanto', 'admin'),
      (2, 'ADELANTO', '2026-11-13', 20000, 'SUELDO', 'Adelanto', 'admin');

    INSERT INTO movimientos_gomeros (id_gomero, tipo, fecha, importe, destino, concepto, usuario) VALUES
      (NULL, 'GASTO_GENERAL', '2026-11-11', 25000, 'NO_APLICA', 'Comida de la semana',  'admin'),
      (NULL, 'GASTO_GENERAL', '2026-11-13', 18000, 'NO_APLICA', 'Gaseosas y consumos', 'admin');
    """
    conexion.executescript(sql_demo)


def sembrar_datos_prueba(incluir_demo=True):
    """Inserta datos de prueba iniciales si la base de datos está vacía."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        # Verificar si ya existen clientes cargados
        cursor.execute("SELECT COUNT(*) FROM clientes")
        if cursor.fetchone()[0] > 0:
            print(
                "[INFO] La base de datos ya contiene registros. No se duplican datos semilla."
            )
            return

        print("Cargando datos semilla iniciales...")

        # 1. Clientes iniciales
        clientes_iniciales = [
            ("Toyota", "30-68312345-4", "011-4567-8900", "flota@toyota.com.ar", 1, 1),
            (
                "Transporte Gomez",
                "30-71239845-9",
                "03487-421122",
                "taller@gomeztrans.com",
                1,
                2,
            ),
            (
                "Logística Norte",
                "30-65498712-3",
                "011-4789-3322",
                "administracion@lognorte.com",
                0,
                1,
            ),
        ]
        cursor.executemany(
            """
            INSERT INTO clientes (nom_cli, cuit, tel, mail, con_iva, lista_precios)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            clientes_iniciales,
        )

        id_toyota = 1
        id_gomez = 2

        # 2. Vehículos
        cursor.execute(
            "INSERT INTO vehiculos (patente, id_cliente) VALUES (?, ?)",
            ("ABC123", id_toyota),
        )
        id_veh1 = cursor.lastrowid
        cursor.execute(
            "INSERT INTO vehiculos (patente, id_cliente) VALUES (?, ?)",
            ("AF123JK", id_toyota),
        )
        cursor.execute(
            "INSERT INTO vehiculos (patente, id_cliente) VALUES (?, ?)",
            ("AE987ZA", id_gomez),
        )

        # 3. Tareas con las 3 listas de precios
        tareas_iniciales = [
            ("Cambio de cubierta", 60000.0, 54000.0, 48000.0, 1),
            ("Pinchadura", 10000.0, 9000.0, 8000.0, 1),
            ("Alineación y balanceo", 35000.0, 31500.0, 28000.0, 1),
            ("Válvula nueva", 5000.0, 4500.0, 4000.0, 1),
            ("Rotación de neumáticos", 15000.0, 13500.0, 12000.0, 1),
        ]
        cursor.executemany(
            """
            INSERT INTO tareas (nom_tar, precio, precio2, precio3, activa)
            VALUES (?, ?, ?, ?, ?)
        """,
            tareas_iniciales,
        )

        # 4. Trabajos / Remitos iniciales
        cursor.execute(
            """
            INSERT INTO trabajos (remito, fecha, id_cliente, id_vehiculo, total, estado, tipo, con_iva)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            ("20213", "2026-08-20", id_toyota, id_veh1, 60000.0, "PENDIENTE", "OI", 1),
        )
        id_trabajo1 = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO detalle_trabajos (id_trabajo, id_tarea, cantidad, precio_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """,
            (id_trabajo1, 1, 1, 60000.0, 60000.0),
        )

        cursor.execute(
            """
            INSERT INTO trabajos (remito, fecha, id_cliente, id_vehiculo, total, estado, tipo, con_iva)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            ("20412", "2026-08-21", id_toyota, id_veh1, 20000.0, "PENDIENTE", "OI", 1),
        )
        id_trabajo2 = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO detalle_trabajos (id_trabajo, id_tarea, cantidad, precio_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """,
            (id_trabajo2, 2, 2, 10000.0, 20000.0),
        )

        # 5. Cheque de ejemplo
        cursor.execute(
            """
            INSERT INTO cheques (
                numero, cliente, banco, fecha_emision, fecha_pago, importe, estado, endosado, id_cliente
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "CH-00098231",
                "Toyota",
                "Banco Galicia",
                "2026-08-25",
                "2026-09-25",
                80000.0,
                "Pendiente",
                "",
                id_toyota,
            ),
        )

        # 6. Usuarios iniciales con contraseñas hasheadas
        from werkzeug.security import generate_password_hash

        cursor.execute(
            """
            INSERT INTO usuarios (usuario, contraseña, rol)
            VALUES (?, ?, ?)
        """,
            ("admin", generate_password_hash("admin123"), "admin"),
        )
        cursor.execute(
            """
            INSERT INTO usuarios (usuario, contraseña, rol)
            VALUES (?, ?, ?)
        """,
            ("operador", generate_password_hash("operador123"), "usuario"),
        )

        # 7. Cargar extensión de demostración
        if incluir_demo:
            cargar_datos_demo(conexion)

        conexion.commit()

        # Reporte final dinámico
        totales = {
            t: conexion.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ["clientes", "tareas", "vehiculos", "trabajos", "cheques"]
        }
        print("[OK] Datos cargados con exito:")
        print(f"  - {totales['clientes']} Empresas")
        print(f"  - {totales['tareas']} Tareas con 3 listas de precios")
        print(f"  - {totales['vehiculos']} Vehículos registrados")
        print(f"  - {totales['trabajos']} Trabajos / Remitos")
        print(f"  - {totales['cheques']} Cheques registrados")
        print("  - Usuarios ('admin' / 'admin123' y 'operador' / 'operador123')")
    finally:
        conexion.close()


if __name__ == "__main__":
    print("=== Inicializando Base de Datos 'Gomeria El Puente' ===")
    crear_tablas()
    sembrar_datos_prueba(incluir_demo=True)
    print("=== Listo para operar ===")