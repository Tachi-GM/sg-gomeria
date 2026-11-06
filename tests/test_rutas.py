"""
Pruebas Automatizadas de Integracion para SG Gomeria.

Verifica la disponibilidad de las rutas principales,
el sistema de autenticacion y control de acceso (Login, Logout, Roles),
el comportamiento de sesiones (Modo Milagritos)
y el funcionamiento de las paginas de error personalizadas.
"""

import unittest
import sys
import io
import shutil
import zipfile
from pathlib import Path

# Agregar raiz del proyecto al path de busqueda
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.support import app, obtener_conexion


class TestSeguridadYAutenticacion(unittest.TestCase):
    def setUp(self):
        """Configuracion previa a cada test."""
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_login_pantalla_responde_200(self):
        """La pantalla de login debe responder con codigo 200."""
        respuesta = self.client.get("/login")
        self.assertEqual(respuesta.status_code, 200)

    def test_ruta_protegida_sin_sesion_redirige_a_login(self):
        """Un usuario anonimo al intentar entrar a /clientes debe ser redirigido a /login."""
        respuesta = self.client.get("/clientes")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login", respuesta.headers.get("Location", ""))

    def test_login_exitoso_y_redireccion(self):
        """El login con credenciales de admin debe autenticar y redirigir a home."""
        respuesta = self.client.post(
            "/login",
            data={"usuario": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.headers.get("Location"), "/")

    def test_login_fallido_con_clave_incorrecta(self):
        """El login con credenciales invalidas debe permanecer en /login."""
        respuesta = self.client.post(
            "/login",
            data={"usuario": "admin", "password": "clave_totalmente_incorrecta"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"incorrectos", respuesta.data)


class TestRutasConSesionIniciada(unittest.TestCase):
    def setUp(self):
        """Configura una sesion de admin autenticado para cada test."""
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["usuario"] = "admin"
            sess["rol"] = "admin"

        self._limpiar_temporales()

    def tearDown(self):
        self._limpiar_temporales()

    def _limpiar_temporales(self):
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM detalle_trabajos WHERE id_trabajo IN (
                SELECT id_trabajo FROM trabajos WHERE remito IN ('98765', '88881', '008882')
            )
        """)
        cursor.execute("""
            DELETE FROM detalle_temporal_trabajos WHERE id_trabajo IN (
                SELECT id_trabajo FROM trabajos WHERE remito IN ('98765', '88881', '008882')
            )
        """)
        cursor.execute(
            "DELETE FROM trabajos WHERE remito IN ('98765', '88881', '008882', '98766')"
        )
        cursor.execute(
            "DELETE FROM clientes WHERE nom_cli = 'Empresa Test Automatizada'"
        )
        conn.commit()
        conn.close()
        shutil.rmtree(
            Path(app.config["UPLOAD_DIR"]) / "fotos_remitos", ignore_errors=True
        )

    def test_inicio_autenticado_responde_200(self):
        """La pantalla principal '/' debe responder 200 para un usuario logueado."""
        respuesta = self.client.get("/")
        self.assertEqual(respuesta.status_code, 200)

    def test_clientes_autenticado_responde_200(self):
        """El dashboard de clientes debe responder 200."""
        respuesta = self.client.get("/clientes")
        self.assertEqual(respuesta.status_code, 200)

    def test_mataburros_autenticado_responde_200(self):
        """El formulario de mataburros debe responder 200."""
        respuesta = self.client.get("/mataburros")
        self.assertEqual(respuesta.status_code, 200)

    def test_precios_autenticado_responde_200(self):
        """La pantalla de tarifas /precios debe responder 200."""
        respuesta = self.client.get("/precios")
        self.assertEqual(respuesta.status_code, 200)

    def test_cheques_autenticado_responde_200(self):
        """La pantalla de cheques /cheques debe responder 200."""
        respuesta = self.client.get("/cheques")
        self.assertEqual(respuesta.status_code, 200)

    def test_acerca_de_responde_200(self):
        """La pantalla /acerca-de debe responder 200."""
        respuesta = self.client.get("/acerca-de")
        self.assertEqual(respuesta.status_code, 200)

    def test_toggle_milagritos_redirige_sin_error(self):
        """El toggle de milagritos debe redirigir y alternar la sesion."""
        respuesta = self.client.get("/toggle-milagritos")
        self.assertIn(respuesta.status_code, [302, 303])

    def test_logout_cierra_sesion(self):
        """El logout debe limpiar la sesion y redirigir a /login."""
        respuesta = self.client.get("/logout")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login", respuesta.headers.get("Location", ""))

    def test_ruta_inexistente_retorna_404(self):
        """Una URL inexistente debe devolver codigo 404."""
        respuesta = self.client.get("/ruta-que-definitivamente-no-existe-404")
        self.assertEqual(respuesta.status_code, 404)

    def test_agregar_cliente_exitoso(self):
        """Registrar un cliente nuevo mediante POST redirige a /clientes."""
        respuesta = self.client.post(
            "/agregar-cliente",
            data={
                "nombre": "Empresa Test Automatizada",
                "cuit": "20-11112222-9",
                "tel": "11-4455-6677",
                "mail": "test@empresa.com",
            },
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/clientes", respuesta.headers.get("Location", ""))

    def test_buscar_cliente_con_filtro(self):
        """El buscador de empresas responde 200 con resultados filtrados."""
        respuesta = self.client.get("/clientes?buscar=Empresa")
        self.assertEqual(respuesta.status_code, 200)

    def test_historial_cliente_responde_200(self):
        """La vista de historial por cliente responde 200."""
        respuesta = self.client.get("/historial-cliente?id_cliente=1")
        self.assertEqual(respuesta.status_code, 200)

    def test_operaciones_tareas_agregar_y_modificar(self):
        """Agregar una tarea y luego modificar sus tarifas responde con éxito."""
        resp_alta = self.client.post(
            "/agregar-tarea",
            data={
                "nombre": "Alineacion Laser Test",
                "precio1-form": "15000",
                "precio2-form": "14000",
                "precio3-form": "16000",
            },
            follow_redirects=False,
        )
        self.assertEqual(resp_alta.status_code, 302)

        resp_mod = self.client.post(
            "/modificar-tarea",
            data={
                "id_tarea": "1",
                "nombre": "Gomeria General",
                "precio1": "1000",
                "precio2": "1000",
                "precio3": "1000",
            },
            follow_redirects=False,
        )
        self.assertEqual(resp_mod.status_code, 302)

    def test_tarea_temporal_no_se_guarda_en_tarifario_y_se_usa_en_remito(self):
        nombre = "Tarea Temporal Automatizada"
        respuesta = self.client.post(
            "/agregar-tarea",
            data={
                "nombre": nombre,
                "precio1-form": "17500",
                "precio2-form": "16000",
                "precio3-form": "15000",
                "temporal": "1",
            },
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)

        with self.client.session_transaction() as sesion:
            temporales = sesion.get("tareas_temporales", [])
            self.assertEqual(len(temporales), 1)
            token = temporales[0]["token"]

        conn = obtener_conexion()
        self.assertIsNone(
            conn.execute(
                "SELECT id_tarea FROM tareas WHERE nom_tar = ?", (nombre,)
            ).fetchone()
        )
        conn.close()

        respuesta = self.client.post(
            "/enviar-trabajo",
            data={
                "remito": "98765",
                "fecha": "2026-10-18",
                "empresa": "1",
                "tipo_lista": "1",
                "tipo": "OI",
                "detalle": "Trabajo temporal",
                "tareas": [f"temporal:{token}"],
                "cantidades": ["1"],
            },
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)

        conn = obtener_conexion()
        detalle = conn.execute(
            """
            SELECT dtt.nombre_tarea, dtt.subtotal
            FROM detalle_temporal_trabajos dtt
            JOIN trabajos t ON t.id_trabajo = dtt.id_trabajo
            WHERE t.remito = ?
            """,
            ("98765",),
        ).fetchone()
        self.assertIsNotNone(detalle)
        self.assertEqual(detalle["nombre_tarea"], nombre)
        self.assertEqual(detalle["subtotal"], 17500.0)
        conn.close()

        with self.client.session_transaction() as sesion:
            self.assertEqual(sesion.get("tareas_temporales", []), [])

    def test_enviar_trabajo_endpoint_exitoso(self):
        """El endpoint POST /enviar-trabajo procesa el remito y redirige."""
        respuesta = self.client.post(
            "/enviar-trabajo",
            data={
                "remito": "98765",
                "fecha": "2026-10-18",
                "empresa": "1",
                "tipo_lista": "1",
                "tipo": "OI",
                "detalle": "Trabajo de prueba",
                "tareas": ["1"],
                "cantidades": ["1"],
            },
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/mataburros", respuesta.headers.get("Location", ""))

    def test_enviar_trabajo_guarda_foto_y_la_consulta_con_sesion(self):
        imagen_png = b"\x89PNG\r\n\x1a\n" + b"contenido de prueba"
        respuesta = self.client.post(
            "/enviar-trabajo",
            data={
                "remito": "98766",
                "fecha": "2026-10-18",
                "empresa": "1",
                "tipo_lista": "1",
                "tipo": "OI",
                "detalle": "Remito con foto",
                "tareas": ["1"],
                "cantidades": ["1"],
                "foto_remito": (io.BytesIO(imagen_png), "remito.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)

        conn = obtener_conexion()
        trabajo = conn.execute(
            "SELECT foto_remito FROM trabajos WHERE remito = ?", ("98766",)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(trabajo["foto_remito"])
        self.assertTrue(
            (Path(app.config["UPLOAD_DIR"]) / trabajo["foto_remito"]).is_file()
        )

        foto = self.client.get(
            f"/foto-remito/{trabajo['foto_remito']}", follow_redirects=False
        )
        try:
            self.assertEqual(foto.status_code, 200)
            self.assertEqual(foto.data, imagen_png)
        finally:
            foto.close()

        with self.client.session_transaction() as sesion:
            sesion.clear()
        protegida = self.client.get(
            f"/foto-remito/{trabajo['foto_remito']}", follow_redirects=False
        )
        self.assertEqual(protegida.status_code, 302)
        self.assertIn("/login", protegida.headers["Location"])

    def test_foto_rechaza_extension_y_firma_incompatibles(self):
        respuesta = self.client.post(
            "/enviar-trabajo",
            data={
                "remito": "98766",
                "fecha": "2026-10-18",
                "empresa": "1",
                "tipo_lista": "1",
                "tipo": "OI",
                "detalle": "Foto inválida",
                "tareas": ["1"],
                "cantidades": ["1"],
                "foto_remito": (io.BytesIO(b"no es una imagen"), "remito.exe"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)
        conn = obtener_conexion()
        self.assertIsNone(
            conn.execute(
                "SELECT id_trabajo FROM trabajos WHERE remito = ?", ("98766",)
            ).fetchone()
        )
        conn.close()

        respuesta = self.client.post(
            "/enviar-trabajo",
            data={
                "remito": "98766",
                "fecha": "2026-10-18",
                "empresa": "1",
                "tipo_lista": "1",
                "tipo": "OI",
                "detalle": "Firma inválida",
                "tareas": ["1"],
                "cantidades": ["1"],
                "foto_remito": (io.BytesIO(b"contenido que no es PNG"), "remito.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)

        respuesta = self.client.post(
            "/enviar-trabajo",
            data={
                "remito": "98766",
                "fecha": "2026-10-18",
                "empresa": "1",
                "tipo_lista": "1",
                "tipo": "OI",
                "detalle": "Foto demasiado grande",
                "tareas": ["1"],
                "cantidades": ["1"],
                "foto_remito": (
                    io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024)),
                    "remito.png",
                ),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 302)

    def test_foto_no_permite_traversal(self):
        respuesta = self.client.get(
            "/foto-remito/fotos_remitos/..%2F..%2Fsg_gomeria.db",
            follow_redirects=False,
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_editar_remito_endpoint_exitoso_y_errores(self):
        """El endpoint POST /editar-remito valida datos y actualiza."""
        # Error por ID inválido o faltante
        resp_error = self.client.post(
            "/editar-remito",
            data={
                "id_trabajo": "0",
                "tipo": "OI",
                "remito": "12345",
                "fecha": "2026-10-18",
            },
        )
        self.assertEqual(resp_error.status_code, 400)
        self.assertFalse(resp_error.get_json()["exito"])

        # Error por formato de remito incorrecto
        resp_invalido = self.client.post(
            "/editar-remito",
            data={
                "id_trabajo": "1",
                "tipo": "OI",
                "remito": "letras",
                "fecha": "2026-10-18",
            },
        )
        self.assertEqual(resp_invalido.status_code, 400)

        # Crear un trabajo previo para editarlo de forma aislada
        self.client.post(
            "/enviar-trabajo",
            data={
                "remito": "88881",
                "fecha": "2026-10-18",
                "empresa": "1",
                "tipo_lista": "1",
                "tipo": "OI",
                "detalle": "Para editar por ruta",
                "tareas": ["1"],
                "cantidades": ["1"],
            },
        )

        conn = obtener_conexion()
        trabajo = conn.execute(
            "SELECT id_trabajo FROM trabajos WHERE remito = '88881'"
        ).fetchone()
        conn.close()

        self.assertIsNotNone(trabajo)
        id_trabajo = trabajo["id_trabajo"]

        # Edición válida sobre el trabajo recién creado
        resp_ok = self.client.post(
            "/editar-remito",
            data={
                "id_trabajo": str(id_trabajo),
                "tipo": "OIB",
                "remito": "8882",
                "fecha": "2026-10-19",
            },
        )
        self.assertEqual(resp_ok.status_code, 200)
        datos = resp_ok.get_json()
        self.assertTrue(datos["exito"])
        self.assertEqual(datos["remito"], "008882")
        self.assertEqual(datos["tipo"], "OIB")

    def test_operaciones_cheques_completas(self):
        """Registrar, cambiar estado y eliminar cheque mediante API."""
        resp_alta = self.client.post(
            "/agregar-cheque",
            data={
                "numero": "CH-AUTO-9988",
                "cliente": "Cliente Cheque Test",
                "banco": "Banco Nacion",
                "fecha_emision": "2026-10-18",
                "fecha_pago": "2026-11-18",
                "importe": "55000.50",
                "estado": "Pendiente",
                "endosado": "",
            },
        )
        self.assertEqual(resp_alta.status_code, 200)
        datos = resp_alta.get_json()
        self.assertIn("id_cheque", datos)
        id_cheque = datos["id_cheque"]

        resp_estado = self.client.post(
            "/actualizar-estado-cheque",
            data={"id_cheque": id_cheque, "estado": "Cobrado"},
        )
        self.assertEqual(resp_estado.status_code, 200)

        resp_eliminar = self.client.post(
            "/eliminar-cheque",
            data={"id_cheque": id_cheque},
        )
        self.assertEqual(resp_eliminar.status_code, 200)

    def test_backup_descarga_archivo_db(self):
        """Un usuario administrador descarga BD y fotos en un ZIP restaurable."""
        carpeta_fotos = Path(app.config["UPLOAD_DIR"]) / "fotos_remitos"
        carpeta_fotos.mkdir(parents=True, exist_ok=True)
        (carpeta_fotos / "foto-backup.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + b"backup"
        )
        respuesta = self.client.get("/backup")
        try:
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn(
                "backup_gomeria_", respuesta.headers.get("Content-Disposition", "")
            )
            nombre = (
                respuesta.headers["Content-Disposition"]
                .split("filename=")[1]
                .strip('"')
            )
            ruta_zip = Path(app.config["BACKUP_DIR"]) / nombre
            with zipfile.ZipFile(ruta_zip) as paquete:
                self.assertIn("sg_gomeria.db", paquete.namelist())
                self.assertIn("fotos_remitos/foto-backup.png", paquete.namelist())
        finally:
            respuesta.close()

    def test_solo_admin_bloquea_usuario_comun(self):
        """Un usuario sin rol de admin es redirigido al intentar hacer backup."""
        with self.client.session_transaction() as sess:
            sess["usuario"] = "operador"
            sess["rol"] = "usuario"

        respuesta = self.client.get("/backup", follow_redirects=False)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.headers.get("Location"), "/")


if __name__ == "__main__":
    unittest.main()
