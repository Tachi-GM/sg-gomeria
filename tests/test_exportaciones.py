"""Pruebas de exportaciones mensuales de remitos."""

from io import BytesIO
from datetime import datetime
import unittest

from tests.support import TEST_DIR, app, obtener_conexion
from utils.exportadores import MESES


class TestExportacionesMensuales(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"

    def test_exportar_excel_general_con_pestanas_mensuales(self):
        respuesta = self.client.get("/exportar-cliente/1/excel")
        try:
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(
                respuesta.mimetype,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            self.assertTrue(respuesta.data.startswith(b"PK"))
            self.assertIn(
                "remitos_Toyota_"
                f"{MESES[datetime.now().strftime('%m')].lower()}_"
                f"{datetime.now().year}.xlsx",
                respuesta.headers["Content-Disposition"],
            )
            from openpyxl import load_workbook

            libro = load_workbook(BytesIO(respuesta.data))
            self.assertEqual(libro.sheetnames, ["Resumen", "Agosto"])
            self.assertEqual(
                libro["Agosto"]["A1"].value,
                "Toyota - Agosto",
            )
            self.assertTrue(libro["Agosto"].sheet_view.showGridLines)
            self.assertEqual(
                [celda.value for celda in libro["Agosto"][2]],
                ["OI N°", "Fecha", "Detalle", "Importe", "Total", "Pagado", "Saldo"],
            )
            self.assertEqual(libro["Agosto"]["B3"].number_format, "d-mmm")
            self.assertIsNone(libro["Agosto"]["C3"].value)
            self.assertEqual(libro["Agosto"]["A1"].font.name, "Arial")
            self.assertEqual(libro["Agosto"]["B3"].font.name, "Arial")
            self.assertEqual(libro["Agosto"]["D3"].value, "=E3/1.21")
            self.assertEqual(libro["Agosto"]["E3"].value, 60000)
            libro.close()
        finally:
            respuesta.close()

    def test_exportar_imagen_de_cliente_y_periodo(self):
        respuesta = self.client.get("/exportar-cliente/1/imagen?periodo=2026-08")
        try:
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.mimetype, "image/png")
            self.assertTrue(respuesta.data.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertIn(".png", respuesta.headers["Content-Disposition"])
        finally:
            respuesta.close()

    def test_exportacion_rechaza_sin_sesion(self):
        with self.client.session_transaction() as sesion:
            sesion.clear()
        respuesta = self.client.get(
            "/exportar-cliente/1/excel",
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login", respuesta.headers["Location"])

    def test_exportacion_excel_aplica_iva_y_pagado_segun_cliente(self):
        conexion = obtener_conexion()
        conexion.execute("UPDATE clientes SET con_iva = 0 WHERE id_cliente = 1")
        conexion.execute(
            "UPDATE trabajos SET estado = 'PAGADO' WHERE remito = ?", ("20213",)
        )
        conexion.commit()
        conexion.close()
        try:
            respuesta = self.client.get("/exportar-cliente/1/excel")
            from openpyxl import load_workbook

            libro = load_workbook(BytesIO(respuesta.data), data_only=False)
            hoja = libro["Agosto"]
            self.assertEqual(hoja["D3"].value, 60000)
            self.assertEqual(hoja["E3"].value, "=D3*1.21")
            self.assertEqual(hoja["F3"].value, "=D3")
            self.assertEqual(hoja["G3"].value, "=D3-F3")
            self.assertEqual(hoja["D6"].value, "subtotal")
            self.assertEqual(hoja["E6"].value, "=SUM(D3:D4)")
            self.assertEqual(hoja["D7"].value, "IVA")
            self.assertEqual(hoja["E7"].value, "=E8-E6")
            self.assertEqual(hoja["D8"].value, "Total")
            self.assertEqual(hoja["E8"].value, "=SUM(E3:E4)")
            libro.close()
        finally:
            conexion = obtener_conexion()
            conexion.execute("UPDATE clientes SET con_iva = 1 WHERE id_cliente = 1")
            conexion.execute(
                "UPDATE trabajos SET estado = 'PENDIENTE' WHERE remito = ?",
                ("20213",),
            )
            conexion.commit()
            conexion.close()

    def test_exportacion_omite_ruta_de_foto_insegura(self):
        conexion = obtener_conexion()
        conexion.execute(
            "UPDATE trabajos SET foto_remito = ? WHERE remito = ?",
            ("fotos_remitos/../sg_gomeria.db", "20213"),
        )
        conexion.commit()
        conexion.close()
        try:
            respuesta = self.client.get("/exportar-cliente/1/imagen?periodo=2026-08")
            self.assertEqual(respuesta.status_code, 200)
        finally:
            conexion = obtener_conexion()
            conexion.execute(
                "UPDATE trabajos SET foto_remito = NULL WHERE remito = ?",
                ("20213",),
            )
            conexion.commit()
            conexion.close()

    def test_exportacion_excel_omite_tareas_si_no_hay_detalle_original(self):
        conexion = obtener_conexion()
        conexion.execute(
            """
            INSERT INTO detalle_temporal_trabajos
                (id_trabajo, nombre_tarea, cantidad, precio_unitario, subtotal)
            SELECT id_trabajo, ?, ?, ?, ?
            FROM trabajos
            WHERE remito = ?
            """,
            ("Tarea temporal exportada", 2, 1250.0, 2500.0, "20213"),
        )
        conexion.commit()
        conexion.close()
        try:
            respuesta = self.client.get("/exportar-cliente/1/excel?periodo=2026-08")
            self.assertEqual(respuesta.status_code, 200)
            from openpyxl import load_workbook

            libro = load_workbook(BytesIO(respuesta.data), read_only=True)
            self.assertIsNone(libro["Agosto"]["C3"].value)
            libro.close()
        finally:
            conexion = obtener_conexion()
            conexion.execute(
                """
                DELETE FROM detalle_temporal_trabajos
                WHERE id_trabajo = (
                    SELECT id_trabajo FROM trabajos WHERE remito = ?
                ) AND nombre_tarea = ?
                """,
                ("20213", "Tarea temporal exportada"),
            )
            conexion.commit()
            conexion.close()

    def test_exportacion_incluye_foto_valida_en_la_imagen(self):
        from PIL import Image

        carpeta_fotos = TEST_DIR / "uploads" / "fotos_remitos"
        carpeta_fotos.mkdir(parents=True, exist_ok=True)
        ruta_foto = carpeta_fotos / "exportacion.png"
        Image.new("RGB", (40, 30), "red").save(ruta_foto)

        conexion = obtener_conexion()
        conexion.execute(
            "UPDATE trabajos SET foto_remito = ? WHERE remito = ?",
            ("fotos_remitos/exportacion.png", "20213"),
        )
        conexion.commit()
        conexion.close()
        try:
            respuesta = self.client.get("/exportar-cliente/1/imagen?periodo=2026-08")
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.data.startswith(b"\x89PNG\r\n\x1a\n"))
        finally:
            conexion = obtener_conexion()
            conexion.execute(
                "UPDATE trabajos SET foto_remito = NULL WHERE remito = ?",
                ("20213",),
            )
            conexion.commit()
            conexion.close()
            ruta_foto.unlink(missing_ok=True)
            try:
                carpeta_fotos.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
