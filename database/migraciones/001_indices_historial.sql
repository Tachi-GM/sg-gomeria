-- Migración 001: índices para el historial de clientes y remitos.
-- Es idempotente: puede ejecutarse más de una vez sin duplicar índices.
-- Hacer un backup de la base antes de ejecutar este archivo.

CREATE INDEX IF NOT EXISTS idx_trabajos_fecha_id
    ON trabajos(fecha DESC, id_trabajo DESC);

CREATE INDEX IF NOT EXISTS idx_trabajos_cliente_fecha_id
    ON trabajos(id_cliente, fecha DESC, id_trabajo DESC);

CREATE INDEX IF NOT EXISTS idx_detalle_trabajos_id_trabajo
    ON detalle_trabajos(id_trabajo);

CREATE INDEX IF NOT EXISTS idx_detalle_temporal_id_trabajo
    ON detalle_temporal_trabajos(id_trabajo);
