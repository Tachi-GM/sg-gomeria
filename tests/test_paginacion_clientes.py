"""Pruebas de la paginación de historiales de clientes y remitos."""

import unittest

from tests.support import app, obtener_conexion


class TestPaginacionHistorialClientes(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["usuario"] = "admin"
            session["rol"] = "admin"

        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO clientes (nom_cli, cuit, activo) VALUES (?, ?, 1)",
            ("Cliente Paginacion Test", "20-77777777-7"),
        )
        self.id_cliente = cursor.lastrowid

        for numero in range(1, 13):
            remito = "PG" + str(numero).zfill(6)
            cursor.execute(
                """
                INSERT INTO trabajos
                    (remito, fecha, id_cliente, total, estado, tipo, detalle)
                VALUES (?, ?, ?, ?, 'PENDIENTE', 'OI', ?)
                """,
                (
                    remito,
                    "2026-11-" + str(numero).zfill(2),
                    self.id_cliente,
                    numero * 1000,
                    "Remito de prueba " + str(numero),
                ),
            )
        conexion.commit()
        conexion.close()

    def tearDown(self):
        conexion = obtener_conexion()
        conexion.execute(
            "DELETE FROM trabajos WHERE id_cliente = ?", (self.id_cliente,)
        )
        conexion.execute(
            "DELETE FROM clientes WHERE id_cliente = ?", (self.id_cliente,)
        )
        conexion.commit()
        conexion.close()

    def test_historial_muestra_diez_y_conserva_total_completo(self):
        respuesta = self.client.get(
            "/historial-cliente?id_cliente=" + str(self.id_cliente)
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data.count(b'class="fila-remito"'), 10)
        self.assertIn(b"12 remito(s) en este historial", respuesta.data)
        self.assertIn(b"Cargar 10 remitos m", respuesta.data)
        self.assertIn(
            (
                b"Este remito corresponde al historial anterior al "
                b"registro detallado de tareas."
            ),
            respuesta.data,
        )

    def test_clientes_no_supera_seis_empresas_y_diez_remitos(self):
        respuesta = self.client.get("/clientes")
        self.assertEqual(respuesta.status_code, 200)
        self.assertLessEqual(respuesta.data.count(b"tarjeta-empresa"), 6)
        self.assertEqual(respuesta.data.count(b'class="fila-remito"'), 10)
        self.assertIn(b"Cargar 10 remitos m", respuesta.data)

    def test_busqueda_encuentra_cliente_coincidente(self):
        respuesta = self.client.get("/clientes?buscar=Paginacion")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Cliente Paginacion Test", respuesta.data)

    def test_endpoint_carga_los_dos_remitos_restantes(self):
        respuesta = self.client.get(
            "/clientes/remitos-pagina?id_cliente="
            + str(self.id_cliente)
            + "&periodo=todos&offset=10"
        )
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.get_json()
        self.assertEqual(datos["cantidad_cargada"], 2)
        self.assertFalse(datos["hay_mas"])
        self.assertIn("PG000001", datos["html"])
        self.assertIn("PG000002", datos["html"])

    def test_manual_usuario_entrega_pdf(self):
        respuesta = self.client.get("/manual")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.mimetype, "application/pdf")
        self.assertTrue(respuesta.data.startswith(b"%PDF"))

    def test_endpoint_rechaza_offset_invalido(self):
        respuesta = self.client.get(
            "/clientes/remitos-pagina?id_cliente="
            + str(self.id_cliente)
            + "&offset=no-es-numero"
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_endpoint_rechaza_offset_negativo(self):
        respuesta = self.client.get(
            "/clientes/remitos-pagina?id_cliente="
            + str(self.id_cliente)
            + "&offset=-1"
        )
        self.assertEqual(respuesta.status_code, 400)


if __name__ == "__main__":
    unittest.main()
