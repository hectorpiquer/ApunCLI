import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apuncli import formato  # noqa: E402


class FilaSimulada(dict):
    """Simula una sqlite3.Row: acceso por clave y valores '' si falta."""


class TestMarkdown(unittest.TestCase):
    def test_a_markdown_con_todo(self):
        apunte = FilaSimulada(titulo="Tema 1", contenido="Cuerpo aquí", asignatura="ED")
        texto = formato.a_markdown(apunte, ["temas", "examen"])
        lineas = texto.split("\n")
        self.assertEqual(lineas[0], "# Tema 1")
        self.assertIn("asignatura: ED", texto)
        self.assertIn("etiquetas: temas, examen", texto)
        self.assertIn("Cuerpo aquí", texto)

    def test_a_markdown_minimo(self):
        apunte = FilaSimulada(titulo="Solo título", contenido="", asignatura="")
        texto = formato.a_markdown(apunte, [])
        self.assertEqual(texto, "# Solo título\n")

    def test_de_markdown_completo(self):
        texto = (
            "# Tema 1\n"
            "\n"
            "asignatura: ED\n"
            "etiquetas: temas, examen\n"
            "\n"
            "Un árbol binario tiene dos hijos.\n"
        )
        titulo, contenido, asignatura, etiquetas, recursos = formato.de_markdown(texto)
        self.assertEqual(titulo, "Tema 1")
        self.assertEqual(asignatura, "ED")
        self.assertEqual(etiquetas, ["temas", "examen"])
        self.assertEqual(contenido, "Un árbol binario tiene dos hijos.")

    def test_de_markdown_sin_metadatos(self):
        texto = "# Apunte\n\nContenido suelto\ncon dos líneas.\n"
        titulo, contenido, asignatura, etiquetas, recursos = formato.de_markdown(texto)
        self.assertEqual(titulo, "Apunte")
        self.assertEqual(asignatura, "")
        self.assertEqual(etiquetas, [])
        self.assertEqual(contenido, "Contenido suelto\ncon dos líneas.")

    def test_de_markdown_sin_titulo(self):
        titulo, contenido, _, _, _ = formato.de_markdown("solo texto, sin cabecera")
        self.assertEqual(titulo, "")
        self.assertEqual(contenido, "solo texto, sin cabecera")

    def test_contenido_con_marcas_no_se_confunde(self):
        texto = "# Tema\n\nasignatura: ED\n\nEl texto habla de asignatura: no debe comérselo.\n"
        _, contenido, asignatura, _, _ = formato.de_markdown(texto)
        self.assertEqual(asignatura, "ED")
        self.assertEqual(contenido, "El texto habla de asignatura: no debe comérselo.")

    def test_round_trip(self):
        original = FilaSimulada(
            titulo="Tema 4", contenido="Línea 1\nLínea 2", asignatura="Matemáticas"
        )
        texto = formato.a_markdown(original, ["geometría"])
        titulo, contenido, asignatura, etiquetas, recursos = formato.de_markdown(texto)
        self.assertEqual(titulo, "Tema 4")
        self.assertEqual(contenido, "Línea 1\nLínea 2")
        self.assertEqual(asignatura, "Matemáticas")
        self.assertEqual(etiquetas, ["geometría"])


class TestDividirBloques(unittest.TestCase):
    def test_divide_por_titulos(self):
        from apuncli.comandos import _dividir_bloques_markdown

        texto = "# Uno\n\nasignatura: ED\n\nContenido 1\n\n# Dos\n\nContenido 2\n"
        bloques = _dividir_bloques_markdown(texto)
        self.assertEqual(len(bloques), 2)
        titulo1, _, _, _, _ = formato.de_markdown(bloques[0])
        titulo2, _, _, _, _ = formato.de_markdown(bloques[1])
        self.assertEqual(titulo1, "Uno")
        self.assertEqual(titulo2, "Dos")


if __name__ == "__main__":
    unittest.main()
