"""Pruebas de integración para la administración de usuarios."""

import unittest
from werkzeug.security import check_password_hash

from tests.support import app, obtener_conexion


class TestAdministracionUsuarios(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "admin"
            sesion["rol"] = "admin"

        conexion = obtener_conexion()
        try:
            conexion.execute("DELETE FROM usuarios WHERE usuario LIKE 'test_usuario_%'")
            conexion.commit()
        finally:
            conexion.close()

    def tearDown(self):
        conexion = obtener_conexion()
        try:
            conexion.execute("DELETE FROM usuarios WHERE usuario LIKE 'test_usuario_%'")
            conexion.commit()
        finally:
            conexion.close()

    def test_admin_puede_ver_pantalla_usuarios(self):
        respuesta = self.client.get("/usuarios")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Administrar usuarios", respuesta.data)
        self.assertIn(b"admin", respuesta.data)

    def test_usuario_comun_no_puede_ver_pantalla_usuarios(self):
        with self.client.session_transaction() as sesion:
            sesion["usuario"] = "operador"
            sesion["rol"] = "usuario"
        respuesta = self.client.get("/usuarios")
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.headers.get("Location"), "/")

    def test_crear_usuario_guarda_hash_y_rol(self):
        respuesta = self.client.post(
            "/usuarios/crear",
            data={"usuario": "test_usuario_nuevo", "password": "clave_segura_123", "rol": "usuario"},
        )
        self.assertEqual(respuesta.status_code, 302)
        conexion = obtener_conexion()
        try:
            fila = conexion.execute(
                "SELECT usuario, contraseña, rol FROM usuarios WHERE usuario = ?",
                ("test_usuario_nuevo",),
            ).fetchone()
        finally:
            conexion.close()
        self.assertIsNotNone(fila)
        self.assertEqual(fila["rol"], "usuario")
        self.assertNotEqual(fila["contraseña"], "clave_segura_123")
        self.assertTrue(check_password_hash(fila["contraseña"], "clave_segura_123"))

    def test_crear_usuario_rechaza_clave_corta(self):
        respuesta = self.client.post(
            "/usuarios/crear",
            data={"usuario": "test_usuario_clave_corta", "password": "123", "rol": "usuario"},
        )
        self.assertEqual(respuesta.status_code, 302)
        conexion = obtener_conexion()
        try:
            fila = conexion.execute(
                "SELECT id_usuario FROM usuarios WHERE usuario = ?",
                ("test_usuario_clave_corta",),
            ).fetchone()
        finally:
            conexion.close()
        self.assertIsNone(fila)

    def test_editar_usuario_sin_clave_conserva_hash(self):
        self.client.post(
            "/usuarios/crear",
            data={"usuario": "test_usuario_editar", "password": "clave_segura_123", "rol": "usuario"},
        )
        conexion = obtener_conexion()
        try:
            fila = conexion.execute(
                "SELECT id_usuario, contraseña FROM usuarios WHERE usuario = ?",
                ("test_usuario_editar",),
            ).fetchone()
            id_usuario, hash_original = fila["id_usuario"], fila["contraseña"]
        finally:
            conexion.close()

        respuesta = self.client.post(
            f"/usuarios/editar/{id_usuario}",
            data={"usuario": "test_usuario_editado", "rol": "admin", "password": ""},
        )
        self.assertEqual(respuesta.status_code, 302)
        conexion = obtener_conexion()
        try:
            actualizado = conexion.execute(
                "SELECT contraseña, rol FROM usuarios WHERE id_usuario = ?", (id_usuario,)
            ).fetchone()
        finally:
            conexion.close()
        self.assertEqual(actualizado["contraseña"], hash_original)
        self.assertEqual(actualizado["rol"], "admin")

    def test_no_permite_degradar_ultimo_admin(self):
        conexion = obtener_conexion()
        try:
            admin = conexion.execute(
                "SELECT id_usuario FROM usuarios WHERE usuario = 'admin'"
            ).fetchone()
            conexion.execute("DELETE FROM usuarios WHERE rol = 'admin' AND usuario != 'admin'")
            conexion.commit()
            id_admin = admin["id_usuario"]
        finally:
            conexion.close()

        respuesta = self.client.post(
            f"/usuarios/editar/{id_admin}",
            data={"usuario": "admin", "rol": "usuario", "password": ""},
        )
        self.assertEqual(respuesta.status_code, 302)
        conexion = obtener_conexion()
        try:
            admin = conexion.execute(
                "SELECT rol FROM usuarios WHERE id_usuario = ?", (id_admin,)
            ).fetchone()
        finally:
            conexion.close()
        self.assertEqual(admin["rol"], "admin")

    def test_no_permite_eliminar_ultimo_admin(self):
        conexion = obtener_conexion()
        try:
            admin = conexion.execute(
                "SELECT id_usuario FROM usuarios WHERE usuario = 'admin'"
            ).fetchone()
            conexion.execute("DELETE FROM usuarios WHERE rol = 'admin' AND usuario != 'admin'")
            conexion.commit()
            id_admin = admin["id_usuario"]
        finally:
            conexion.close()

        respuesta = self.client.post(f"/usuarios/eliminar/{id_admin}")
        self.assertEqual(respuesta.status_code, 302)
        conexion = obtener_conexion()
        try:
            admin = conexion.execute(
                "SELECT id_usuario FROM usuarios WHERE id_usuario = ?", (id_admin,)
            ).fetchone()
        finally:
            conexion.close()
        self.assertIsNotNone(admin)


if __name__ == "__main__":
    unittest.main()
