import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apuncli import db  # noqa: E402


class BaseDeDatos(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.directorio.name, "test.db")
        os.environ["APUNCLI_DB"] = self.ruta
        self.conexion = db.conectar()

    def tearDown(self):
        self.conexion.close()
        del os.environ["APUNCLI_DB"]
        self.directorio.cleanup()


class TestCrear(BaseDeDatos):
    def test_crear_apunte_sencillo(self):
        id_apunte = db.crear_apunte(self.conexion, "Tema 1", "Contenido", "Matemáticas")
        apunte = db.obtener_apunte(self.conexion, id_apunte)
        self.assertEqual(apunte["titulo"], "Tema 1")
        self.assertEqual(apunte["contenido"], "Contenido")
        self.assertEqual(apunte["asignatura"], "Matemáticas")

    def test_crear_con_etiquetas(self):
        id_apunte = db.crear_apunte(
            self.conexion, "Tema", "", "", ["Algebra", " EXAMEN "]
        )
        etiquetas = db.etiquetas_del_apunte(self.conexion, id_apunte)
        self.assertEqual(etiquetas, ["algebra", "examen"])

    def test_etiquetas_se_reutilizan(self):
        db.crear_apunte(self.conexion, "A", "", "", ["x"])
        db.crear_apunte(self.conexion, "B", "", "", ["x"])
        self.assertEqual(db.todas_las_etiquetas(self.conexion), ["x"])


class TestEditar(BaseDeDatos):
    def test_editar_solo_titulo(self):
        id_apunte = db.crear_apunte(self.conexion, "Viejo", "Cuerpo", "Asig")
        db.editar_apunte(self.conexion, id_apunte, titulo="Nuevo")
        apunte = db.obtener_apunte(self.conexion, id_apunte)
        self.assertEqual(apunte["titulo"], "Nuevo")
        self.assertEqual(apunte["contenido"], "Cuerpo")
        self.assertEqual(apunte["asignatura"], "Asig")

    def test_editar_etiquetas_sustituye(self):
        id_apunte = db.crear_apunte(self.conexion, "A", "", "", ["vieja"])
        db.editar_apunte(self.conexion, id_apunte, etiquetas=["nueva"])
        self.assertEqual(db.etiquetas_del_apunte(self.conexion, id_apunte), ["nueva"])

    def test_editar_no_existente_no_falla(self):
        db.editar_apunte(self.conexion, 999, titulo="nada")


class TestBuscar(BaseDeDatos):
    def test_busca_por_contenido(self):
        db.crear_apunte(self.conexion, "Árboles", "Recorrido inorden y postorden")
        db.crear_apunte(self.conexion, "Pilas", "LIFO")
        resultados = db.buscar_apuntes(self.conexion, "inorden")
        self.assertEqual([r["titulo"] for r in resultados], ["Árboles"])

    def test_busca_por_titulo(self):
        db.crear_apunte(self.conexion, "Teorema de Pitágoras", "")
        resultados = db.buscar_apuntes(self.conexion, "pitágoras")
        self.assertEqual(len(resultados), 1)

    def test_busca_prefijo(self):
        db.crear_apunte(self.conexion, "ejecución", "")
        resultados = db.buscar_apuntes(self.conexion, " ejecu*")
        self.assertEqual(len(resultados), 1)

    def test_busca_sin_resultados(self):
        db.crear_apunte(self.conexion, "Algo", "nada que ver")
        self.assertEqual(db.buscar_apuntes(self.conexion, "quijote"), [])

    def test_consulta_rara_no_rompe(self):
        db.crear_apunte(self.conexion, "Cosas", "con comillas \"y\" varias")
        resultados = db.buscar_apuntes(self.conexion, '"y"')
        self.assertIsInstance(resultados, list)


class TestListar(BaseDeDatos):
    def test_filtrar_por_asignatura(self):
        db.crear_apunte(self.conexion, "A", "", "ED")
        db.crear_apunte(self.conexion, "B", "", "Lengua")
        resultados = db.listar_apuntes(self.conexion, asignatura="ED")
        self.assertEqual([r["titulo"] for r in resultados], ["A"])

    def test_filtrar_por_etiqueta(self):
        db.crear_apunte(self.conexion, "A", "", "", ["tema1"])
        db.crear_apunte(self.conexion, "B", "", "", ["tema2"])
        resultados = db.listar_apuntes(self.conexion, etiqueta="TEMA1")
        self.assertEqual([r["titulo"] for r in resultados], ["A"])

    def test_orden_descendente_por_id(self):
        db.crear_apunte(self.conexion, "Primero")
        db.crear_apunte(self.conexion, "Segundo")
        resultados = db.listar_apuntes(self.conexion)
        self.assertEqual([r["titulo"] for r in resultados], ["Segundo", "Primero"])


class TestBorrar(BaseDeDatos):
    def test_borrar(self):
        id_apunte = db.crear_apunte(self.conexion, "A", "", "", ["x"])
        self.assertTrue(db.borrar_apunte(self.conexion, id_apunte))
        self.assertIsNone(db.obtener_apunte(self.conexion, id_apunte))

    def test_borrar_no_deja_etiquetas_huerfanas(self):
        id_apunte = db.crear_apunte(self.conexion, "A", "", "", ["x"])
        db.borrar_apunte(self.conexion, id_apunte)
        self.assertEqual(db.todas_las_etiquetas(self.conexion), [])

    def test_borrar_no_existente(self):
        self.assertFalse(db.borrar_apunte(self.conexion, 999))


class TestRepasar(BaseDeDatos):
    def test_marcar_repasado(self):
        id_apunte = db.crear_apunte(self.conexion, "A")
        db.marcar_repasado(self.conexion, id_apunte)
        db.marcar_repasado(self.conexion, id_apunte)
        self.assertEqual(db.obtener_apunte(self.conexion, id_apunte)["veces_repasado"], 2)


class TestEstadisticas(BaseDeDatos):
    def test_estadisticas(self):
        db.crear_apunte(self.conexion, "A", "una dos tres", "ED")
        db.crear_apunte(self.conexion, "B", "cuatro cinco", "Lengua")
        datos = db.estadisticas(self.conexion)
        self.assertEqual(datos["total"], 2)
        self.assertEqual(datos["sin_repasar"], 2)
        self.assertEqual(sorted(datos["por_asignatura"]), [("ED", 1), ("Lengua", 1)])


if __name__ == "__main__":
    unittest.main()
