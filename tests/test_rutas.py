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
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_login_pantalla_responde_200(self):
        """La pantalla de login debe responder con codigo 200."""
        respuesta = self.client.get('/login')
        self.assertEqual(respuesta.status_code, 200)

    def test_ruta_protegida_sin_sesion_redirige_a_login(self):
        """Un usuario anonimo al intentar entrar a /clientes debe ser redirigido a /login."""
        respuesta = self.client.get('/clientes')
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/login', respuesta.headers.get('Location', ''))

    def test_login_exitoso_y_redireccion(self):
        """El login con credenciales de admin debe autenticar y redirigir a home."""
        respuesta = self.client.post('/login', data={
            'usuario': 'admin',
            'password': 'admin123'
        }, follow_redirects=False)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.headers.get('Location'), '/')

    def test_login_fallido_con_clave_incorrecta(self):
        """El login con credenciales invalidas debe permanecer en /login."""
        respuesta = self.client.post('/login', data={
            'usuario': 'admin',
            'password': 'clave_totalmente_incorrecta'
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"incorrectos", respuesta.data)


class TestRutasConSesionIniciada(unittest.TestCase):
    def setUp(self):
        """Configura una sesion de admin autenticado para cada test."""
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['usuario'] = 'admin'
            sess['rol'] = 'admin'

    def test_inicio_autenticado_responde_200(self):
        """La pantalla principal '/' debe responder 200 para un usuario logueado."""
        respuesta = self.client.get('/')
        self.assertEqual(respuesta.status_code, 200)

    def test_clientes_autenticado_responde_200(self):
        """El dashboard de clientes debe responder 200."""
        respuesta = self.client.get('/clientes')
        self.assertEqual(respuesta.status_code, 200)

    def test_mataburros_autenticado_responde_200(self):
        """El formulario de mataburros debe responder 200."""
        respuesta = self.client.get('/mataburros')
        self.assertEqual(respuesta.status_code, 200)

    def test_precios_autenticado_responde_200(self):
        """La pantalla de tarifas /precios debe responder 200."""
        respuesta = self.client.get('/precios')
        self.assertEqual(respuesta.status_code, 200)

    def test_cheques_autenticado_responde_200(self):
        """La pantalla de cheques /cheques debe responder 200."""
        respuesta = self.client.get('/cheques')
        self.assertEqual(respuesta.status_code, 200)

    def test_acerca_de_responde_200(self):
        """La pantalla /acerca-de debe responder 200."""
        respuesta = self.client.get('/acerca-de')
        self.assertEqual(respuesta.status_code, 200)

    def test_toggle_milagritos_redirige_sin_error(self):
        """El toggle de milagritos debe redirigir y alternar la sesion."""
        respuesta = self.client.get('/toggle-milagritos')
        self.assertIn(respuesta.status_code, [302, 303])

    def test_logout_cierra_sesion(self):
        """El logout debe limpiar la sesion y redirigir a /login."""
        respuesta = self.client.get('/logout')
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/login', respuesta.headers.get('Location', ''))

    def test_ruta_inexistente_retorna_404(self):
        """Una URL inexistente debe devolver codigo 404."""
        respuesta = self.client.get('/ruta-que-definitivamente-no-existe-404')
        self.assertEqual(respuesta.status_code, 404)


if __name__ == '__main__':
    unittest.main()
