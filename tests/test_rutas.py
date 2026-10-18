"""
Pruebas Automatizadas de Integracion para SG Gomeria.

Verifica la disponibilidad de las rutas principales,
el sistema de autenticacion y control de acceso (Login, Logout, Roles),
el comportamiento de sesiones (Modo Milagritos)
y el funcionamiento de las paginas de error personalizadas.
"""

import unittest
import sys
from pathlib import Path

# Agregar raiz del proyecto al path de busqueda
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app


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
                "cuit": "30-99887766-1",
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

    def test_enviar_trabajo_endpoint_exitoso(self):
        """El endpoint POST /enviar-trabajo procesa el remito y redirige."""
        respuesta = self.client.post(
            "/enviar-trabajo",
            data={
                "remito": "R-TEST-AUTO-999",
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
        """Un usuario administrador puede descargar el resguardo de la BD."""
        respuesta = self.client.get("/backup")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            "backup_gomeria_", respuesta.headers.get("Content-Disposition", "")
        )

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
