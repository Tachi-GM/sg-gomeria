"""Pruebas del formato argentino (puntos de miles y coma decimal) en los campos de importe."""

import unittest

from tests.support import app, obtener_conexion
from services.gomeros_service import ErrorGomeros, _importe


class TestImportesArgentinos(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"
        self._limpiar()

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        conexion = obtener_conexion()
        try:
            conexion.execute("DELETE FROM tareas WHERE nom_tar LIKE 'ZZ Formato%'")
            conexion.commit()
        finally:
            conexion.close()

    def _precios(self, nombre):
        conexion = obtener_conexion()
        try:
            fila = conexion.execute(
                "SELECT id_tarea, precio, precio2, precio3 FROM tareas WHERE nom_tar = ?", (nombre,)).fetchone()
            return fila
        finally:
            conexion.close()

    def test_gomeros_lee_importes_enteros_a_la_argentina(self):
        self.assertEqual(_importe("1.250.000"), 1250000)
        self.assertEqual(_importe("50000"), 50000)
        self.assertEqual(_importe("300.000"), 300000)
        self.assertEqual(_importe("1.250,00"), 1250)
        for malo in ("1.250,50", "abc", "", "0", "-5"):
            with self.subTest(valor=malo):
                with self.assertRaises(ErrorGomeros):
                    _importe(malo)

    def test_tarea_nueva_con_precios_escritos_a_la_argentina(self):
        self.client.post("/agregar-tarea", data={
            "nombre": "ZZ Formato Uno", "precio1-form": "1.250,50", "precio2-form": "2.000", "precio3-form": "3.500.000"})
        fila = self._precios("ZZ Formato Uno")
        self.assertEqual((fila["precio"], fila["precio2"], fila["precio3"]), (1250.5, 2000.0, 3500000.0))

    def test_modificar_tarea_con_formato_argentino(self):
        self.client.post("/agregar-tarea", data={"nombre": "ZZ Formato Dos", "precio1-form": "100"})
        id_tarea = self._precios("ZZ Formato Dos")["id_tarea"]
        self.client.post("/modificar-tarea", data={
            "id_tarea": id_tarea, "nombre": "ZZ Formato Dos", "precio1": "12.345,67", "precio2": "20.000", "precio3": "30.000"})
        fila = self._precios("ZZ Formato Dos")
        self.assertEqual((fila["precio"], fila["precio2"], fila["precio3"]), (12345.67, 20000.0, 30000.0))

    def test_las_pantallas_usan_campos_con_formato(self):
        for url, esperado in (("/gomeros", 'data-importe-ar="entero"'), ("/precios", "data-importe-ar"),
                              ("/mataburros", "data-importe-ar"), ("/cheques", "data-importe-ar")):
            html = self.client.get(url).get_data(as_text=True)
            self.assertIn(esperado, html, url)
            self.assertIn("formato-importes.js", html, url)
        self.assertNotIn('name="importe" type="number"', self.client.get("/gomeros").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
