"""Pruebas para el ciclo de vida, edición y estado de Clientes."""

import unittest
from tests.support import app, obtener_conexion


class TestGestionClientes(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin"
            sess["rol"] = "admin"

    def test_editar_cliente_exitoso(self):
        """Modifica datos de una empresa existente y verifica persistencia."""
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            """INSERT INTO clientes (nom_cli, cuit, tel, mail, con_iva, lista_precios, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)""",
            ("Empresa Inicial", "20-12345610-7", "11-2222", "ini@test.com", 1, 1),
        )
        id_cliente = cursor.lastrowid
        conexion.commit()
        conexion.close()

        resp = self.client.post(
            f"/editar-cliente/{id_cliente}",
            data={
                "nombre": "Empresa Modificada S.A.",
                "cuit": "20-12345610-7",
                "tel": "11-9999",
                "mail": "mod@test.com",
                "con_iva": "0",
                "lista_precios": "2",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        conexion = obtener_conexion()
        modificado = conexion.execute(
            "SELECT nom_cli, tel, mail, con_iva, lista_precios FROM clientes WHERE id_cliente = ?",
            (id_cliente,),
        ).fetchone()
        conexion.close()

        self.assertEqual(modificado["nom_cli"], "Empresa Modificada S.A.")
        self.assertEqual(modificado["tel"], "11-9999")
        self.assertEqual(modificado["mail"], "mod@test.com")
        self.assertEqual(modificado["con_iva"], 0)
        self.assertEqual(modificado["lista_precios"], 2)

    def test_editar_cliente_rechaza_cuit_duplicado(self):
        """Impide asignar un CUIT que ya pertenezca a otra empresa."""
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO clientes (nom_cli, cuit, activo) VALUES (?, ?, 1)",
            ("Empresa Dup A", "20-12345611-5"),
        )
        cursor.execute(
            "INSERT INTO clientes (nom_cli, cuit, activo) VALUES (?, ?, 1)",
            ("Empresa Dup B", "20-12345612-3"),
        )
        id_b = cursor.lastrowid
        conexion.commit()
        conexion.close()

        resp = self.client.post(
            f"/editar-cliente/{id_b}",
            data={
                "nombre": "Empresa Dup B Modificada",
                "cuit": "20-12345611-5",  # CUIT de Empresa Dup A
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ya pertenece a la empresa".encode("utf-8"), resp.data)

    def test_alternar_estado_cliente_ocultar_y_reactivar(self):
        """Oculta un cliente de mostrador (activo=0) y luego lo reactiva (activo=1)."""
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO clientes (nom_cli, cuit, activo) VALUES (?, ?, 1)",
            ("Empresa Ocultable XYZ", "20-12345613-1"),
        )
        id_cli = cursor.lastrowid
        conexion.commit()
        conexion.close()

        # 1. Ocultar cliente
        resp_ocultar = self.client.post(
            f"/alternar-cliente/{id_cli}", follow_redirects=True
        )
        self.assertEqual(resp_ocultar.status_code, 200)

        conexion = obtener_conexion()
        cli_oculto = conexion.execute(
            "SELECT activo FROM clientes WHERE id_cliente = ?", (id_cli,)
        ).fetchone()
        conexion.close()
        self.assertEqual(cli_oculto["activo"], 0)

        # 2. Verificar que NO aparece en Mataburros en el bloque de datos JSON de clientes
        resp_mataburros = self.client.get("/mataburros")
        self.assertEqual(resp_mataburros.status_code, 200)
        self.assertNotIn(b'"nom_cli": "Empresa Ocultable XYZ"', resp_mataburros.data)

        # 3. Reactivar cliente
        resp_reactivar = self.client.post(
            f"/alternar-cliente/{id_cli}", follow_redirects=True
        )
        self.assertEqual(resp_reactivar.status_code, 200)

        conexion = obtener_conexion()
        cli_activo = conexion.execute(
            "SELECT activo FROM clientes WHERE id_cliente = ?", (id_cli,)
        ).fetchone()
        conexion.close()
        self.assertEqual(cli_activo["activo"], 1)

        # 4. Ahora SÍ debe aparecer en Mataburros
        resp_mataburros_2 = self.client.get("/mataburros")
        self.assertIn(b'"nom_cli": "Empresa Ocultable XYZ"', resp_mataburros_2.data)


if __name__ == "__main__":
    unittest.main()
