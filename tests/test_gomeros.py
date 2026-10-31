"""Pruebas del control semanal de sueldos y movimientos de gomeros."""
import unittest
from datetime import date, timedelta

from tests.support import app, obtener_conexion
from services.gomeros_service import (
    ErrorGomeros, guardar_gomero, registrar_movimiento, obtener_resumen,
    registrar_ausencia, eliminar_ausencia,
)


class TestControlGomeros(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"
        conexion = obtener_conexion()
        try:
            conexion.execute("DELETE FROM ausencias_gomeros")
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
            conexion.execute("DELETE FROM ausencias_gomeros")
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

    def test_usuario_comun_puede_ver_control(self):
        with self.client.session_transaction() as sesion:
            sesion["rol"] = "usuario"
        respuesta = self.client.get("/gomeros")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Control semanal de gomeros", respuesta.data)

    def test_usuario_no_autenticado_es_redirigido(self):
        with self.client.session_transaction() as sesion:
            sesion.clear()
        respuesta = self.client.get("/gomeros")
        self.assertEqual(respuesta.status_code, 302)

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

    def test_sin_ausencias_conserva_sueldo_completo(self):
        fila = obtener_resumen(date.today().isoformat())["gomeros"][0]
        self.assertEqual(fila["descuento_ausencias"], 0)
        self.assertEqual(fila["saldo"], 260000)

    def test_una_dos_y_seis_ausencias_descuentan_sin_error_acumulado(self):
        lunes = date.fromisoformat(date.today().isoformat())
        lunes = lunes - timedelta(days=lunes.weekday())
        for cantidad in (1, 2, 6):
            for numero in range(cantidad):
                registrar_ausencia(
                    self.id_gomero,
                    (lunes + timedelta(days=numero)).isoformat(),
                )
            fila = obtener_resumen(lunes.isoformat())["gomeros"][0]
            self.assertEqual(fila["descuento_ausencias"], round(260000 * cantidad / 6))
            self.assertEqual(fila["saldo"], 260000 - round(260000 * cantidad / 6))
            conexion = obtener_conexion()
            conexion.execute("DELETE FROM ausencias_gomeros WHERE gomero_id = ?", (self.id_gomero,))
            conexion.commit()
            conexion.close()

    def test_ausencia_es_idempotente_y_se_puede_eliminar(self):
        fecha = date.today().isoformat()
        registrar_ausencia(self.id_gomero, fecha)
        registrar_ausencia(self.id_gomero, fecha)
        conexion = obtener_conexion()
        total = conexion.execute(
            "SELECT COUNT(*) FROM ausencias_gomeros WHERE gomero_id = ? AND fecha = ?",
            (self.id_gomero, fecha),
        ).fetchone()[0]
        conexion.close()
        self.assertEqual(total, 1)
        eliminar_ausencia(self.id_gomero, fecha)
        self.assertEqual(
            obtener_resumen(fecha)["gomeros"][0]["descuento_ausencias"], 0
        )

    def test_ausencia_de_otra_semana_no_afecta(self):
        fecha = date.today()
        semana_anterior = fecha - timedelta(days=7)
        registrar_ausencia(self.id_gomero, semana_anterior.isoformat())
        fila = obtener_resumen(fecha.isoformat())["gomeros"][0]
        self.assertEqual(fila["descuento_ausencias"], 0)

    def test_ausencia_de_otro_gomero_no_afecta(self):
        guardar_gomero("Otro Gomero Test", "260000")
        conexion = obtener_conexion()
        otro_id = conexion.execute(
            "SELECT id_gomero FROM gomeros WHERE nombre = ?", ("Otro Gomero Test",)
        ).fetchone()["id_gomero"]
        conexion.close()
        registrar_ausencia(otro_id, date.today().isoformat())
        fila = next(
            gomero
            for gomero in obtener_resumen(date.today().isoformat())["gomeros"]
            if gomero["id_gomero"] == self.id_gomero
        )
        self.assertEqual(fila["descuento_ausencias"], 0)

    def test_ausencia_reduce_limite_de_movimientos(self):
        registrar_ausencia(self.id_gomero, date.today().isoformat())
        with self.assertRaises(ErrorGomeros):
            registrar_movimiento("ADELANTO", date.today().isoformat(), "220000", self.id_gomero, "SUELDO")

    def test_ausencia_invalida_o_gomero_inexistente_falla(self):
        with self.assertRaises(ErrorGomeros):
            registrar_ausencia(999999, date.today().isoformat())
        with self.assertRaises(ErrorGomeros):
            registrar_ausencia(self.id_gomero, "31/10/2026")

    def test_ruta_ausencia_actualiza_saldo(self):
        fecha = date.today().isoformat()
        respuesta = self.client.post(
            "/gomeros/ausencia",
            data={
                "gomero_id": self.id_gomero,
                "fecha": fecha,
                "ausente": "true",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["descuento_ausencias"], round(260000 / 6))

        respuesta = self.client.post(
            "/gomeros/ausencia",
            data={
                "gomero_id": self.id_gomero,
                "fecha": fecha,
                "ausente": "false",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["descuento_ausencias"], 0)


if __name__ == "__main__":
    unittest.main()
