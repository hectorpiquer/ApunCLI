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
