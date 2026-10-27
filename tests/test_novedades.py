import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apuncli import db, recursos, temario, testmotor  # noqa: E402
from apuncli.errores import ApuncliError  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        os.environ["APUNCLI_DB"] = os.path.join(self.directorio.name, "test.db")
        self.conexion = db.conectar()

    def tearDown(self):
        self.conexion.close()
        del os.environ["APUNCLI_DB"]
        self.directorio.cleanup()


class TestRecursos(Base):
    def test_adjuntar_y_listar(self):
        id_apunte = db.crear_apunte(self.conexion, "A")
        id_recurso = db.adjuntar_recurso(self.conexion, id_apunte,
                                         "https://docs.python.org", "docs python")
        recursos_lista = db.recursos_del_apunte(self.conexion, id_apunte)
        self.assertEqual(len(recursos_lista), 1)
        self.assertEqual(recursos_lista[0]["nombre"], "docs python")
        self.assertEqual(recursos_lista[0]["url"], "https://docs.python.org")

    def test_borrar_recurso(self):
        id_apunte = db.crear_apunte(self.conexion, "A")
        id_recurso = db.adjuntar_recurso(self.conexion, id_apunte, "https://x.com")
        self.assertTrue(db.borrar_recurso(self.conexion, id_recurso))
        self.assertEqual(db.recursos_del_apunte(self.conexion, id_apunte), [])

    def test_borrar_apunte_lleva_sus_recursos(self):
        id_apunte = db.crear_apunte(self.conexion, "A")
        db.adjuntar_recurso(self.conexion, id_apunte, "https://x.com")
        db.borrar_apunte(self.conexion, id_apunte)
        self.assertEqual(db.recursos_de_apuntes(self.conexion, [id_apunte]), [])


class TestDeteccion(unittest.TestCase):
    def test_detecta_urls(self):
        texto = "mira https://docs.python.org/3/tutorial y también http://a.b/c?x=1."
        encontrados = recursos.detectar_en_texto(texto)
        urls = [u for u, _ in encontrados]
        self.assertIn("https://docs.python.org/3/tutorial", urls)
        self.assertIn("http://a.b/c?x=1", urls)

    def test_detecta_ficheros_existentes(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as archivo:
            ruta = archivo.name
        try:
            encontrados = recursos.detectar_en_texto(f"apunte en {ruta}")
            self.assertTrue(any(u == ruta for u, _ in encontrados))
        finally:
            os.unlink(ruta)

    def test_no_detecta_rutas_inventadas(self):
        self.assertEqual(recursos.detectar_en_texto("en ~/no/existe/nada.pdf nada"), [])

    def test_clasificar(self):
        self.assertEqual(recursos.clasificar("https://x.com"), "web")
        self.assertEqual(recursos.clasificar("/tmp/a.pdf"), "documento")
        self.assertEqual(recursos.clasificar("/tmp/a.png"), "imagen")
        self.assertEqual(recursos.clasificar("/tmp/a.py"), "código")


class TestTemario(Base):
    def test_genera_indice_y_enlaces(self):
        db.crear_apunte(self.conexion, "Pilas", "LIFO", "ED", ["tema2"])
        id_seg = db.crear_apunte(self.conexion, "Colas", "FIFO", "ED")
        db.adjuntar_recurso(self.conexion, id_seg, "https://col.es", "col web")
        texto = temario.generar_temario(self.conexion, asignatura="ED")
        self.assertIn("# 📚 Temario de ED", texto)
        self.assertIn("## Índice", texto)
        self.assertIn("[Pilas](#", texto)
        self.assertIn("col web", texto)
        self.assertIn("2 repasos · id", texto.replace("0 repasos", "2 repasos"))

    def test_sin_apuntes_falla(self):
        with self.assertRaises(ApuncliError):
            temario.generar_temario(self.conexion)


class TestTestAutomatico(Base):
    def test_extrae_preguntas(self):
        contenido = ("Tema pilas.\n"
                     "**Pregunta:** ¿Qué es una pila?\n"
                     "**Respuesta:** Una estructura LIFO.\n"
                     "**Pregunta:** ¿Y la cola?\n"
                     "**Respuesta:** FIFO.")
        db.crear_apunte(self.conexion, "Tema", contenido, "ED")
        preguntas = testmotor.preparar_preguntas(self.conexion)
        self.assertEqual(len(preguntas), 2)
        self.assertEqual(preguntas[0]["pregunta"], "¿Qué es una pila?")

    def test_sin_preguntas_falla(self):
        db.crear_apunte(self.conexion, "A", "sin bloques de pregunta")
        with self.assertRaises(ApuncliError):
            testmotor.preparar_preguntas(self.conexion)

    def test_comparacion_tolerante(self):
        self.assertTrue(testmotor.es_correcta("Una pila es lifo", "Una estructura LIFO, PILA lifo."))
        self.assertTrue(testmotor.es_correcta("estructura lifo", "Estructura LIFO"))
        self.assertFalse(testmotor.es_correcta("no tengo ni idea de esto", "La mitocondria"))
        self.assertFalse(testmotor.es_correcta("", "cualquier cosa"))


if __name__ == "__main__":
    unittest.main()
