"""La CLI desde fuera: una prueba por código de salida, como la teclearía una persona.

argumentos.ejecutar() es el 'main' real: recibe argv y devuelve el código, así
que sustituye a un CliRunner (no usamos Typer; con argparse esto es lo mismo).
"""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from apuncli import argumentos
from conftest import ProveedorFalso

BUENA = {"nombre": "ordenar", "descripcion": "Mueve los PDF", "tipo": "mover",
         "destino": "~/PDF", "filtro": {"extensiones": [".pdf"]}}
CON_IA = {"nombre": "res", "descripcion": "Resume", "tipo": "resumir-ia"}


def ejecutar(*argv):
    salida, errores = io.StringIO(), io.StringIO()
    with redirect_stdout(salida), redirect_stderr(errores):
        codigo = argumentos.ejecutar(list(argv))
    return codigo, salida.getvalue() + errores.getvalue()


def test_version_imprime_la_version_de_pyproject():
    codigo, texto = ejecutar("version")
    assert codigo == 0
    from apuncli import __version__
    assert texto.strip() == f"apuncli {__version__}"


def test_la_ayuda_funciona_sale_con_0():
    codigo, texto = ejecutar("--help")
    assert codigo == 0
    assert "apuncli" in texto


def test_json_roto_sale_con_3_y_sin_traceback(escribir_config):
    ruta = escribir_config('{"version": 1, "acciones": [ } ]')
    codigo, texto = ejecutar("--config", str(ruta), "validar")
    assert codigo == 3
    assert "JSON" in texto
    assert "Traceback" not in texto


def test_accion_que_no_existe_sale_con_3(escribir_config, descargas):
    """Acción inexistente = problema de configuración: bloque ordenado y código 3."""
    ruta = escribir_config([BUENA])
    codigo, texto = ejecutar("--config", str(ruta), "ejecutar", "inventada",
                             str(descargas))
    assert codigo == 3
    assert "error de configuración" in texto
    assert "inventada" in texto and "no existe" in texto
    assert "Acciones disponibles" in texto  # te dice qué sí existe


def test_opcion_que_no_existe_sale_con_2():
    codigo, _ = ejecutar("listar", "--no-existe-esa-opcion")
    assert codigo == 2


def test_id_invalido_sale_con_1_y_mensaje_humano():
    codigo, texto = ejecutar("ver", "un-id-que-no-es-numero")
    assert codigo == 1
    assert "no es un id válido" in texto
    assert "Traceback" not in texto


def test_ejecutar_simular_desde_la_orden_no_toca_el_disco(escribir_config, descargas,
                                                          tmp_path):
    ruta = escribir_config([BUENA])
    codigo, texto = ejecutar("--config", str(ruta), "ejecutar", "ordenar",
                             str(descargas), "--simular")
    assert codigo == 0
    assert "SIMULACIÓN" in texto
    # el destino ni se creó, y los PDF siguen en Descargas
    assert not (tmp_path / "PDF").exists()
    assert (descargas / "factura.pdf").exists()


class SinRed:
    """Un proveedor que, al preguntarle, avisa de que no hay IA."""

    url = "http://192.0.2.1:9/v1"
    modelo = "qwen3:8b"

    def preguntar(self, consigna, texto, largo_max=16000):
        from apuncli.errores import SinRedError
        raise SinRedError("No hay conexión con el proveedor de IA en "
                          "http://192.0.2.1:9/v1. Sin red la CLI sigue "
                          "funcionando con las acciones que no necesitan IA.")


def test_ia_sin_disponible_sale_con_4_y_avisa(escribir_config, monkeypatch):
    """Sin red/clave: código 4, mensaje humano y aviso de que todo lo demás sigue."""
    import apuncli.db as db
    import apuncli.comandos as comandos
    monkeypatch.setattr(db, "obtener_apunte",
                        lambda conexion, id_: {"id": id_, "titulo": "t", "contenido": "x"})
    monkeypatch.setattr(comandos.db, "obtener_apunte",
                        lambda conexion, id_: {"id": id_, "titulo": "t", "contenido": "x"})
    monkeypatch.setattr(comandos, "_apunte_obligatorio", lambda conexion, id_: None)
    monkeypatch.setattr(comandos.ai, "ProveedorIA",
                        lambda *a, **k: SinRed())
    ruta = escribir_config([CON_IA])
    codigo, texto = ejecutar("--config", str(ruta), "ejecutar", "res", "1")
    assert codigo == 4
    assert "sigue" in texto  # «…sigue funcionando con todo lo demás»


def test_ia_con_proveedor_falso_funciona_desde_la_orden(escribir_config, monkeypatch,
                                                        proveedor_falso):
    """Con un modelo de juguete, la acción IA hace su trabajo desde la CLI."""
    falso = proveedor_falso("- resumen de pega")
    monkeypatch.setattr("apuncli.ai.ProveedorIA", lambda *a, **k: falso)
    import apuncli.db as db
    import apuncli.comandos as comandos
    monkeypatch.setattr(db, "obtener_apunte",
                        lambda conexion, id_: {"id": id_, "titulo": "T", "contenido": "cuerpo"})
    monkeypatch.setattr(comandos.db, "obtener_apunte",
                        lambda conexion, id_: {"id": id_, "titulo": "T", "contenido": "cuerpo"})
    monkeypatch.setattr(comandos, "_apunte_obligatorio", lambda conexion, id_: None)
    ruta = escribir_config([CON_IA])
    codigo, texto = ejecutar("--config", str(ruta), "ejecutar", "res", "1", "--si")
    assert codigo == 0
    assert "resumen de pega" in texto
    assert falso.preguntas  # el documento viajó al modelo


def test_modo_forzado_sin_config_aceptado():
    """--modo se parsea sin tocar el flujo de comandos normales."""
    codigo, texto = ejecutar("--modo", "organizador", "version")
    assert codigo == 0 and "apuncli" in texto


def test_version_en_ayuda():
    codigo, texto = ejecutar("--help")
    assert codigo == 0 and "version" in texto
