"""Tests pytest del sistema de acciones: config, motor, validador y capa IA.

El aislamiento (carpeta temporal, sin ia.env, sin red) lo garantiza la fixture
`aislado` de tests/conftest.py, que se aplica sola a TODAS las pruebas.
"""

import os
import unittest as _unittest
from datetime import datetime, timedelta
from pathlib import Path

if "unittest" in globals():     # descubierto por unittest: no es su fichero
    raise _unittest.SkipTest("este fichero solo funciona con pytest")
import pytest

from conftest import ProveedorFalso  # el mismo «modelo» que en el resto de tests

from apuncli import motor as motor_mod
from apuncli.config import AccionConfig, Configuracion, validar_esquema
from apuncli.errores import ConfigError, FalloEjecucion, SinRedError
from apuncli.motor import Motor, hash_de


def accion(**datos):
    """Construye una AccionConfig válida con los campos que se pasen."""
    base = {"nombre": "prueba", "descripcion": "acción de prueba", "tipo": "mover"}
    base.update(datos)
    return AccionConfig(base)


def fichero_de(ruta: Path, texto="hola", edad_dias=0) -> Path:
    ruta.write_text(texto, encoding="utf-8")
    if edad_dias:
        viejo = datetime.now() - timedelta(days=edad_dias)
        os.utime(ruta, (viejo.timestamp(), viejo.timestamp()))
    return ruta


# ---------------------------------------------------------------------------
# Validador de acciones.json (camino feliz y casos feos)
# ---------------------------------------------------------------------------

def test_esquema_valido():
    datos = {"version": 1, "acciones": [{
        "nombre": "ordenar-pdf", "descripcion": "mueve los PDF", "tipo": "mover",
        "destino": "~/Documentos/PDF", "filtro": {"extensiones": [".pdf"]}
    }]}
    acciones = validar_esquema(datos)
    assert len(acciones) == 1
    assert acciones[0].nombre == "ordenar-pdf"
    assert acciones[0].confirmar is True  # mover es destructivo por defecto


def test_json_roto_dice_que_falla():
    with pytest.raises(ConfigError) as error:
        Configuracion.cargar(Path("/definitivamente/no/existe.json"))
    assert "no existe" in str(error.value)


def test_json_mal_formado_no_rompe(tmp_path):
    roto = tmp_path / "roto.json"
    roto.write_text("{ version: 1 ...", encoding="utf-8")
    with pytest.raises(ConfigError) as error:
        Configuracion.cargar(roto)
    assert "JSON" in str(error.value)


def test_validador_seala_el_campo_exacto():
    datos = {"version": "uno", "acciones": [
        {"nombre": "MAL NOMBRE", "tipo": "teletransporte", "descripcion": "x"},
    ]}
    with pytest.raises(ConfigError) as error:
        validar_esquema(datos)
    texto = "; ".join(error.value.problemas)
    assert "version" in texto
    assert "acciones[0].nombre" in texto
    assert "acciones[0].tipo" in texto


def test_borrar_sin_filtro_no_pasa():
    """Caso feo: un 'borrar' sin filtro borraría media carpeta. Debe rechazarse."""
    datos = {"version": 1, "acciones": [{
        "nombre": "peligro", "descripcion": "borra todo", "tipo": "borrar"
    }]}
    with pytest.raises(ConfigError) as error:
        validar_esquema(datos)
    assert "acciones[0].filtro" in str(error.value)


BUENA = {"nombre": "ordenar", "descripcion": "Mueve los PDF", "tipo": "mover",
         "destino": "~/PDF"}


@pytest.mark.parametrize(
    "cambio, campo",
    [
        ({"tipo": "mober"}, "acciones[0].tipo"),
        ({"nombre": "MAL NOMBRE"}, "acciones[0].nombre"),
        ({"descripcion": None}, "acciones[0].descripcion"),
        ({"filtro": {"patron": "*.tmp"}}, "acciones[0].filtro.patron"),
    ],
    ids=["tipo-inexistente", "nombre-malo", "sin-descripcion", "regex-rota"],
)
def test_el_error_dice_que_campo_falla(cambio, campo):
    """El validador señala el campo exacto: 'acciones[0].tipo: …'."""
    with pytest.raises(ConfigError) as error:
        validar_esquema({"version": 1, "acciones": [BUENA | cambio]})
    assert any(fallo.startswith(campo) for fallo in error.value.problemas), error.value.problemas


def test_nombre_repetido():
    acc = {"nombre": "duplicada", "descripcion": "x", "tipo": "copiar"}
    datos = {"version": 1, "acciones": [acc, dict(acc)]}
    with pytest.raises(ConfigError) as error:
        validar_esquema(datos)
    assert "repetido" in str(error.value)


def test_patron_invalido_se_detecta():
    datos = {"version": 1, "acciones": [{
        "nombre": "raro", "descripcion": "x", "tipo": "borrar",
        "filtro": {"patron": "([sin cerrar"}
    }]}
    with pytest.raises(ConfigError) as error:
        validar_esquema(datos)
    assert "patron" in str(error.value)


def test_acciones_json_del_proyecto_es_valido():
    ruta = Path(__file__).resolve().parents[1] / "acciones.json"
    config = Configuracion.cargar(ruta)
    nombres = {a.nombre for a in config.acciones}
    assert {"ordenar-descargas", "limpiar-temporales", "renombrar-fotos",
            "respaldo-pdfs", "duplicados-descargas"} <= nombres
    assert any(a.con_ia for a in config.acciones)


# ---------------------------------------------------------------------------
# Motor: casos reales sobre carpetas temporales
# ---------------------------------------------------------------------------

def test_mover_con_colision_no_pisa(tmp_path):
    origen = tmp_path / "origen"
    destino = tmp_path / "destino"
    origen.mkdir(); destino.mkdir()
    fichero_de(origen / "apunte.pdf", "nuevo")
    fichero_de(destino / "apunte.pdf", "ya estaba")

    resultado = Motor().ejecutar(
        accion(tipo="mover", destino=destino, filtro={"extensiones": [".pdf"]}),
        origen)
    assert resultado.tocados == 1
    assert (destino / "apunte.pdf").read_text(encoding="utf-8") == "ya estaba"
    assert (destino / "apunte-1.pdf").exists()
    assert not (origen / "apunte.pdf").exists()


def test_borrar_solo_los_viejos(tmp_path):
    fichero_de(tmp_path / "viejo.tmp", edad_dias=40)
    fichero_de(tmp_path / "joven.tmp", edad_dias=2)
    accion_borrar = accion(
        tipo="borrar",
        filtro={"patron": r"\.tmp$", "mas_antiguo_que_dias": 30})
    resultado = Motor().ejecutar(accion_borrar, tmp_path)
    assert resultado.tocados == 1
    assert not (tmp_path / "viejo.tmp").exists()
    assert (tmp_path / "joven.tmp").exists()


def test_simular_no_toca_nada(tmp_path):
    fichero_de(tmp_path / "a.pdf")
    accion_mover = accion(tipo="mover", destino=tmp_path / "otro",
                         filtro={"extensiones": [".pdf"]})
    resultado = Motor().ejecutar(accion_mover, tmp_path, simular=True)
    assert resultado.tocados == 1
    assert (tmp_path / "a.pdf").exists()          # intacto
    assert not (tmp_path / "otro").exists()        # ni siquiera creado


def test_renombrar_con_tilde_y_espacios(tmp_path):
    fichero_de(tmp_path / "Apuntes de Física.jpg")
    accion_re = accion(tipo="renombrar",
                       filtro={"extensiones": [".jpg"]},
                       plantilla="{nombre}_{n:02}{ext}")
    resultado = Motor().ejecutar(accion_re, tmp_path)
    assert resultado.tocados == 1
    assert any(f.name.startswith("Apuntes de F") and f.name.endswith("_01.jpg")
               for f in tmp_path.iterdir())


def test_carpeta_inexistente_fallo_limpio(tmp_path):
    with pytest.raises(FalloEjecucion):
        Motor().ejecutar(accion(tipo="mover", destino=tmp_path), tmp_path / "no-existe")


def test_duplicados_por_hash(tmp_path):
    fichero_de(tmp_path / "a.txt", "mismo contenido")
    fichero_de(tmp_path / "b.txt", "mismo contenido")
    fichero_de(tmp_path / "c.txt", "distinto")
    resultado = Motor().ejecutar(accion(tipo="duplicados"), tmp_path)
    assert resultado.tocados == 1
    assert "a.txt" in resultado.hechos[0] and "b.txt" in resultado.hechos[0]


def test_hash_de_estable(tmp_path):
    assert hash_de.__doc__  # existe
    fichero = fichero_de(tmp_path / "a.txt", "mismo contenido")
    vacio = tmp_path / "vacio.txt"
    vacio.write_bytes(b"")
    assert hash_de(fichero) == hash_de(fichero)      # estable
    assert hash_de(fichero) != hash_de(vacio)         # distingue contenidos


# ---------------------------------------------------------------------------
# Capa IA: sin red y con proveedor simulado (nunca toca la red real)
# ---------------------------------------------------------------------------

def test_sin_clave_no_rompe(tmp_path, monkeypatch):
    monkeypatch.delenv("APUNCLI_IA_MODELO", raising=False)
    from apuncli.ai import ProveedorIA
    proveedor = ProveedorIA(url="http://192.0.2.1:9/v1", modelo="")  # IP sin ruta (TEST-NET)
    with pytest.raises(SinRedError):
        proveedor.preguntar("resume", "texto")


def test_sin_red_mensaje_humano(tmp_path, monkeypatch):
    """IP no enrutable: SinRedError con explicación, no un traceback de urllib."""
    from apuncli.ai import ProveedorIA
    proveedor = ProveedorIA(url="http://192.0.2.1:9/v1", modelo="qwen3:8b")
    with pytest.raises(SinRedError) as error:
        proveedor.preguntar("resume", "texto")
    assert "sin red" in str(error.value).lower() or "conexión" in str(error.value)


def test_comprobar_ia_sin_servidor(tmp_path, monkeypatch):
    from apuncli.ai import ProveedorIA
    prueba = ProveedorIA(url="http://192.0.2.1:9/v1", modelo="qwen3:8b").comprobar()
    assert prueba.disponible is False
    assert "192.0.2.1" in prueba.detalle or "conexión" in prueba.detalle


class PreguntasFalsas(ProveedorFalso):
    """ProveedorFalso que imita el formato de las preguntas de examen."""

    def preguntar(self, consigna, texto, largo_max=16000):
        if "pregunta" in consigna:
            return ("- ¿Qué es una pila? => Es una estructura LIFO.\n"
                    "- ¿Y una cola? Es una estructura FIFO.")
        return super().preguntar(consigna, texto, largo_max)


def test_accion_resumir_con_falso(proveedor_falso):
    from apuncli.ai import accion_resumir
    falso = proveedor_falso("- viñeta uno\n- viñeta dos")
    assert "viñeta" in accion_resumir("texto largo", falso)
    # la prueba que prueba: al modelo falso le llegó el documento
    assert falso.preguntas == ["texto largo"]


def test_accion_preguntas_normaliza_formato():
    from apuncli.ai import _SEP_PREGUNTA, accion_generar_preguntas
    salida = accion_generar_preguntas("texto", PreguntasFalsas())
    lineas = salida.splitlines()
    assert len(lineas) >= 2
    # cada pregunta normalizada empieza por '¿' (los guiones se quitan)
    assert all(l.startswith("¿") for l in lineas)
    # la respuesta suelta se pega a su pregunta (una línea = pregunta + respuesta)
    assert "FIFO" in lineas[-1]
    assert lineas[0].count(_SEP_PREGUNTA) == 1


def test_borrar_fichero_entre_listado_y_accion_no_rompe(tmp_path, monkeypatch):
    """Un .tmp que desaparece a mitad de la acción se omite, no revienta."""
    viejo = fichero_de(tmp_path / "viejo.tmp", edad_dias=40)
    accion_borrar = accion(tipo="borrar",
                           filtro={"patron": r"\.tmp$", "mas_antiguo_que_dias": 30})
    motor = Motor()
    original = motor._seleccion

    def seleccion_con_trampa(o, a, r):
        ficheros = original(o, a, r)
        ficheros[0].unlink()                 # desaparecido tras el listado
        return ficheros

    monkeypatch.setattr(motor, "_seleccion", seleccion_con_trampa)
    resultado = motor.ejecutar(accion_borrar, tmp_path)
    assert resultado.tocados == 0
    assert any("ya no existía" in o for o in resultado.omitidos)
