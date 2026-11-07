"""Pruebas para el endpoint AJAX de validación de CUIT duplicado."""

import unittest
from tests.support import app, obtener_conexion


class TestValidarCuitAPI(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin"
            sess["rol"] = "admin"

        # Insertar un cliente con CUIT conocido para las pruebas
        con = obtener_conexion()
        con.execute(
            "INSERT INTO clientes (nom_cli, cuit, activo) VALUES (?, ?, 1)",
            ("Empresa Test CUIT", "20-11112222-9"),
        )
        con.commit()
        self.id_cliente = con.execute(
            "SELECT id_cliente FROM clientes WHERE cuit = ?",
            ("20-11112222-9",),
        ).fetchone()["id_cliente"]
        con.close()

    def tearDown(self):
        # Limpiar el cliente insertado en setUp
        con = obtener_conexion()
        con.execute(
            "DELETE FROM clientes WHERE cuit = ?", ("20-11112222-9",)
        )
        con.commit()
        con.close()

    def test_cuit_duplicado(self):
        """Un CUIT ya registrado devuelve exists=True."""
        resp = self.client.post(
            "/clientes/validar-cuit",
            json={"cuit": "20-11112222-9"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["exists"])
        self.assertIn("message", data)

    def test_cuit_libre(self):
        """Un CUIT no registrado devuelve exists=False."""
        resp = self.client.post(
            "/clientes/validar-cuit",
            json={"cuit": "30-22223333-4"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["exists"])

    def test_cuit_duplicado_excluyendo_id(self):
        """El mismo CUIT con su propio id_cliente no se considera duplicado."""
        resp = self.client.post(
            "/clientes/validar-cuit",
            json={"cuit": "20-11112222-9", "id_cliente": self.id_cliente},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["exists"])


if __name__ == "__main__":
    unittest.main()
