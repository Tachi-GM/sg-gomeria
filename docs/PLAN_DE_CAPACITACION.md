# ==============================================================================
# PLAN DE CAPACITACIÓN OPERATIVA — SISTEMA SG GOMERÍA
# Puesto: Operadora de Mostrador y Facturación (Gomería "El Puente")
# ==============================================================================

> **Destinataria:** Operadora de mostrador (Capacitación 1 a 1).
> **Objetivo:** Adquirir autonomía total en la carga de remitos, consulta de clientes, seguimiento de cobros y emisión de reportes sin fricción técnica.
> **Duración estimada:** 45 a 60 minutos (práctica guiada interactiva).
> **Modalidad:** Taller práctico frente a la computadora con casos reales simulados de la gomería.

---

## 1. ESTRUCTURA Y HOJA DE RUTA DE LA CAPACITACIÓN

La capacitación se divide en **4 bloques secuenciales**, ordenados de lo más frecuente y urgente a lo periódico y administrativo:

```
[Bloque 1: Inicio y Conceptos Clave] (10 min)
   └─ Ingreso con usuario, entender qué es una flota, listas L1-L3 e IVA.
[Bloque 2: El Corazón del Taller — Mataburros] (20 min)
   └─ Cargar remitos OI/OIB, usar botones +/-, subir foto del talonario y tareas temporales.
[Bloque 3: Seguimiento de Clientes y Cobranzas] (15 min)
   └─ Ver historial mensual, descargar Excel, marcar remitos PAGADOS y chequear saldos.
[Bloque 4: Cierres y Qué Hacer ante Dudas] (10 min)
   └─ Respaldo con 1 clic (Backup ZIP) y soluciones a errores comunes.
```

---

## 2. DESARROLLO DE LOS BLOQUES DE APRENDIZAJE

### BLOQUE 1: PUESTA EN MARCHA Y CONCEPTOS BÁSICOS (10 min)
1. **Cómo se enciende el sistema:**
   - Hacer doble clic en el archivo `iniciar.bat` del escritorio.
   - Entrar al navegador a la dirección habitual (`http://127.0.0.1:5000`).
2. **Ingreso con usuario propio:**
   - Iniciar sesión con su usuario y contraseña asignada. Explicar que el sistema registra quién confecciona cada remito por seguridad y orden interno.
3. **Las 3 Reglas de Oro del Negocio (explicación simple):**
   - **Remito OI vs OIB:** OI es la orden común/oficial numerada; OIB es para comprobantes secundarios o con detalle específico.
   - **Las 3 Listas de Precios:**
     - *L1 (Mostrador):* Para el cliente particular que entra de la calle.
     - *L2 (Flota Amiga):* Descuento especial para empresas con las que hay convenio.
     - *L3 (Cuenta Corriente):* Tarifa para pagos a 30/60 días.
   - **El IVA (21%):** El sistema ya sabe si la empresa paga con IVA o sin IVA. ¡Ella no tiene que calcular porcentajes en la calculadora!

---

### BLOQUE 2: DOMINIO DE "MATABURROS" — NUEVO REMITO (20 min)
*Es la pantalla que más va a usar durante el día. Se hace una práctica guiada en vivo.*

1. **Paso a paso de carga (Caso práctico: Llega un camión a emparchar):**
   - Entrar a **Mataburros**.
   - Elegir el **Tipo** (OI u OIB) y poner el **Número de Remito** de papel.
   - Elegir la **Empresa**: notar cómo el sistema ya selecciona solo la lista (L1, L2 o L3) y avisa si va con o sin IVA.
   - Seleccionar la tarea (ej. "Parche Camión") y ajustar la cantidad con los botones `+` y `-`.
2. **Situaciones especiales de mostrador:**
   - **¿Hicieron un trabajo que no está en la lista?** → Usar la opción de **"Tarea temporal"** para cobrarla en este remito sin ensuciar el catálogo general de precios.
   - **Foto del remito de papel:** Subir una foto del talonario físico firmado por el chofer desde la computadora/celular (máximo 5 MB en formato JPG o PNG). Así el taller nunca pierde el papel físico.
   - **Detalle u observaciones:** Anotar si vino un chofer específico, patente o aclaración del neumático.
   - **Guardar:** Presionar el botón grande *"Guardar Remito y Calcular Total"*.

---

### BLOQUE 3: HISTORIAL, EXPORTACIONES Y COBRANZAS (15 min)
1. **Consultar la cuenta de un cliente:**
   - Ir a la pestaña **Clientes**.
   - Usar el buscador en vivo (escribir 3 letras del nombre o CUIT y filtra al instante).
   - Tocar **"Ver Historial"** para abrir la ficha de la empresa.
2. **Navegación mensual por pestañas:**
   - Mostrar cómo ver el acumulado de octubre, noviembre o el total general.
   - Ver el desglose: hacer clic en cualquier remito para ver qué tareas incluía y la miniatura de la foto del remito en papel.
3. **Marcar remito como PAGADO:**
   - Si la empresa transfirió o pagó en efectivo, cambiar el estado de **PENDIENTE** a **PAGADO** con un simple clic. El saldo de la empresa se actualiza automáticamente.
4. **Descargar el Excel para enviar por mail/WhatsApp:**
   - En la pestaña "Ver Todos", presionar el botón verde **"Descargar Excel general"**.
   - Mostrar cómo el archivo generado ya viene listo con fecha, desglose de IVA y formato prolijo para presentar al contador o a la empresa.

---

### BLOQUE 4: CIERRE DE TURNO Y RESGUARDO (10 min)
1. **Copia de seguridad en 1 clic (Backup):**
   - Explicar la importancia de hacer un clic en el botón de **Backup (💾)** al terminar la semana o el turno.
   - Explicar que el sistema descarga un archivo comprimido `.zip` que contiene tanto la base de datos como todas las fotos de los remitos guardadas.
2. **Qué hacer si algo sale mal (Tranquilidad ante todo):**
   - Si se equivocó en el número de remito o la fecha: mostrar cómo editar la cabecera desde la tabla de remitos sin necesidad de borrar todo.
   - Si la página no responde: recargar con `F5`.
   - Mostrar el botón de **Modo Milagritos 🧚** para cambiar la estética visual si prefiere una interfaz personalizada.

---

## 3. CHECKLIST DE EVALUACIÓN PRÁCTICA (SIMULACIÓN FINAL)

Para confirmar que la capacitación fue exitosa, la operadora realizará **2 ejercicios reales por su cuenta** sin ayuda:

- [ ] **Ejercicio 1 (Carga completa):** Cargar un remito OI para "Transporte El Rápido", con 2 Parches, 1 Arme/Desarme, subir una foto de prueba y guardar.
- [ ] **Ejercicio 2 (Cobranza y Reporte):** Entrar al cliente, marcar el remito anterior como PAGADO y descargar el reporte en Excel.

---

## 4. MATERIAL DE APOYO ENTREGADO
1. **Manual de Usuario Oficial en PDF** (`MANUAL_DE_USUARIO_SG_GOMERIA.pdf`).
2. **Tarjeta plastificada de atajos rápidos** al lado del teclado con el usuario, la dirección web y los 3 pasos para emitir un remito.
