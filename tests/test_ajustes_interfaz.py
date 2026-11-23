"""Pruebas de los ajustes de interfaz: botón de manual, ojo de contraseña y botón de gomeros."""

import unittest

from tests.support import app


class TestAjustesInterfaz(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"

    def test_index_tiene_boton_de_manual_en_la_esquina_inferior_derecha(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/manual"', html)
        self.assertIn("bottom-0 end-0", html)

    def test_encabezado_ya_no_tiene_boton_de_manual(self):
        for url in ("/precios", "/clientes", "/gomeros"):
            html = self.client.get(url).get_data(as_text=True)
            self.assertNotIn("MANUAL", html, url)
            self.assertNotIn('href="/manual"', html, url)

    def test_login_tiene_ojo_para_ver_la_contrasena(self):
        anonimo = app.test_client()
        html = anonimo.get("/login").get_data(as_text=True)
        self.assertIn('data-ojo-clave="password"', html)
        self.assertIn("ver-contrasena.js", html)

    def test_usuarios_tiene_ojo_en_alta_y_en_edicion(self):
        html = self.client.get("/usuarios").get_data(as_text=True)
        self.assertIn('data-ojo-clave="nueva-clave"', html)
        self.assertIn('data-ojo-clave="clave-', html)

    def test_script_del_ojo_se_sirve(self):
        respuesta = self.client.get("/static/js/ver-contrasena.js")
        self.assertEqual(respuesta.status_code, 200)
        respuesta.close()

    def test_gomeros_muestra_boton_proximamente_deshabilitado(self):
        html = self.client.get("/gomeros").get_data(as_text=True)
        self.assertIn("Importar Excel de gomeros", html)
        self.assertIn("Próximamente", html)


if __name__ == "__main__":
    unittest.main()
