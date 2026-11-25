"""Pruebas de: importes a la argentina, remito con total directo, cheques sin fecha de
emisión y la etiqueta «Aceptado» de los remitos."""

import unittest

from tests.support import app, obtener_conexion
from services.trabajos_service import crear_trabajo_completo, ETIQUETA_TOTAL_DIRECTO
from utils.formateadores import (
    etiqueta_estado_remito,
    parse_float_seguro,
    parse_importe_ar,
)

REMITOS_PRUEBA = ("98001", "98002", "98003", "98004", "98005", "98006", "98007")


class TestParsersArgentinos(unittest.TestCase):
    def test_parse_importe_ar_entiende_puntos_de_miles_y_coma_decimal(self):
        casos = {
            "1.234.567,89": 1234567.89, "1234,5": 1234.5, "1.250": 1250.0,
            "1.250,00": 1250.0, "$ 500": 500.0, "1234.5": 1234.5, "0,5": 0.5, " 75 ": 75.0,
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(parse_importe_ar(texto), esperado)

    def test_parse_importe_ar_devuelve_el_valor_por_defecto_si_no_se_entiende(self):
        for texto in ("abc", "", None, "nan", "inf", "1,2,3x"):
            with self.subTest(texto=texto):
                self.assertIsNone(parse_importe_ar(texto, None))

    def test_parse_float_seguro_tambien_lee_punto_de_miles_con_coma_decimal(self):
        self.assertEqual(parse_float_seguro("1.234,56"), 1234.56)
        self.assertEqual(parse_float_seguro("1234,5"), 1234.5)
        self.assertEqual(parse_float_seguro("1234.5"), 1234.5)  # decimal con punto: igual que antes

    def test_etiqueta_aceptado(self):
        self.assertEqual(etiqueta_estado_remito("PENDIENTE"), "Aceptado")
        self.assertEqual(etiqueta_estado_remito("EN PROCESO"), "En proceso")
        self.assertEqual(etiqueta_estado_remito("PAGADO"), "Pagado")


class TestTotalDirecto(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"
        self.conexion = obtener_conexion()
        self._limpiar()
        self.conexion.execute(
            "INSERT INTO clientes (id_cliente, nom_cli, cuit, con_iva) "
            "VALUES (9996, 'Total Directo Con IVA', '20-00009996-3', 1)")
        self.conexion.execute(
            "INSERT INTO clientes (id_cliente, nom_cli, cuit, con_iva) "
            "VALUES (9997, 'Total Directo Sin IVA', '20-00009997-1', 0)")
        self.conexion.execute(
            "INSERT OR IGNORE INTO tareas (id_tarea, nom_tar, precio, precio2, precio3) "
            "VALUES (9997, 'Tarea Total Directo', 1000, 1000, 1000)")
        self.conexion.commit()

    def tearDown(self):
        self._limpiar()
        self.conexion.close()

    def _limpiar(self):
        marcas = ",".join("?" for _ in REMITOS_PRUEBA)
        ids = f"SELECT id_trabajo FROM trabajos WHERE remito IN ({marcas})"
        self.conexion.execute(f"DELETE FROM detalle_temporal_trabajos WHERE id_trabajo IN ({ids})", REMITOS_PRUEBA)
        self.conexion.execute(f"DELETE FROM detalle_trabajos WHERE id_trabajo IN ({ids})", REMITOS_PRUEBA)
        self.conexion.execute(f"DELETE FROM trabajos WHERE remito IN ({marcas})", REMITOS_PRUEBA)
        self.conexion.execute("DELETE FROM clientes WHERE id_cliente IN (9996, 9997)")
        self.conexion.execute("DELETE FROM tareas WHERE id_tarea = 9997")
        self.conexion.commit()

    def _crear(self, remito, cliente, total=None, tareas=(), cantidades=()):
        return crear_trabajo_completo(
            remito=remito, id_cliente=cliente, tipo_lista="1", tipo="OI", detalle="",
            tareas_raw=list(tareas), cantidades_raw=list(cantidades),
            fecha="2026-11-20", total_directo=total,
        )

    def _remito(self, remito):
        trabajo = self.conexion.execute(
            "SELECT id_trabajo, total FROM trabajos WHERE remito = ?", (remito,)).fetchone()
        renglones = self.conexion.execute(
            "SELECT nombre_tarea, cantidad, precio_unitario, subtotal "
            "FROM detalle_temporal_trabajos WHERE id_trabajo = ?", (trabajo["id_trabajo"],)).fetchall()
        return trabajo, renglones

    # ------------------------------------------------------------------ servicio
    def test_guarda_el_total_con_puntos_y_coma_en_un_renglon_unico(self):
        exito, mensaje = self._crear("98001", 9996, total="1.250.000,50")
        self.assertTrue(exito, mensaje)
        trabajo, renglones = self._remito("98001")
        self.assertEqual(trabajo["total"], 1250000.50)
        self.assertEqual(len(renglones), 1)
        self.assertEqual(renglones[0]["nombre_tarea"], ETIQUETA_TOTAL_DIRECTO)
        self.assertEqual(renglones[0]["subtotal"], 1250000.50)

    def test_cliente_sin_iva_no_divide_nada(self):
        exito, mensaje = self._crear("98002", 9997, total="121.000")
        self.assertTrue(exito, mensaje)
        self.assertEqual(self._remito("98002")[0]["total"], 121000.0)  # no 100.000

    def test_no_se_pueden_mezclar_tareas_y_total(self):
        exito, mensaje = self._crear("98003", 9996, total="5.000", tareas=["9997"], cantidades=["1"])
        self.assertFalse(exito)
        self.assertIn("no las dos cosas", mensaje)
        self.assertIsNone(self.conexion.execute(
            "SELECT 1 FROM trabajos WHERE remito = '98003'").fetchone())

    def test_sin_tareas_ni_total_sigue_rechazando(self):
        exito, mensaje = self._crear("98004", 9996)
        self.assertFalse(exito)
        self.assertIn("al menos una tarea válida", mensaje)

    def test_total_invalido_o_cero_se_rechaza(self):
        for total in ("0", "abc", "-100"):
            with self.subTest(total=total):
                exito, mensaje = self._crear("98005", 9996, total=total)
                self.assertFalse(exito)
                self.assertIn("no es válido", mensaje)

    def test_sin_total_directo_las_tareas_funcionan_como_siempre(self):
        exito, mensaje = self._crear("98006", 9996, tareas=["9997"], cantidades=["2"])
        self.assertTrue(exito, mensaje)
        self.assertEqual(self._remito("98006")[0]["total"], 2000.0)

    # ------------------------------------------------------------------ ruta y pantallas
    def test_la_ruta_enviar_trabajo_acepta_el_total_directo(self):
        respuesta = self.client.post("/enviar-trabajo", data={
            "remito": "98007", "tipo": "OI", "empresa": "9996", "tipo_lista": "1",
            "fecha": "2026-11-20", "total_directo": "75.500,25", "tareas": [""], "cantidades": ["1"],
        }, follow_redirects=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Remito OI N° 98007 guardado", respuesta.get_data(as_text=True))
        self.assertEqual(self._remito("98007")[0]["total"], 75500.25)

    def test_nuevo_remito_muestra_el_campo_de_total_final(self):
        html = self.client.get("/mataburros").get_data(as_text=True)
        self.assertIn('name="total_directo"', html)
        self.assertIn("data-importe-ar", html)
        self.assertIn("formato-importes.js", html)

    def test_listado_de_remitos_muestra_aceptado_en_vez_de_pendiente(self):
        self._crear("98001", 9996, total="1.000")
        html = self.client.get("/clientes").get_data(as_text=True)
        self.assertIn('title="Aceptado"', html)
        self.assertNotIn('title="PENDIENTE"', html)


class TestChequesSinEmision(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"

    def test_pantalla_de_cheques_ya_no_pide_ni_muestra_la_emision(self):
        html = self.client.get("/cheques").get_data(as_text=True)
        self.assertNotIn("fecha_emision", html)
        self.assertNotIn("Emisión", html)
        self.assertIn('name="importe"', html)
        self.assertIn("data-importe-ar", html)

    def test_alta_de_cheque_sin_emision_con_importe_a_la_argentina(self):
        respuesta = self.client.post("/agregar-cheque", data={
            "numero": "CH-TD-0001", "cliente": "Cliente Cheque Sin Emision", "banco": "Banco Test",
            "fecha_pago": "2026-12-15", "importe": "125.000,50", "estado": "Pendiente", "endosado": "",
        })
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.get_json()
        self.assertEqual(datos["importe"], 125000.50)
        self.assertNotIn("fecha_emision", datos)
        conexion = obtener_conexion()
        try:
            fila = conexion.execute(
                "SELECT fecha_emision, importe FROM cheques WHERE id_cheque = ?", (datos["id_cheque"],)).fetchone()
            self.assertIsNone(fila["fecha_emision"])
            self.assertEqual(fila["importe"], 125000.50)
            conexion.execute("DELETE FROM cheques WHERE id_cheque = ?", (datos["id_cheque"],))
            conexion.execute("DELETE FROM clientes WHERE nom_cli = 'Cliente Cheque Sin Emision'")
            conexion.commit()
        finally:
            conexion.close()

    def test_alta_con_importe_invalido_se_rechaza(self):
        respuesta = self.client.post("/agregar-cheque", data={
            "numero": "CH-TD-0002", "cliente": "Alguien", "banco": "Banco Test",
            "fecha_pago": "2026-12-15", "importe": "abc",
        })
        self.assertEqual(respuesta.status_code, 400)


if __name__ == "__main__":
    unittest.main()
