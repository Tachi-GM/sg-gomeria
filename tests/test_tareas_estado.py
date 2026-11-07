"""Pruebas para ocultar y reactivar tareas del catálogo."""

import unittest
from tests.support import app, obtener_conexion


class TestEstadoTareas(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin"
            sess["rol"] = "admin"

    def test_alternar_tarea_ocultar_y_reactivar(self):
        """Oculta una tarea del mostrador (activa=0) y luego la reactiva (activa=1)."""
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO tareas (nom_tar, precio, precio2, precio3, activa) VALUES (?, ?, ?, ?, 1)",
            ("Servicio Temporal de Prueba", 12000.0, 11000.0, 10000.0),
        )
        id_tarea = cursor.lastrowid
        conexion.commit()
        conexion.close()

        # 1. Ocultar tarea
        resp_ocultar = self.client.post(
            f"/alternar-tarea/{id_tarea}", follow_redirects=True
        )
        self.assertEqual(resp_ocultar.status_code, 200)

        conexion = obtener_conexion()
        tarea_oculta = conexion.execute(
            "SELECT activa FROM tareas WHERE id_tarea = ?", (id_tarea,)
        ).fetchone()
        conexion.close()
        self.assertEqual(tarea_oculta["activa"], 0)

        # 2. Verificar que NO aparece en Mataburros (<script id="tareas-data">)
        resp_mataburros = self.client.get("/mataburros")
        self.assertEqual(resp_mataburros.status_code, 200)
        self.assertNotIn(
            b'"nom_tar": "Servicio Temporal de Prueba"', resp_mataburros.data
        )

        # 3. Reactivar tarea
        resp_reactivar = self.client.post(
            f"/alternar-tarea/{id_tarea}", follow_redirects=True
        )
        self.assertEqual(resp_reactivar.status_code, 200)

        conexion = obtener_conexion()
        tarea_activa = conexion.execute(
            "SELECT activa FROM tareas WHERE id_tarea = ?", (id_tarea,)
        ).fetchone()
        conexion.close()
        self.assertEqual(tarea_activa["activa"], 1)

        # 4. Ahora SÍ debe aparecer en Mataburros
        resp_mataburros_2 = self.client.get("/mataburros")
        self.assertIn(
            b'"nom_tar": "Servicio Temporal de Prueba"', resp_mataburros_2.data
        )


if __name__ == "__main__":
    unittest.main()
