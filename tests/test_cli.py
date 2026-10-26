import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apuncli import argumentos, db  # noqa: E402
from apuncli.errores import ApuncliError  # noqa: E402


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        os.environ["APUNCLI_DB"] = os.path.join(self.directorio.name, "test.db")

    def tearDown(self):
        del os.environ["APUNCLI_DB"]
        self.directorio.cleanup()

    def ejecutar(self, *argv):
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = argumentos.ejecutar(list(argv))
        return codigo, salida.getvalue()

    def test_sin_argumentos_muestra_ayuda(self):
        codigo, salida = self.ejecutar()
        self.assertEqual(codigo, 0)
        self.assertIn("usage: apuncli", salida)

    def test_crear_y_ver(self):
        self.ejecutar("crear", "Tema 1", "-c", "Contenido", "-a", "ED", "-t", "a,b")
        codigo, salida = self.ejecutar("ver", "1")
        self.assertEqual(codigo, 0)
        self.assertIn("Tema 1", salida)
        self.assertIn("Contenido", salida)
        self.assertIn("[a] [b]", salida)

    def test_crear_titulo_vacio_falla(self):
        codigo, _ = self.ejecutar("crear", "   ", "-c", "x")
        self.assertEqual(codigo, 1)

    def test_listar_con_aliases(self):
        self.ejecutar("crear", "Uno", "-c", "x")
        for alias in ("listar", "ls"):
            codigo, salida = self.ejecutar(alias)
            self.assertEqual(codigo, 0)
            self.assertIn("Uno", salida)

    def test_ver_id_inexistente(self):
        codigo, _ = self.ejecutar("ver", "999")
        self.assertEqual(codigo, 1)

    def test_ver_id_no_numerico(self):
        codigo, _ = self.ejecutar("ver", "abc")
        self.assertEqual(codigo, 1)

    def test_buscar(self):
        self.ejecutar("crear", "Pilas", "-c", "estructura LIFO")
        codigo, salida = self.ejecutar("buscar", "LIFO")
        self.assertEqual(codigo, 0)
        self.assertIn("Pilas", salida)

    def test_editar_y_borrar(self):
        self.ejecutar("crear", "Borrable", "-c", "x")
        codigo, _ = self.ejecutar("editar", "1", "-T", " renombrado ", "--anadir", "-c", "más texto")
        self.assertEqual(codigo, 0)
        _, salida = self.ejecutar("ver", "1")
        self.assertIn("renombrado", salida)
        self.assertIn("más texto", salida)
        codigo, _ = self.ejecutar("borrar", "1", "--si")
        self.assertEqual(codigo, 0)
        codigo, _ = self.ejecutar("ver", "1")
        self.assertEqual(codigo, 1)

    def test_stats(self):
        self.ejecutar("crear", "A", "-c", "una palabra más", "-a", "ED")
        codigo, salida = self.ejecutar("stats")
        self.assertEqual(codigo, 0)
        self.assertIn("Apuntes totales:        1", salida)
        self.assertIn("ED", salida)

    def test_etiquetas_y_asignaturas(self):
        self.ejecutar("crear", "A", "-c", "x", "-a", "ED", "-t", "tema1")
        _, salida = self.ejecutar("etiquetas")
        self.assertIn("[tema1]", salida)
        _, salida = self.ejecutar("asignaturas")
        self.assertIn("ED", salida)

    def test_exportar_un_apunte(self):
        self.ejecutar("crear", "Exportable", "-c", "cuerpo", "-a", "ED")
        codigo, salida = self.ejecutar("exportar", "1")
        self.assertEqual(codigo, 0)
        self.assertIn("# Exportable", salida)
        self.assertIn("asignatura: ED", salida)

    def test_exportar_sin_nada_pide_args(self):
        codigo, _ = self.ejecutar("exportar")
        self.assertEqual(codigo, 1)

    def test_ciclo_completo_exportar_importar(self):
        self.ejecutar("crear", "Uno", "-c", "cuerpo uno", "-a", "ED", "-t", "x")
        self.ejecutar("crear", "Dos", "-c", "cuerpo dos")
        _, export = self.ejecutar("exportar", "--todos")
        ruta = os.path.join(self.directorio.name, "apuntes.md")
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(export)
        os.environ["APUNCLI_DB"] = os.path.join(self.directorio.name, "nueva.db")
        codigo, salida = self.ejecutar("importar", ruta)
        self.assertEqual(codigo, 0)
        self.assertIn("Importados 2 apuntes", salida)
        _, salida = self.ejecutar("ver", "1")
        self.assertIn("Dos", salida)
        self.assertIn("cuerpo dos", salida)
        _, salida = self.ejecutar("ver", "2")
        self.assertIn("Uno", salida)
        self.assertIn("cuerpo uno", salida)
        self.assertIn("ED", salida)

    def test_repasar_no_interactivo(self):
        self.ejecutar("crear", "A", "-c", "x")
        self.ejecutar("crear", "B", "-c", "y")
        with mock.patch("builtins.input", return_value=""):
            codigo, salida = self.ejecutar("repasar", "-n", "1")
        self.assertEqual(codigo, 0)
        self.assertIn("Repaso terminado", salida)
        self.assertIn("Modo repaso", salida)


if __name__ == "__main__":
    unittest.main()
