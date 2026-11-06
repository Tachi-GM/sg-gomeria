# Diagramas Técnicos: Entidad-Relación y Casos de Uso
**Sistema de Gestión — Gomería "El Puente"**  
*Cátedras: Programación 4 & Gestión de Desarrollo de Software (UTN FRGP)*

---

## 1. DIAGRAMA ENTIDAD-RELACIÓN (MER / DER)

Este modelo refleja con precisión el esquema relacional implementado en **SQLite 3** (`database/init_db.py`), incluyendo claves primarias, claves foráneas, reglas de integridad referencial (`ON DELETE`) y campos de negocio clave (listas L1-L3, condición de IVA, fotos de remitos y tareas temporales).

```mermaid
erDiagram
    CLIENTES ||--o{ VEHICULOS : "posee"
    CLIENTES ||--o{ TRABAJOS : "solicita"
    CLIENTES ||--o{ CHEQUES : "emite"
    VEHICULOS ||--o{ TRABAJOS : "asignado_en"
    
    TRABAJOS ||--|{ DETALLE_TRABAJOS : "contiene"
    TAREAS ||--o{ DETALLE_TRABAJOS : "incluida_en"
    TRABAJOS ||--o{ DETALLE_TEMPORAL_TRABAJOS : "incluye_temporal"
    
    GOMEROS ||--o{ MOVIMIENTOS_GOMEROS : "registra"
    GOMEROS ||--o{ AUSENCIAS_GOMEROS : "acumula"

    CLIENTES {
        int id_cliente PK
        string nom_cli
        string cuit UK
        string tel
        string mail
        int con_iva "0 o 1"
        int lista_precios "1, 2 o 3"
    }

    VEHICULOS {
        int id_vehiculo PK
        string patente UK
        int id_cliente FK "ON DELETE CASCADE"
    }

    TAREAS {
        int id_tarea PK
        string nom_tar UK
        real precio "Lista 1 - Base"
        real precio2 "Lista 2 - Flota"
        real precio3 "Lista 3 - Cta Cte"
        int activa "0 o 1"
    }

    TRABAJOS {
        int id_trabajo PK
        string remito UK "XXXXX o 00XXXX"
        string fecha "YYYY-MM-DD"
        int id_cliente FK "ON DELETE RESTRICT"
        int id_vehiculo FK "ON DELETE SET NULL"
        real total ">= 0"
        string estado "PENDIENTE, EN PROCESO, PAGADO"
        string tipo "OI o OIB"
        string detalle "Observaciones"
        string foto_remito "Ruta archivo seguro"
        int con_iva "0 o 1"
    }

    DETALLE_TRABAJOS {
        int id_detalle PK
        int id_trabajo FK "ON DELETE CASCADE"
        int id_tarea FK "ON DELETE RESTRICT"
        int cantidad ">= 1"
        real precio_unitario
        real subtotal
    }

    DETALLE_TEMPORAL_TRABAJOS {
        int id_detalle_temporal PK
        int id_trabajo FK "ON DELETE CASCADE"
        string nombre_tarea
        int cantidad ">= 1"
        real precio_unitario
        real subtotal
    }

    CHEQUES {
        int id_cheque PK
        string numero
        string cliente
        string banco
        string fecha_emision
        string fecha_pago
        real importe
        string estado "Pendiente, Cobrado, Rechazado"
        string endosado "Detalle tercero"
        int id_cliente FK "ON DELETE RESTRICT"
    }

    USUARIOS {
        int id_usuario PK
        string usuario UK
        string contraseña "Hash seguro Werkzeug"
        string rol "usuario o admin"
    }

    GOMEROS {
        int id_gomero PK
        string nombre UK
        int sueldo_semanal "Base"
    }

    MOVIMIENTOS_GOMEROS {
        int id_movimiento PK
        int id_gomero FK "ON DELETE CASCADE"
        string tipo "adelanto o gasto"
        int monto
        string descripcion
        string fecha
    }

    AUSENCIAS_GOMEROS {
        int id PK
        int gomero_id FK "ON DELETE CASCADE"
        string fecha "YYYY-MM-DD"
        string created_at
    }
```

### Relaciones y Cardinalidades Clave:
1. **`CLIENTES (1) — (N) TRABAJOS`:** Un cliente puede tener múltiples remitos emitidos. Integridad `RESTRICT` para no borrar un cliente con historial facturado.
2. **`TRABAJOS (1) — (N) DETALLE_TRABAJOS`:** Estructura maestro-detalle donde cada renglón referencia una tarea de tarifario. Borrado en cascada (`CASCADE`).
3. **`TRABAJOS (1) — (N) DETALLE_TEMPORAL_TRABAJOS`:** Servicios esporádicos cargados directamente en el remito sin alterar el catálogo de `TAREAS`.
4. **`GOMEROS (1) — (N) AUSENCIAS_GOMEROS / MOVIMIENTOS`:** Trazabilidad de días no trabajados y adelantos para la liquidación semanal automática.

---

## 2. DIAGRAMA DE CASOS DE USO (UML)

El sistema contempla dos actores principales autenticados (**Operador de Mostrador** y **Administrador / Dueño del Taller**), además del subsistema de persistencia/seguridad.

```mermaid
flowchart LR
    subgraph Actores
        Operador["👤 Operador de Mostrador<br/>(Rol: usuario)"]
        Admin["👑 Administrador / Dueño<br/>(Rol: admin)"]
    end

    subgraph "SG Gomería — Límite del Sistema"
        subgraph "Módulo Mostrador y Facturación"
            CU_Login(["Iniciar Sesión"]):::seguridad
            CU_Mataburros(["Confeccionar Remito<br/>(Mataburros OI/OIB)"]):::core
            CU_Foto(["Adjuntar Foto de Remito"]):::core
            CU_Temp(["Agregar Tarea Temporal"]):::core
            CU_EstadoRemito(["Actualizar Estado de Cobro<br/>(Pendiente / Pagado)"]):::core
            CU_EditarCabecera(["Corregir Cabecera Remito<br/>(Número / Fecha)"]):::core
        end

        subgraph "Módulo Clientes y Cuenta Corriente"
            CU_AltaCliente(["Dar de Alta Cliente"]):::clientes
            CU_BuscarCliente(["Buscar Empresa en Vivo"]):::clientes
            CU_Historial(["Consultar Historial Mensualizado"]):::clientes
            CU_Excel(["Exportar Cuenta a Excel"]):::clientes
        end

        subgraph "Módulo Cheques"
            CU_Cheque(["Registrar E-Check / Cheque"]):::cheques
            CU_CobroCheque(["Asentar Cobro o Endoso"]):::cheques
        end

        subgraph "Módulo Administración y Taller (Solo Admin)"
            CU_Precios(["Gestionar 3 Listas de Precios<br/>(L1, L2, L3)"]):::admin
            CU_Gomeros(["Control Semanal de Gomeros"]):::admin
            CU_Ausencias(["Registrar Ausencias de Operarios"]):::admin
            CU_Usuarios(["Administrar Usuarios y Roles"]):::admin
            CU_Backup(["Descargar Backup Atómico ZIP<br/>(Base de Datos + Fotos)"]):::admin
        end
    end

    %% Relaciones Operador
    Operador --> CU_Login
    Operador --> CU_Mataburros
    Operador --> CU_BuscarCliente
    Operador --> CU_AltaCliente
    Operador --> CU_Historial
    Operador --> CU_EstadoRemito
    Operador --> CU_EditarCabecera
    Operador --> CU_Excel
    Operador --> CU_Cheque
    Operador --> CU_CobroCheque

    %% Relaciones Admin (Herencia de permisos + Exclusivos)
    Admin --> Operador
    Admin --> CU_Precios
    Admin --> CU_Gomeros
    Admin --> CU_Ausencias
    Admin --> CU_Usuarios
    Admin --> CU_Backup

    %% Inclusiones y Extensiones
    CU_Mataburros -.->|<<extend>>| CU_Foto
    CU_Mataburros -.->|<<extend>>| CU_Temp
    CU_Historial -.->|<<extend>>| CU_Excel

    classDef core fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0f172a;
    classDef clientes fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#0f172a;
    classDef cheques fill:#f3e8ff,stroke:#8b5cf6,stroke-width:1.5px,color:#0f172a;
    classDef admin fill:#ffedd5,stroke:#ea580c,stroke-width:1.5px,color:#0f172a;
    classDef seguridad fill:#f1f5f9,stroke:#64748b,stroke-width:1.5px,color:#0f172a;
```

### Especificación de Casos de Uso Principales:

| Caso de Uso | Actor | Precondición | Flujo Principal / Resultado |
| :--- | :--- | :--- | :--- |
| **Confeccionar Remito (Mataburros)** | Operador / Admin | Sesión iniciada | Selecciona cliente, carga número de remito (OI/OIB), selecciona lista (L1-L3), añade servicios, calcula IVA (21%) y guarda. Opcionalmente adjunta foto física del comprobante y tareas temporales. |
| **Actualizar Estado de Cobro** | Operador / Admin | Remito emitido | Conmuta estado entre `PENDIENTE` y `PAGADO` de forma asíncrona (AJAX/fetch) impactando de inmediato en el saldo mensual de la empresa. |
| **Exportar Cuenta a Excel** | Operador / Admin | Cliente seleccionado | Genera y descarga un libro `.xlsx` con el detalle histórico discriminado por mes, con subtotales, IVA y saldos. |
| **Control de Asistencia y Sueldos** | Solo Admin | Cierre de semana | Registra ausencias por día del gomero y el sistema descuenta proporcionalmente el valor del jornal sobre el sueldo semanal fijado. |
| **Descargar Backup Atómico** | Solo Admin | Permiso admin | SQLite ejecuta copia en caliente (`backup API`) y empaqueta la base junto a las fotos de remitos en un archivo `.zip` con timestamp descargable. |
