"""Pruebas del botón «Actualizar precios desde Excel» de la pantalla de Precios."""

import re
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from tests.support import app, get_db_path, obtener_conexion
from scripts.importar_precios import importar


def _excel(filas_por_lista, hojas=(1, 2, 3)):
    """Arma un .xlsx en memoria: una hoja «Lista N» por lista, con los encabezados reales."""
    libro = Workbook()
    libro.remove(libro.active)
    for numero in hojas:
        hoja = libro.create_sheet(f"Lista {numero}")
        hoja.append(["Descripción", "Precio sin IVA", "Precio final"])
        for descripcion, final in filas_por_lista.get(numero, []):
            hoja.append([descripcion, round(final / 1.21, 2), final])
    memoria = BytesIO()
    libro.save(memoria)
    return memoria.getvalue()


class TestImportarPreciosWeb(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"
        self._limpiar()
        conexion = obtener_conexion()
        try:
            conexion.execute(
                "INSERT INTO tareas (nom_tar, precio, precio2, precio3) VALUES (?, ?, ?, ?)",
                ("ZZ Importar Uno", 1000, 1100, 1200),
            )
            conexion.commit()
        finally:
            conexion.close()

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        conexion = obtener_conexion()
        try:
            conexion.execute("DELETE FROM tareas WHERE nom_tar LIKE 'ZZ Importar%' COLLATE NOCASE")
            conexion.commit()
        finally:
            conexion.close()

    def _precios(self, nombre):
        conexion = obtener_conexion()
        try:
            fila = conexion.execute(
                "SELECT precio, precio2, precio3 FROM tareas WHERE nom_tar = ?", (nombre,)
            ).fetchone()
            return None if fila is None else (fila["precio"], fila["precio2"], fila["precio3"])
        finally:
            conexion.close()

    def _backups(self):
        return list(Path(app.config["BACKUP_DIR"]).glob("antes_import_precios_*.db"))

    def _subir(self, contenido, nombre="precios.xlsx", cliente=None):
        cliente = cliente or self.client
        datos = {} if contenido is None else {"archivo": (BytesIO(contenido), nombre)}
        respuesta = cliente.post(
            "/precios/importar", data=datos, content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.get_data(as_text=True)

    # ------------------------------------------------------------------
    def test_pantalla_de_precios_muestra_el_boton(self):
        html = self.client.get("/precios").get_data(as_text=True)
        self.assertIn("Actualizar precios desde Excel", html)
        self.assertIn('enctype="multipart/form-data"', html)

    def test_actualiza_precios_crea_tareas_nuevas_y_hace_backup(self):
        excel = _excel({
            1: [("ZZ Importar Uno", 2000), ("ZZ Importar Nueva", 500)],
            2: [("ZZ Importar Uno", 2200)],
            3: [("zz importar uno", 1200), ("ZZ Importar Nueva", 700)],  # igual / nueva
        })
        html = self._subir(excel)
        self.assertEqual(self._precios("ZZ Importar Uno"), (2000, 2200, 1200))
        self.assertEqual(self._precios("ZZ Importar Nueva"), (500, 0, 700))
        self.assertIn("2 precios actualizados", html)
        self.assertIn("1 tareas nuevas", html)
        self.assertIn("ZZ Importar Nueva", html)
        # El aviso nombra la copia de seguridad y esa copia existe de verdad en disco.
        nombre = re.search(r"antes_import_precios_[0-9_-]+\.db", html)
        self.assertIsNotNone(nombre)
        self.assertTrue((Path(app.config["BACKUP_DIR"]) / nombre.group(0)).exists())

    def test_si_no_hay_cambios_no_toca_nada_ni_hace_backup(self):
        antes = len(self._backups())
        html = self._subir(_excel({
            1: [("ZZ Importar Uno", 1000)], 2: [("ZZ Importar Uno", 1100)],
            3: [("ZZ Importar Uno", 1200)],
        }))
        self.assertIn("ya estaban al día", html)
        self.assertEqual(self._precios("ZZ Importar Uno"), (1000, 1100, 1200))
        self.assertEqual(len(self._backups()), antes)

    def test_cualquier_usuario_con_sesion_puede_importar(self):
        comun = app.test_client()
        with comun.session_transaction() as sesion:
            sesion["usuario"] = "operador"
            sesion["rol"] = "usuario"
        self._subir(_excel({1: [("ZZ Importar Uno", 3000)]}), cliente=comun)
        self.assertEqual(self._precios("ZZ Importar Uno")[0], 3000)

    def test_sin_sesion_redirige_al_login(self):
        respuesta = app.test_client().post("/precios/importar")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login", respuesta.headers["Location"])

    def test_rechaza_archivos_que_no_son_xlsx(self):
        html = self._subir(b"datos", nombre="precios.xls")
        self.assertIn("tiene que ser un Excel .xlsx", html)
        html = self._subir(b"esto no es un excel", nombre="precios.xlsx")
        self.assertIn("no parece un Excel", html)
        html = self._subir(None)
        self.assertIn("Elegí un archivo de Excel", html)
        self.assertEqual(self._precios("ZZ Importar Uno"), (1000, 1100, 1200))

    def test_avisa_si_faltan_hojas_y_no_cambia_nada(self):
        html = self._subir(_excel({1: [("ZZ Importar Uno", 9999)]}, hojas=(1,)))
        self.assertIn("Faltan hojas de listas", html)
        self.assertIn("Lista 1", html)
        self.assertEqual(self._precios("ZZ Importar Uno"), (1000, 1100, 1200))

    def test_ignora_precios_negativos_con_advertencia(self):
        html = self._subir(_excel({
            1: [("ZZ Importar Uno", -5)], 2: [("ZZ Importar Uno", 2200)],
        }))
        self.assertIn("precio negativo", html)
        self.assertEqual(self._precios("ZZ Importar Uno"), (1000, 2200, 1200))

    def test_no_modifica_tareas_con_nombre_repetido(self):
        conexion = obtener_conexion()
        try:
            conexion.execute(
                "INSERT INTO tareas (nom_tar, precio) VALUES ('ZZ Importar Dos', 100)")
            conexion.execute(
                "INSERT INTO tareas (nom_tar, precio) VALUES ('ZZ IMPORTAR DOS', 100)")
            conexion.commit()
        finally:
            conexion.close()
        html = self._subir(_excel({1: [("zz importar dos", 999)]}))
        self.assertIn("nombre repetido", html)
        self.assertEqual(self._precios("ZZ Importar Dos")[0], 100)
        self.assertEqual(self._precios("ZZ IMPORTAR DOS")[0], 100)

    def test_importar_en_modo_comparacion_no_toca_la_base(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "precios.xlsx"
            ruta.write_bytes(_excel({1: [("ZZ Importar Uno", 5000)]}))
            datos = importar(ruta, get_db_path(), actualizar=False)
        self.assertEqual(datos["precios_actualizados"], 0)
        self.assertIsNone(datos["backup"])
        self.assertEqual(self._precios("ZZ Importar Uno"), (1000, 1100, 1200))


if __name__ == "__main__":
    unittest.main()
