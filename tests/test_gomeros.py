"""Pruebas del control semanal de sueldos y movimientos de gomeros."""
import unittest
from datetime import date

from tests.support import app, obtener_conexion
from services.gomeros_service import (
    ErrorGomeros, guardar_gomero, registrar_movimiento, obtener_resumen,
)


class TestControlGomeros(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"
        conexion = obtener_conexion()
        try:
            conexion.execute("DELETE FROM movimientos_gomeros")
            conexion.execute("DELETE FROM gomeros")
            conexion.commit()
        finally:
            conexion.close()
        guardar_gomero("Test Sebastián", "260000")
        conexion = obtener_conexion()
        try:
            self.id_gomero = conexion.execute(
                "SELECT id_gomero FROM gomeros WHERE nombre = ?", ("Test Sebastián",)
            ).fetchone()["id_gomero"]
        finally:
            conexion.close()

    def tearDown(self):
        conexion = obtener_conexion()
        try:
            conexion.execute("DELETE FROM movimientos_gomeros")
            conexion.execute("DELETE FROM gomeros")
            conexion.commit()
        finally:
            conexion.close()

    def test_admin_puede_ver_control(self):
        respuesta = self.client.get("/gomeros")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Control semanal de gomeros", respuesta.data)
        self.assertIn(b"260.000", respuesta.data)

    def test_usuario_comun_no_puede_ver_control(self):
        with self.client.session_transaction() as sesion:
            sesion["rol"] = "usuario"
        self.assertEqual(self.client.get("/gomeros").status_code, 302)

    def test_adelanto_reduce_saldo_semanal(self):
        hoy = date.today().isoformat()
        registrar_movimiento("ADELANTO", hoy, "40000", self.id_gomero, "SUELDO")
        resumen = obtener_resumen(hoy)
        fila = next(g for g in resumen["gomeros"] if g["id_gomero"] == self.id_gomero)
        self.assertEqual(fila["adelantos"], 40000)
        self.assertEqual(fila["saldo"], 220000)

    def test_adelanto_para_aguinaldo_no_reduce_sueldo(self):
        hoy = date.today().isoformat()
        registrar_movimiento("ADELANTO", hoy, "30000", self.id_gomero, "AGUINALDO", f"{date.today().year}-1")
        resumen = obtener_resumen(hoy)
        fila = next(g for g in resumen["gomeros"] if g["id_gomero"] == self.id_gomero)
        self.assertEqual(fila["saldo"], 260000)

    def test_no_permite_superar_sueldo_semanal(self):
        hoy = date.today().isoformat()
        registrar_movimiento("ADELANTO", hoy, "200000", self.id_gomero, "SUELDO")
        with self.assertRaises(ErrorGomeros):
            registrar_movimiento("ADELANTO", hoy, "70000", self.id_gomero, "SUELDO")

    def test_gasto_general_no_afecta_sueldo(self):
        registrar_movimiento("GASTO_GENERAL", date.today().isoformat(), "15000", concepto="Comida")
        resumen = obtener_resumen(date.today().isoformat())
        self.assertEqual(resumen["total_gastos"], 15000)
        self.assertEqual(resumen["gomeros"][0]["saldo"], 260000)

    def test_no_permite_descontar_mas_aguinaldo_pendiente(self):
        with self.assertRaises(ErrorGomeros):
            registrar_movimiento("DESCUENTO_AGUINALDO", date.today().isoformat(), "10000",
                                 self.id_gomero, "AGUINALDO", f"{date.today().year}-1")


if __name__ == "__main__":
    unittest.main()
