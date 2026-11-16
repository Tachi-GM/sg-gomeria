-- =====================================================================
-- DATOS DE DEMOSTRACIÓN — SG Gomería "El Puente"
-- Todo es ficticio (empresas, CUIT, patentes, importes, cheques).
--
-- Cómo usarlo (DB Browser for SQLite):
--   1. Trabajá sobre una COPIA de la base (ej. sg_gomeria_demo.db).
--   2. Pestaña "Ejecutar SQL" > abrir este archivo > "Ejecutar todo" (Ctrl+Return).
--   3. Guardar los cambios con "Escribir cambios" (Ctrl+S).
--   Ejecutarlo UNA sola vez. Si algo sale mal: "Revertir cambios" y volver a empezar.
--
-- Resultado: 6 clientes, 14 tareas (13 activas), 24 remitos, 12 cheques,
-- 10 vehículos (7 nuevos), y movimientos de gomeros para la semana actual.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 0. ANONIMIZAR GOMEROS
--    La base actual tiene nombres y sueldos de empleados que parecen reales.
--    Se reemplazan por datos genéricos antes de subir nada a Git.
-- ---------------------------------------------------------------------
UPDATE gomeros
SET nombre = 'Gomero ' || id_gomero,
    sueldo_semanal = 300000;


-- ---------------------------------------------------------------------
-- 1. CLIENTES (3 nuevos)
--    CUIT ficticios con dígito verificador válido (módulo 11).
--    Variedad a propósito: listas L1/L2/L3 y clientes con y sin IVA.
-- ---------------------------------------------------------------------
INSERT INTO clientes (nom_cli, cuit, tel, mail, con_iva, lista_precios) VALUES
  ('Expreso Horizonte SA',      '30-90000041-9', '011-5555-0141', 'flota@horizonte.example.com',   1, 3),
  ('Distribuidora Pampa SRL',   '30-90000052-5', '011-5555-0152', 'taller@pampa.example.com',      0, 2),
  ('Transportes Del Plata SA',  '30-90000063-0', '03487-55-0163', 'compras@delplata.example.com',  1, 1);


-- ---------------------------------------------------------------------
-- 2. TAREAS (9 nuevas: quedan 14, de las cuales 13 activas)
--    Precio L2 = -10% y L3 = -20% respecto de L1, igual que las tareas existentes.
--    La última está inactiva a propósito: no aparece al cargar un remito.
-- ---------------------------------------------------------------------
INSERT INTO tareas (nom_tar, precio, precio2, precio3, activa) VALUES
  ('Montaje y desmontaje',          20000, 18000, 16000, 1),
  ('Reparación con parche',         12000, 10800,  9600, 1),
  ('Balanceo de rueda',              8000,  7200,  6400, 1),
  ('Alineación de tren delantero',  25000, 22500, 20000, 1),
  ('Cambio de cubierta de camión',  90000, 81000, 72000, 1),
  ('Inflado con nitrógeno',          3000,  2700,  2400, 1),
  ('Auxilio en ruta',               45000, 40500, 36000, 1),
  ('Reparación de llanta',          18000, 16200, 14400, 1),
  ('Recapado (discontinuado)',      70000, 63000, 56000, 0);


-- ---------------------------------------------------------------------
-- 3. VEHÍCULOS (patentes ficticias, vinculadas por CUIT del cliente)
-- ---------------------------------------------------------------------
WITH v(patente, cuit) AS (VALUES
  ('AC101DE', '30-90000041-9'),
  ('AC102DE', '30-90000041-9'),
  ('AD201FG', '30-90000052-5'),
  ('AD202FG', '30-90000052-5'),
  ('AE301HI', '30-90000063-0'),
  ('AA401JK', '30-65498712-3'),
  ('AB501LM', '30-71239845-9')
)
INSERT INTO vehiculos (patente, id_cliente)
SELECT v.patente, c.id_cliente
FROM v
JOIN clientes c ON c.cuit = v.cuit;


-- ---------------------------------------------------------------------
-- 4. REMITOS (22 nuevos; con los 2 existentes quedan 24)
--    Se insertan con total 0 y el total se calcula más abajo a partir de
--    los renglones. Mezcla de OI/OIB, de estados y de meses (ago-nov 2026).
-- ---------------------------------------------------------------------
WITH r(remito, tipo, fecha, cuit, patente, estado, detalle) AS (VALUES
  ('20440',  'OI',  '2026-08-24', '30-71239845-9', 'AE987ZA', 'PAGADO',     'Cambio de cubiertas del eje trasero'),
  ('20451',  'OI',  '2026-08-27', '30-65498712-3', 'AA401JK', 'PAGADO',     NULL),
  ('20468',  'OI',  '2026-08-31', '30-90000041-9', 'AC101DE', 'PAGADO',     'Servicio mensual de flota'),
  ('20503',  'OI',  '2026-09-02', '30-68312345-4', 'ABC123',  'PAGADO',     NULL),
  ('20517',  'OI',  '2026-09-04', '30-90000052-5', 'AD201FG', 'PAGADO',     NULL),
  ('20534',  'OI',  '2026-09-09', '30-71239845-9', 'AE987ZA', 'PAGADO',     'Camión con cubiertas gastadas'),
  ('20552',  'OI',  '2026-09-11', '30-90000063-0', 'AE301HI', 'PAGADO',     NULL),
  ('000141', 'OIB', '2026-09-15', '30-90000041-9', 'AC102DE', 'PAGADO',     'Trabajo adicional fuera del remito OI'),
  ('20589',  'OI',  '2026-09-18', '30-68312345-4', 'AF123JK', 'PAGADO',     NULL),
  ('20611',  'OI',  '2026-09-24', '30-65498712-3', 'AA401JK', 'PAGADO',     NULL),
  ('20640',  'OI',  '2026-09-29', '30-90000052-5', 'AD202FG', 'EN PROCESO', 'Pago parcial acordado con el cliente'),
  ('20672',  'OI',  '2026-10-02', '30-68312345-4', 'ABC123',  'PAGADO',     NULL),
  ('20693',  'OI',  '2026-10-07', '30-90000041-9', 'AC101DE', 'PENDIENTE',  'Cambio de cubiertas de camión'),
  ('000142', 'OIB', '2026-10-09', '30-90000063-0', 'AE301HI', 'PAGADO',     NULL),
  ('20718',  'OI',  '2026-10-14', '30-71239845-9', 'AE987ZA', 'EN PROCESO', NULL),
  ('20745',  'OI',  '2026-10-19', '30-65498712-3', 'AA401JK', 'PENDIENTE',  NULL),
  ('20771',  'OI',  '2026-10-23', '30-90000052-5', 'AD201FG', 'PENDIENTE',  NULL),
  ('20790',  'OI',  '2026-10-28', '30-68312345-4', 'AF123JK', 'PAGADO',     NULL),
  ('20812',  'OI',  '2026-11-03', '30-90000063-0', 'AE301HI', 'PENDIENTE',  'Auxilio en ruta, ruta 9'),
  ('000143', 'OIB', '2026-11-05', '30-71239845-9', 'AE987ZA', 'PENDIENTE',  NULL),
  ('20834',  'OI',  '2026-11-09', '30-90000041-9', 'AC102DE', 'PENDIENTE',  NULL),
  ('20851',  'OI',  '2026-11-12', '30-68312345-4', 'ABC123',  'PENDIENTE',  NULL)
)
INSERT INTO trabajos (remito, tipo, fecha, id_cliente, id_vehiculo, total, estado, detalle, con_iva)
SELECT r.remito, r.tipo, r.fecha, c.id_cliente, v.id_vehiculo, 0, r.estado, r.detalle, c.con_iva
FROM r
JOIN clientes c ON c.cuit = r.cuit
LEFT JOIN vehiculos v ON v.patente = r.patente
ORDER BY r.fecha, r.remito;


-- ---------------------------------------------------------------------
-- 5. RENGLONES DE CADA REMITO
--    El precio unitario sale de la lista del cliente (L1/L2/L3). Si el cliente
--    NO lleva IVA, se divide por 1,21: la misma regla que aplica la aplicación.
-- ---------------------------------------------------------------------
WITH d(remito, tarea, cantidad) AS (VALUES
  ('20440',  'Cambio de cubierta',            4), ('20440',  'Válvula nueva',                 4),
  ('20451',  'Pinchadura',                    3), ('20451',  'Rotación de neumáticos',        1),
  ('20468',  'Alineación y balanceo',         2), ('20468',  'Inflado con nitrógeno',         6),
  ('20503',  'Cambio de cubierta',            2), ('20503',  'Balanceo de rueda',             2),
  ('20517',  'Reparación con parche',         3), ('20517',  'Pinchadura',                    2),
  ('20534',  'Cambio de cubierta de camión',  2), ('20534',  'Montaje y desmontaje',          2),
  ('20552',  'Alineación de tren delantero',  1),
  ('000141', 'Auxilio en ruta',               1),
  ('20589',  'Rotación de neumáticos',        1), ('20589',  'Válvula nueva',                 2),
  ('20611',  'Cambio de cubierta',            3), ('20611',  'Alineación y balanceo',         1),
  ('20640',  'Reparación de llanta',          2), ('20640',  'Montaje y desmontaje',          2),
  ('20672',  'Pinchadura',                    1),
  ('20693',  'Cambio de cubierta de camión',  4), ('20693',  'Balanceo de rueda',             4),
  ('000142', 'Inflado con nitrógeno',         8),
  ('20718',  'Cambio de cubierta',            2), ('20718',  'Alineación de tren delantero',  1),
  ('20745',  'Pinchadura',                    4), ('20745',  'Válvula nueva',                 4),
  ('20771',  'Rotación de neumáticos',        2), ('20771',  'Reparación con parche',         2),
  ('20790',  'Cambio de cubierta',            1), ('20790',  'Montaje y desmontaje',          1), ('20790', 'Balanceo de rueda', 1),
  ('20812',  'Auxilio en ruta',               1), ('20812',  'Cambio de cubierta',            2),
  ('000143', 'Reparación de llanta',          1),
  ('20834',  'Cambio de cubierta de camión',  2), ('20834',  'Alineación y balanceo',         2),
  ('20851',  'Alineación de tren delantero',  1), ('20851',  'Rotación de neumáticos',        1), ('20851', 'Válvula nueva', 1)
)
INSERT INTO detalle_trabajos (id_trabajo, id_tarea, cantidad, precio_unitario, subtotal)
SELECT id_trabajo, id_tarea, cantidad, unitario, ROUND(unitario * cantidad, 2)
FROM (
  SELECT t.id_trabajo, ta.id_tarea, d.cantidad,
         CASE WHEN c.con_iva = 0
              THEN ROUND(CASE c.lista_precios WHEN 1 THEN ta.precio WHEN 2 THEN ta.precio2 ELSE ta.precio3 END / 1.21, 2)
              ELSE CASE c.lista_precios WHEN 1 THEN ta.precio WHEN 2 THEN ta.precio2 ELSE ta.precio3 END
         END AS unitario
  FROM d
  JOIN trabajos t  ON t.remito = d.remito
  JOIN clientes c  ON c.id_cliente = t.id_cliente
  JOIN tareas   ta ON ta.nom_tar = d.tarea
);

-- El total de cada remito nuevo = suma de sus renglones (los 2 remitos originales ya tienen total).
UPDATE trabajos
SET total = COALESCE((SELECT ROUND(SUM(subtotal), 2)
                      FROM detalle_trabajos dt
                      WHERE dt.id_trabajo = trabajos.id_trabajo), 0)
WHERE total = 0;


-- ---------------------------------------------------------------------
-- 6. CHEQUES (10 nuevos; con los 2 existentes quedan 12)
--    Estados Pendiente/Cobrado/Rechazado, algunos endosados, algunos a futuro.
-- ---------------------------------------------------------------------
WITH ch(numero, cuit, banco, fecha_emision, fecha_pago, importe, estado, endosado) AS (VALUES
  ('00412087', '30-71239845-9', 'Banco Santander', '2026-08-28', '2026-09-28', 185000.00, 'Cobrado',   ''),
  ('55210934', '30-65498712-3', 'Banco Nación',    '2026-09-01', '2026-10-01', 120000.00, 'Cobrado',   ''),
  ('77340218', '30-90000041-9', 'Banco Provincia', '2026-09-05', '2026-10-05', 310500.00, 'Cobrado',   'Proveedor Cubiertas SA'),
  ('00418855', '30-90000052-5', 'Banco Macro',     '2026-09-20', '2026-10-20',  96500.50, 'Rechazado', ''),
  ('88120045', '30-90000063-0', 'Banco Galicia',   '2026-10-02', '2026-11-02', 142000.00, 'Cobrado',   ''),
  ('66103377', '30-68312345-4', 'Banco ICBC',      '2026-10-10', '2026-11-10', 210000.00, 'Cobrado',   'Lubricantes del Centro SRL'),
  ('00419302', '30-71239845-9', 'Banco Credicoop', '2026-10-25', '2026-11-25', 240000.00, 'Pendiente', ''),
  ('99215566', '30-90000041-9', 'Banco BBVA',      '2026-11-02', '2026-12-02', 275000.00, 'Pendiente', 'Proveedor Cubiertas SA'),
  ('31405188', '30-65498712-3', 'Banco Santander', '2026-11-05', '2026-11-18',  88000.00, 'Pendiente', ''),
  ('00420011', '30-90000052-5', 'Banco Provincia', '2026-11-09', '2026-12-09', 130000.00, 'Pendiente', '')
)
INSERT INTO cheques (numero, cliente, banco, fecha_emision, fecha_pago, importe, estado, endosado, id_cliente)
SELECT ch.numero, c.nom_cli, ch.banco, ch.fecha_emision, ch.fecha_pago, ch.importe, ch.estado, ch.endosado, c.id_cliente
FROM ch
JOIN clientes c ON c.cuit = ch.cuit
ORDER BY ch.fecha_emision;


-- ---------------------------------------------------------------------
-- 7. GOMEROS: ausencias y movimientos de la semana (opcional)
--    Para que la pantalla de Gomeros no se vea vacía en la demo.
--    Si estos números no te cierran con lo que calcula la pantalla,
--    borrá todo este bloque 7: el resto de la base queda igual.
-- ---------------------------------------------------------------------
INSERT INTO ausencias_gomeros (gomero_id, fecha) VALUES
  (1, '2026-11-03'),
  (2, '2026-11-10'),
  (4, '2026-11-12');

-- Pago semanal de la semana anterior, uno por gomero
INSERT INTO movimientos_gomeros (id_gomero, tipo, fecha, importe, destino, concepto, usuario)
SELECT id_gomero, 'PAGO_SEMANAL', '2026-11-07', sueldo_semanal, 'SUELDO', 'Pago semanal', 'admin'
FROM gomeros;

-- Adelantos de esta semana
INSERT INTO movimientos_gomeros (id_gomero, tipo, fecha, importe, destino, concepto, usuario) VALUES
  (1, 'ADELANTO', '2026-11-10', 40000, 'SUELDO', 'Adelanto', 'admin'),
  (3, 'ADELANTO', '2026-11-11', 30000, 'SUELDO', 'Adelanto', 'admin'),
  (5, 'ADELANTO', '2026-11-12', 50000, 'SUELDO', 'Adelanto', 'admin'),
  (2, 'ADELANTO', '2026-11-13', 20000, 'SUELDO', 'Adelanto', 'admin');

-- Gastos generales de la gomería (sin gomero asignado)
INSERT INTO movimientos_gomeros (id_gomero, tipo, fecha, importe, destino, concepto, usuario) VALUES
  (NULL, 'GASTO_GENERAL', '2026-11-11', 25000, 'NO_APLICA', 'Comida de la semana',  'admin'),
  (NULL, 'GASTO_GENERAL', '2026-11-13', 18000, 'NO_APLICA', 'Gaseosas y consumos', 'admin');


-- ---------------------------------------------------------------------
-- 8. CONTROL: cantidades finales (mínimos pedidos: 3 clientes nuevos,
--    12 tareas, 20 remitos, 10 cheques)
-- ---------------------------------------------------------------------
SELECT 'clientes' AS tabla, COUNT(*) AS filas FROM clientes
UNION ALL SELECT 'tareas',     COUNT(*) FROM tareas
UNION ALL SELECT 'tareas activas', COUNT(*) FROM tareas WHERE activa = 1
UNION ALL SELECT 'remitos',    COUNT(*) FROM trabajos
UNION ALL SELECT 'renglones',  COUNT(*) FROM detalle_trabajos
UNION ALL SELECT 'cheques',    COUNT(*) FROM cheques
UNION ALL SELECT 'vehículos',  COUNT(*) FROM vehiculos
UNION ALL SELECT 'movimientos de gomeros', COUNT(*) FROM movimientos_gomeros;
