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

    # ------------------------------------------------------------------
    # Edición/baja de aguinaldos, ficha por gomero, planillas y fin de semana
    # Fechas fijas: lunes 16/11/2026 ... sábado 21/11/2026, domingo 22/11/2026
    # ------------------------------------------------------------------
    MIERCOLES = "2026-11-18"
    SABADO = "2026-11-21"
    DOMINGO = "2026-11-22"

    def _id_aguinaldo(self):
        conexion = obtener_conexion()
        try:
            return conexion.execute(
                "SELECT id_aguinaldo FROM aguinaldos WHERE id_gomero = ?", (self.id_gomero,)
            ).fetchone()["id_aguinaldo"]
        finally:
            conexion.close()

    def _id_movimiento(self, importe):
        conexion = obtener_conexion()
        try:
            return conexion.execute(
                "SELECT id_movimiento FROM movimientos_gomeros WHERE importe = ?", (importe,)
            ).fetchone()["id_movimiento"]
        finally:
            conexion.close()

    def test_sabado_y_domingo_solo_permiten_adelanto_de_aguinaldo(self):
        for dia in (self.SABADO, self.DOMINGO):
            with self.assertRaises(ErrorGomeros):
                registrar_movimiento("ADELANTO", dia, "10000", self.id_gomero, "SUELDO")
        registrar_movimiento("ADELANTO", self.SABADO, "10000", self.id_gomero,
                             "AGUINALDO", "2026-2")
        # El pago del sábado sigue permitido.
        registrar_movimiento("PAGO_SEMANAL", self.SABADO, "50000", self.id_gomero, "SUELDO")

    def test_no_se_puede_mover_un_adelanto_de_sueldo_a_sabado(self):
        from services.gomeros_service import actualizar_movimiento
        registrar_movimiento("ADELANTO", self.MIERCOLES, "10000", self.id_gomero, "SUELDO")
        with self.assertRaises(ErrorGomeros):
            actualizar_movimiento(self._id_movimiento(10000), self.SABADO, "10000", "")

    def test_corregir_importe_de_aguinaldo_60_por_600(self):
        from services.gomeros_service import actualizar_aguinaldo
        guardar_aguinaldo(self.id_gomero, "2026-2", "60000")
        actualizar_aguinaldo(self._id_aguinaldo(), "600000")
        self.assertEqual(obtener_resumen_aguinaldos()[0]["importe"], 600000)

    def test_corregir_aguinaldo_no_baja_de_lo_comprometido(self):
        from services.gomeros_service import actualizar_aguinaldo
        guardar_aguinaldo(self.id_gomero, "2026-2", "100000")
        registrar_movimiento("ADELANTO", self.MIERCOLES, "40000", self.id_gomero,
                             "AGUINALDO", "2026-2")
        with self.assertRaises(ErrorGomeros):
            actualizar_aguinaldo(self._id_aguinaldo(), "30000")

    def test_eliminar_aguinaldo_solo_si_esta_vacio(self):
        from services.gomeros_service import eliminar_aguinaldo
        guardar_aguinaldo(self.id_gomero, "2026-2", "100000")
        registrar_movimiento("ADELANTO", self.MIERCOLES, "40000", self.id_gomero,
                             "AGUINALDO", "2026-2")
        with self.assertRaises(ErrorGomeros):
            eliminar_aguinaldo(self._id_aguinaldo())
        # Un aguinaldo de otro período, sin nada asociado, sí se puede borrar.
        guardar_aguinaldo(self.id_gomero, "2026-1", "80000")
        conexion = obtener_conexion()
        try:
            vacio = conexion.execute(
                "SELECT id_aguinaldo FROM aguinaldos WHERE periodo_aguinaldo = '2026-1'"
            ).fetchone()["id_aguinaldo"]
        finally:
            conexion.close()
        eliminar_aguinaldo(vacio)
        self.assertEqual(len(obtener_resumen_aguinaldos()), 1)

    def test_corregir_y_eliminar_pago_de_aguinaldo(self):
        from services.gomeros_service import (
            actualizar_pago_aguinaldo, eliminar_pago_aguinaldo,
        )
        guardar_aguinaldo(self.id_gomero, "2026-2", "100000")
        registrar_pago_aguinaldo(self._id_aguinaldo(), self.MIERCOLES, "20000")
        conexion = obtener_conexion()
        try:
            id_pago = conexion.execute(
                "SELECT id_pago_aguinaldo FROM pagos_aguinaldo"
            ).fetchone()["id_pago_aguinaldo"]
        finally:
            conexion.close()
        actualizar_pago_aguinaldo(id_pago, self.MIERCOLES, "25000", "Corregido")
        self.assertEqual(obtener_resumen_aguinaldos()[0]["pagos"], 25000)
        with self.assertRaises(ErrorGomeros):
            actualizar_pago_aguinaldo(id_pago, self.MIERCOLES, "100001", "")
        eliminar_pago_aguinaldo(id_pago)
        self.assertEqual(obtener_resumen_aguinaldos()[0]["pagos"], 0)

    def test_eliminar_adelanto_de_aguinaldo_con_descuentos_depende_de_el(self):
        from services.gomeros_service import eliminar_movimiento
        registrar_movimiento("ADELANTO", self.MIERCOLES, "40000", self.id_gomero,
                             "AGUINALDO", "2026-2")
        registrar_movimiento("DESCUENTO_AGUINALDO", self.MIERCOLES, "30000",
                             self.id_gomero, "AGUINALDO", "2026-2")
        with self.assertRaises(ErrorGomeros):
            eliminar_movimiento(self._id_movimiento(40000))
        eliminar_movimiento(self._id_movimiento(30000))      # el descuento sí
        eliminar_movimiento(self._id_movimiento(40000))      # y ahora el adelanto
        with self.assertRaises(ErrorGomeros):
            eliminar_movimiento(self._id_movimiento_inexistente())

    def _id_movimiento_inexistente(self):
        return 999999

    def test_ficha_ordena_lo_mas_reciente_primero_e_incluye_ausencias(self):
        from services.gomeros_service import obtener_ficha_gomero
        registrar_movimiento("ADELANTO", "2026-11-09", "10000", self.id_gomero, "SUELDO")
        registrar_movimiento("ADELANTO", "2026-11-16", "20000", self.id_gomero, "SUELDO")
        registrar_movimiento("ADELANTO", self.MIERCOLES, "30000", self.id_gomero, "SUELDO")
        registrar_ausencia(self.id_gomero, "2026-11-17")
        ficha = obtener_ficha_gomero(self.id_gomero, hoy=date(2026, 11, 18))
        self.assertEqual([s["iso"] for s in ficha["semanas"]], ["2026-11-16", "2026-11-09"])
        semana = ficha["semanas"][0]
        self.assertEqual(semana["total_adelantos"], 50000)
        self.assertEqual(semana["cantidad_ausencias"], 1)
        self.assertEqual([e["fecha"] for e in semana["eventos"]],
                         [self.MIERCOLES, "2026-11-17", "2026-11-16"])
        self.assertEqual(ficha["adelantado_actual"], 50000)
        self.assertEqual(ficha["periodo_actual"], "2026-2")

    def test_ficha_agrupa_aguinaldos_aunque_no_tengan_importe(self):
        from services.gomeros_service import obtener_ficha_gomero
        registrar_movimiento("ADELANTO", self.SABADO, "10000", self.id_gomero,
                             "AGUINALDO", "2026-2")
        guardar_aguinaldo(self.id_gomero, "2026-1", "50000")
        ficha = obtener_ficha_gomero(self.id_gomero, hoy=date(2026, 11, 18))
        self.assertEqual([a["periodo"] for a in ficha["aguinaldos"]], ["2026-2", "2026-1"])
        self.assertIsNone(ficha["aguinaldos"][0]["importe"])
        self.assertEqual(ficha["aguinaldos"][0]["adelantos"], 10000)

    def test_planilla_semanal_calcula_total_resto_y_observaciones(self):
        from services.gomeros_service import obtener_planilla_semanal
        for dia in ("2026-11-16", "2026-11-17"):
            registrar_movimiento("ADELANTO", dia, "50000", self.id_gomero, "SUELDO",
                                 concepto="Comida" if dia == "2026-11-17" else "")
        registrar_ausencia(self.id_gomero, self.MIERCOLES)
        # El pago del sábado NO se resta en la planilla.
        registrar_movimiento("PAGO_SEMANAL", self.SABADO, "100000", self.id_gomero, "SUELDO")
        p = obtener_planilla_semanal(self.id_gomero, "2026-11-19")
        self.assertEqual([d["nombre"] for d in p["dias"]],
                         ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        self.assertEqual(p["total_adelantado"], 100000)
        self.assertEqual(p["descuento_ausencias"], round(260000 / 6))
        self.assertEqual(p["resto"], 260000 - round(260000 / 6) - 100000)
        textos = " | ".join(p["observaciones"])
        self.assertIn("Comida", textos)
        self.assertIn("Faltó el miércoles 18/11", textos)

    def test_planilla_aguinaldo_rango_y_totales(self):
        from services.gomeros_service import obtener_planilla_aguinaldo, rango_periodo_aguinaldo
        self.assertEqual(rango_periodo_aguinaldo("2026-1"), (date(2026, 1, 1), date(2026, 6, 30)))
        self.assertEqual(rango_periodo_aguinaldo("2026-2"), (date(2026, 7, 1), date(2026, 12, 31)))
        guardar_aguinaldo(self.id_gomero, "2026-2", "100000")
        registrar_movimiento("ADELANTO", self.MIERCOLES, "30000", self.id_gomero,
                             "AGUINALDO", "2026-2")
        registrar_pago_aguinaldo(self._id_aguinaldo(), self.SABADO, "20000")
        p = obtener_planilla_aguinaldo(self.id_gomero, "2026-2")
        self.assertEqual((p["total_adelantos"], p["total_pagos"], p["resto"]),
                         (30000, 20000, 50000))
        with self.assertRaises(ErrorGomeros):
            obtener_planilla_aguinaldo(self.id_gomero, "2026-3")

    def test_rutas_ficha_e_impresiones(self):
        guardar_aguinaldo(self.id_gomero, "2026-2", "100000")
        registrar_movimiento("ADELANTO", self.MIERCOLES, "30000", self.id_gomero, "SUELDO")
        for url in (
            f"/gomeros/{self.id_gomero}",
            f"/gomeros/{self.id_gomero}/imprimir/semana?semana={self.MIERCOLES}",
            f"/gomeros/{self.id_gomero}/imprimir/aguinaldo?periodo=2026-2",
        ):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200, url)
        self.assertEqual(self.client.get("/gomeros/999999").status_code, 404)
        self.assertEqual(
            self.client.get(f"/gomeros/{self.id_gomero}/imprimir/semana?semana=hola").status_code, 302
        )
        pagina = self.client.get(f"/gomeros/{self.id_gomero}/imprimir/semana?semana={self.MIERCOLES}")
        self.assertIn("$30.000", pagina.get_data(as_text=True))

    def test_rutas_editar_y_eliminar_aguinaldo_vuelven_a_la_seccion(self):
        guardar_aguinaldo(self.id_gomero, "2026-2", "60000")
        id_aguinaldo = self._id_aguinaldo()
        respuesta = self.client.post(f"/gomeros/aguinaldo/editar/{id_aguinaldo}",
                                     data={"importe": "600000", "semana": self.MIERCOLES})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers["Location"].endswith("#gestion-aguinaldos"))
        self.assertEqual(obtener_resumen_aguinaldos()[0]["importe"], 600000)
        self.client.post(f"/gomeros/aguinaldo/eliminar/{id_aguinaldo}",
                         data={"semana": self.MIERCOLES})
        self.assertEqual(obtener_resumen_aguinaldos(), [])

    def test_volver_a_solo_acepta_destinos_propios(self):
        guardar_aguinaldo(self.id_gomero, "2026-2", "60000")
        id_aguinaldo = self._id_aguinaldo()
        propio = self.client.post(f"/gomeros/aguinaldo/editar/{id_aguinaldo}", data={
            "importe": "70000", "volver_a": f"ficha:{self.id_gomero}", "ancla": "aguinaldo"})
        self.assertTrue(propio.headers["Location"].endswith(f"/gomeros/{self.id_gomero}#aguinaldo"))
        ajeno = self.client.post(f"/gomeros/aguinaldo/editar/{id_aguinaldo}", data={
            "importe": "80000", "volver_a": "https://sitio-malo.com", "ancla": "x\"><script>"})
        self.assertNotIn("sitio-malo", ajeno.headers["Location"])
        self.assertNotIn("script", ajeno.headers["Location"])

    def test_rutas_eliminar_movimiento_usa_el_servicio(self):
        registrar_movimiento("ADELANTO", self.MIERCOLES, "12345", self.id_gomero, "SUELDO")
        respuesta = self.client.post(
            f"/gomeros/movimiento/eliminar/{self._id_movimiento(12345)}",
            data={"semana": self.MIERCOLES})
        self.assertEqual(respuesta.status_code, 302)
        conexion = obtener_conexion()
        try:
            n = conexion.execute("SELECT COUNT(*) AS n FROM movimientos_gomeros").fetchone()["n"]
        finally:
            conexion.close()
        self.assertEqual(n, 0)

    def test_hoja_de_aguinaldo_no_muestra_fechas_del_semestre(self):
        guardar_aguinaldo(self.id_gomero, "2026-2", "100000")
        pagina = self.client.get(f"/gomeros/{self.id_gomero}/imprimir/aguinaldo?periodo=2026-2")
        html = pagina.get_data(as_text=True)
        self.assertEqual(pagina.status_code, 200)
        self.assertIn("CONTROL DE ADELANTOS DE AGUINALDO".lower(), html.lower())
        self.assertNotIn("SEMESTRE", html)
        self.assertNotIn("01/07/26", html)
        self.assertNotIn("31/12/26", html)


if __name__ == "__main__":
    unittest.main()
