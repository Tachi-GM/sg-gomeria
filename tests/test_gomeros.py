"""Pruebas del control semanal de sueldos y movimientos de gomeros."""
import unittest
from datetime import date, timedelta

from tests.support import app, obtener_conexion
from services.gomeros_service import (
    ErrorGomeros, guardar_gomero, registrar_movimiento, obtener_resumen,
    registrar_ausencia, eliminar_ausencia, guardar_aguinaldo,
    registrar_pago_aguinaldo, obtener_resumen_aguinaldos, inicio_semana,
)


def _hoy():
    """Miércoles de la semana actual: un día hábil fijo, así los tests no
    dependen del día en que se ejecutan (sábado y domingo no admiten
    adelantos al sueldo)."""
    return inicio_semana(date.today()) + timedelta(days=2)


class TestControlGomeros(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"
        conexion = obtener_conexion()
        try:
            conexion.execute("DELETE FROM pagos_aguinaldo")
            conexion.execute("DELETE FROM aguinaldos")
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
            conexion.execute("DELETE FROM pagos_aguinaldo")
            conexion.execute("DELETE FROM aguinaldos")
            conexion.execute("DELETE FROM ausencias_gomeros")
            conexion.execute("DELETE FROM movimientos_gomeros")
            conexion.execute("DELETE FROM gomeros")
            conexion.commit()
        finally:
            conexion.close()

    def test_corregir_movimiento_actualiza_fecha_importe_y_concepto(self):
        fecha = _hoy().isoformat()
        registrar_movimiento("ADELANTO", fecha, "40000", self.id_gomero, "SUELDO", concepto="Adelanto")
        conexion = obtener_conexion()
        try:
            id_movimiento = conexion.execute(
                "SELECT id_movimiento FROM movimientos_gomeros WHERE id_gomero = ?",
                (self.id_gomero,),
            ).fetchone()["id_movimiento"]
        finally:
            conexion.close()

        nueva_fecha = (_hoy() - timedelta(days=1)).isoformat()
        from services.gomeros_service import actualizar_movimiento
        actualizar_movimiento(id_movimiento, nueva_fecha, "50000", "Corrección")

        conexion = obtener_conexion()
        try:
            movimiento = conexion.execute(
                "SELECT fecha, importe, concepto FROM movimientos_gomeros WHERE id_movimiento = ?",
                (id_movimiento,),
            ).fetchone()
        finally:
            conexion.close()
        self.assertEqual(movimiento["fecha"], nueva_fecha)
        self.assertEqual(movimiento["importe"], 50000)
        self.assertEqual(movimiento["concepto"], "Corrección")

    def test_corregir_movimiento_no_permite_superar_sueldo(self):
        fecha = _hoy().isoformat()
        registrar_movimiento("ADELANTO", fecha, "200000", self.id_gomero, "SUELDO")
        registrar_movimiento("ADELANTO", fecha, "30000", self.id_gomero, "SUELDO")
        conexion = obtener_conexion()
        try:
            id_movimiento = conexion.execute(
                "SELECT id_movimiento FROM movimientos_gomeros WHERE importe = 30000"
            ).fetchone()["id_movimiento"]
        finally:
            conexion.close()
        from services.gomeros_service import actualizar_movimiento
        with self.assertRaises(ErrorGomeros):
            actualizar_movimiento(id_movimiento, fecha, "70000", "No debe exceder")

    def test_ruta_editar_movimiento(self):
        fecha = _hoy().isoformat()
        registrar_movimiento("ADELANTO", fecha, "10000", self.id_gomero, "SUELDO")
        conexion = obtener_conexion()
        try:
            id_movimiento = conexion.execute(
                "SELECT id_movimiento FROM movimientos_gomeros WHERE id_gomero = ?",
                (self.id_gomero,),
            ).fetchone()["id_movimiento"]
        finally:
            conexion.close()
        respuesta = self.client.post(
            f"/gomeros/movimiento/editar/{id_movimiento}",
            data={"fecha": fecha, "importe": "15000", "concepto": "Ajustado",
                  "semana": fecha},
        )
        self.assertEqual(respuesta.status_code, 302)
        conexion = obtener_conexion()
        try:
            importe = conexion.execute(
                "SELECT importe FROM movimientos_gomeros WHERE id_movimiento = ?",
                (id_movimiento,),
            ).fetchone()["importe"]
        finally:
            conexion.close()
        self.assertEqual(importe, 15000)

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
        hoy = _hoy().isoformat()
        registrar_movimiento("ADELANTO", hoy, "40000", self.id_gomero, "SUELDO")
        resumen = obtener_resumen(hoy)
        fila = next(g for g in resumen["gomeros"] if g["id_gomero"] == self.id_gomero)
        self.assertEqual(fila["adelantos"], 40000)
        self.assertEqual(fila["saldo"], 220000)

    def test_adelanto_para_aguinaldo_no_reduce_sueldo(self):
        hoy = _hoy().isoformat()
        registrar_movimiento("ADELANTO", hoy, "30000", self.id_gomero, "AGUINALDO", f"{_hoy().year}-1")
        resumen = obtener_resumen(hoy)
        fila = next(g for g in resumen["gomeros"] if g["id_gomero"] == self.id_gomero)
        self.assertEqual(fila["saldo"], 260000)

    def test_no_permite_superar_sueldo_semanal(self):
        hoy = _hoy().isoformat()
        registrar_movimiento("ADELANTO", hoy, "200000", self.id_gomero, "SUELDO")
        with self.assertRaises(ErrorGomeros):
            registrar_movimiento("ADELANTO", hoy, "70000", self.id_gomero, "SUELDO")

    def test_gasto_general_no_afecta_sueldo(self):
        registrar_movimiento("GASTO_GENERAL", _hoy().isoformat(), "15000", concepto="Comida")
        resumen = obtener_resumen(_hoy().isoformat())
        self.assertEqual(resumen["total_gastos"], 15000)
        self.assertEqual(resumen["gomeros"][0]["saldo"], 260000)

    def test_no_permite_descontar_mas_aguinaldo_pendiente(self):
        with self.assertRaises(ErrorGomeros):
            registrar_movimiento("DESCUENTO_AGUINALDO", _hoy().isoformat(), "10000",
                                 self.id_gomero, "AGUINALDO", f"{_hoy().year}-1")

    def test_sin_ausencias_conserva_sueldo_completo(self):
        fila = obtener_resumen(_hoy().isoformat())["gomeros"][0]
        self.assertEqual(fila["descuento_ausencias"], 0)
        self.assertEqual(fila["saldo"], 260000)

    def test_una_dos_y_seis_ausencias_descuentan_sin_error_acumulado(self):
        lunes = date.fromisoformat(_hoy().isoformat())
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
        fecha = _hoy().isoformat()
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
        fecha = _hoy()
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
        registrar_ausencia(otro_id, _hoy().isoformat())
        fila = next(
            gomero
            for gomero in obtener_resumen(_hoy().isoformat())["gomeros"]
            if gomero["id_gomero"] == self.id_gomero
        )
        self.assertEqual(fila["descuento_ausencias"], 0)

    def test_ausencia_reduce_limite_de_movimientos(self):
        registrar_ausencia(self.id_gomero, _hoy().isoformat())
        with self.assertRaises(ErrorGomeros):
            registrar_movimiento("ADELANTO", _hoy().isoformat(), "220000", self.id_gomero, "SUELDO")

    def test_ausencia_invalida_o_gomero_inexistente_falla(self):
        with self.assertRaises(ErrorGomeros):
            registrar_ausencia(999999, _hoy().isoformat())
        with self.assertRaises(ErrorGomeros):
            registrar_ausencia(self.id_gomero, "31/10/2026")

    def test_ruta_ausencia_actualiza_saldo(self):
        fecha = _hoy().isoformat()
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


    def test_guardar_aguinaldo_crea_y_actualiza_un_periodo(self):
        guardar_aguinaldo(self.id_gomero, "2026-2", "200000")
        guardar_aguinaldo(self.id_gomero, "2026-2", "210000")
        resumen = obtener_resumen_aguinaldos()
        self.assertEqual(len(resumen), 1)
        self.assertEqual(resumen[0]["importe"], 210000)
        self.assertEqual(resumen[0]["saldo"], 210000)

    def test_aguinaldo_calcula_adelantos_descuentos_y_pagos(self):
        guardar_aguinaldo(self.id_gomero, "2026-2", "200000")
        registrar_movimiento(
            "ADELANTO", _hoy().isoformat(), "50000",
            self.id_gomero, "AGUINALDO", "2026-2",
        )
        registrar_movimiento(
            "DESCUENTO_AGUINALDO", _hoy().isoformat(), "20000",
            self.id_gomero, "AGUINALDO", "2026-2",
        )
        resumen = obtener_resumen_aguinaldos()[0]
        self.assertEqual(resumen["adelantos"], 50000)
        self.assertEqual(resumen["descuentos_aplicados"], 20000)
        self.assertEqual(resumen["adelantos_pendientes"], 30000)
        self.assertEqual(resumen["saldo"], 150000)

        conexion = obtener_conexion()
        try:
            id_aguinaldo = conexion.execute(
                "SELECT id_aguinaldo FROM aguinaldos WHERE id_gomero = ?",
                (self.id_gomero,),
            ).fetchone()["id_aguinaldo"]
        finally:
            conexion.close()
        registrar_pago_aguinaldo(id_aguinaldo, _hoy().isoformat(), "30000")
        resumen = obtener_resumen_aguinaldos()[0]
        self.assertEqual(resumen["pagos"], 30000)
        self.assertEqual(resumen["saldo"], 120000)

    def test_pago_aguinaldo_no_permite_superar_saldo(self):
        guardar_aguinaldo(self.id_gomero, "2026-2", "100000")
        registrar_movimiento(
            "ADELANTO", _hoy().isoformat(), "40000",
            self.id_gomero, "AGUINALDO", "2026-2",
        )
        conexion = obtener_conexion()
        try:
            id_aguinaldo = conexion.execute(
                "SELECT id_aguinaldo FROM aguinaldos WHERE id_gomero = ?",
                (self.id_gomero,),
            ).fetchone()["id_aguinaldo"]
        finally:
            conexion.close()
        with self.assertRaises(ErrorGomeros):
            registrar_pago_aguinaldo(id_aguinaldo, _hoy().isoformat(), "61000")

    def test_no_permite_reducir_aguinaldo_por_debajo_de_lo_comprometido(self):
        guardar_aguinaldo(self.id_gomero, "2026-2", "100000")
        registrar_movimiento(
            "ADELANTO", _hoy().isoformat(), "40000",
            self.id_gomero, "AGUINALDO", "2026-2",
        )
        with self.assertRaises(ErrorGomeros):
            guardar_aguinaldo(self.id_gomero, "2026-2", "30000")

    def test_aguinaldo_rechaza_periodo_invalido(self):
        with self.assertRaises(ErrorGomeros):
            guardar_aguinaldo(self.id_gomero, "2026-3", "100000")

    def test_rutas_guardar_aguinaldo_y_registrar_pago(self):
        respuesta = self.client.post(
            "/gomeros/aguinaldo/guardar",
            data={"id_gomero": self.id_gomero, "periodo_aguinaldo": "2026-2",
                  "importe": "100000", "semana": _hoy().isoformat()},
        )
        self.assertEqual(respuesta.status_code, 302)
        conexion = obtener_conexion()
        try:
            id_aguinaldo = conexion.execute(
                "SELECT id_aguinaldo FROM aguinaldos WHERE id_gomero = ?",
                (self.id_gomero,),
            ).fetchone()["id_aguinaldo"]
        finally:
            conexion.close()
        respuesta = self.client.post(
            "/gomeros/aguinaldo/pagar",
            data={"id_aguinaldo": id_aguinaldo, "fecha": _hoy().isoformat(),
                  "importe": "25000", "concepto": "Pago parcial",
                  "semana": _hoy().isoformat()},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(obtener_resumen_aguinaldos()[0]["saldo"], 75000)


if __name__ == "__main__":
    unittest.main()
