# ==============================================================================
# LÍNEA DE TIEMPO Y EVOLUCIÓN HISTÓRICA DEL PROYECTO
# Sistema de Gestión — Gomería "El Puente" 🔧🐾
# ==============================================================================

Este documento recopila la trazabilidad cronológica completa del desarrollo del 
sistema: desde el análisis preliminar de requerimientos en el taller físico hasta 
las fases avanzadas de arquitectura, seguridad, control de operarios, exportaciones
y la entrega formal de la **Versión 1.0**.

Integración de fuentes:
- Entrevista inicial y relevamiento con el cliente (22/08/2026).
- Planificación y seguimiento del Diagrama de Gantt oficial (`docs/Extras/Gantt - SG Gomez Miño.xlsx`).
- Registro real de hitos, prototipado y presentaciones académicas (Canva / UTN FRGP).
- Historial completo de versiones y commits del repositorio Git (`Tachi-GM/sg-gomeria`).

---

## 1. RESUMEN EJECUTIVO DE HITOS Y MÉTRICAS GLOBALES

- **Fecha de Inicio (Entrevista y Análisis):** 22 de Agosto de 2026.
- **Arranque de Construcción de Software (Primer Commit):** 09 de Septiembre de 2026.
- **Fecha de Cierre y Entrega Oficial (Versión 1.0):** Sábado 21 de Noviembre de 2026.
- **Presupuesto y Esfuerzo Estimado (Gantt y Costos):** 
  - Régimen de trabajo: **2 horas diarias** dedicadas por jornada.
  - Distribución: 5 días de Análisis, 3 de Diseño, 70 de Programación, 10 de Pruebas y 14 de Documentación.
  - Presupuesto económico total: **$1.769.000 ARS** (ampliamente por debajo del tope previsto de 3 millones).
- **Evolución del Repositorio:** Más de 85 commits, arquitectura desacoplada en Blueprints y Services, 90 pruebas unitarias automatizadas con 100% de éxito y 91% de cobertura.

---

## 2. CRONOLOGÍA DETALLADA: FASE POR FASE

### FASE 0: ANÁLISIS PRELIMINAR, RELEVAMIENTO Y DISEÑO UI (Agosto – Septiembre 2026)

* **22/08/2026 — Entrevista Inicial y Relevamiento en el Taller:**
  - Reunión con la encargada y personal de Gomería "El Puente".
  - Detección de la problemática central: transcripción lenta de talonarios en papel (remitos de mostrador), pérdida de comprobantes de flotas de camiones, dificultad para discriminar tarifas según cliente (L1, L2, L3) y falta de control de cheques diferidos.
  - Definición del alcance inicial del sistema y requerimientos funcionales.

* **22/08/2026 al 26/08/2026 — Análisis de Requerimientos y Definición del Problema:**
  - Elaboración del documento de alcance, reglas de negocio y restricciones técnicas.
  - Finalización del documento de análisis preliminar (Registro en Canva: 26/08/2026).

* **05/09/2026 al 07/09/2026 — Prototipado y Diseño de Interfaces de Usuario (UI):**
  - Maquetado visual de pantallas principales en Canva: pantalla de mostrador ("Mataburros"), catálogo de precios, listado de empresas y gestión de cartera.
  - Cierre del diseño preliminar (Registro en Canva: 07/09/2026, 1 día antes de lo planeado).

---

### FASE 1: ARQUITECTURA BASE Y PRIMEROS MÓDULOS DE NEGOCIO (Septiembre 2026)

* **09/09/2026 — Inicialización del Proyecto y Núcleo Web:**
  - *Commits `729aec3` y `2cd5926`*: Creación del repositorio `sg-gomeria`. Estructura base en Python/Flask, diseño de base de datos relacional SQLite (`sg_gomeria.db`) y primeras vistas operativas (Inicio, Mataburros y Clientes).

* **10/09/2026 al 12/09/2026 — Historial Consolidado por Cliente:**
  - *Commit `eff767c` (12/09/2026)*: Implementación del historial mensualizado por empresa. Filtrado por períodos anuales/mensuales y cálculo de saldos.

* **13/09/2026 al 18/09/2026 — Módulo de Precios y Correcciones de Mostrador:**
  - *Commits `e01abed`, `3b989f5` y `c0510ff` (18/09/2026)*: 
    - Implementación de las 3 listas de precios simultáneas (L1 Mostrador, L2 Flotas frecuentes, L3 Cuenta corriente).
    - Ajuste ergonómico en botones de incremento/decremento (`+` / `-`) en mostrador.
    - Primera entrega de documentación operativa (`MANUAL_DE_USUARIO.txt` y `README.md`).

* **21/09/2026 al 23/09/2026 — Presentación Académica y Estados de Trabajo:**
  - *22/09/2026 al 23/09/2026*: Primera presentación parcial de Programación IV (UTN) basada en prototipo funcional de Canva y código base.
  - *Commits `c37fc59` (21/09) y `38f5c17` (23/09)*: Incorporación de ciclo de vida del remito (estados de cobro), modularización de recursos estáticos (`css/`, `js/`) y botón de cierre de sesión.

* **23/09/2026 al 25/09/2026 — Presentación de Gestión de Desarrollo de Software:**
  - Presentación de metodología, planificación de entregas, métricas de esfuerzo y control de versiones ante la cátedra de Gestión.

---

### FASE 2: CONSOLIDACIÓN OPERATIVA Y ESTANDARIZACIÓN FISCAL (Fines de Septiembre – Inicios de Octubre 2026)

* **24/09/2026 al 27/09/2026 — Mejoras en Mataburros y Backups Atómicos:**
  - *Commits `e0739f2` (26/09) y `56a29ad` (27/09)*: Rediseño del formulario de carga rápida de remitos, sistema de respaldo atómico de base de datos en 1-clic y alta interactiva de nuevas tareas de taller.

* **28/09/2026 al 01/10/2026 — Remitos Oficiales (OI / OIB), Ordenamiento y Clientes Reales:**
  - *Commit `bc78304` (28/09)*: Soporte formal para comprobantes OI (Orden Interna) y OIB (con detalle secundario), con numeración diferenciada.
  - *Commits `b51322d` y `393d30b` (01/10)*: Carga y validación con clientes corporativos reales. Incorporación de ordenamiento dinámico por columnas en tablas web y pantalla institucional "Acerca de".

* **02/10/2026 al 08/10/2026 — Plantillas Base Jinja2, Cheques e Interactividad:**
  - *Commit `4f8fa85` (08/10)*: Estandarización de vistas con Jinja2 (`base.html`), configuración segura por variables de entorno (`.env`), interactividad asíncrona en módulo de Cheques y campo de observaciones técnicas en remitos.

---

### FASE 3: AUDITORÍA, REFACTORIZACIÓN ARQUITECTURAL Y CALIDAD (Octubre 2026)

* **09/10/2026 al 10/10/2026 — Lógica de IVA Inteligente:**
  - *Commit `8762b8e` (10/10)*: Liquidación impositiva automática con cálculo y desglose de IVA (21%) según condición fiscal configurada en el cliente.

* **11/10/2026 al 16/10/2026 — Blindaje de Seguridad, Roles y Auditoría:**
  - *Commit `6aa6b55` (16/10)*: Incorporación del sistema de autenticación con hash seguro (`werkzeug`), roles diferenciados (`admin` / `usuario`), registro persistente de auditoría en base de datos y páginas amigables para errores 404/500.

* **17/10/2026 al 19/10/2026 — Modularización en Blueprints, Capa de Servicios y Mostrador:**
  - *Commits `49f5e6d`, `c703c3c`, `66dff07`, `1d9cfbf`, `70908dc`, `27f55b7` y `884c0b5`*:
    - División en Blueprints de rutas (`routes/auth.py`, `routes/trabajos.py`, `routes/clientes.py`, `routes/cheques.py`, `routes/general.py`).
    - Desacoplamiento de lógica en capa de servicios (`services/trabajos_service.py`).
    - Creación del lanzador automatizado `iniciar.bat`.
    - Selección manual de fecha retrospectiva, vinculación automática cliente-lista y checkbox de cobro directo.

* **20/10/2026 al 22/10/2026 — Administración de Usuarios y Entornos de Prueba Aislados:**
  - *Commits `f24067f`, `471066a`, `5660a7c` y `e914dd4`*: Incorporación de `CONTEXT.md` para seguimiento dinámico del proyecto, gestión de usuarios del sistema y aislamiento de pruebas con base SQLite temporal.

---

### FASE 4: MÓDULO DE GOMEROS, AUSENCIAS Y CONTROL SEMANAL (Fines de Octubre 2026)

* **23/10/2026 al 27/10/2026 — Control Semanal de Gomeros, Sueldos y Dashboard:**
  - *Commits `c33f556` al `68ac035` (PR #5 y #6)*: Creación completa del servicio `gomeros_service.py`, pantalla de control semanal de operarios, registro de adelantos/gastos y liquidación proporcional.
  - Renovación integral del panel de inicio con tarjetas de acceso rápido, métricas en vivo y visual moderna.

* **28/10/2026 al 31/10/2026 — Registro de Ausencias de Personal y Layout Unificado:**
  - *Commits `d6394b8`, `029779c`, `2490928` y `e43c9ff` (PR #7 y #8)*: Registro y persistencia de ausencias diarias de gomeros con descuento de sueldo automatizado y unificación visual en `base.html`.

---

### FASE 5: REPORTES MENSUALES, DIGITALIZACIÓN Y EDICIÓN AVANZADA (Inicios de Noviembre 2026)

* **01/11/2026 al 06/11/2026 — Tareas Temporales, Fotos de Remitos y Documentación Editorial:**
  - *Commits `d0624f1`, `dca49b7`, `725fd6e` y `99b162b` (PR #9 y #12)*:
    - Incorporación de tareas temporales en remitos (servicios fuera de catálogo).
    - Subida y almacenamiento seguro de fotos de remitos en papel (hasta 5 MB) vinculadas al detalle.
    - Exportación general por cliente a Excel con pestañas mensuales y generación de imágenes PNG de resumen.
    - Generación del Manual de Usuario Oficial v2.2 en PDF (10 páginas), plan de capacitación y diagramas técnicos (MER y Casos de Uso).

* **07/11/2026 al 11/11/2026 — Edición de Clientes, Ocultar/Reactivar y Validación CUIT en Tiempo Real:**
  - *Commits `82ce346`, `f09e4df`, `436bdb6`, `bcf1ac2` y `bdeb512` (PR #13 y #14)*:
    - Edición rápida de clientes y posibilidad de ocultar/reactivar empresas y tareas del catálogo.
    - Validación asíncrona de CUIT duplicado en tiempo real con endpoint dedicado.
    - Script de importación de listas de precios desde Excel y personalización de datos institucionales de la empresa.

---

### FASE 6: TALONARIO FÍSICO, SUITE DE 90 TESTS Y CIERRE VERSIÓN 1.0 (Noviembre 2026)

* **12/11/2026 al 16/11/2026 — Vista Imprimible de Remito (PDF), Choices.js y 90 Tests:**
  - *Commits `c52b5c7`, `1fe9328`, `e14a649`, `a809fb2` y `2efbc7e`*:
    - Vista imprimible formal adaptada al talonario físico comercial (`/remito/<id>/imprimir`) para impresión y PDF directo sin barras de navegación.
    - Buscador Choices.js interactivo en cheques con sugerencia de endosos.
    - Importador de remitos históricos y manual de uso e instalación.
    - Suite de 90 tests unitarios e integrales automatizados con 100% de éxito.

* **17/11/2026 al 20/11/2026 — Pruebas Finales Integrales y Ensayo de Defensa:**
  - Verificación de flujos completos en PC de taller, ajustes de filtros en exportaciones y preparación para la defensa académica.

* **21/11/2026 — Hito Oficial: Entrega Final Versión 1.0:**
  - Congelamiento de código, puesta en marcha operativa definitiva en Gomería "El Puente" y entrega de versión productiva.

---

## 3. COMPARATIVA PLANIFICADO (GANTT) VS. REAL (COMMITS Y HITOS)

La siguiente tabla refleja exactamente los 20 tramos de trabajo, el hito de entrega y las presentaciones del archivo oficial de Gantt (`Gantt - SG Gomez Miño.xlsx`):

| N° | Tarea / Entregable | Planeado (Gantt) | Real (Evidencia / Git) | Desvío | Estado |
|---|---|---|---|:---:|:---:|
| 1 | Análisis del proyecto (contexto, problema, objetivos, alcance) | 22/08 al 26/08 | 22/08 al 26/08 (Entrevista + Canva) | 0 días | ✅ En fecha |
| 2 | Diseño de las pantallas en Canva | 05/09 al 08/09 | 05/09 al 07/09 (Canva) | -1 día | ⚡ Adelantado |
| 3 | Modelo de datos, estructura Flask y pantallas base | 09/09 al 11/09 | 09/09 (Commits 729aec3, 2cd5926) | -2 días | ⚡ Adelantado |
| 4 | Historial por cliente con filtro por mes | 12/09 al 14/09 | 10/09 al 12/09 (Commit eff767c) | -2 días | ⚡ Adelantado |
| 5 | Pantalla de precios, listas L1-L3 y corrección de cantidades | 15/09 al 19/09 | 13/09 al 18/09 (Commits e01abed, c0510ff) | -1 día | ⚡ Adelantado |
| 6 | Documentación inicial (manual de usuario y README) | 20/09 al 21/09 | 18/09 (Commits 18/09) | -3 días | ⚡ Adelantado |
| 7 | Estados de remito, pantalla Salir y reorganización de static | 20/09 al 23/09 | 19/09 al 23/09 (Commits c37fc59, 38f5c17) | 0 días | ✅ En fecha |
| 8 | Mejoras en Mataburros, backups de la base y alta de tareas | 24/09 al 27/09 | 24/09 al 27/09 (Commits e0739f2, 56a29ad) | 0 días | ✅ En fecha |
| 9 | Remitos OI/OIB, clientes reales, ordenar columnas y Acerca de | 28/09 al 02/10 | 28/09 al 01/10 (Commits bc78304, 393d30b) | -1 día | ⚡ Adelantado |
| 10 | Plantillas base (Jinja2), Cheques con JS y detalle remito | 03/10 al 07/10 | 02/10 al 08/10 (Commit 4f8fa85) | +1 día | ⏳ Leve atraso |
| 11 | Cálculo de IVA con subtotal y discriminación según cliente | 08/10 al 12/10 | 09/10 al 10/10 (Commit 8762b8e) | -2 días | ⚡ Adelantado |
| 12 | Autenticación con roles (admin/usuario), auditoría y blindaje | 13/10 al 17/10 | 11/10 al 16/10 (Commit 6aa6b55) | -1 día | ⚡ Adelantado |
| 13 | Blueprints, capa de servicios, fecha manual y lanzador bat | 18/10 al 21/10 | 17/10 al 19/10 (Commits 18/10 y 19/10) | -2 días | ⚡ Adelantado |
| 14 | Administración de usuarios, SQLite temporal y CONTEXT.md | 22/10 al 24/10 | 20/10 al 22/10 (Commits 22/10) | -2 días | ⚡ Adelantado |
| 15 | Control de gomeros, sueldos semanales y panel de inicio | 25/10 al 29/10 | 23/10 al 27/10 (PR #5 y #6) | -2 días | ⚡ Adelantado |
| 16 | Registro de ausencias diarias de gomeros y liquidación | 30/10 al 02/11 | 28/10 al 31/10 (PR #8) | -2 días | ⚡ Adelantado |
| 17 | Tareas temporales, fotos adjuntas y exportaciones Excel/PNG | 03/11 al 07/11 | 01/11 al 06/11 (PR #9 y #12) | -1 día | ⚡ Adelantado |
| 18 | Edición de clientes, ocultar/reactivar y CUIT en tiempo real | 08/11 al 12/11 | 07/11 al 11/11 (PR #13) | -1 día | ⚡ Adelantado |
| 19 | Vista imprimible remitos (PDF), Choices cheques e importador | 13/11 al 17/11 | 12/11 al 16/11 (Commits 14/11 al 16/11) | -1 día | ⚡ Adelantado |
| 20 | Pruebas finales (90 tests), manual instalación y defensa | 18/11 al 20/11 | 17/11 al 20/11 (Suite 90 tests y defensa) | 0 días | ✅ En fecha |
| **21** | **Entrega final del proyecto — Versión 1.0 (Hito)** | **21/11/2026** | **21/11/2026 (Entrega formal v1.0)** | **0 días** | 🎯 **Cumplido** |
| 22 | Presentación de Programación IV (parcial) | 21/09 al 23/09 | 22/09 al 23/09 (Canva 23/09) | 0 días | ✅ En fecha |
| 23 | Presentación de Gestión de Desarrollo de Software (parcial) | 23/09 al 25/09 | 23/09 al 25/09 (Canva 25/09) | 0 días | ✅ En fecha |

---

## 4. CONCLUSIONES DEL DESARROLLO

1. **Curva de Rendimiento Sólida:** De las 20 tareas de desarrollo, 14 se entregaron con anticipación (desvíos negativos de 1 a 3 días), 5 se cumplieron con exactitud en la fecha comprometida, y solo 1 presentó una demora menor de 1 día (ajuste de plantillas base).
2. **Entrega Oficial en Fecha (Sábado 21/11/2026):** Se alcanzó el congelamiento total de la Versión 1.0 lista para producción con holgura controlada y sin sobrecostos.
3. **Calidad y Mantenibilidad Garantizadas:** 90 tests automáticos ejecutados en base temporal aislada, arquitectura desacoplada en Blueprints y Services, y resguardo ZIP en caliente aseguran que el taller cuente con una solución robusta y de bajo costo operativo.
