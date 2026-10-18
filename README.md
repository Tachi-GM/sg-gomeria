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
  - Selección de cliente con asignación automática de lista de precios por defecto y condición de IVA.
  - Selección múltiple de tareas con controles interactivos de incremento/decremento de cantidades (+ / -).
  - Tres listas de precios diferenciadas por política comercial (L1: Lista base / L2: Clientes frecuentes / L3: Pago diferido).
  - Cálculo automático de subtotales, recargo por IVA (21%) y total final del trabajo.

- **Módulo de Clientes:**
  - Alta y consulta de empresas (Razón Social, CUIT con validación única, teléfono, email).
  - Asignación de condición impositiva (Con IVA / Sin IVA) y lista de precios habitual (1, 2 o 3).
  - Listado de clientes con buscador en tiempo real y vista en tarjetas.
  - Historial detallado por empresa con navegación mensual por pestañas y totales acumulados.

- **Historial General y Remitos:**
  - Tabla interactiva de remitos con ordenamiento dinámico por columnas (fecha, número de remito, cliente, total y estado).
  - Despliegue en acordeón de los renglones de tareas realizadas por remito sin recargar la página.
  - Actualización del estado de cobro (`PENDIENTE`, `EN PROCESO`, `PAGADO`) mediante peticiones asíncronas (`fetch` POST).

- **Módulo de Cheques:**
  - Registro y seguimiento de cartera de cheques recibidos de clientes (número, banco emisor, cliente asociado, fecha de emisión, fecha de cobro e importe).
  - Control de estados: `Pendiente`, `Cobrado`, `Rechazado` y registro de endosos.

- **Autenticación y Control de Acceso por Roles:**
  - Inicio y cierre de sesión seguro (`/login`, `/logout`) con contraseñas protegidas mediante hashing criptográfico con sal (`werkzeug.security`).
  - Control de acceso por roles: `admin` (acceso total y generación de backups) y `usuario` (operador de mostrador).
  - Decoradores `@login_requerido` y `@solo_admin` para proteger rutas contra accesos no autorizados.
  - Credenciales demo para evaluación: `admin` / `admin123` y `operador` / `operador123`.

- **Mantenimiento y Resguardo:**
  - Resguardo de base de datos (`/backup`) exclusivo para administradores con timestamp en la carpeta `backups/`.
  - Páginas de error personalizadas (`401`, `403`, `404` y `500`) con registro de eventos de auditoría en `sistema.log`.
  - Modo Milagritos accesible vía sesión HTTP.

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
├── routes/                     # Controladores modularizados (Blueprints de Flask)
│   ├── auth.py                 # Login, logout y control de sesión
│   ├── general.py              # Pantalla de inicio, acerca-de, salir y backups
│   ├── clientes.py             # Dashboard de empresas, historial y alta de clientes
│   ├── trabajos.py             # Mataburros (emisión de remitos) y administración de precios
│   └── cheques.py              # Cartera de cheques, cobros y cambios de estado
│
├── utils/                      # Utilidades y funciones transversales
│   ├── seguridad.py            # Decoradores login_requerido, solo_admin y auditoría
│   └── formateadores.py        # Conversiones seguras de tipos (parse_int, parse_float) y filtros
│
├── services/                   # Capa de servicios y lógica de negocio desacoplada
│   └── trabajos_service.py     # Procesamiento comercial, cálculo de IVA por tarea y persistencia
│
├── database/                   # Persistencia y base de datos
│   ├── connection.py           # Conexión centralizada a SQLite (FK ON, row_factory)
│   └── init_db.py              # Script DDL de inicialización y datos semilla
│
├── templates/                  # Plantillas Jinja2
│   ├── base/
│   │   └── base.html           # Layout base compartido (Navbar, CDN Bootstrap, estilos)
│   ├── index.html              # Pantalla principal con accesos directos
│   ├── mataburros.html         # Formulario de carga de trabajos y cálculo de remitos
│   ├── clientes.html           # Dashboard de empresas y tabla de remitos interactiva
│   ├── historial-cliente.html  # Vista mensual consolidada por cliente
│   ├── precios.html            # Gestión y consulta de tarifas (L1, L2, L3)
│   ├── cheques.html            # Cartera y seguimiento de cheques
│   ├── acerca-de.html          # Información del sistema
│   ├── salir.html              # Pantalla de confirmación de salida
│   └── error.html              # Vista unificada de errores HTTP (401, 403, 404, 500)
│
├── static/                     # Recursos estáticos
│   ├── css/                    # Hojas de estilo (estilos.css, cheques.css)
│   ├── js/                     # Scripts del cliente (clientes.js, mataburros.js, cheques.js)
│   └── logo.png                # Logo del taller
│
└── tests/                      # Suite de pruebas automatizadas
    ├── test_rutas.py           # Pruebas de integración sobre endpoints, seguridad y roles
    └── test_trabajos_service.py# Pruebas unitarias de cálculo de tarifas, IVA y persistencia
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

El proyecto cuenta con **25 pruebas automatizadas** desarrolladas con el módulo nativo `unittest` de Python, alcanzando un **91% de cobertura de código**:

### 1. Ejecutar las pruebas
```bash
python -m unittest discover tests
```

Salida esperada:
```
Ran 25 tests in 0.664s
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

