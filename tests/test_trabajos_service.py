"""
Pruebas unitarias para la capa de servicios de Trabajos y Remitos (trabajos_service),
así como funciones de estandarización y validación (formateadores).
Verifica:
- Validaciones de entrada (cliente inexistente, tareas inválidas, formatos de remito y CUIT).
- Cálculo para clientes Con IVA (precio de lista pleno).
- Cálculo para clientes Sin IVA (descuento del 21% aplicado renglón por renglón).
- Edición de cabecera de remito (tipo, número, fecha) y control de unicidad.
- Asignación de fecha personalizada en emisión de remito.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.support import obtener_conexion
from services.trabajos_service import crear_trabajo_completo, editar_cabecera_remito
from utils.formateadores import validar_y_formatear_cuit, validar_y_formatear_remito


class TestTrabajosService(unittest.TestCase):
    def setUp(self):
        self.conexion = obtener_conexion()
        self._limpiar_datos_prueba()

        # Creamos registros semilla de prueba con CUITs válidos y únicos
        self.conexion.execute(
            "INSERT INTO clientes (id_cliente, nom_cli, cuit, con_iva) "
            "VALUES (9998, 'Cliente Con IVA Test', '20-00009998-9', 1)"
        )
        self.conexion.execute(
            "INSERT INTO clientes (id_cliente, nom_cli, cuit, con_iva) "
            "VALUES (9999, 'Cliente Sin IVA Test', '20-00009999-7', 0)"
        )
        self.conexion.execute(
            "INSERT OR IGNORE INTO tareas (id_tarea, nom_tar, precio, precio2, precio3) "
            "VALUES (9999, 'Tarea Test 1210', 1210.0, 1210.0, 1210.0)"
        )
        self.conexion.commit()

    def _limpiar_datos_prueba(self):
        cursor = self.conexion.cursor()
        cursor.execute("""
            DELETE FROM detalle_trabajos WHERE id_trabajo IN (
                SELECT id_trabajo FROM trabajos WHERE remito IN ('99001', '99002', '99003', '99004', '99005', '009001')
            )
        """)
        cursor.execute(
            "DELETE FROM trabajos WHERE remito IN ('99001', '99002', '99003', '99004', '99005', '009001')"
        )
        cursor.execute("DELETE FROM clientes WHERE id_cliente IN (9998, 9999)")
        cursor.execute("DELETE FROM tareas WHERE id_tarea = 9999")
        self.conexion.commit()

    def tearDown(self):
        self._limpiar_datos_prueba()
        self.conexion.close()

    def test_cliente_inexistente_retorna_error(self):
        exito, msg = crear_trabajo_completo(
            "99003", 888888, "1", "OI", "", ["9999"], ["1"]
        )
        self.assertFalse(exito)
        self.assertIn("Cliente inexistente", msg)

    def test_sin_tareas_validas_retorna_error(self):
        exito, msg = crear_trabajo_completo("99004", 9998, "1", "OI", "", [], [])
        self.assertFalse(exito)
        self.assertIn("al menos una tarea válida", msg)

    def test_cliente_con_iva_guarda_precio_de_lista(self):
        exito, msg = crear_trabajo_completo(
            "99001", 9998, "1", "OI", "Test Con IVA", ["9999"], ["2"]
        )
        self.assertTrue(exito)

        cursor = self.conexion.cursor()
        trabajo = cursor.execute(
            "SELECT id_trabajo, total FROM trabajos WHERE remito = '99001'"
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
            "99002", 9999, "1", "OI", "Test Sin IVA", ["9999"], ["2"]
        )
        self.assertTrue(exito)

        cursor = self.conexion.cursor()
        trabajo = cursor.execute(
            "SELECT id_trabajo, total FROM trabajos WHERE remito = '99002'"
        ).fetchone()
        self.assertIsNotNone(trabajo)

        # 1210 / 1.21 = 1000.0 por tarea, cantidad 2 = 2000.0
        self.assertEqual(trabajo["total"], 2000.0)

        detalle = cursor.execute(
            "SELECT precio_unitario, subtotal FROM detalle_trabajos WHERE id_trabajo = ?",
            (trabajo["id_trabajo"],),
        ).fetchone()
        self.assertEqual(detalle["precio_unitario"], 1000.0)
        self.assertEqual(detalle["subtotal"], 2000.0)
        self.assertEqual(trabajo["total"], detalle["subtotal"])

    def test_creacion_con_fecha_personalizada(self):
        exito, msg = crear_trabajo_completo(
            "99005",
            9998,
            "1",
            "OI",
            "Fecha pasada",
            ["9999"],
            ["1"],
            fecha="2026-05-15",
        )
        self.assertTrue(exito)
        cursor = self.conexion.cursor()
        trabajo = cursor.execute(
            "SELECT fecha FROM trabajos WHERE remito = '99005'"
        ).fetchone()
        self.assertEqual(trabajo["fecha"], "2026-05-15")

    def test_creacion_con_fecha_invalida_retorna_error(self):
        exito, msg = crear_trabajo_completo(
            "99005",
            9998,
            "1",
            "OI",
            "Fecha rota",
            ["9999"],
            ["1"],
            fecha="15/05/2026",
        )
        self.assertFalse(exito)
        self.assertIn("Formato de fecha inválido", msg)

    def test_editar_cabecera_remito_exitoso(self):
        exito_crear, _ = crear_trabajo_completo(
            "99001", 9998, "1", "OI", "Para editar", ["9999"], ["1"]
        )
        self.assertTrue(exito_crear)

        cursor = self.conexion.cursor()
        trabajo = cursor.execute(
            "SELECT id_trabajo FROM trabajos WHERE remito = '99001'"
        ).fetchone()
        id_trabajo = trabajo["id_trabajo"]

        exito_edit, msg_edit, nuevo_num = editar_cabecera_remito(
            id_trabajo, "OIB", "9001", "2026-06-20"
        )
        self.assertTrue(exito_edit)
        self.assertEqual(nuevo_num, "009001")

        trabajo_actualizado = cursor.execute(
            "SELECT tipo, remito, fecha FROM trabajos WHERE id_trabajo = ?",
            (id_trabajo,),
        ).fetchone()
        self.assertEqual(trabajo_actualizado["tipo"], "OIB")
        self.assertEqual(trabajo_actualizado["remito"], "009001")
        self.assertEqual(trabajo_actualizado["fecha"], "2026-06-20")

    def test_editar_cabecera_remito_duplicado_falla(self):
        crear_trabajo_completo(
            "99001", 9998, "1", "OI", "Primer remito", ["9999"], ["1"]
        )
        crear_trabajo_completo(
            "99002", 9998, "1", "OI", "Segundo remito", ["9999"], ["1"]
        )

        cursor = self.conexion.cursor()
        trabajo2 = cursor.execute(
            "SELECT id_trabajo FROM trabajos WHERE remito = '99002'"
        ).fetchone()

        # Intentar cambiar trabajo2 al remito 99001 que ya existe
        exito, msg, _ = editar_cabecera_remito(
            trabajo2["id_trabajo"], "OI", "99001", "2026-10-18"
        )
        self.assertFalse(exito)
        self.assertIn("Ya existe", msg)

    def test_editar_cabecera_inexistente_falla(self):
        exito, msg, _ = editar_cabecera_remito(9999999, "OI", "12345", "2026-10-18")
        self.assertFalse(exito)
        self.assertIn("no existe", msg)


class TestFormateadores(unittest.TestCase):
    def test_validar_y_formatear_cuit(self):
        # CUITs válidos
        valido, formato = validar_y_formatear_cuit("20123456786")
        self.assertTrue(valido)
        self.assertEqual(formato, "20-12345678-6")

        valido, formato = validar_y_formatear_cuit("30-99887766-7")
        self.assertTrue(valido)
        self.assertEqual(formato, "30-99887766-7")

        # CUITs inválidos
        self.assertFalse(validar_y_formatear_cuit("")[0])
        self.assertFalse(validar_y_formatear_cuit("12345")[0])
        self.assertFalse(validar_y_formatear_cuit("30-99887766-1")[0])

    def test_validar_y_formatear_remito_oi(self):
        valido, res = validar_y_formatear_remito("OI", "12345")
        self.assertTrue(valido)
        self.assertEqual(res, "12345")

        valido, res = validar_y_formatear_remito("OI", "421")
        self.assertTrue(valido)
        self.assertEqual(res, "00421")

        self.assertFalse(validar_y_formatear_remito("OI", "123456")[0])
        self.assertFalse(validar_y_formatear_remito("OI", "abc")[0])
        self.assertFalse(validar_y_formatear_remito("OI", "")[0])

    def test_validar_y_formatear_remito_oib(self):
        valido, res = validar_y_formatear_remito("OIB", "001234")
        self.assertTrue(valido)
        self.assertEqual(res, "001234")

        valido, res = validar_y_formatear_remito("OIB", "1234")
        self.assertTrue(valido)
        self.assertEqual(res, "001234")

        valido, res = validar_y_formatear_remito("OIB", "42")
        self.assertTrue(valido)
        self.assertEqual(res, "000042")

        self.assertFalse(validar_y_formatear_remito("OIB", "0012345")[0])
        self.assertFalse(validar_y_formatear_remito("OIB", "00abcd")[0])
        self.assertFalse(validar_y_formatear_remito("OIB", "")[0])

    def test_validar_remito_tipo_invalido(self):
        self.assertFalse(validar_y_formatear_remito("FACTURA", "12345")[0])


if __name__ == "__main__":
    unittest.main()
