"""
Pruebas unitarias para la capa de servicios de Trabajos y Remitos (trabajos_service).
Verifica:
- Validaciones de entrada (cliente inexistente, tareas inválidas).
- Cálculo para clientes Con IVA (precio de lista pleno).
- Cálculo para clientes Sin IVA (descuento del 21% aplicado renglón por renglón).
- Coherencia exacta entre los subtotales de detalle_trabajos y el total de trabajos.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import obtener_conexion
from services.trabajos_service import crear_trabajo_completo


class TestTrabajosService(unittest.TestCase):
    def setUp(self):
        self.conexion = obtener_conexion()
        # Creamos registros semilla de prueba
        self.conexion.execute(
            "INSERT OR IGNORE INTO clientes (id_cliente, nom_cli, cuit, con_iva) "
            "VALUES (9998, 'Cliente Con IVA Test', '99-9998-9', 1)"
        )
        self.conexion.execute(
            "INSERT OR IGNORE INTO clientes (id_cliente, nom_cli, cuit, con_iva) "
            "VALUES (9999, 'Cliente Sin IVA Test', '99-9999-9', 0)"
        )
        self.conexion.execute(
            "INSERT OR IGNORE INTO tareas (id_tarea, nom_tar, precio, precio2, precio3) "
            "VALUES (9999, 'Tarea Test 1210', 1210.0, 1210.0, 1210.0)"
        )
        self.conexion.commit()

    def tearDown(self):
        cursor = self.conexion.cursor()
        cursor.execute(
            "DELETE FROM detalle_trabajos WHERE id_trabajo IN "
            "(SELECT id_trabajo FROM trabajos WHERE remito LIKE 'TEST-%')"
        )
        cursor.execute("DELETE FROM trabajos WHERE remito LIKE 'TEST-%'")
        cursor.execute("DELETE FROM clientes WHERE id_cliente IN (9998, 9999)")
        cursor.execute("DELETE FROM tareas WHERE id_tarea = 9999")
        self.conexion.commit()
        self.conexion.close()

    def test_cliente_inexistente_retorna_error(self):
        exito, msg = crear_trabajo_completo(
            "TEST-001", 888888, "1", "OI", "", ["9999"], ["1"]
        )
        self.assertFalse(exito)
        self.assertIn("Cliente inexistente", msg)

    def test_sin_tareas_validas_retorna_error(self):
        exito, msg = crear_trabajo_completo("TEST-002", 9998, "1", "OI", "", [], [])
        self.assertFalse(exito)
        self.assertIn("al menos una tarea válida", msg)

    def test_cliente_con_iva_guarda_precio_de_lista(self):
        exito, msg = crear_trabajo_completo(
            "TEST-IVA", 9998, "1", "OI", "Test Con IVA", ["9999"], ["2"]
        )
        self.assertTrue(exito)

        cursor = self.conexion.cursor()
        trabajo = cursor.execute(
            "SELECT id_trabajo, total FROM trabajos WHERE remito = 'TEST-IVA'"
        ).fetchone()
        self.assertIsNotNone(trabajo)
        self.assertEqual(trabajo["total"], 2420.0)

        detalle = cursor.execute(
            "SELECT precio_unitario, subtotal FROM detalle_trabajos WHERE id_trabajo = ?",
            (trabajo["id_trabajo"],),
        ).fetchone()
        self.assertEqual(detalle["precio_unitario"], 1210.0)
        self.assertEqual(detalle["subtotal"], 2420.0)

    def test_cliente_sin_iva_descuenta_iva_por_tarea(self):
        exito, msg = crear_trabajo_completo(
            "TEST-SINIVA", 9999, "1", "OI", "Test Sin IVA", ["9999"], ["2"]
        )
        self.assertTrue(exito)

        cursor = self.conexion.cursor()
        trabajo = cursor.execute(
            "SELECT id_trabajo, total FROM trabajos WHERE remito = 'TEST-SINIVA'"
        ).fetchone()
        self.assertIsNotNone(trabajo)

        # 1210 / 1.21 = 1000.0 por tarea, cantidad 2 = 2000.0
        self.assertEqual(trabajo["total"], 2000.0)

        detalle = cursor.execute(
            "SELECT precio_unitario, subtotal FROM detalle_trabajos WHERE id_trabajo = ?",
            (trabajo["id_trabajo"],),
        ).fetchone()
        # Verificar que el precio unitario y subtotal se guardaron ya netos sin IVA
        self.assertEqual(detalle["precio_unitario"], 1000.0)
        self.assertEqual(detalle["subtotal"], 2000.0)
        # La suma de los renglones coincide exactamente con el total del remito
        self.assertEqual(trabajo["total"], detalle["subtotal"])


if __name__ == "__main__":
    unittest.main()
