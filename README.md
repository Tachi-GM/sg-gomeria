# Sistema de Gestión - Gomería "El Puente" 🔧🐾

Aplicación web para la gestión integral de la operatoria diaria de un taller mecánico / gomería enfocado en flotas corporativas: facturación de trabajos (remitos OI y OIB), administración de clientes y vehículos, 3 listas de precios simultáneas, módulo de cartera de cheques, y cálculo automático de IVA.

Desarrollada para la materia **Programación 4** de la **Tecnicatura Superior en Programación (UTN)**.

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Tecnologías utilizadas](#-tecnologías-utilizadas)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Variables de entorno](#-variables-de-entorno)
- [Requisitos previos](#-requisitos-previos)
- [Instalación y puesta en marcha](#-instalación-y-puesta-en-marcha)
- [Ejecución de Pruebas Automáticas](#-ejecución-de-pruebas-automáticas)
- [Arquitectura y Buenas Prácticas](#-arquitectura-y-buenas-prácticas)
- [Cómo usar el sistema](#-cómo-usar-el-sistema)

---

## ✨ Funcionalidades

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
  - Tabla interactiva de remitos con ordenamiento dinámico por cualquier columna (fecha, número de remito, cliente, total y estado).
  - Despliegue en acordeón de los renglones de tareas realizadas por remito sin recargar la página.
  - Actualización inline del estado de cobro (`PENDIENTE`, `EN PROCESO`, `PAGADO`) mediante peticiones asíncronas (`fetch` POST).

- **Módulo de Cheques:**
  - Registro y seguimiento de cartera de cheques recibidos de clientes (número, banco emisor, cliente asociado, fecha de emisión, fecha de cobro e importe).
  - Control de estados: `Pendiente`, `Cobrado`, `Rechazado` y registro de endosos.

- **Autenticación y Control de Acceso por Roles:**
  - Inicio y cierre de sesión seguro (`/login`, `/logout`) con contraseñas protegidas mediante **hashing criptográfico con sal** (`werkzeug.security`).
  - Control de acceso por roles: `admin` (acceso total y generación de backups) y `usuario` (operador de mostrador).
  - Decoradores `@login_requerido` y `@solo_admin` para proteger rutas contra accesos no autorizados.
  - Credenciales demo para evaluación: `admin` / `admin123` y `operador` / `operador123`.

- **Herramientas de Mantenimiento y Seguridad:**
  - Resguardo automático de base de datos (`/backup`) exclusivo para administradores con timestamp en `backups/`.
  - Páginas de error personalizadas (`404` y `500`) con registro de eventos anómalos en `errores.log`.
  - **Modo Milagritos 🧚:** Personalización visual accesible vía sesión HTTP.

---

## 🛠 Tecnologías utilizadas

| Capa | Tecnología | Justificación |
|---|---|---|
| **Backend** | Python 3 + Flask 3.1 | Microframework ágil, modular y de bajo consumo de recursos. |
| **Base de Datos** | SQLite 3 | Base de datos relacional serverless, ACID, con foreign keys activadas. |
| **Frontend** | HTML5 + Jinja2 | Herencia de plantillas modular (`base.html`), lógica declarativa segura. |
| **Estilos** | CSS3 + Bootstrap 5.3 | Diseño responsivo con componentes modernos y hojas CSS modulares. |
| **Interactividad** | JavaScript (ES6) | Asincronismo con `fetch`, manipulación del DOM y ordenamiento cliente. |
| **Configuración** | `python-dotenv` | Separación estricta entre código y configuración de entorno (.env). |

---

## 📁 Estructura del proyecto

El proyecto implementa una arquitectura modular con separación de responsabilidades:

```
SG - Gomería/
│
├── app.py                      # Punto de entrada de la aplicación y controladores de rutas
├── requirements.txt            # Dependencias del proyecto en formato estándar UTF-8
├── .env.example                # Plantilla de variables de entorno para desarrollo
├── .gitignore                  # Exclusión de archivos sensibles, entornos y bases de datos
├── README.md                   # Documentación técnica y guía de instalación
│
├── database/                   # Módulo de persistencia y base de datos
│   ├── connection.py           # Conexión centralizada a SQLite (FK ON, row_factory)
│   └── init_db.py              # Script DDL de inicialización y datos semilla
│
├── templates/                  # Plantillas Jinja2
│   ├── base/
│   │   └── base.html           # Layout base compartido (Navbar, CDN Bootstrap, estilos)
│   ├── index.html              # Pantalla principal de acceso rápido
│   ├── mataburros.html         # Formulario de carga de trabajos y cálculo de remitos
│   ├── clientes.html           # Dashboard de empresas y tabla de remitos interactiva
│   ├── historial-cliente.html  # Vista mensual consolidada por cliente
│   ├── precios.html            # Gestión y consulta de tarifas (L1, L2, L3)
│   ├── cheques.html            # Cartera y seguimiento de cheques
│   ├── acerca-de.html          # Información del sistema
│   ├── salir.html              # Pantalla de confirmación de salida
│   └── error.html              # Vista unificada de errores HTTP (404, 500)
│
├── static/                     # Archivos estáticos
│   ├── css/
│   │   ├── estilos.css         # Reglas visuales globales y tema Modo Milagritos
│   │   └── cheques.css         # Estilos específicos del módulo de cheques
│   ├── js/
│   │   ├── clientes.js         # Filtros, ordenamiento de tablas y actualización AJAX
│   │   ├── mataburros.js       # Dinámica de cantidades, tareas y listas de precios
│   │   ├── cheques.js          # Control de estados y acciones de cheques
│   │   └── precios.js          # Edición modal de tareas y precios
│   └── logo.png                # Isotipo del taller
│
└── tests/                      # Suite de pruebas automatizadas
    └── test_rutas.py           # Pruebas de integración sobre los endpoints principales
```

---

## ⚙ Variables de entorno

El sistema utiliza variables de entorno para evitar datos sensibles en el código fuente. Se incluye un archivo `.env.example` de referencia:

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Clave criptográfica para firmas de sesión Flask | Valor de respaldo para desarrollo |
| `DATABASE_PATH` | Ruta al archivo de base de datos SQLite | `sg_gomeria.db` |
| `FLASK_DEBUG` | Activa o desactiva el modo de depuración (`True`/`False`) | `True` |

---

## ✅ Requisitos previos

- **Python 3.10 o superior** ([python.org](https://www.python.org/))
- **Git** ([git-scm.com](https://git-scm.com/))
- Navegador web moderno (Chrome, Edge, Firefox, Brave)

---

## 🚀 Instalación y puesta en marcha

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
Copiá la plantilla de variables de entorno:
- En Windows (PowerShell):
  ```powershell
  Copy-Item .env.example .env
  ```
- En Linux / macOS / CMD:
  ```bash
  copy .env.example .env   # CMD
  cp .env.example .env     # Bash
  ```

### 5. Inicializar la base de datos
Ejecutá el script constructor del esquema relacional:
```bash
python database/init_db.py
```
*Este comando crea todas las tablas con sus restricciones y carga datos semilla de prueba si la base se encuentra vacía.*

### 6. Iniciar el servidor
```bash
python app.py
```
Abrí en tu navegador: **http://127.0.0.1:5000/**

---

## 🧪 Ejecución de Pruebas Automáticas

El proyecto cuenta con un conjunto de pruebas automáticas desarrolladas con el módulo estándar `unittest` de Python para garantizar la estabilidad de las rutas principales y el manejo de errores:

```bash
python -m unittest discover tests
```

Salida esperada:
```
Ran 6 tests in 0.120s
OK
```

---

## 🏛 Arquitectura y Buenas Prácticas

1. **Separación de Persistencia:** Toda la lógica de conexión vive en `database/connection.py`. Los controladores obtienen conexiones de corta duración y liberan recursos al finalizar cada solicitud.
2. **Integridad Referencial:** Claves foráneas activas (`PRAGMA foreign_keys = ON`) y restricciones `CHECK` a nivel de motor para garantizar la validez de precios, cantidades y estados.
3. **Frontend Componentizado:** Las plantillas extienden de `templates/base/base.html`, reduciendo código duplicado y asegurando consistencia visual.
4. **Seguridad y Resguardo:** Exclusión de bases de datos operativas del repositorio Git mediante `.gitignore` y parametrización segura de credenciales mediante `python-dotenv`.
