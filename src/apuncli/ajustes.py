"""Ajustes locales de apuncli (JSON en ~/.apuncli/config.json).

Pocos valores, todos opcionales: modo recordado del menú, favoritas de
explorador… Se escribe solo al elegir; se puede editar a mano.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .errores import ApuncliError

MODOS = ("estudio", "organizador", "preguntar")


def ruta_config() -> Path:
    """~/.apuncli/config.json (respeta APUNCLI_HOME para poder probarlo)."""
    base = os.environ.get("APUNCLI_HOME") or os.path.join(
        os.path.expanduser("~"), ".apuncli")
    return Path(base) / "config.json"


def leer_ajustes() -> Dict[str, Any]:
    ruta = ruta_config()
    if not ruta.is_file():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}                      # config ilegible: no rompe, empieza limpia
    return datos if isinstance(datos, dict) else {}


def guardar_ajustes(**valores: Any) -> None:
    datos = leer_ajustes()
    datos.update(valores)
    ruta = ruta_config()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    except OSError as error:
        raise ApuncliError(f"No se pudo guardar la configuración ({ruta}): {error}")


def modo_recordado() -> Optional[str]:
    """El modo elegido la última vez ('estudio' u 'organizador') si existe."""
    valor = leer_ajustes().get("modo")
    return valor if valor in ("estudio", "organizador") else None


# ---------------------------------------------------------------------------
# Registro de acciones: que el usuario siempre sepa qué tocó la herramienta
# ---------------------------------------------------------------------------

import time


def registrar(accion: str, detalle: str, resultado: str = "hecho") -> None:
    """Añade una línea a ~/.apuncli/acciones.log (nunca rompe la orden)."""
    linea = f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{accion}\t{resultado}\t{detalle}\n"
    try:
        ruta = ruta_config().parent / "acciones.log"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as archivo:
            archivo.write(linea)
    except OSError:
        pass                                   # sin disco de registro: seguimos


def ver_registro(cuantas: int = 20):
    """Las últimas N líneas del registro [(línea, …)], o lista vacía."""
    ruta = ruta_config().parent / "acciones.log"
    if not ruta.is_file():
        return []
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return lineas[-cuantas:]
