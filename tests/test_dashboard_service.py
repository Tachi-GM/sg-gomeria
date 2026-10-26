import unittest
from datetime import date

from tests.support import obtener_conexion
from services.dashboard_service import obtener_resumen_inicio


class TestDashboardService(unittest.TestCase):
    REMITOS_PRUEBA = ("77881", "77882", "77883")
    CHEQUES_PRUEBA = ("CH-DASH-1", "CH-DASH-2")

    def setUp(self):
        self.conexion = obtener_conexion()
        self._limpiar()
        self.resumen_base = obtener_resumen_inicio(date(2026, 10, 26))
        self.conexion.executemany(
            """
            INSERT INTO trabajos (remito, fecha, id_cliente, total, estado, tipo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("77881", "2026-10-10", 1, 12500.0, "PENDIENTE", "OI"),
                ("77882", "2026-10-12", 1, 8000.0, "EN PROCESO", "OI"),
                ("77883", "2026-09-30", 1, 9900.0, "PAGADO", "OI"),
            ],
        )
        self.conexion.executemany(
            """
            INSERT INTO cheques (
                numero, cliente, banco, fecha_pago, importe, estado, id_cliente
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("CH-DASH-1", "Toyota", "Banco Test", "2026-11-10", 5000.0, "Pendiente", 1),
                ("CH-DASH-2", "Toyota", "Banco Test", "2026-12-10", 7000.0, "Pendiente", 1),
            ],
        )
        self.conexion.commit()

    def tearDown(self):
        self._limpiar()
        self.conexion.close()

    def _limpiar(self):
        self.conexion.execute(
            "DELETE FROM trabajos WHERE remito IN (?, ?, ?)", self.REMITOS_PRUEBA
        )
        self.conexion.execute(
            "DELETE FROM cheques WHERE numero IN (?, ?)", self.CHEQUES_PRUEBA
        )
        self.conexion.commit()

    def test_obtener_resumen_inicio_calcula_metricas_reales(self):
        resumen = obtener_resumen_inicio(date(2026, 10, 26))

        self.assertEqual(
            resumen["remitos_pendientes"],
            self.resumen_base["remitos_pendientes"] + 2,
        )
        self.assertEqual(resumen["total_mes"], self.resumen_base["total_mes"] + 20500.0)
        self.assertEqual(
            resumen["cheques_por_vencer"],
            self.resumen_base["cheques_por_vencer"] + 1,
        )


if __name__ == "__main__":
    unittest.main()
