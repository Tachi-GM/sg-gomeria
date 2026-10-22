# CONTEXT.md — Estado actual del proyecto SG Gomería
> **Leer este archivo al iniciar cada sesión** para conocer el estado real del proyecto sin necesidad de que el usuario lo explique.
> Última actualización: 2026-10-22

---

## Descripción general

Aplicación web local de gestión para **Gomería "El Puente"**, orientada a flotas corporativas.
Proyecto académico de Programación 4 (UTN) con código de nivel productivo.

- **URL local:** `http://127.0.0.1:5000`
- **Repo:** `https://github.com/Tachi-GM/sg-gomeria` (rama `main`)
- **Lanzador:** `iniciar.bat` (autodetecta entorno virtual y levanta el servidor)

---

## Stack real en uso

| Capa | Tecnología |
|---|---|
| Backend | Python 3.10+ · Flask 3.1 con Blueprints |
| Base de datos | SQLite 3 (`sg_gomeria.db`) con FK activadas |
| Frontend | HTML5 · Jinja2 · Bootstrap 5.3 |
| JS | ES6 con `fetch` (sin frameworks) |
| Config | `python-dotenv` (`.env` en raíz) |
| Calidad | `flake8` + `black` · `unittest` + `coverage` |

---

## Estructura de carpetas (estado actual)

```
SG - Gomería/
├── app.py                      # Punto de entrada, registro de Blueprints, logging
├── AGENTS.md                   # Reglas de comportamiento del agente IA
├── CONTEXT.md                  # Este archivo — contexto dinámico del proyecto
├── iniciar.bat                 # Lanzador automático con venv
├── requirements.txt
├── .env                        # Variables de entorno (NO commitear)
├── sg_gomeria.db               # Base de datos activa (NO commitear)
│
├── routes/                     # Blueprints — controladores HTTP (sin lógica de negocio)
│   ├── auth.py                 # Login / Logout · decorador @login_requerido
│   ├── cheques.py              # CRUD de cheques (endpoints REST + JSON)
│   ├── clientes.py             # ABM clientes, historial, exportación
│   ├── general.py              # Home, backup, modo milagritos, acerca-de
│   └── trabajos.py             # Mataburros, envío de remito, actualización de estado
│
├── services/
│   └── trabajos_service.py     # Lógica de negocio: crear_trabajo_completo(), editar_cabecera_remito()
│
├── utils/
│   ├── seguridad.py            # login_requerido, solo_admin, registrar_auditoria, modo_activo
│   └── formateadores.py        # parse_int_seguro, parse_float_seguro, validar_y_formatear_remito
│
├── database/
│   ├── connection.py           # obtener_conexion(), get_db_path()
│   └── init_db.py              # DDL completo + datos semilla
│
├── templates/
│   ├── base/
│   │   └── base.html           # Plantilla base con herencia Jinja2 (ya implementada)
│   ├── componentes/
│   │   └── tabla_remitos.html  # Componente reutilizable de tabla de remitos
│   ├── index.html
│   ├── login.html
│   ├── mataburros.html
│   ├── clientes.html
│   ├── historial-cliente.html
│   ├── cheques.html
│   ├── precios.html
│   ├── pagos.html
│   ├── salir.html
│   ├── acerca-de.html
│   └── error.html
│
├── static/
│   ├── css/
│   │   ├── estilos.css         # Paleta principal + Modo Milagritos
│   │   └── cheques.css         # Estilos específicos del módulo de cheques
│   └── js/
│       ├── mataburros.js       # Cálculo de totales, selector de tareas
│       ├── clientes.js         # Filtros y ordenamiento de tabla
│       ├── cheques.js          # CRUD de cheques vía fetch
│       └── precios.js          # Gestión de lista de precios
│
├── tests/
│   ├── __init__.py
│   ├── test_rutas.py           # Tests de integración de rutas y autenticación
│   └── test_trabajos_service.py # Tests unitarios del servicio de trabajos
│
└── backups/                    # Copias de seguridad .db (NO commitear)
```

---

## Base de datos — Tablas activas

| Tabla | Descripción | Campos clave |
|---|---|---|
| `clientes` | Empresas de flota | `con_iva` (0/1), `lista_precios` (1/2/3) |
| `tareas` | Catálogo de servicios | `precio`, `precio2`, `precio3`, `activa` |
| `trabajos` | Cabecera de remitos | `tipo` (OI/OIB), `detalle`, `foto_remito`, `con_iva` |
| `detalle_trabajos` | Renglones de cada remito | `precio_unitario`, `subtotal` |
| `cheques` | E-checks recibidos | `numero`, `banco`, `endosado`, `estado`, `id_cliente` |
| `usuarios` | Acceso al sistema | `usuario`, `contraseña` (hash), `rol` (usuario/admin) |
| `vehiculos` | Vehículos por cliente | `patente`, `id_cliente` |

---

## Funcionalidades implementadas (✅ Listo)

- **Login/Logout** con sesión Flask, roles `usuario` y `admin`, hash de contraseñas (werkzeug).
- **Decoradores de seguridad:** `@login_requerido` y `@solo_admin` en todas las rutas protegidas.
- **Sistema de auditoría:** `registrar_auditoria()` loguea acciones clave con usuario y rol.
- **Mataburros (Nuevo Remito):** formulario completo con selección de cliente, tipo OI/OIB, lista de precios (L1/L2/L3), campo de detalle/observaciones, fecha manual y cálculo automático de totales.
- **Lógica de IVA por cliente:** si `con_iva = 0`, el servicio descuenta el 21% a cada renglón automáticamente.
- **Tipos de remito OI y OIB:** validación y formato automático (`XXXXX` para OI, `00XXXX` para OIB), numeración separada.
- **Edición de cabecera de remito:** modal para modificar tipo, número y fecha de un remito ya guardado.
- **Estado de remitos:** checkbox en la tabla general para marcar como PENDIENTE / EN PROCESO / PAGADO.
- **Gestión de clientes:** alta con CUIT, teléfono, email, condición de IVA y lista de precios asignada. Buscador en tiempo real.
- **Historial por cliente:** pestañas por mes/año, total del período, desglose por tarea.
- **Módulo de Cheques:** CRUD completo persistido en SQLite (número, banco, cliente, endosado, fecha de emisión, fecha de cobro, importe, estado).
- **Lista de precios:** vista y gestión de las 3 listas por tarea. Campo `activa` para activar/desactivar servicios.
- **Herencia de plantillas Jinja2:** `base.html` implementado, los templates extienden de él.
- **Componente `tabla_remitos.html`:** reutilizable en clientes e historial.
- **Backup en un clic:** descarga del archivo `.db` con timestamp.
- **Modo Milagritos 🧚:** tema visual rosa, toggle persistido en sesión.
- **Tests automatizados:** `test_rutas.py` (integración) y `test_trabajos_service.py` (unitarios). Cobertura ~91%.
- **Importador de clientes:** `importar_clientes.py` para migración masiva desde Excel.

---

## Pendiente / Por hacer

> Esta lista se actualiza a medida que se completan ítems. Orden aproximado de prioridad.

### Alta prioridad
- [ ] **Hosting:** investigar cómo desplegar la app (PythonAnywhere, Railway, VPS). Actualmente solo corre local.
- [ ] **Foto de remito:** columna `foto_remito` ya existe en la tabla `trabajos`, pero falta el formulario de carga y la vista.
- [ ] **Exportación mensual a Excel/imagen** desde `historial-cliente`.
- [ ] **Personalización de empresa:** datos propios en pantalla de inicio o en los comprobantes (nombre, dirección, CUIT del local).
- [ ] **Desglose de IVA en pantalla:** mostrar subtotal + IVA + total final al estilo factura en el remito.

### Media prioridad
- [ ] **Cheques: vincular estado a remitos** — mostrar en cheques si el remito asociado está pago o pendiente.
- [ ] **Opción para no guardar tarea nueva** — checkbox de confirmación antes de persistir una tarea agregada desde el remito.
- [ ] **Pagos:** la tabla `pagos` existe en la base pero no tiene pantallas ni rutas (`pagos.html` está creado pero vacío).
- [ ] **Edición y eliminación de clientes** — actualmente solo se pueden dar de alta.
- [ ] **Validación de CUIT duplicado** en tiempo real al dar de alta un cliente.

### Baja prioridad / Ideas futuras
- [ ] **Generación de comprobante PDF** imprimible o para WhatsApp.
- [ ] **Configuración de `.env` en producción** — `SECRET_KEY` robusta, `DEBUG=False`.
- [ ] **Migraciones automáticas de esquema** — script para actualizar la DB sin perder datos.
- [ ] **Variables de entorno completas** — mover parámetros de conexión al `.env`.

---

## Commits recientes (referencia)

```
f24067f fix: quitar espacios sobrantes en content de options de tarea en mataburros
e4bc244 fix: ajustar tamaño de formulario en mataburros.html
884c0b5 feat: checkbox de pago en tabla remitos, endpoint actualizar-estado y fix layout mataburros
f76eaa1 docs: actualizar README con fecha manual, estandarizacion OI/OIB/CUIT, edicion modal y 35 tests
27f55b7 feat: fecha manual en remitos, vinculacion automatica cliente-lista, estandarizacion OI/OIB/CUIT y edicion modal
1d9cfbf feat: capa de servicios de trabajos, IVA por tarea, cheques con id_cliente NOT NULL y cobertura al 91%
c703c3c refactor: modularizar rutas en blueprints y utilidades de seguridad
6aa6b55 feat: login con roles, auditoria, blindaje de errores, documentacion y suite de pruebas
```

---

## Notas de desarrollo

- El `app.py` solo registra Blueprints y configura logging — **no contiene lógica de negocio**.
- La lógica de negocio va en `services/`, los controladores HTTP en `routes/`.
- Todas las consultas SQL usan parámetros (`?`), nunca concatenación.
- Toda operación compuesta usa `commit()` / `rollback()` explícito.
- Mensajes de interfaz, flash y logs siempre en **español**.
- Antes de tocar la base de datos en producción: generar backup primero.
