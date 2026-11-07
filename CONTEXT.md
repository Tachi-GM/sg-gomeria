# CONTEXT.md — Estado actual del proyecto SG Gomería
> **Leer este archivo al iniciar cada sesión** para conocer el estado real del proyecto.
> Última actualización: 2026-11-07 (sincronizado con el log de `main`, commit `436bdb6`).

Leyenda: `[x]` hecho · `[~]` parcial · `[ ]` pendiente · `[-]` descartado

---

## Descripción general

Aplicación web local de gestión para **Gomería "El Puente"**, orientada a flotas corporativas.
Proyecto académico de Programación 4 (UTN) con código de nivel productivo.
La usuaria final es la encargada de la gomería: la interfaz tiene que ser intuitiva y con lenguaje simple.

- **URL local:** `http://127.0.0.1:5000`
- **Repo:** `https://github.com/Tachi-GM/sg-gomeria` (rama `main`, público)
- **Lanzador:** `iniciar.bat` (autodetecta entorno virtual y levanta el servidor)
- **Hosting:** `[-]` descartado. Se usa en la PC de la gomería, en local.

---

## Stack real en uso

| Capa | Tecnología |
|---|---|
| Backend | Python 3.10+ · Flask 3.1 con Blueprints |
| Base de datos | SQLite 3 (`sg_gomeria.db`) con FK activadas |
| Frontend | HTML5 · Jinja2 (herencia de `templates/base/base.html`) · Bootstrap 5.3 |
| JS | ES6 con `fetch` · Choices.js 9.0.1 (combobox buscable) |
| Config | `python-dotenv` (`.env` en raíz) |
| Calidad | `flake8` + `black` · `unittest` + `coverage` |

---

## Estructura de carpetas (resumen)

```
SG - Gomería/
├── app.py                      # Blueprints, logging, manejadores de error
├── AGENTS.md · CONTEXT.md · README.md · MANUAL_DE_USUARIO.txt
├── iniciar.bat · requirements.txt · .env.example · .flake8 · .gitignore
├── importar_clientes.py        # Importador de clientes desde Excel
├── sg_gomeria.sqbpro           # Proyecto de DB Browser for SQLite
│
├── routes/
│   ├── auth.py                 # Login / Logout
│   ├── cheques.py              # Cartera de cheques
│   ├── clientes.py             # Clientes, historial, ABM, ocultar/reactivar
│   ├── general.py              # Inicio, salir, acerca-de, backup
│   ├── trabajos.py             # Mataburros, remitos, precios, estado
│   ├── exportaciones.py        # Exportación mensual Excel / PNG
│   └── ...                     # Gomeros (asistencia), fotos de remitos, usuarios
│
├── services/
│   ├── trabajos_service.py     # Emisión de remitos, IVA, edición
│   ├── exportaciones_service.py
│   ├── dashboard_service.py    # Métricas del inicio
│   └── gomeros_service.py      # Sueldos, ausencias
│
├── utils/
│   ├── seguridad.py · formateadores.py · exportadores.py
│
├── database/
│   ├── connection.py · init_db.py
│
├── templates/                  # base/, componentes/, y una vista por módulo
│   # Nota: gomeros.html cubre el módulo de gomeros. pagos.html está vacío y debe eliminarse.
│
├── static/css/ · static/js/ · static/logo.png
└── tests/ · backups/ (NO commitear)
```

---

## Base de datos — Tablas

| Tabla | Descripción | Campos clave |
|---|---|---|
| `clientes` | Empresas de flota | `cuit` (único), `tel`, `mail`, `con_iva`, `lista_precios` (1/2/3), oculto/activo |
| `tareas` | Catálogo de servicios | `precio`, `precio2`, `precio3`, `activa` (ocultar/reactivar) |
| `trabajos` | Cabecera de remitos | `remito` (único), `tipo` (OI/OIB), `fecha`, `total`, `detalle`, `estado`, `foto_remito`, `id_vehiculo` |
| `detalle_trabajos` | Renglones de cada remito | `cantidad`, `precio_unitario`, `subtotal` |
| `detalle_temporal_trabajos` | Tareas temporales (no van al tarifario) | `nombre_tarea`, `precio_unitario`, `subtotal` |
| `cheques` | E-checks | `numero`, `banco`, `cliente`, `id_cliente`, `endosado`, `estado` |
| `usuarios` | Acceso | `usuario`, `contraseña` (hash), `rol` (usuario/admin) |
| `vehiculos` | Vehículos por cliente | `patente`, `id_cliente` (se mantiene para trabajos particulares) |
| `ausencias_gomeros` | Días no trabajados de gomeros | `gomero_id`, `fecha`, `created_at` |

---

## Funcionalidades implementadas

### Acceso y seguridad
- [x] Login / Logout con sesión, hash de contraseñas (werkzeug) y roles `usuario` / `admin`.
- [x] Decoradores `@login_requerido` y `@solo_admin`.
- [x] Auditoría en `sistema.log` con usuario y rol.
- [x] Páginas de error 401 / 403 / 404 / 500.
- [x] Administración de usuarios (solo admin), con protección del último administrador.
- [x] Backup restaurable en ZIP (`sg_gomeria.db` + `fotos_remitos/`), solo admin.

### Remitos (Mataburros)
- [x] Formulario con tipo OI/OIB, número validado, fecha manual, cliente con combobox buscable, detalle libre.
- [x] Listas de precios L1 / L2 / L3 y tareas con +/- de cantidad. Total parcial en vivo.
- [x] **Desglose de IVA** (subtotal, IVA 21%, total) en `mataburros`, confirmado por Tachi.
- [x] IVA por cliente: si `con_iva = 0`, el servicio divide cada renglón por 1,21.
- [x] Número de remito único y validación de formato (`XXXXX` para OI, `00XXXX` para OIB).
- [x] Edición de cabecera de remito (tipo, número, fecha) con control de duplicados.
- [x] **Tareas temporales:** se usan en un remito sin guardarlas en el tarifario. Cubre el checkbox "guardar tarea nueva".
- [x] Foto del remito (JPG / PNG / GIF / WEBP, hasta 5 MB), con acceso protegido desde el detalle.

### Clientes e historial
- [x] Alta de empresa con CUIT validado (módulo 11 de AFIP).
- [x] **Validación de CUIT duplicado en tiempo real** (API separada).
- [x] **Edición de clientes** y **ocultar / reactivar empresas** en mostrador.
- [x] Buscador por nombre, CUIT o teléfono.
- [x] Historial general con filtro por mes, e historial por cliente con pestañas mensuales y totales.
- [x] Detalle de tareas por remito (fila expandible) y cambio de estado por `fetch`.
- [x] Exportación general por cliente a Excel (una pestaña por mes).
- [x] Exportación mensual a Excel o imagen PNG.

### Precios
- [x] Lista de precios con 3 columnas por tarea.
- [x] Alta de tareas desde el remito, con aviso si no se respeta L1 ≤ L2 ≤ L3.
- [x] Edición de tareas y precios desde `precios.html`.
- [x] **Ocultar / reactivar tareas** en la lista de precios.
- [x] Lista de precios por cliente (1/2/3) asignada. Falta actualizar los datos al migrar la base, a mano.

### Cheques
- [x] Cartera con alta, estado (Pendiente / Cobrado / Rechazado), endoso y cliente por `id_cliente`.
- [x] Resumen con cantidad, pendientes e importe pendiente.

### Gomeros
- [x] Módulo en `gomeros.html`: asistencia por día, registro de ausencias y descuento proporcional del sueldo semanal. Cubre lo que se había pensado como "pagos a gomeros".

### General
- [x] Inicio renovado con métricas reales (`dashboard_service`).
- [x] Pantallas "Acerca de" y "Salir".
- [x] Modo Milagritos 🧚 (tema rosa, persistido en sesión).
- [x] Manual de usuario en PDF, plan de capacitación y diagramas ER y de casos de uso.
- [x] Tests automatizados (`test_rutas.py`, `test_trabajos_service.py`).
- [x] Importador de clientes desde Excel (`importar_clientes.py`), con backup previo.
- [x] **Eliminar `templates/pagos.html`** (vacío, reemplazado por `gomeros.html`).

---

## Pendiente

### Alta prioridad
- [ ] **Migrar la base real.** Clientes ya migrados. Faltan **tareas** y **remitos**. La lista de precios por cliente se actualiza a mano durante la migración.
- [ ] **Personalización de la empresa:** nombre, dirección y CUIT del local en comprobantes.

### Media prioridad
- [ ] **Cheques: vincular estado con remitos** (mostrar si el remito asociado está pagado o pendiente).
- [ ] **Remitos con y sin IVA:** listado Factura A (sin descontar el 21%) y listado sin IVA (con el 21% descontado). Falta definir la fórmula con Tachi.
- [ ] **Eliminar clientes de verdad.** Hoy se pueden editar y ocultar, pero no borrar.
- [ ] **Confirmar ordenamiento de la tabla de remitos** por columnas. El README lo lista como hecho, pero `clientes.js` debe verificarse.

### Baja prioridad / Ideas futuras
- [ ] **Comprobante PDF** imprimible o para WhatsApp.
- [ ] **Migraciones de esquema versionadas.** Útil para la migración de la base real.
- [ ] **Variables de entorno completas** (ruta de la base y otros parámetros al `.env`).
- [ ] **Configuración de producción** (`SECRET_KEY` sin valor por defecto en el código, `FLASK_DEBUG=False`). **Postergada hasta migrar la base.**
- [ ] **Limpieza de archivos viejos** si quedan copias duplicadas en el repo.

---

## Bugs o puntos a revisar

- `templates/cheques.html` tiene `<body>` dentro de `{% block content %}`, lo que anida un `<body>` dentro de `base.html`. Hay que quitarlo.
- `historial_cliente` falla si se entra sin `id_cliente` o con un id inexistente. Conviene validarlo y devolver 404.
- **Documentación desincronizada:** el README dice 35 tests y el CONTEXT dice cobertura 91%. Revisar y dejar un solo dato. El README también muestra credenciales de demo en un repo público.

---

## Commits recientes (referencia)

```
436bdb6 feat: validacion en tiempo real de CUIT duplicado (API separada)
f09e4df feat: permitir ocultar y reactivar tareas en lista de precios
f01ca20 Merge branch 'feat/abm-completo-clientes' into main
82ce346 feat: permitir editar clientes y ocultar o reactivar empresas en mostrador
be7e322 Merge pull request #12 from Tachi-GM/generate_user_manual_pdf
99b162b docs: agregar manual pdf, plan de capacitacion, linea de tiempo y diagramas er/casos de uso
725fd6e feat: agregar exportacion general por cliente
66f315f feat: mejorar exportaciones y clientes
aacfba5 feat: agregar fotos de remitos
dca49b7 feat: agregar fotos de remitos y backup restaurable
cb0ebe0 Merge pull request #9 from Tachi-GM/tareas-temporales
d0624f1 feat: permitir tareas temporales en remitos
2993eb1 Merge pull request #8 from Tachi-GM/implementar-ausencias
e43c9ff feat: registrar ausencias de gomeros
2490928 Merge pull request #7 from Tachi-GM/tachi-gm-mejorar-pagina-inicio
```

---

## Notas de desarrollo

- `app.py` solo registra Blueprints, logging y manejadores de error. No contiene lógica de negocio.
- La lógica de negocio va en `services/`, los controladores HTTP en `routes/`.
- Todas las consultas SQL usan parámetros (`?`), nunca concatenación.
- Toda operación compuesta usa `commit()` / `rollback()` explícito.
- Mensajes de interfaz, flash y logs siempre en **español**.
- Antes de tocar la base de datos real: generar backup primero (`/backup` o copia manual de `sg_gomeria.db`).
- Cambios de estructura de la base: un único script SQL que sirva tanto para la base de prueba como para la real.