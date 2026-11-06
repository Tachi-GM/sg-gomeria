# ==============================================================================
# LÍNEA DE TIEMPO Y EVOLUCIÓN HISTÓRICA DEL PROYECTO
# Sistema de Gestión — Gomería "El Puente" 🔧🐾
# ==============================================================================

Este documento recopila la trazabilidad cronológica completa del desarrollo del 
sistema: desde el análisis preliminar de requerimientos en el taller físico hasta 
las fases avanzadas de arquitectura, seguridad, control de operarios y entrega.

Integración de fuentes:
- Entrevista inicial y relevamiento con el cliente (22/08/2026).
- Planificación y seguimiento del Diagrama de Gantt oficial (Canva / Project Plan).
- Registro real de hitos, prototipado y presentaciones académicas (Canva).
- Historial completo de versiones y commits del repositorio Git (Tachi-GM/sg-gomeria).

---

## 1. RESUMEN EJECUTIVO DE HITOS Y MÉTRICAS GLOBALES

- **Fecha de Inicio (Entrevista y Análisis):** 22 de Agosto de 2026.
- **Arranque de Construcción de Software (Primer Commit):** 09 de Septiembre de 2026.
- **Fecha de Cierre / Entrega Estimada:** 10 de Noviembre de 2026.
- **Presupuesto y Esfuerzo Estimado (Gantt):** 
  - 83 días totales planificados (5 de Análisis, 3 de Diseño, 55 de Programación, 8 de Pruebas, 12 de Documentación).
  - Tasa de rendimiento: La mayoría de los módulos base se entregaron con holgura o adelantados respecto al plan inicial.
- **Evolución del Repositorio:** Más de 55 commits, arquitectura desacoplada en Blueprints y Services, cobertura de pruebas automatizadas al 91%.

---

## 2. CRONOLOGÍA DETALLADA: FASE POR FASE

### FASE 0: ANÁLISIS PRELIMINAR, RELEVAMIENTO Y DISEÑO UI (Agosto – Septiembre 2026)

* **22/08/2026 — Entrevista Inicial y Relevamiento en el Taller:**
  - Reunión con el dueño y personal de Gomería "El Puente".
  - Detección de la problemática central: transcripción lenta de talonarios en papel (remitos de mostrador), pérdida de seguimiento de comprobantes de flotas de camiones, dificultad para discriminar tarifas según cliente (L1, L2, L3) y falta de control de cheques diferidos.
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

* **10/10/2026 — Lógica de IVA Inteligente:**
  - *Commit `8762b8e`*: Liquidación impositiva automática con cálculo y desglose de IVA (21%) según condición fiscal configurada en el cliente.

* **16/10/2026 — Blindaje de Seguridad, Roles y Auditoría:**
  - *Commit `6aa6b55`*: Incorporación del sistema de autenticación con hash seguro (`werkzeug`), roles diferenciados (`admin` / `usuario`), registro persistente de auditoría en base de datos y páginas amigables para errores 404/500.

* **18/10/2026 — Modularización en Blueprints, Capa de Servicios y Cobertura 91%:**
  - *Commits `49f5e6d`, `c703c3c`, `66dff07`, `1d9cfbf` y `70908dc`*:
    - Refactorización total de `app.py`: división en Blueprints de rutas (`routes/auth.py`, `routes/trabajos.py`, `routes/clientes.py`, `routes/cheques.py`, `routes/general.py`).
    - Desacoplamiento de lógica en capa de servicios (`services/trabajos_service.py`).
    - Creación del lanzador automatizado multiplataforma `iniciar.bat`.
    - Integración de suite de pruebas con `unittest` alcanzando un 91% de cobertura de código.

* **19/10/2026 — Flexibilidad Operativa en Mostrador:**
  - *Commits `27f55b7`, `f76eaa1`, `884c0b5` y `e4bc244`*: Selección de fecha manual retrospectiva, vinculación automática cliente-lista de precios, modal de corrección de cabecera de remito sin alterar ítems y checkbox interactivo de cobro.

---

### FASE 4: MÓDULO DE GOMEROS, AUSENCIAS, CONTROL SEMANAL Y PULIDO FINAL (Fines de Octubre 2026)

* **22/10/2026 — Administración de Usuarios y Entornos de Prueba Aislados:**
  - *Commits `f24067f` al `e914dd4`*: Incorporación de `CONTEXT.md` para seguimiento dinámico del proyecto, gestión de usuarios del sistema y aislamiento de pruebas con base SQLite en memoria temporal.

* **23/10/2026 al 26/10/2026 — Módulo Integral de Gomeros y Liquidación de Sueldos:**
  - *Commits `c33f556` al `74d6b4e`*: Creación completa del servicio `gomeros_service.py`, pantalla de control semanal de operarios, registro de movimientos/gastos y liquidación proporcional.
  - *Commits `c4e2102`, `1643ebb`, `176a370` y `0401412`*: Renovación integral del panel de inicio con tarjetas de acceso rápido, métricas en vivo y visual moderna.

* **27/10/2026 al 31/10/2026 — Ausencias de Personal, Layout Unificado y Manual Oficial:**
  - *Commits `6d890b3`, `68ac035`, `d6394b8`, `029779c`, `b0b8772`, `2490928` y `e43c9ff`*: Unificación de todas las plantillas al layout `base.html`, registro y persistencia de ausencias diarias de gomeros con descuento de sueldo.
  - *31/10/2026*: Generación y compilación del Manual de Usuario Oficial v2.2 en PDF con diseño editorial completo (10 páginas).

---

## 3. COMPARATIVA PLANIFICADO (GANTT) VS. REAL (COMMITS Y HITOS)

| N° | Hito / Subfase | Planeado (Gantt) | Real (Evidencia / Git) | Desvío | Estado |
|---|---|---|---|:---:|:---:|
| 1 | Análisis del proyecto y entrevista | 22/08 al 26/08 | 22/08 al 26/08 (Entrevista + Canva) | 0 días | ✅ En fecha |
| 2 | Diseño de pantallas en Canva | 05/09 al 08/09 | 05/09 al 07/09 (Canva) | -1 día | ⚡ Adelantado |
| 3 | Modelo de datos y pantallas base | 09/09 al 11/09 | 09/09 (Commits 729aec3, 2cd5926) | -2 días | ⚡ Adelantado |
| 4 | Historial por cliente con filtro mes | 12/09 al 14/09 | 10/09 al 12/09 (Commit eff767c) | -2 días | ⚡ Adelantado |
| 5 | Precios, L1-L3 y selector cantidades | 15/09 al 19/09 | 13/09 al 18/09 (Commits e01abed, c0510ff) | -1 día | ⚡ Adelantado |
| 6 | Documentación inicial de usuario | 20/09 al 21/09 | 18/09 (Commit 3b989f5) | -3 días | ⚡ Adelantado |
| 7 | Estados remito y orden de static | 20/09 al 23/09 | 19/09 al 23/09 (Commits c37fc59, 38f5c17) | 0 días | ✅ En fecha |
| 8 | Mejoras Mataburros y Backup .db | 24/09 al 27/09 | 24/09 al 27/09 (Commits e0739f2, 56a29ad) | 0 días | ✅ En fecha |
| 9 | Remitos OI/OIB y orden de columnas | 28/09 al 02/10 | 28/09 al 01/10 (Commits bc78304, 393d30b) | -1 día | ⚡ Adelantado |
| 10 | Plantillas Jinja2, Cheques y .env | 03/10 al 07/10 | 02/10 al 08/10 (Commit 4f8fa85) | +1 día | ⏳ Leve atraso |
| 11 | Cálculo inteligente de IVA | 08/10 al 12/10 | 10/10 al 18/10 (Commits 8762b8e, 1d9cfbf) | +6 días | ✅ Cumplido |
| 12 | Login, seguridad y auditoría | 24/10 al 27/10 | 16/10 (Commit 6aa6b55) | -8 días | ⚡ Muy adelantado |
| 13 | Control de gomeros y ausencias | Fase de ampliación | 23/10 al 31/10 (Commits e43c9ff, d6394b8) | Anticipado | ✅ Implementado |
| 14 | Manual de Usuario Editorial (PDF) | 02/11 al 05/11 | 31/10 (Compilación formal v2.2) | -2 días | ⚡ Adelantado |
| 15 | Entrega final del proyecto | 10/11/2026 | Prevista según cronograma | 0 días | 🎯 En curso |

---

## 4. CONCLUSIONES DEL DESARROLLO

1. **Eficiencia en la curva de trabajo:** Los componentes críticos del negocio (carga de remitos, clientes y listas de tarifas) fueron concluidos antes del tiempo estipulado en el Gantt original.
2. **Evolución arquitectónica continua:** La aplicación pasó de un prototipo monolítico en `app.py` a un sistema enterprise modular con Blueprints, separación estricta de servicios, DDL versionado, pruebas unitarias automatizadas con cobertura del 91% y control de personal.
3. **Fidelidad con la necesidad del taller:** Todo cambio implementado provino de requerimientos directos relevados en la entrevista inicial del 22/08 (rapidez en mostrador, evitar errores de IVA y trazabilidad de cheques y operarios).
