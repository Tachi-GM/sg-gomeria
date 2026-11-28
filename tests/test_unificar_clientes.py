"""Pruebas de la unificación de clientes duplicados."""

import unittest
from pathlib import Path

from tests.support import app, obtener_conexion
from services.clientes_service import ErrorClientes, unificar_clientes


class TestUnificarClientes(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.carpeta = app.config["BACKUP_DIR"]
        self.admin = app.test_client()
        with self.admin.session_transaction() as sesion:
            sesion["usuario"], sesion["rol"] = "admin", "admin"
        self.operador = app.test_client()
        with self.operador.session_transaction() as sesion:
            sesion["usuario"], sesion["rol"] = "operador", "usuario"

        self._limpiar()
        c = obtener_conexion()
        try:
            if "cliente_alias" not in {f["name"] for f in c.execute("PRAGMA table_info(trabajos)")}:
                c.execute("ALTER TABLE trabajos ADD COLUMN cliente_alias TEXT")
            c.execute("CREATE TABLE IF NOT EXISTS alias_clientes (alias TEXT PRIMARY KEY, id_cliente INTEGER NOT NULL)")
            c.execute("INSERT INTO clientes (nom_cli, tel, con_iva) VALUES ('ZZ UC Principal', '1111', 1)")
            c.execute("INSERT INTO clientes (nom_cli, cuit, tel, mail, con_iva) "
                      "VALUES ('ZZ UC Duplicado', '20-33333333-3', '2222', 'dup@ejemplo.com', 0)")
            self.principal = c.execute("SELECT id_cliente FROM clientes WHERE nom_cli = 'ZZ UC Principal'").fetchone()[0]
            self.duplicado = c.execute("SELECT id_cliente FROM clientes WHERE nom_cli = 'ZZ UC Duplicado'").fetchone()[0]
            c.execute("INSERT INTO trabajos (remito, tipo, fecha, id_cliente, total) VALUES ('ZZUC1', 'OI', '2026-11-10', ?, 1000)", (self.duplicado,))
            c.execute("INSERT INTO trabajos (remito, tipo, fecha, id_cliente, total) VALUES ('ZZUC2', 'OI', '2026-11-11', ?, 2000)", (self.duplicado,))
            c.execute("INSERT INTO trabajos (remito, tipo, fecha, id_cliente, total) VALUES ('ZZUC3', 'OI', '2026-11-12', ?, 3000)", (self.principal,))
            c.execute("INSERT INTO cheques (numero, cliente, banco, importe, id_cliente) VALUES ('ZZUC-CH', 'ZZ UC Duplicado', 'Macro', 500, ?)", (self.duplicado,))
            c.execute("INSERT INTO vehiculos (patente, id_cliente) VALUES ('ZZ999UC', ?)", (self.duplicado,))
            c.execute("INSERT INTO alias_clientes (alias, id_cliente) VALUES ('zz uc viejo alias', ?)", (self.duplicado,))
            c.commit()
        finally:
            c.close()

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        c = obtener_conexion()
        try:
            c.execute("CREATE TABLE IF NOT EXISTS alias_clientes (alias TEXT PRIMARY KEY, id_cliente INTEGER NOT NULL)")
            c.execute("DELETE FROM cheques WHERE numero = 'ZZUC-CH'")
            c.execute("DELETE FROM trabajos WHERE remito LIKE 'ZZUC%'")
            c.execute("DELETE FROM vehiculos WHERE patente = 'ZZ999UC'")
            c.execute("DELETE FROM alias_clientes WHERE alias LIKE 'zz uc%'")
            c.execute("DELETE FROM clientes WHERE nom_cli LIKE 'ZZ UC%'")
            c.commit()
        finally:
            c.close()

    def _uno(self, sql, *params):
        c = obtener_conexion()
        try:
            return c.execute(sql, params).fetchone()
        finally:
            c.close()

    # ------------------------------------------------------------------ servicio
    def test_mueve_todo_al_principal_y_elimina_el_duplicado(self):
        r = unificar_clientes(self.duplicado, self.principal, self.carpeta)
        self.assertEqual((r["remitos"], r["cheques"], r["vehiculos"]), (2, 1, 1))
        self.assertIsNone(self._uno("SELECT 1 FROM clientes WHERE id_cliente = ?", self.duplicado))
        self.assertEqual(self._uno("SELECT COUNT(*) FROM trabajos WHERE id_cliente = ?", self.principal)[0], 3)
        self.assertEqual(self._uno("SELECT COUNT(*) FROM vehiculos WHERE id_cliente = ?", self.principal)[0], 1)
        cheque = self._uno("SELECT id_cliente, cliente FROM cheques WHERE numero = 'ZZUC-CH'")
        self.assertEqual((cheque["id_cliente"], cheque["cliente"]), (self.principal, "ZZ UC Principal"))
        self.assertTrue(Path(r["backup"]).exists())

    def test_guarda_el_nombre_del_duplicado_como_alias_y_conserva_los_anteriores(self):
        unificar_clientes(self.duplicado, self.principal, self.carpeta)
        c = obtener_conexion()
        try:
            alias = {f["alias"]: f["id_cliente"] for f in c.execute(
                "SELECT alias, id_cliente FROM alias_clientes WHERE alias LIKE 'zz uc%'")}
        finally:
            c.close()
        self.assertEqual(alias, {"zz uc duplicado": self.principal, "zz uc viejo alias": self.principal})

    def test_los_remitos_conservan_el_nombre_con_el_que_se_cargaron(self):
        unificar_clientes(self.duplicado, self.principal, self.carpeta)
        fila = self._uno("SELECT cliente_alias FROM trabajos WHERE remito = 'ZZUC1'")
        self.assertEqual(fila["cliente_alias"], "ZZ UC Duplicado")
        self.assertIsNone(self._uno("SELECT cliente_alias FROM trabajos WHERE remito = 'ZZUC3'")["cliente_alias"])

    def test_solo_completa_datos_vacios_y_no_toca_iva_ni_lista_del_principal(self):
        r = unificar_clientes(self.duplicado, self.principal, self.carpeta)
        p = self._uno("SELECT cuit, tel, mail, con_iva FROM clientes WHERE id_cliente = ?", self.principal)
        self.assertEqual(p["tel"], "1111")                     # el principal ya tenía teléfono
        self.assertEqual((p["cuit"], p["mail"]), ("20-33333333-3", "dup@ejemplo.com"))   # estaban vacíos
        self.assertEqual(p["con_iva"], 1)                      # no se toca (el duplicado era sin IVA)
        self.assertEqual(set(r["completados"]), {"cuit", "mail"})
        self.assertEqual(self._uno("SELECT total FROM trabajos WHERE remito = 'ZZUC1'")["total"], 1000)  # sin recalcular

    def test_errores_esperables_no_cambian_nada(self):
        for duplicado, principal in ((self.duplicado, self.duplicado), (0, self.principal),
                                      (self.duplicado, 999999), (999999, self.principal)):
            with self.subTest(duplicado=duplicado, principal=principal):
                with self.assertRaises(ErrorClientes):
                    unificar_clientes(duplicado, principal, self.carpeta)
        self.assertEqual(self._uno("SELECT COUNT(*) FROM trabajos WHERE id_cliente = ?", self.duplicado)[0], 2)

    # ------------------------------------------------------------------ pantalla
    def _unificar(self, cliente):
        return cliente.post("/clientes/unificar", data={
            "id_duplicado": self.duplicado, "id_principal": self.principal}, follow_redirects=True)

    def test_el_administrador_unifica_desde_la_pantalla(self):
        html = self._unificar(self.admin).get_data(as_text=True)
        self.assertIn("se unificó dentro de", html)
        self.assertIn("2 remitos, 1 cheques y 1 vehículos", html)
        self.assertIsNone(self._uno("SELECT 1 FROM clientes WHERE id_cliente = ?", self.duplicado))

    def test_un_usuario_comun_no_puede_unificar(self):
        respuesta = self.operador.post("/clientes/unificar", data={
            "id_duplicado": self.duplicado, "id_principal": self.principal})
        self.assertEqual(respuesta.status_code, 302)           # lo manda al inicio, sin hacer nada
        self.assertNotIn("/clientes", respuesta.headers["Location"])
        self.assertIsNotNone(self._uno("SELECT 1 FROM clientes WHERE id_cliente = ?", self.duplicado))
        self.assertEqual(app.test_client().post("/clientes/unificar").status_code, 302)   # sin sesión

    def test_el_boton_solo_lo_ve_el_administrador(self):
        for cliente, debe_verlo in ((self.admin, True), (self.operador, False)):
            html = cliente.get("/clientes?buscar=ZZ+UC").get_data(as_text=True)
            self.assertEqual("Unificar con otro cliente" in html, debe_verlo)
            self.assertEqual('id="modalUnificarCliente"' in html, debe_verlo)
        # el modal lista a los clientes para elegir el principal
        self.assertIn("ZZ UC Principal", self.admin.get("/clientes?buscar=ZZ+UC").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
