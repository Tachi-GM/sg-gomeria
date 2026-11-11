import sys
import sqlite3
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from importar_precios import (
    calcular_sin_iva,
    comparar_con_base,
    comparar_importes,
    normalizar_descripcion,
    preparar_tareas_nuevas,
)


class TestImportarPrecios(unittest.TestCase):
    def test_normaliza_descripcion_para_comparar_tareas(self):
        self.assertEqual(
            normalizar_descripcion("  Alineación   Camión "),
            "alineacion camion",
        )

    def test_calcula_precio_sin_iva_con_dos_decimales(self):
        self.assertEqual(calcular_sin_iva(Decimal("1210")), Decimal("1000.00"))

    def test_compara_importes_con_tolerancia_de_centavos(self):
        self.assertTrue(comparar_importes(Decimal("1000.00"), Decimal("1000.004")))
        self.assertFalse(comparar_importes(Decimal("1000.00"), Decimal("1000.02")))

    def test_agrupa_tres_listas_para_crear_una_tarea(self):
        resultados = [
            {
                "estado": "faltante",
                "clave": "tarea nueva",
                "descripcion": "Tarea Nueva",
                "campo": "precio",
                "precio_final": Decimal("100"),
            },
            {
                "estado": "faltante",
                "clave": "tarea nueva",
                "descripcion": "Tarea Nueva",
                "campo": "precio2",
                "precio_final": Decimal("110"),
            },
        ]

        self.assertEqual(
            preparar_tareas_nuevas(resultados),
            [
                {
                    "nom_tar": "Tarea Nueva",
                    "precio": Decimal("100"),
                    "precio2": Decimal("110"),
                    "precio3": Decimal("0"),
                }
            ],
        )

    def test_detecta_diferencia_en_tarea_existente(self):
        conexion = sqlite3.connect(":memory:")
        conexion.row_factory = sqlite3.Row
        conexion.execute("""
            CREATE TABLE tareas (
                id_tarea INTEGER PRIMARY KEY,
                nom_tar TEXT,
                precio REAL,
                precio2 REAL,
                precio3 REAL
            )
            """)
        conexion.execute(
            "INSERT INTO tareas VALUES (1, 'Tarea Existente', 1000, 1000, 1000)"
        )

        fila = {
            "fila_excel": 3,
            "descripcion": "Tarea Existente",
            "clave": "tarea existente",
            "precio_sin_iva": Decimal("909.09"),
            "precio_final": Decimal("1100"),
        }
        resultados = comparar_con_base(
            {1: [fila], 2: [fila], 3: [fila]},
            conexion,
        )

        self.assertEqual(
            {resultado["estado"] for resultado in resultados}, {"diferente"}
        )
        self.assertTrue(all(resultado["calculo_iva_ok"] for resultado in resultados))
        conexion.close()


if __name__ == "__main__":
    unittest.main()
