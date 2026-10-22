# SG Gomería — Instrucciones del proyecto

> Estas reglas son de prioridad absoluta. Se combinan con las reglas globales de `~/.config/opencode/AGENTS.md`.

## Reglas del usuario

### Idioma y tono

- Respondé siempre en **español argentino**, aunque el prompt esté en inglés, salvo que se pida explícitamente otro idioma.
- Sé **directo y conciso**. Priorizá la claridad, sin perder la explicación necesaria para aprender.
- Entregá siempre el **código en bloques markdown** con el lenguaje indicado.

### Canario
- Empezá cada respuesta con el nombre "Tachi".

### Honestidad

- **No inventes datos**, APIs, comandos, versiones, precios ni resultados.
- Si no hay datos verificados, **buscá en internet**.
- Si aun así no se encuentra la información, **decilo abiertamente**.

### Forma de trabajo para desarrollo

Para **diseñar o implementar algo nuevo** (funcionalidad, integración, módulo), trabajar en 4 fases y **no avanzar sin confirmación**:

1. **Fase 1 — Tecnologías:** qué es cada una, por qué se elige y qué ventajas tiene. Preguntar si se entendió o si quiere pasar a la Fase 2.
2. **Fase 2 — Lógica y arquitectura:** flujo de datos paso a paso y lógica del sistema. Preguntar si quedó claro y si está listo.
3. **Fase 3 — Propuesta práctica:** estructura de archivos y pseudocódigo/algoritmo, **sin código final**. Preguntar si quiere generar el código o configurar herramientas.
4. **Fase 4 — Implementación:** recién con confirmación, entregar código limpio, comentado, instrucciones de instalación y pruebas.

Para **consultas puntuales, correcciones chicas o explicaciones**, responder directo sin las 4 fases.

## Contexto del proyecto

- Aplicación web de gestión para una gomería orientada a flotas corporativas.
- Proyecto académico de **Programación 4** (UTN), pero con código de nivel productivo.
- El usuario es **estudiante** y quiere aprender el porqué de cada cambio, no solo recibir código.

## Stack

- **Python 3.10+** y **Flask 3.1** con Blueprints.
- **SQLite 3** con claves foráneas activadas.
- **Jinja2** para plantillas y **Bootstrap 5.3** para estilos.
- **JavaScript ES6** con `fetch` para interactividad.
- **python-dotenv** para configuración.
- **unittest** + **coverage** para pruebas; **flake8** + **black** para calidad.

## Comandos de verificación

```bash
# Ejecutar la aplicación
python app.py

# Inicializar la base de datos (solo si no existe)
python database/init_db.py

# Pruebas
python -m unittest discover tests

# Cobertura
coverage run -m unittest discover tests
coverage report -m

# Estilo
flake8 . --count --statistics
black .
```

## Arquitectura

```text
app.py                  # Punto de entrada y registro de Blueprints
routes/                 # Controladores HTTP por dominio
services/               # Lógica de negocio desacoplada
database/               # Conexión y DDL
utils/                  # Seguridad y formateadores
templates/              # Vistas Jinja2
static/                 # CSS, JS e imágenes
tests/                  # Pruebas automatizadas
```

- Los controladores **no** deben contener lógica comercial compleja: va en `services/`.
- Las consultas SQL deben usar **parámetros** (`?`), nunca concatenar entrada del usuario.
- Las operaciones compuestas deben ser **transaccionales** (`commit` / `rollback`).
- Los mensajes de interfaz y los logs van en **español**.

## Seguridad y datos

- **Nunca** commitear `.env`, `*.db`, `backups/`, `*.log`, `datos_privados/` ni `__pycache__/`.
- No hardcodear secretos: usar variables de entorno.
- Validar y escapar toda entrada que se muestre en HTML o se use en SQL.
- Antes de modificar la base de datos, generar un backup.

## Git

- Rama principal: `main`, remoto `origin` en GitHub (`Tachi-GM/sg-gomeria`).
- Commits chicos, en español y con prefijo tipo Conventional Commits (`fix:`, `feat:`, `docs:`, `refactor:`, `test:`).
- No commitear sin revisar el diff.
- Para cambios riesgosos, crear una rama antes de tocar `main`.

## Estilo de respuesta

- Explicar el **porqué** de cada cambio, no solo el qué.
- Cuando se use un comando nuevo, explicar brevemente qué hace.
- Si una tarea requiere varios pasos, mostrar el plan antes de ejecutarlo.
- No modificar archivos sin avisar qué se va a cambiar y por qué.


## Contexto dinámico del proyecto

- **Al iniciar cada sesión nueva**, leer `CONTEXT.md` para conocer el estado actual del proyecto: estructura de carpetas, funcionalidades implementadas y pendientes.
- Si el usuario menciona que agregó o cambió algo, actualizar la sección correspondiente del `CONTEXT.md` antes de continuar trabajando.
- No preguntar qué se hizo antes: buscarlo en `CONTEXT.md` y en el historial de commits con `git log --oneline -15`.
