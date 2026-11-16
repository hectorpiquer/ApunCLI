"""Andamiaje común de los tests: la caja de arena.

Regla de oro: NINGUNA prueba toca las carpetas reales del usuario ni llama al
servidor de IA del centro. Todo ocurre en tmp_path, con HOME/USERPROFILE
apuntando ahí y con la configuración de IA anulada.
"""

import os
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    """Cada prueba, en su carpeta temporal y sin la IA de verdad."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))          # ~ apunta aquí (Linux/macOS)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))   # y aquí (Windows)
    monkeypatch.setenv("APUNCLI_ENV", str(tmp_path / "ia-inexistente.env"))
    for variable in ("APUNCLI_IA_URL", "APUNCLI_IA_CLAVE", "APUNCLI_IA_MODELO"):
        monkeypatch.delenv(variable, raising=False)
    # sin red real: cualquier petición cae en un proxy que falla al instante
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.delenv("NO_PROXY", raising=False)


@pytest.fixture
def descargas(tmp_path) -> Path:
    """Una carpeta con ficheros feos: tildes, espacios, mayúsculas y uno viejo."""
    import time
    carpeta = tmp_path / "Descargas"
    carpeta.mkdir()
    for nombre in ["factura.pdf", "apuntes de redes.docx", "FOTO1.JPG",
                   "cumpleaños 2.png", "viejo.tmp"]:
        (carpeta / nombre).write_text("contenido de prueba", encoding="utf-8")
    hace_40_dias = time.time() - 40 * 86400
    os.utime(carpeta / "viejo.tmp", (hace_40_dias, hace_40_dias))
    return carpeta


@pytest.fixture
def escribir_config(tmp_path):
    """Escribe un acciones.json (lista de acciones o texto tal cual) y da su ruta."""
    import json

    def escribir(acciones) -> Path:
        ruta = tmp_path / "acciones.json"
        if isinstance(acciones, str):
            texto = acciones
        else:
            texto = json.dumps({"version": 1, "acciones": acciones})
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    return escribir


@pytest.fixture
def proveedor_falso():
    return ProveedorFalso

class ProveedorFalso:
    """Un «modelo» que contesta lo que tú digas y apunta lo que le preguntan.

    Heredar de ProveedorIA hace que cualquier acción la acepte igual que el
    proveedor real: pruebas sin red, sin clave y sin gastar un token.
    """

    from apuncli.ai import ProveedorIA as _base

    def __init__(self, respuesta="respuesta de pega"):
        self.respuesta = respuesta
        self.preguntas = []
        self.url = "falso://sin-red"
        self.modelo = "modelo-falso"
        self.clave = ""
        self._donde = "prueba"

    def preguntar(self, consigna, texto, largo_max=16000):
        self.preguntas.append(texto)
        return self.respuesta
