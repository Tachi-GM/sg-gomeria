"""
Unifica las bases sueltas en UNA sola sg_gomeria.db lista para la presentación.

Qué hace:
  1. Crea una base nueva con la MISMA estructura que database/init_db.py (main).
  2. Copia los usuarios y las tareas reales (sin las primeras 5, que eran de prueba)
     desde la sg_gomeria.db vieja.
  3. Copia los clientes y sus alias desde sg_gomeria2.db.
  4. Deja VACÍO todo lo demás (remitos, cheques, vehículos, movimientos, etc.).
  5. Hace un backup de la base actual y recién ahí reemplaza sg_gomeria.db.

Uso (desde la carpeta del proyecto, con el servidor Flask APAGADO):
    python unificar_base.py
    python unificar_base.py --forzar     # solo si querés rehacer aunque ya haya remitos
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_FINAL = BASE / "sg_gomeria.db"
DB_NUEVA = BASE / "sg_gomeria_nueva.db"  # base temporal: se arma acá y recién después reemplaza
CARPETA_PRIVADA = BASE / "datos_privados"
DB_ORIGEN = CARPETA_PRIVADA / "sg_gomeria_origen.db"  # copia intacta de la sg_gomeria.db vieja
CARPETA_BACKUPS = BASE / "backups"

# Dónde buscar la base de clientes (la primera que exista)
CANDIDATOS_CLIENTES = [CARPETA_PRIVADA / "sg_gomeria2.db", BASE / "sg_gomeria2.db"]

# Las tareas con id <= a este número las creaste vos de prueba: se descartan.
ULTIMA_TAREA_DE_PRUEBA = 5

# CUIT de las empresas que se cobran SIN IVA (se les descuenta el 21%).
# En la base vieja ninguna estaba marcada. Completá esta lista con las que falten.
CUITS_SIN_IVA = {
    "30-70848889-1",  # Transporte Ibarra Hnos. S.A.
}

# Gomeros iniciales: son los mismos que siembra database/init_db.py en main.
GOMEROS_INICIALES = [
    ("Sebastián", 300000),
    ("Lucas", 300000),
    ("Marcelo", 350000),
    ("Braian", 300000),
    ("Javier", 400000),
]

# Estructura idéntica a database/init_db.py (main). Lo único agregado:
#  - clientes: columnas extra que venían de sg_gomeria2.db (dirección, contacto, etc.)
#  - alias_clientes: la usa el script de importación de remitos para reconocer nombres.
DDL = """
CREATE TABLE clientes (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_cli TEXT NOT NULL,
    cuit TEXT UNIQUE,
    tel TEXT,
    mail TEXT,
    con_iva INTEGER NOT NULL DEFAULT 1,
    lista_precios INTEGER NOT NULL DEFAULT 1 CHECK (lista_precios IN (1, 2, 3)),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    -- extras que vienen de sg_gomeria2.db
    codigo TEXT,
    direccion TEXT,
    localidad TEXT,
    condicion_iva TEXT,
    tipo_factura TEXT,
    contacto TEXT,
    tipo_remito TEXT NOT NULL DEFAULT 'OI'
);

CREATE TABLE alias_clientes (
    alias TEXT PRIMARY KEY,
    id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente)
);

CREATE TABLE vehiculos (
    id_vehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
    patente TEXT NOT NULL UNIQUE,
    id_cliente INTEGER NOT NULL,
    FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente) ON DELETE CASCADE
);

CREATE TABLE tareas (
    id_tarea INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_tar TEXT NOT NULL UNIQUE,
    precio REAL NOT NULL CHECK (precio >= 0),
    precio2 REAL DEFAULT 0 CHECK (precio2 >= 0),
    precio3 REAL DEFAULT 0 CHECK (precio3 >= 0),
    activa INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1))
);

CREATE TABLE trabajos (
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
    cliente_alias TEXT,                      -- nombre con el que figura en el Excel (alias)
    con_iva INTEGER NOT NULL DEFAULT 1 CHECK (con_iva IN (0, 1)),
    FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente) ON DELETE RESTRICT,
    FOREIGN KEY (id_vehiculo) REFERENCES vehiculos (id_vehiculo) ON DELETE SET NULL
);

CREATE TABLE detalle_trabajos (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_trabajo INTEGER NOT NULL,
    id_tarea INTEGER NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
    subtotal REAL NOT NULL CHECK (subtotal >= 0),
    FOREIGN KEY (id_trabajo) REFERENCES trabajos (id_trabajo) ON DELETE CASCADE,
    FOREIGN KEY (id_tarea) REFERENCES tareas (id_tarea) ON DELETE RESTRICT
);

CREATE TABLE detalle_temporal_trabajos (
    id_detalle_temporal INTEGER PRIMARY KEY AUTOINCREMENT,
    id_trabajo INTEGER NOT NULL,
    nombre_tarea TEXT NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
    subtotal REAL NOT NULL CHECK (subtotal >= 0),
    FOREIGN KEY (id_trabajo) REFERENCES trabajos (id_trabajo) ON DELETE CASCADE
);

CREATE TABLE cheques (
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

CREATE TABLE usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL UNIQUE,
    contraseña TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'usuario' CHECK (rol IN ('usuario', 'admin'))
);

CREATE TABLE gomeros (
    id_gomero INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL COLLATE NOCASE UNIQUE,
    sueldo_semanal INTEGER NOT NULL DEFAULT 260000 CHECK (sueldo_semanal > 0),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE movimientos_gomeros (
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
CREATE INDEX idx_movimientos_gomeros_fecha ON movimientos_gomeros(fecha);
CREATE INDEX idx_movimientos_gomeros_gomero_fecha ON movimientos_gomeros(id_gomero, fecha);

CREATE TABLE ausencias_gomeros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gomero_id INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gomero_id) REFERENCES gomeros(id_gomero) ON DELETE RESTRICT,
    UNIQUE (gomero_id, fecha)
);
CREATE INDEX idx_ausencias_gomeros_gomero_fecha ON ausencias_gomeros(gomero_id, fecha);

CREATE TABLE proveedores (
    id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL COLLATE NOCASE UNIQUE,
    cuit TEXT,
    telefono TEXT,
    contacto TEXT,
    rubro TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cuentas_proveedores (
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
CREATE INDEX idx_cuentas_proveedores_proveedor_fecha ON cuentas_proveedores(id_proveedor, fecha);
"""

# Tablas que deben quedar vacías
TABLAS_VACIAS = [
    "vehiculos",
    "trabajos",
    "detalle_trabajos",
    "detalle_temporal_trabajos",
    "cheques",
    "movimientos_gomeros",
    "ausencias_gomeros",
    "proveedores",
    "cuentas_proveedores",
]


def abortar(mensaje):
    print(f"\n[ERROR] {mensaje}")
    sys.exit(1)


def tablas_de(ruta):
    con = sqlite3.connect(ruta)
    try:
        return {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()


def preparar_origen(forzar):
    """Deja una copia intacta de la sg_gomeria.db vieja, para poder re-ejecutar sin riesgo."""
    if DB_ORIGEN.exists():
        # Si ya se unificó antes y la base actual ya tiene remitos, no pisarla por accidente.
        if DB_FINAL.exists() and "alias_clientes" in tablas_de(DB_FINAL):
            con = sqlite3.connect(DB_FINAL)
            try:
                remitos = con.execute("SELECT COUNT(*) FROM trabajos").fetchone()[0]
            finally:
                con.close()
            if remitos > 0 and not forzar:
                abortar(
                    f"La base actual ya tiene {remitos} remitos cargados. Si la rehacés se pierden.\n"
                    "        Si de verdad querés rehacerla, ejecutá: python unificar_base.py --forzar"
                )
        return

    if not DB_FINAL.exists():
        abortar(f"No encuentro la base vieja: {DB_FINAL}")
    if "alias_clientes" in tablas_de(DB_FINAL):
        abortar("sg_gomeria.db ya parece estar unificada y no hay copia de origen. Revisá los archivos.")

    CARPETA_PRIVADA.mkdir(exist_ok=True)
    shutil.copy2(DB_FINAL, DB_ORIGEN)
    print(f"[OK] Copia de la base vieja guardada en: {DB_ORIGEN}")


def ubicar_base_clientes():
    for ruta in CANDIDATOS_CLIENTES:
        if ruta.exists():
            return ruta
    abortar("No encuentro sg_gomeria2.db (busqué en datos_privados/ y en la carpeta del proyecto).")


def construir_base_nueva(ruta_clientes):
    if DB_NUEVA.exists():
        DB_NUEVA.unlink()

    nueva = sqlite3.connect(DB_NUEVA)
    nueva.execute("PRAGMA foreign_keys = ON")
    try:
        nueva.executescript(DDL)

        # --- Usuarios (con sus contraseñas ya hasheadas) y tareas desde la base vieja ---
        origen = sqlite3.connect(DB_ORIGEN)
        try:
            usuarios = origen.execute(
                "SELECT usuario, contraseña, rol FROM usuarios ORDER BY id_usuario"
            ).fetchall()
            tareas = origen.execute(
                """SELECT nom_tar, precio, precio2, precio3, activa
                   FROM tareas WHERE id_tarea > ? ORDER BY id_tarea""",
                (ULTIMA_TAREA_DE_PRUEBA,),
            ).fetchall()
        finally:
            origen.close()

        nueva.executemany("INSERT INTO usuarios (usuario, contraseña, rol) VALUES (?, ?, ?)", usuarios)
        # Sin id explícito: los ids se renumeran de 1 en adelante, sin huecos.
        nueva.executemany(
            "INSERT INTO tareas (nom_tar, precio, precio2, precio3, activa) VALUES (?, ?, ?, ?, ?)",
            tareas,
        )

        # --- Clientes y alias desde sg_gomeria2.db ---
        cli = sqlite3.connect(ruta_clientes)
        try:
            clientes = cli.execute(
                """SELECT id_cliente, nom_cli, cuit, tel, mail, sin_iva, codigo, direccion,
                          localidad, condicion_iva, tipo_factura, contacto, tipo_remito
                   FROM clientes ORDER BY id_cliente"""
            ).fetchall()
            alias = cli.execute("SELECT alias, id_cliente FROM alias_clientes").fetchall()
        finally:
            cli.close()

        filas = []
        for (idc, nom, cuit, tel, mail, sin_iva, cod, dire, loc, cond, tfac, cont, trem) in clientes:
            con_iva = 0 if (sin_iva or cuit in CUITS_SIN_IVA) else 1
            # Se conserva el id original para que los alias sigan apuntando al cliente correcto.
            filas.append((idc, nom, cuit, tel, mail, con_iva, cod, dire, loc, cond, tfac, cont, trem or "OI"))
        nueva.executemany(
            """INSERT INTO clientes (id_cliente, nom_cli, cuit, tel, mail, con_iva, codigo, direccion,
                                     localidad, condicion_iva, tipo_factura, contacto, tipo_remito)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filas,
        )
        nueva.executemany("INSERT INTO alias_clientes (alias, id_cliente) VALUES (?, ?)", alias)

        # --- Gomeros (personal fijo) ---
        nueva.executemany(
            "INSERT INTO gomeros (nombre, sueldo_semanal) VALUES (?, ?)", GOMEROS_INICIALES
        )

        nueva.commit()
    except Exception:
        nueva.rollback()
        nueva.close()
        DB_NUEVA.unlink(missing_ok=True)
        raise
    nueva.close()


def verificar():
    """Revisa que la base nueva esté sana y que los conteos sean los esperados."""
    con = sqlite3.connect(DB_NUEVA)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            abortar("La base nueva no pasó el chequeo de integridad.")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            abortar("La base nueva tiene claves foráneas rotas.")

        cuenta = lambda t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in TABLAS_VACIAS:
            if cuenta(t) != 0:
                abortar(f"La tabla {t} debería estar vacía y tiene {cuenta(t)} filas.")

        resumen = {
            "clientes": cuenta("clientes"),
            "alias_clientes": cuenta("alias_clientes"),
            "tareas": cuenta("tareas"),
            "usuarios": cuenta("usuarios"),
            "gomeros": cuenta("gomeros"),
            "clientes sin IVA": con.execute("SELECT COUNT(*) FROM clientes WHERE con_iva = 0").fetchone()[0],
        }
        return resumen
    finally:
        con.close()


def reemplazar_base():
    """Backup de la base actual y reemplazo por la nueva."""
    CARPETA_BACKUPS.mkdir(exist_ok=True)
    if DB_FINAL.exists():
        copia = CARPETA_BACKUPS / f"antes_unificar_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
        shutil.copy2(DB_FINAL, copia)
        print(f"[OK] Backup de la base anterior: {copia}")
    try:
        DB_NUEVA.replace(DB_FINAL)  # reemplazo atómico: o queda la vieja o queda la nueva
    except PermissionError:
        abortar("No se pudo reemplazar sg_gomeria.db: cerrá el servidor Flask (iniciar.bat) y reintentá.")


def main():
    parser = argparse.ArgumentParser(description="Unifica las bases de Gomería El Puente.")
    parser.add_argument("--forzar", action="store_true", help="Rehacer aunque ya haya remitos cargados")
    args = parser.parse_args()

    print("=== Unificando bases de 'Gomería El Puente' ===")
    ruta_clientes = ubicar_base_clientes()
    print(f"[INFO] Clientes y alias desde: {ruta_clientes}")

    preparar_origen(args.forzar)
    construir_base_nueva(ruta_clientes)
    resumen = verificar()
    reemplazar_base()

    print("\n[OK] Base unificada en:", DB_FINAL)
    for nombre, valor in resumen.items():
        print(f"   - {nombre}: {valor}")
    print("   - remitos, cheques, vehículos, movimientos y proveedores: vacíos")
    print("=== Listo: ahora podés ejecutar el script de importación de remitos ===")


if __name__ == "__main__":
    main()