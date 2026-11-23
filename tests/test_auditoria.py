"""Tests de la auditoría de la v1.0.2: salidas --json, robustez de rutas y
errores, código de salida del motor, copiar, generar-temario y el repaso
espaciado. Todo a través de la orden real (argumentos.ejecutar) cuando toca.
"""

import io
import json
import os
import unittest as _unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

if "unittest" in globals():     # descubierto por unittest: no es su fichero
    raise _unittest.SkipTest("este fichero solo funciona con pytest")
import pytest

from apuncli import argumentos, db
from apuncli.errores import AccionNoValida, FalloEjecucion

BUENA = {"nombre": "ordenar", "descripcion": "Mueve los PDF", "tipo": "mover",
         "destino": "~/PDF", "filtro": {"extensiones": [".pdf"]}}


def ejecutar(*argv):
    salida, errores = io.StringIO(), io.StringIO()
    with redirect_stdout(salida), redirect_stderr(errores):
        codigo = argumentos.ejecutar(list(argv))
    return codigo, salida.getvalue() + errores.getvalue()


def _db_de_prueba(tmp_path):
    """Base de datos aislada para la prueba (conectar() la toma al vuelo)."""
    os.environ["APUNCLI_DB"] = str(tmp_path / "prueba.db")


# ---------------------------------------------------------------------------
# Salidas --json (la "salida para máquinas" de la rúbrica)
# ---------------------------------------------------------------------------

def test_listar_json_es_json_valido(escribir_config, tmp_path):
    _db_de_prueba(tmp_path)
    try:
        codigo, texto = ejecutar("listar", "--json")
        assert codigo == 0
        datos = json.loads(texto)
        assert isinstance(datos, list)
    finally:
        del os.environ["APUNCLI_DB"]


def test_ver_json_incluye_contenido_y_etiquetas(tmp_path):
    _db_de_prueba(tmp_path)
    try:
        ejecutar("crear", "Tema X", "-c", "contenido", "-t", "examen")
        codigo, texto = ejecutar("ver", "1", "--json")
        assert codigo == 0
        datos = json.loads(texto)
        assert datos["titulo"] == "Tema X"
        assert datos["etiquetas"] == ["examen"]
        assert "contenido" in datos and "recursos" in datos
    finally:
        del os.environ["APUNCLI_DB"]


def test_buscar_json(tmp_path):
    _db_de_prueba(tmp_path)
    try:
        ejecutar("crear", "Tema Y", "-c", "la pila es LIFO")
        codigo, texto = ejecutar("buscar", "pila", "--json")
        assert codigo == 0
        assert json.loads(texto)[0]["titulo"] == "Tema Y"
    finally:
        del os.environ["APUNCLI_DB"]


def test_stats_json(tmp_path):
    _db_de_prueba(tmp_path)
    try:
        codigo, texto = ejecutar("stats", "--json")
        assert codigo == 0
        datos = json.loads(texto)
        assert {"total", "palabras", "sin_repasar", "repasados"} <= set(datos)
    finally:
        del os.environ["APUNCLI_DB"]


def test_acciones_json_y_comprobar_ia_json(escribir_config):
    ruta = escribir_config([BUENA])
    codigo, texto = ejecutar("--config", str(ruta), "acciones", "--json")
    assert codigo == 0
    datos = json.loads(texto)
    assert datos["acciones"][0]["nombre"] == "ordenar"
    # comprobar-ia sin servidor: JSON bien formado y disponible=false
    codigo2, texto2 = ejecutar("comprobar-ia", "--json")
    assert codigo2 in (0, 1)
    assert json.loads(texto2)["disponible"] is False


def test_ejecutar_simular_json(escribir_config, descargas):
    ruta = escribir_config([BUENA])
    codigo, texto = ejecutar("--config", str(ruta), "ejecutar", "ordenar",
                             str(descargas), "--simular", "--json")
    assert codigo == 0
    datos = json.loads(texto)
    assert datos["simulada"] is True
    assert any("factura.pdf" in h for h in datos["hechos"])


# ---------------------------------------------------------------------------
# Robustez: errores de rutas y permisos, sin tracebacks
# ---------------------------------------------------------------------------

def test_base_de_datos_sin_permisos_mensaje_humano(tmp_path):
    prohibida = tmp_path / "sin-permiso" / "sub"
    codigo, texto = "", ""
    import os
    os.environ["APUNCLI_DB"] = str(prohibida / "x.db")
    try:
        (tmp_path / "sin-permiso").mkdir()
        os.chmod(tmp_path / "sin-permiso", 0o500)
        try:
            db.conectar()
            pytest.skip("el sistema permite escribir donde no debía")
        except Exception as error:            # noqa: BLE001 — es lo que probamos
            from apuncli.errores import ApuncliError
            assert isinstance(error, ApuncliError), f"traceback en crudo: {error!r}"
            assert "base de datos" in str(error).lower()
    finally:
        os.chmod(tmp_path / "sin-permiso", 0o700)
        del os.environ["APUNCLI_DB"]


def test_config_directorio_da_codigo_3(escribir_config, tmp_path):
    directorio = tmp_path / "soy-un-directorio.json"
    directorio.mkdir()
    codigo, texto = ejecutar("--config", str(directorio), "validar")
    assert codigo == 3
    assert "Traceback" not in texto


def test_accion_inexistente_es_error_de_config(escribir_config, descargas):
    from apuncli import comandos
    ruta = escribir_config([BUENA])
    from apuncli.config import Configuracion
    config = Configuracion.cargar(ruta)
    with pytest.raises(AccionNoValida):
        comandos.cmd_ejecutar(db.conectar(), config, "no-existe", str(descargas),
                              False, True)


def test_fallo_del_motor_sale_con_1_por_consola(escribir_config, tmp_path):
    """Un mover cuyo origen no existe: humano y con código 1 (rúbrica)."""
    ruta = escribir_config([{"nombre": "m", "descripcion": "d", "tipo": "mover",
                             "origen": str(tmp_path / "no-existe"),
                             "destino": str(tmp_path / "dest")}])
    codigo, texto = ejecutar("--config", str(ruta), "ejecutar", "m", "--si")
    assert codigo == 1
    assert "no existe" in texto and "Traceback" not in texto


# ---------------------------------------------------------------------------
# Tipos de acción y recursos sin huecos
# ---------------------------------------------------------------------------

def test_copiar_deja_los_originales(descargas, tmp_path):
    from apuncli.config import AccionConfig
    from apuncli.motor import Motor
    accion = AccionConfig({"nombre": "c", "descripcion": "d", "tipo": "copiar",
                           "destino": str(tmp_path / "Copia"),
                           "filtro": {"extensiones": [".pdf"]}})
    resultado = Motor().ejecutar(accion, descargas)
    assert resultado.tocados == 1
    assert (descargas / "factura.pdf").exists()                  # original intacto
    assert (tmp_path / "Copia" / "factura.pdf").exists()          # copia hecha


def test_ejecutar_generar_temario_desde_la_orden(tmp_path):
    _db_de_prueba(tmp_path)
    try:
        ejecutar("crear", "Tema Z", "-a", "ED", "-c", "cuerpo")
        ruta = escribir_config_simple(tmp_path, [{"nombre": "temario",
                                                 "descripcion": "d",
                                                 "tipo": "generar-temario"}])
        codigo, texto = ejecutar("--config", str(ruta), "ejecutar", "temario", "ED")
        assert codigo == 0
        assert "Tema Z" in texto
        assert "#" in texto       # es Markdown
    finally:
        del os.environ["APUNCLI_DB"]


def escribir_config_simple(tmp_path, acciones):
    import json as _json
    ruta = tmp_path / "acciones-temario.json"
    ruta.write_text(_json.dumps({"version": 1, "acciones": acciones}), encoding="utf-8")
    return ruta


def test_recurso_ruta_inexistente_falla_al_anadir(tmp_path):
    _db_de_prueba(tmp_path)
    try:
        ejecutar("crear", "Con recurso", "-c", "texto")
        codigo, texto = ejecutar("recurso", "anadir", "1", str(tmp_path / "no.pdf"))
        assert codigo == 1
        assert "no existe" in texto
    finally:
        del os.environ["APUNCLI_DB"]


# ---------------------------------------------------------------------------
# Repaso espaciado (SM-2 ligero)
# ---------------------------------------------------------------------------

def test_repaso_espaciado_intervals_y_cola(tmp_path):
    _db_de_prueba(tmp_path)
    try:
        conexion = db.conectar()
        apunte_id = db.crear_apunte(conexion, "T", "contenido", "ED", [])
        hoy = date.today().toordinal()
        for esperado in (1, 3, 7, 14, 21, 30):
            db.marcar_repasado(conexion, apunte_id, hoy=hoy)
            fila = db.obtener_apunte(conexion, apunte_id)
            assert fila["intervalo"] == esperado
            assert fila["proximo_repaso"] == hoy + esperado
            assert db.cola_de_repaso(conexion, hoy) == []   # no toca hasta entonces
            assert len(db.cola_de_repaso(conexion, hoy + esperado)) == 1
        db.marcar_repasado(conexion, apunte_id, hoy=hoy)     # 7ª vez: +30
        assert db.obtener_apunte(conexion, apunte_id)["intervalo"] == 60
    finally:
        del os.environ["APUNCLI_DB"]


def test_migracion_de_base_vieja(tmp_path):
    """Una base creada antes del espaciado gana las columnas y entran en cola.

    Se recrea el esquema completo que `inicializar()` deja en una base antigua
    (con el índice FTS externo vacío) antes de medir la migración.
    """
    import sqlite3
    ruta = tmp_path / "vieja.db"
    conexion = sqlite3.connect(ruta)
    db.inicializar(conexion)                 # esquema viejo tal cual
    conexion.execute(
        "INSERT INTO apuntes (titulo, contenido, asignatura, creado, modificado) "
        "VALUES ('Viejo', 'cuerpo', 'ED', 'x', 'x')")
    conexion.commit()
    conexion.close()
    os.environ["APUNCLI_DB"] = str(ruta)
    try:
        conexion = db.conectar()
        fila = db.obtener_apunte(conexion, 1)
        assert fila["intervalo"] == 0
        assert fila["proximo_repaso"] == 1           # los viejos entran en la cola
        assert [a["id"] for a in db.cola_de_repaso(conexion, 1)] == [1]
        # y la búsqueda sigue funcionando tras la migración
        assert len(db.buscar_apuntes(conexion, "Viejo")) == 1
    finally:
        del os.environ["APUNCLI_DB"]
