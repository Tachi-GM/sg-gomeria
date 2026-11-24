# Sistema de Gestión - Gomería "El Puente"

Aplicación web desarrollada para la administración integral de la operatoria diaria de un taller mecánico / gomería orientado a flotas corporativas. Incluye emisión de órdenes de trabajo y remitos (OI y OIB), gestión de clientes y condiciones impositivas, 3 listas de precios simultáneas, seguimiento de cheques y cálculo automático de IVA.

Proyecto desarrollado para la materia **Programación 4** de la **Tecnicatura Superior en Programación (UTN)**.

---

## Índice

- [Funcionalidades](#funcionalidades)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Variables de entorno](#variables-de-entorno)
- [Requisitos previos](#requisitos-previos)
- [Instalación y puesta en marcha](#instalación-y-puesta-en-marcha)
- [Ejecución de Pruebas Automáticas](#ejecución-de-pruebas-automáticas)
- [Arquitectura y Buenas Prácticas](#arquitectura-y-buenas-prácticas)

---

## Funcionalidades

- **Mataburros (Emisión de Remitos):**
  - Registro de órdenes de trabajo con soporte para comprobantes oficiales (**OI**) y adicionales (**OIB**).
  - Selector manual de fecha (por defecto la fecha del día actual, con soporte para registrar remitos pasados o diferidos).
  - Vinculación automática en tiempo real del cliente seleccionado con su lista de precios habitual (L1, L2, L3) y tipo de comprobante sugerido.
  - Estandarización y validación estricta: formato `XXXXX` (5 dígitos numéricos) para **OI** y `00XXXX` (`00` seguido de 4 dígitos) para **OIB**.
  - Selección múltiple de tareas con controles interactivos de incremento/decremento de cantidades (+ / -).
  - Tres listas de precios diferenciadas por política comercial (L1: Lista base / L2: Clientes frecuentes / L3: Pago diferido).
  - Cálculo automático de subtotales, recargo por IVA (21%) y total final del trabajo.
  - Tareas temporales: se cobran en un remito puntual sin incorporarlas al tarifario general.
  - **Vista imprimible** del remito (`/remito/<id>/imprimir`): comprobante formal en A4 con datos institucionales de la empresa, desglose de tareas, área de firmas y guardado directo como PDF desde el navegador.

- **Módulo de Clientes:**
  - Alta y consulta de empresas (Razón Social, CUIT con validación algorítmica de módulo 11 de AFIP, teléfono, email).
  - Asignación de condición impositiva (Con IVA / Sin IVA) y lista de precios habitual (1, 2 o 3).
  - Listado de clientes con buscador en tiempo real (nombre, CUIT o teléfono) y vista en tarjetas.
  - Edición de datos de la empresa y ocultar / reactivar clientes sin borrar su historial.
  - Validación de CUIT duplicado en tiempo real (API asíncrona `/clientes/validar-cuit`).
  - Historial detallado por empresa con navegación mensual por pestañas y totales acumulados.

- **Historial General y Remitos:**
  - Tabla interactiva de remitos con ordenamiento dinámico por columnas (fecha, número de remito, cliente, total y estado).
  - Edición rápida de remitos existentes vía modal interactivo (permite modificar fecha, tipo y número de comprobante con validación asíncrona y control de duplicados).
  - Despliegue en acordeón de los renglones de tareas realizadas por remito sin recargar la página.
  - Actualización del estado de cobro (`PENDIENTE`, `EN PROCESO`, `PAGADO`) mediante peticiones asíncronas (`fetch` POST).
  - Carga opcional de foto del remito (JPG, PNG, GIF o WEBP, hasta 5 MB) con acceso protegido desde el detalle.
  - Exportación general por cliente a Excel, con una pestaña por mes y cálculo de Importe, IVA, Total y Saldo según la condición de IVA.
  - Exportación mensual a imagen PNG, incluyendo tareas, totales, estado y miniaturas disponibles.

- **Módulo de Cheques:**
  - Registro y seguimiento de cartera de cheques recibidos de clientes (número, banco emisor, cliente asociado por `id_cliente`, fecha de emisión, fecha de cobro e importe).
  - Selector de cliente interactivo con búsqueda en tiempo real mediante **Choices.js** (mismo comportamiento de Mataburros).
  - Control de estados: `Pendiente`, `Cobrado`, `Rechazado` y sugerencias automáticas de endosos previos.
  - Listado relacional con `LEFT JOIN clientes` para reflejar siempre la razón social canónica.
  - Resumen de cartera con cantidad total, cheques pendientes e importe pendiente acumulado.

- **Módulo de Gomeros:**
  - Gestión de personal del taller: alta, edición y desactivación de gomeros.
  - Control semanal de asistencia: registro de ausencias con descuento proporcional automático sobre el sueldo semanal.
  - Registro de movimientos (adelantos, gastos, aguinaldo) por gomero y período, con historial y eliminación individual.
  - Saldos de aguinaldo acumulados por período.

- **Administración de Usuarios (solo admin):**
  - Alta, edición y eliminación de usuarios con protección del último administrador activo.
  - Contraseña mínima de 8 caracteres y cambio de rol en la misma pantalla.
  - Dos roles disponibles: `admin` (acceso total) y `usuario` (operador de mostrador).

- **Autenticación y Control de Acceso por Roles:**
  - Inicio y cierre de sesión seguro (`/login`, `/logout`) con contraseñas protegidas mediante hashing criptográfico con sal (`werkzeug.security`).
  - Decoradores `@login_requerido` y `@solo_admin` para proteger rutas contra accesos no autorizados.
  - Auditoría de eventos en `sistema.log` con usuario, rol y acción realizada.

- **Mantenimiento y Resguardo:**
  - Resguardo (`/backup`) exclusivo para administradores con timestamp en `backups/`, en formato ZIP restaurable: `sg_gomeria.db` y `fotos_remitos/...`.
  - Páginas de error personalizadas (`401`, `403`, `404` y `500`) con registro de eventos de auditoría en `sistema.log`.
  - Modo Milagritos 🧚 accesible vía sesión HTTP.
  - Scripts de importación masiva: clientes desde Excel (`scripts/importar_clientes.py`), precios desde Excel (`scripts/importar_precios.py`) y remitos (`scripts/importar_remitos.py`), todos con backup previo automático. Los precios también se pueden actualizar desde la pantalla **Precios** con el botón «Actualizar precios desde Excel» (cualquier usuario con sesión; pide confirmación y hace backup automático antes de cambiar nada).

---

## Tecnologías utilizadas

| Capa | Tecnología | Justificación |
|---|---|---|
| **Backend** | Python 3 + Flask 3.1 | Microframework ágil, modularizado con Blueprints. |
| **Base de Datos** | SQLite 3 | Motor relacional local, transaccional (ACID), con foreign keys activadas. |
| **Frontend** | HTML5 + Jinja2 | Herencia de plantillas modular (`base.html`), inyección global de contexto. |
| **Estilos** | CSS3 + Bootstrap 5.3 | Interfaz responsiva con componentes modernos y hojas CSS específicas. |
| **Interactividad** | JavaScript (ES6) | Asincronismo con `fetch`, manipulación del DOM y ordenamiento en cliente. |
| **Configuración** | `python-dotenv` | Separación estricta entre código fuente y variables de entorno (`.env`). |

---

## Estructura del proyecto

El proyecto implementa una arquitectura modular organizada en Blueprints y capas de soporte:

```
SG - Gomería/
│
├── app.py                      # Punto de entrada, configuración global y registro de Blueprints
├── iniciar.bat                 # Lanzador de un solo clic para Windows (inicia servidor y abre navegador)
├── requirements.txt            # Dependencias del proyecto
├── .env.example                # Plantilla de variables de entorno para desarrollo
├── .flake8                     # Configuración de auditoría de código PEP 8
├── .gitignore                  # Exclusión de archivos sensibles, logs, entornos y base de datos
├── README.md                   # Documentación técnica y guía de uso
│
├── config/                     # Configuración dinámica de la empresa (nombre, CUIT, dirección)
│   ├── empresa_loader.py       # Carga de datos institucionales desde la base de datos
│   └── empresa_ejemplo.py      # Plantilla de referencia con valores de ejemplo
│
├── routes/                     # Controladores modularizados (Blueprints de Flask)
│   ├── auth.py                 # Login, logout y control de sesión
│   ├── general.py              # Pantalla de inicio, acerca-de, salir y backups
│   ├── clientes.py             # Dashboard de empresas, historial, alta y edición de clientes
│   ├── clientes_api.py         # API JSON liviana: validación de CUIT en tiempo real
│   ├── trabajos.py             # Mataburros (emisión de remitos) y administración de precios
│   ├── exportaciones.py        # Descarga mensual de remitos en Excel e imagen
│   ├── cheques.py              # Cartera de cheques, cobros y cambios de estado
│   ├── gomeros.py              # Control semanal de asistencia, sueldos y adelantos
│   └── usuarios.py             # Administración de usuarios (solo admin)
│
├── utils/                      # Utilidades y funciones transversales
│   ├── seguridad.py            # Decoradores login_requerido, solo_admin y auditoría
│   ├── formateadores.py        # Validación CUIT, remitos OI/OIB, parse_int, parse_float
│   ├── exportadores.py         # Generación de archivos XLSX y PNG
│   └── fotos.py                # Gestión de carga y acceso protegido a fotos de remitos
│
├── services/                   # Capa de servicios y lógica de negocio desacoplada
│   ├── trabajos_service.py     # Emisión, cálculo de IVA, edición y persistencia de remitos
│   ├── exportaciones_service.py# Consulta y preparación de datos mensuales para exportar
│   ├── dashboard_service.py    # Métricas y estadísticas de la pantalla de inicio
│   └── gomeros_service.py      # Lógica de sueldos semanales, ausencias y aguinaldo
│
├── database/                   # Persistencia y base de datos
│   ├── connection.py           # Conexión centralizada a SQLite (FK ON, row_factory)
│   ├── init_db.py              # Script DDL de inicialización y datos semilla
│   └── datos_demo.sql          # Datos de demostración para evaluación
│
├── scripts/                    # Utilidades de importación y administración
│   ├── importar_clientes.py    # Importador masivo de clientes desde Excel (con backup previo)
│   ├── importar_precios.py     # Importador de tarifario desde Excel (con validación de IVA)
│   └── importar_remitos.py     # Importador de remitos históricos
│
├── templates/                  # Plantillas Jinja2
│   ├── base/
│   │   └── base.html           # Layout base compartido (Navbar, CDN Bootstrap, estilos)
│   ├── componentes/
│   │   └── tabla_remitos.html  # Componente reutilizable de tabla de remitos
│   ├── index.html              # Pantalla principal con métricas y accesos directos
│   ├── mataburros.html         # Formulario de carga de trabajos y cálculo de remitos
│   ├── clientes.html           # Dashboard de empresas y tabla de remitos interactiva
│   ├── historial-cliente.html  # Vista mensual consolidada por cliente
│   ├── precios.html            # Gestión y consulta de tarifas (L1, L2, L3)
│   ├── cheques.html            # Cartera y seguimiento de cheques
│   ├── gomeros.html            # Control semanal de asistencia y sueldos de gomeros
│   ├── usuarios.html           # Administración de usuarios del sistema
│   ├── remito_imprimible.html  # Vista formal del remito para imprimir o guardar como PDF
│   ├── acerca-de.html          # Información del sistema
│   ├── salir.html              # Pantalla de confirmación de salida
│   └── error.html              # Vista unificada de errores HTTP (401, 403, 404, 500)
│
├── static/                     # Recursos estáticos
│   ├── css/                    # Hojas de estilo (estilos.css, cheques.css)
│   ├── js/                     # Scripts del cliente (clientes.js, mataburros.js, cheques.js, gomeros.js)
│   └── logo.png                # Logo del taller
│
└── tests/                      # Suite de pruebas automatizadas (90 tests con unittest)
    ├── test_rutas.py           # Pruebas de integración: endpoints, seguridad y roles
    ├── test_trabajos_service.py# Pruebas unitarias: cálculo de tarifas, IVA y persistencia
    ├── test_clientes.py        # Pruebas de alta, edición y validación de clientes
    ├── test_clientes_ajax.py   # Pruebas de la API de validación de CUIT
    ├── test_exportaciones.py   # Pruebas de generación de archivos Excel y PNG
    ├── test_gomeros.py         # Pruebas del módulo de asistencia y sueldos
    ├── test_usuarios.py        # Pruebas de administración de usuarios
    └── support.py              # Utilidades compartidas de testing
```

---

## Variables de entorno

Se incluye un archivo `.env.example` de referencia con la configuración mínima:

| Variable | Descripción | Valor sugerido |
|---|---|---|
| `SECRET_KEY` | Clave criptográfica para firmas de sesión Flask | Cadena aleatoria segura en producción |
| `DATABASE_PATH` | Ruta al archivo de base de datos SQLite | `sg_gomeria.db` |
| `FLASK_DEBUG` | Modo depuración (`True` para desarrollo, `False` en producción) | `False` |

---

## Requisitos previos

- **Python 3.10 o superior** ([python.org](https://www.python.org/))
- **Git** ([git-scm.com](https://git-scm.com/))
- Navegador web moderno (Chrome, Edge, Firefox, Brave)

---

## Instalación y puesta en marcha

### 1. Clonar el repositorio
```bash
git clone https://github.com/Tachi-GM/sg-gomeria.git
cd "sg-gomeria"
```

### 2. Crear y activar el entorno virtual
En Windows (PowerShell / CMD):
```bash
python -m venv venv
venv\Scripts\activate
```
En Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar las variables de entorno
```powershell
Copy-Item .env.example .env     # PowerShell
copy .env.example .env          # CMD
cp .env.example .env            # Bash
```

### 5. Inicializar la base de datos
```bash
python database/init_db.py
```
*Crea la base de datos `sg_gomeria.db` con todas sus tablas, restricciones y usuarios iniciales si aún no existen.*

### 6. Ejecución del sistema

#### Modo uso diario (Windows):
Hacer doble clic sobre el archivo **`iniciar.bat`**.
Este script activa automáticamente el entorno virtual, levanta el servidor Flask y abre el navegador predeterminado directamente en la pantalla de inicio de sesión (`http://127.0.0.1:5000/login`).

> Se puede crear un acceso directo en el Escritorio apuntando a `iniciar.bat` y cambiarle el icono para que funcione exactamente como un programa de escritorio tradicional, evitando la necesidad de abrir terminales o escribir comandos manuales.

#### Modo manual / desarrollo:
```bash
python app.py
```
Y luego abrir en el navegador: **http://127.0.0.1:5000/login**

---

## Ejecución de Pruebas y Calidad de Código

El proyecto cuenta con **90 pruebas automatizadas** distribuidas en 10 módulos de test, desarrolladas con el módulo nativo `unittest` de Python:

### 1. Ejecutar las pruebas
```bash
python -m unittest discover tests
```

Salida esperada:
```
Ran 90 tests in ~2s
OK
```

### 2. Medir cobertura con Coverage
```bash
coverage run -m unittest discover tests
coverage report -m
coverage html
```

### 3. Estándares de calidad y formato (Black y Flake8)
- **Formateo automático de código con Black:**
  ```bash
  black .
  ```
- **Auditoría de estilo y errores con Flake8:**
  ```bash
  flake8 . --count --statistics
  ```

---

## Arquitectura y Buenas Prácticas

1. **Modularización con Blueprints:** Rutas separadas por dominio funcional (`auth`, `clientes`, `trabajos`, `cheques`, `general`) en lugar de concentrar toda la aplicación en un único archivo.
2. **Capa de Servicios (`services/`):** Desacoplamiento estricto entre los controladores HTTP y la lógica comercial. El cálculo de precios e IVA por tarea y las transacciones se resuelven en `trabajos_service.py`.
3. **Separación de Persistencia y Conexiones:** Conexión centralizada en `database/connection.py`, garantizando conexiones de vida corta y cierre explícito tras cada operación.
4. **Integridad Referencial y Transacciones:** Claves foráneas activas (`PRAGMA foreign_keys = ON`), `id_cliente NOT NULL` en cheques y transacciones atómicas para operaciones compuestas (cabecera y renglones de tareas).
5. **Seguridad:** Contraseñas hasheadas con `werkzeug.security`, variables sensibles aisladas en `.env` y exclusión de archivos de datos y logs en `.gitignore`.
