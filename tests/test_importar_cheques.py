"""Pruebas de la importación de cheques desde Excel (script, servicio y pantalla)."""

import tempfile
import unittest
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from scripts.importar_cheques import (
    importar,
    parsear_fecha,
    parsear_importe,
    unificar_bancos,
)
from tests.support import app, get_db_path, obtener_conexion

CABECERA = ["Numero", "Banco", "Librador", "Destino", "Importe", "Fecha"]


def _excel(filas, cabecera=CABECERA):
    """Arma un .xlsx parecido al real: fila vacía, título, encabezados y luego los cheques."""
    libro = Workbook()
    hoja = libro.active
    hoja.append([None] * 6)
    hoja.append(["CHEQUES EN CARTERA"])
    hoja.append(cabecera)
    for fila in filas:
        hoja.append(list(fila))
    memoria = BytesIO()
    libro.save(memoria)
    return memoria.getvalue()


class TestParsersDeCheques(unittest.TestCase):
    def test_fechas_reales_y_texto_con_errores_de_tipeo(self):
        self.assertEqual(parsear_fecha(datetime(2026, 5, 7))[0], date(2026, 5, 7))
        fecha, dia, error = parsear_fecha(" Vierne 26de junio de2026")
        self.assertEqual((fecha, dia, error), (date(2026, 6, 26), 4, None))   # viernes real
        self.assertEqual(parsear_fecha("Sabado 27 de junio 2026")[0], date(2026, 6, 27))
        self.assertEqual(parsear_fecha("lunes 14 de Septiembre de 2026")[0], date(2026, 9, 14))

    def test_fecha_con_dia_de_semana_equivocado_se_detecta(self):
        fecha, dia, _ = parsear_fecha("Jueves 30 de Junio de 2026")
        self.assertEqual(fecha, date(2026, 6, 30))
        self.assertNotEqual(dia, fecha.weekday())   # 30/06/2026 fue martes

    def test_fechas_invalidas(self):
        for texto in ("31 de junio de 2026", "hola", "", None, "5 de xyz de 2026"):
            with self.subTest(texto=texto):
                self.assertIsNone(parsear_fecha(texto)[0])

    def test_importes_numericos_y_texto_roto(self):
        self.assertEqual(parsear_importe(181500), (181500.0, False))
        self.assertEqual(parsear_importe(421848.44), (421848.44, False))
        self.assertEqual(parsear_importe("600,000,00"), (600000.0, True))
        self.assertEqual(parsear_importe("113,416,00"), (113416.0, True))
        self.assertEqual(parsear_importe("250 000 00"), (250000.0, True))
        self.assertEqual(parsear_importe("1.234,50"), (1234.5, True))
        self.assertEqual(parsear_importe("abc"), (None, False))
        self.assertEqual(parsear_importe(None), (None, False))

    def test_bancos_se_unifican_pero_echeq_queda_igual(self):
        r = unificar_bancos(["CREDICOOP", "Credicoop", "credicoop ", "Echeq", "BBVA", "Macro"])
        self.assertEqual(r["CREDICOOP"], "Credicoop")
        self.assertEqual(r["credicoop "], "Credicoop")
        self.assertEqual((r["Echeq"], r["BBVA"], r["Macro"]), ("Echeq", "BBVA", "Macro"))


class TestImportarCheques(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"
        self._limpiar()
        conexion = obtener_conexion()
        try:
            conexion.execute("INSERT INTO clientes (nom_cli) VALUES ('ZZ Cliente Existente')")
            id_existente = conexion.execute(
                "SELECT id_cliente FROM clientes WHERE nom_cli = 'ZZ Cliente Existente'").fetchone()[0]
            conexion.execute("INSERT INTO alias_clientes (alias, id_cliente) VALUES ('zz alias viejo', ?)", (id_existente,))
            conexion.commit()
        finally:
            conexion.close()
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = Path(self.carpeta.name) / "cheques.xlsx"
        self.backups = []

    def tearDown(self):
        self._limpiar()
        self.carpeta.cleanup()

    def _limpiar(self):
        conexion = obtener_conexion()
        try:
            conexion.execute("CREATE TABLE IF NOT EXISTS alias_clientes (alias TEXT PRIMARY KEY, id_cliente INTEGER NOT NULL)")
            conexion.execute("DELETE FROM cheques WHERE cliente LIKE 'ZZ%'")
            conexion.execute("DELETE FROM alias_clientes WHERE id_cliente IN (SELECT id_cliente FROM clientes WHERE nom_cli LIKE 'ZZ%')")
            conexion.execute("DELETE FROM clientes WHERE nom_cli LIKE 'ZZ%'")
            conexion.commit()
        finally:
            conexion.close()

    def _filas(self):
        return [
            ("ZZ-1001", "Macro", "ZZ Cliente Uno (ZZ Aclaracion)", "Orlando", 181500, datetime(2026, 5, 7)),
            ("ZZ-1002", "CREDICOOP", "ZZ Cliente Dos", None, "600,000,00", "Viernes 26de junio de2026"),
            ("ZZ-1003", "Credicoop", "ZZ Cliente Dos", "Anulado/No aceptado", 1000, "Jueves 30 de Junio de 2026"),
            (None, "Echeq", "ZZ Sin Numero", "Cambiado x efectivo - Marcelo", 5000, datetime(2026, 7, 1)),
            ("ZZ-1001", "Macro", "ZZ Cliente Uno (ZZ Aclaracion)", "Orlando", 181500, datetime(2026, 5, 7)),  # repetido
            ("ZZ-1004", "Macro", "ZZ Fecha Rota", None, 2000, "31 de junio de 2026"),                          # inválida
            ("ZZ-1005", "Galicia", "ZZ Alias Viejo", None, 7000, datetime(2026, 8, 3)),                          # por alias
        ]

    def _importar(self, actualizar=True):
        self.ruta.write_bytes(_excel(self._filas()))

        def backup(ruta_db):
            destino = Path(self.carpeta.name) / f"backup_{len(self.backups)}.db"
            destino.write_bytes(Path(ruta_db).read_bytes())
            self.backups.append(destino)
            return destino

        return importar(self.ruta, get_db_path(), actualizar=actualizar, funcion_backup=backup)

    def _cheques(self):
        conexion = obtener_conexion()
        try:
            return conexion.execute(
                "SELECT * FROM cheques WHERE cliente LIKE 'ZZ%' ORDER BY id_cheque").fetchall()
        finally:
            conexion.close()

    # ------------------------------------------------------------------ script
    def test_la_prueba_no_toca_la_base(self):
        informe = self._importar(actualizar=False)
        self.assertFalse(informe["aplicado"])
        self.assertEqual(self._cheques(), [])
        self.assertEqual(informe["resumen"]["importados"], 5)
        self.assertEqual(self.backups, [])

    def test_importa_con_las_reglas_acordadas(self):
        informe = self._importar()
        r = informe["resumen"]
        self.assertEqual((r["filas_leidas"], r["importados"], r["duplicados_en_excel"], r["invalidas"]),
                         (7, 5, 1, 1))
        por_numero = {c["numero"]: c for c in self._cheques()}

        uno = por_numero["ZZ-1001"]
        self.assertEqual((uno["banco"], uno["importe"], uno["fecha_pago"], uno["endosado"]),
                         ("Macro", 181500.0, "2026-05-07", "Orlando"))
        self.assertIsNone(uno["fecha_emision"])
        self.assertEqual(uno["cliente"], "ZZ Cliente Uno")             # sin el paréntesis

        dos = por_numero["ZZ-1002"]
        self.assertEqual((dos["banco"], dos["importe"], dos["fecha_pago"], dos["estado"]),
                         ("Credicoop", 600000.0, "2026-06-26", "Pendiente"))   # banco unificado, importe corregido

        tres = por_numero["ZZ-1003"]
        self.assertEqual(tres["estado"], "Rechazado")                  # «Anulado/No aceptado»
        self.assertEqual(tres["fecha_pago"], "2026-06-30")             # se ignora el día escrito

        sin_numero = [c for c in self._cheques() if c["numero"].startswith("SIN-N°-")]
        self.assertEqual(len(sin_numero), 1)
        self.assertEqual(sin_numero[0]["endosado"], "Cambiado x efectivo - Marcelo")  # texto plano

        alias = por_numero["ZZ-1005"]                                   # asociado por alias
        self.assertEqual(alias["cliente"], "ZZ Cliente Existente")

        self.assertEqual([x["fila"] for x in informe["fechas_a_revisar"]], [6])
        self.assertEqual([x["original"] for x in informe["importes_corregidos"]], ["600,000,00"])
        self.assertEqual({x["nombre"] for x in informe["clientes_creados"]},
                         {"ZZ Cliente Uno", "ZZ Cliente Dos", "ZZ Sin Numero"})
        self.assertEqual(informe["clientes_asociados"][0]["cliente"], "ZZ Cliente Existente")
        self.assertEqual(len(self.backups), 1)

    def test_guarda_el_texto_completo_como_alias_del_cliente_nuevo(self):
        self._importar()
        conexion = obtener_conexion()
        try:
            alias = conexion.execute("SELECT alias FROM alias_clientes a JOIN clientes c USING(id_cliente) "
                                     "WHERE c.nom_cli = 'ZZ Cliente Uno'").fetchall()
        finally:
            conexion.close()
        self.assertEqual([a["alias"] for a in alias], ["zz cliente uno zz aclaracion"])

    def test_volver_a_importar_no_duplica_nada(self):
        self._importar()
        antes = len(self._cheques())
        informe = self._importar()
        self.assertEqual(len(self._cheques()), antes)
        self.assertEqual(informe["resumen"]["importados"], 0)
        self.assertEqual(informe["resumen"]["ya_existian"], 5)   # incluye el que no tenía número
        self.assertFalse(informe["aplicado"])
        self.assertEqual(len(self.backups), 1)                   # la segunda vez no hizo falta backup

    def test_dos_cheques_con_mismo_numero_pero_distinta_fecha_son_distintos(self):
        self.ruta.write_bytes(_excel([
            ("ZZ-2001", "Galicia", "ZZ Dagostino", "Ezequiel", 412400.04, datetime(2026, 12, 8)),
            ("ZZ-2001", "Galicia", "ZZ Dagostino", "Dacmar", 412400.04, datetime(2026, 11, 8)),
        ]))
        informe = importar(self.ruta, get_db_path(), actualizar=True,
                           funcion_backup=lambda r: Path(self.carpeta.name) / "b.db")
        self.assertEqual(informe["resumen"]["importados"], 2)

    def test_error_si_faltan_columnas(self):
        self.ruta.write_bytes(_excel([], cabecera=["Numero", "Banco", "Importe"]))
        with self.assertRaises(ValueError) as contexto:
            importar(self.ruta, get_db_path())
        self.assertIn("Faltan columnas", str(contexto.exception))

    # ------------------------------------------------------------------ pantalla
    def _subir(self, contenido, nombre="cheques.xlsx", cliente=None):
        datos = {} if contenido is None else {"archivo": (BytesIO(contenido), nombre)}
        return (cliente or self.client).post(
            "/cheques/importar", data=datos, content_type="multipart/form-data", follow_redirects=True)

    def test_la_pantalla_importa_y_muestra_el_informe(self):
        respuesta = self._subir(_excel(self._filas()))
        html = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Se importaron 5 cheques", html)
        self.assertIn("Fechas para revisar", html)
        self.assertIn("Jueves 30 de Junio de 2026", html)
        self.assertIn("martes", html)                               # el día real
        self.assertIn("$600.000,00", html)
        self.assertEqual(len(self._cheques()), 5)

    def test_cualquier_usuario_con_sesion_puede_importar_y_sin_sesion_no(self):
        comun = app.test_client()
        with comun.session_transaction() as sesion:
            sesion["usuario"] = "operador"
            sesion["rol"] = "usuario"
        self.assertEqual(self._subir(_excel(self._filas()), cliente=comun).status_code, 200)
        respuesta = app.test_client().post("/cheques/importar")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login", respuesta.headers["Location"])

    def test_la_pantalla_rechaza_archivos_invalidos(self):
        self.assertIn("tiene que ser un Excel .xlsx", self._subir(b"datos", "cheques.xls").get_data(as_text=True))
        self.assertIn("no parece un Excel", self._subir(b"no es excel", "cheques.xlsx").get_data(as_text=True))
        self.assertIn("Elegí un archivo", self._subir(None).get_data(as_text=True))
        html = self._subir(_excel([], cabecera=["Numero", "Banco", "Importe"])).get_data(as_text=True)
        self.assertIn("Faltan columnas", html)
        self.assertEqual(self._cheques(), [])

    def test_cheques_muestra_el_boton_de_importar_y_la_etiqueta_aceptado(self):
        html = self.client.get("/cheques").get_data(as_text=True)
        self.assertIn("Importar desde Excel", html)
        self.assertIn('enctype="multipart/form-data"', html)
        self.assertIn(">Aceptado</option>", html)
        self.assertNotIn(">Pendiente</option>", html)


if __name__ == "__main__":
    unittest.main()
