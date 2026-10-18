"""
Script de Inicialización de la Base de Datos para 'Gomería El Puente'.

Crea la estructura relacional completa con todas las restricciones de integridad
(PRIMARY KEY, FOREIGN KEY, CHECK, UNIQUE) e inserta datos semilla iniciales
coherentes con el funcionamiento actual del sistema (múltiples listas de precios,
condición de IVA, remitos OI/OIB, cheques y usuarios).
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
        lista_precios INTEGER NOT NULL DEFAULT 1 CHECK (lista_precios IN (1, 2, 3))
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

    -- 6. Cheques recibidos de clientes
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

    -- 7. Usuarios del sistema
    CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL UNIQUE,
        contraseña TEXT NOT NULL,
        rol TEXT NOT NULL DEFAULT 'usuario' CHECK (rol IN ('usuario', 'admin'))
    );
    """
    conexion = obtener_conexion()
    try:
        conexion.executescript(ddl_script)
        conexion.commit()
        print(f"[OK] Estructura de tablas creada con exito en: {get_db_path()}")
    finally:
        conexion.close()


def sembrar_datos_prueba():
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

        # 6. Usuarios iniciales con contraseñas hasheadas (seguridad criptográfica)
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

        conexion.commit()
        print("[OK] Datos semilla cargados con exito:")
        print("  - 3 Empresas (Toyota, Transporte Gomez, Logistica Norte)")
        print("  - 5 Tareas con 3 listas de precios")
        print("  - 2 Trabajos registrados")
        print("  - 1 Cheque registrado")
        print("  - 1 Usuario admin ('admin' / 'admin123')")
    finally:
        conexion.close()


if __name__ == "__main__":
    print("=== Inicializando Base de Datos 'Gomeria El Puente' ===")
    crear_tablas()
    sembrar_datos_prueba()
    print("=== Listo para operar ===")
