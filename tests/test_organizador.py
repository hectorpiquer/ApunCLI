"""Tests del modo organizador (v1.0.6): espacio, duplicados, crear, IA saneada.

Nada de UI: el explorador y el menú se prueban en el aula; aquí se prueba el
motor puro (organizador.py), la puerta de la IA con falso (ai.py) y la CLI.
"""

import io
import json
import os
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from apuncli import argumentos, ai, ajustes, organizador as org
from apuncli.errores import ApuncliError


def ejecutar(*argv):
    salida, errores = io.StringIO(), io.StringIO()
    with redirect_stdout(salida), redirect_stderr(errores):
        codigo = argumentos.ejecutar(list(argv))
    return codigo, salida.getvalue() + errores.getvalue()


@pytest.fixture
def carpeta_fea(tmp_path):
    """Una carpeta con: duplicados reales, temporales viejos y subcarpetas."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "x.md").write_text("contenido", encoding="utf-8")
    (tmp_path / "a.pdf").write_bytes(b"CONTENIDO-IGUAL")
    (tmp_path / "b.pdf").write_bytes(b"CONTENIDO-IGUAL")          # duplicado de a
    (tmp_path / "c.pdf").write_bytes(b"otro")                       # único
    viejo = tmp_path / "cache.tmp"
    viejo.write_text("basura", encoding="utf-8")
    hace_60 = time.time() - 60 * 86400
    os.utime(viejo, (hace_60, hace_60))
    return tmp_path


# ---------------------------------------------------------------------------
# organizador puro
# ---------------------------------------------------------------------------

def test_listar_contenido_carpetas_primero(carpeta_fea):
    hijos = org.listar_contenido(carpeta_fea)
    assert hijos[0].name == "docs"                      # carpetas antes
    assert not any(h.name.startswith(".") for h in hijos)


def test_uso_espacio(carpeta_fea):
    datos = org.uso_espacio(carpeta_fea)
    assert any(p.name == "docs" for p, _ in datos)
    assert all(n > 0 for _, n in datos)


def test_tamano_legible():
    assert org.tamano_legible(500) == "500 B"
    assert org.tamano_legible(2048).startswith("2.0 KB")


def test_grupos_duplicados_solo_reales(carpeta_fea):
    grupos = org.grupos_duplicados(carpeta_fea)
    assert len(grupos) == 1
    nombres = sorted(f.name for f in grupos[0][1])
    assert nombres == ["a.pdf", "b.pdf"]               # c.pdf NO está


def test_borrar_menos_el_mas_antiguo(carpeta_fea):
    grupos = org.grupos_duplicados(carpeta_fea)
    (firma, grupo) = grupos[0]
    borrados = org.borrar_menos_el_ancien(grupo)
    conservados = [f.name for f in grupo if f.exists()]
    assert len(borrados) == 1
    assert len(conservados) == 1                       # queda exactamente uno
    assert not (carpeta_fea / "c.pdf").exists() is False  # el único intacto


def test_crear_documento_y_colision(carpeta_fea):
    destino = org.crear_documento(carpeta_fea, "tema 4", "md")
    assert destino.name == "tema-4.md" or destino.name == "tema 4.md"
    assert destino.read_text(encoding="utf-8").startswith("# ")
    otra = org.crear_documento(carpeta_fea, "tema 4", "md")
    assert otra != destino                             # nunca pisa
    con_slash = pytest.raises(ApuncliError)
    with con_slash:
        org.crear_documento(carpeta_fea, "..", "md")


def test_plantillas_validas():
    for tipo in org.PLANTILLAS:
        assert org.PLANTILLAS[tipo] is not None


def test_temporales_viejos(carpeta_fea):
    viejos = org.temporales_viejos(carpeta_fea, dias=30)
    assert [v.name for v in viejos] == ["cache.tmp"]


def test_plan_ordenar_y_ejecucion(carpeta_fea, tmp_path):
    plan = org.plan_ordenar(carpeta_fea, ["documentos"], raiz=tmp_path / "raiz")
    assert len(plan) >= 1                              # pdf
    movidos = org.ejecutar_plan_ordenar(plan)
    assert movidos >= 1
    assert not (carpeta_fea / "a.pdf").exists()
    assert (tmp_path / "raiz" / "Documentos" / "a.pdf").exists()
    assert (carpeta_fea / "cache.tmp").exists()        # los temporales no se mueven


def test_renombrar_por_fecha(carpeta_fea):
    ruta = carpeta_fea / "c.pdf"
    nueva = org.renombrar_por_fecha(ruta)
    assert nueva != ruta and nueva.exists()
    assert "_" in nueva.name and nueva.name.count(".") == 1


# ---------------------------------------------------------------------------
# a_nombre_seguro (el nombre que propone el modelo, saneado)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bruto, sugerida, esperado",
    [
        ("Tema 3: ¡Linux & Bash!", "x.md", "tema-3-linux-bash.md"),
        ("../../etc/passwd", "x.md", "etc-passwd.md"),
        ("redes-ip-protocolos.md", "x.md", "redes-ip-protocolos.md"),
        ("", "x.md", "sin-nombre.md"),
        ("Apuntes de Redes", "x.txt", "apuntes-de-redes.txt"),
        ("P1.2 Activitats", "x.pdf", "p1-2-activitats.pdf"),
    ],
    ids=["tildes-y-signos", "ruta-peligrosa", "con-extension",
         "vacia", "espacios", "punto-en-medio"],
)
def test_a_nombre_seguro(bruto, sugerida, esperado):
    assert ai.a_nombre_seguro(bruto, sugerida) == esperado


def test_clasificar_con_falso_y_rara(proveedor_falso):
    """Con proveedor falso: categoría válida y desconocida → sin-clasificar."""
    falso = proveedor_falso("apuntes")
    assert ai.accion_clasificar("texto", ["apuntes", "admin"], falso) == "apuntes"
    falso2 = proveedor_falso("matemáticas del espacio")
    assert ai.accion_clasificar("x", ["apuntes", "admin"], falso2) == "sin-clasificar"


def test_renombrar_ia_sin_red_avisa(tmp_path):
    """Sin red, el error es humano (no traceback): se comprueba en la CLI arriba."""
    import apuncli.organizador_menu as om
    monkey = tmp_path / "doc.txt"
    monkey.write_text("hola", encoding="utf-8")
    # el menú lanza ApuncliError cuando el proveedor falla
    from apuncli import ai as ai_mod
    original = ai_mod.ProveedorIA
    class SinRed:
        def preguntar(self, *a, **k):
            raise ai_mod.SinRedError("sin conexión de prueba")
    ai_mod.ProveedorIA = SinRed
    try:
        with pytest.raises(ApuncliError):
            om.renombrar_ia(monkey)
    finally:
        ai_mod.ProveedorIA = original


# ---------------------------------------------------------------------------
# Ajustes (config recordada) y CLI espejo
# ---------------------------------------------------------------------------

def test_ajustes_recordar_y_leer(tmp_path):
    ruta = tmp_path / "config.json"
    os.environ["APUNCLI_HOME"] = str(tmp_path)
    try:
        assert ajustes.modo_recordado() is None
        ajustes.guardar_ajustes(modo="organizador")
        assert ajustes.modo_recordado() == "organizador"
        assert ajustes.leer_ajustes()["modo"] == "organizador"
        ruta.write_text("{roto", encoding="utf-8")    # config ilegible no rompe
        assert ajustes.leer_ajustes() == {}
    finally:
        del os.environ["APUNCLI_HOME"]


def test_cli_organizar_espacio_y_json(carpeta_fea):
    codigo, texto = ejecutar("organizar", "espacio", str(carpeta_fea), "--json")
    assert codigo == 0
    assert any("docs" in str(f) for f in json.loads(texto))


def test_cli_organizar_duplicados_borra(carpeta_fea):
    codigo, texto = ejecutar("organizar", "duplicados", str(carpeta_fea), "--borrar")
    assert codigo == 0 and "borrados" in texto
    assert (carpeta_fea / "a.pdf").exists() or (carpeta_fea / "b.pdf").exists()
    assert not ((carpeta_fea / "a.pdf").exists() and (carpeta_fea / "b.pdf").exists())


def test_cli_organizar_temporales_simular(carpeta_fea):
    codigo, texto = ejecutar("organizar", "temporales", str(carpeta_fea), "--simular")
    assert codigo == 0
    assert "cache.tmp" in texto
    assert (carpeta_fea / "cache.tmp").exists()


def test_cli_crear_doc(carpeta_fea):
    ruta = str(carpeta_fea / "notas.md")
    codigo, texto = ejecutar("crear-doc", ruta)
    assert codigo == 0 and "Creado" in texto
    assert Path(ruta).exists()
    codigo2, _ = ejecutar("crear-doc", ruta)          # colisión: crea -1
    assert codigo2 == 0 and list(carpeta_fea.glob("notas*.md"))
