"""Capa IA: habla con un proveedor OpenAI-compatible (los modelos del centro).

Reglas:
  · la clave NUNCA está en el código: se lee de .env (o variables de entorno)
  · sin clave o sin red no revienta: lanza SinRedError y la CLI sigue
    ofreciendo todo lo que no necesita IA
"""

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .errores import SinRedError

# .env en la carpeta actual; en el centro se copia .env.example → .env
_DEFAULT_ENV = Path.cwd() / ".env"
# orden de busqueda: APUNCLI_ENV decide; si no, .env y luego ia.env (carpeta actual)
_ENV_CANDIDATOS = (".env", "ia.env")
_MODELO_POR_DEFECTO = "qwen3:8b"  # el modelo del centro; cambialo en tu ia.env


def _ruta_env_preferida(ruta):
    if ruta:
        return Path(ruta)
    explicita = os.environ.get("APUNCLI_ENV")
    if explicita:
        return Path(explicita)
    for nombre in _ENV_CANDIDATOS:
        candidato = Path.cwd() / nombre
        if candidato.exists():
            return candidato
    return _DEFAULT_ENV


@dataclass
class PruebaIA:
    disponible: bool
    origen: str          # dónde está la config
    proveedor: str
    modelo: str
    detalle: str = ""


def leer_env(ruta: Optional[Path] = None) -> dict:
    """Mini-lector de .env (sin dependencias). Las vars reales ganan."""
    valores = {}
    ruta = _ruta_env_preferida(ruta)
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            valores[clave.strip()] = valor.strip().strip("'\"")
    for clave in ("APUNCLI_IA_URL", "APUNCLI_IA_CLAVE", "APUNCLI_IA_MODELO"):
        if os.environ.get(clave):
            valores[clave] = os.environ[clave]
    return valores


class ProveedorIA:
    """Cliente mínimo de la API /chat/completions (como la de OpenAI/Ollama)."""

    def __init__(self, url: Optional[str] = None, clave: Optional[str] = None,
                 modelo: Optional[str] = None, env_ruta: Optional[Path] = None):
        valores = leer_env(env_ruta)
        self.url = (url or valores.get("APUNCLI_IA_URL")
                    or "http://127.0.0.1:11434/v1").rstrip("/")
        self.clave = clave or valores.get("APUNCLI_IA_CLAVE") or ""
        self.modelo = modelo or valores.get("APUNCLI_IA_MODELO") or _MODELO_POR_DEFECTO
        self._donde = str(_ruta_env_preferida(env_ruta).name) if _ruta_env_preferida(env_ruta).exists() else "variables de entorno"

    @property
    def _url_chat(self) -> str:
        return self.url + "/chat/completions"

    def preguntar(self, consigna: str, texto: str, largo_max: int = 16000) -> str:
        if not self.modelo:
            raise SinRedError(
                "No hay modelo de IA configurado (APUNCLI_IA_MODELO). "
                "Copia .env.example a .env y rellénalo, o exporta las variables.")
        cuerpo = json.dumps({
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": consigna},
                {"role": "user", "content": texto[:largo_max]},
            ],
            "temperature": 0.2,
        }).encode("utf-8")
        peticion = urllib.request.Request(self._url_chat, data=cuerpo, method="POST")
        peticion.add_header("Content-Type", "application/json")
        if self.clave:
            peticion.add_header("Authorization", f"Bearer {self.clave}")
        try:
            with urllib.request.urlopen(peticion, timeout=60) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise SinRedError("La clave de IA no es válida (HTTP "
                                  f"{error.code}). Revisa APUNCLI_IA_CLAVE en .env.")
            raise SinRedError(f"El proveedor de IA respondió mal (HTTP {error.code}).")
        except (urllib.error.URLError, TimeoutError, OSError):
            raise SinRedError(f"No hay conexión con el proveedor de IA en {self.url}. "
                              "Sin red la CLI sigue funcionando con las acciones "
                              "que no necesitan IA.")
        try:
            return datos["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise SinRedError("La respuesta de la IA no trae texto; "
                              "¿el modelo sigue instalado?")

    def comprobar(self) -> PruebaIA:
        """Prueba real de conexión (para el comando comprobar-ia)."""
        if not self.modelo:
            return PruebaIA(False, self._donde, self.url, "(sin modelo)",
                            "Falta APUNCLI_IA_MODELO.")
        try:
            respuesta = self.preguntar("Contesta solo con la palabra: OK", "prueba",
                                       largo_max=10)
        except SinRedError as error:
            return PruebaIA(False, self._donde, self.url, self.modelo, str(error))
        return PruebaIA(True, self._donde, self.url, self.modelo,
                        f"respuesta: {respuesta[:40]}")


# --- las dos acciones con IA ----------------------------------------------

_CONSINA_RESUMEN = (
    "Eres un asistente de estudio. Resume el apunte en español en 5-8 viñetas "
    "cortas de Markdown, sin preámbulos ni saludos. Solo el resumen."
)

_CONSINA_PREGUNTAS = (
    "Eres un asistente de estudio. A partir del apunte, genera entre 5 y 8 "
    "preguntas de examen en español, una por línea, empezando cada una por "
    "'- '. Al final de cada pregunta añade '=> ' y la respuesta correcta "
    "en una línea. Sin preámbulos."
)

_SEP_PREGUNTA = "=>"


def accion_resumir(texto: str, proveedor: Optional[ProveedorIA] = None) -> str:
    proveedor = proveedor or ProveedorIA()
    return proveedor.preguntar(_CONSINA_RESUMEN, texto)


def accion_generar_preguntas(texto: str,
                             proveedor: Optional[ProveedorIA] = None) -> str:
    proveedor = proveedor or ProveedorIA()
    bruto = proveedor.preguntar(_CONSINA_PREGUNTAS, texto)
    lineas = []
    for linea in bruto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith(("-", "*", "•")) or _SEP_PREGUNTA in linea:
            lineas.append(linea.lstrip("-*• ").strip())
        elif lineas:
            lineas[-1] += " " + linea  # respuesta larga: se pega a su pregunta
    if not lineas:
        raise SinRedError("La IA no devolvió preguntas con el formato esperado; "
                          "reintenta o revisa el modelo.")
    return "\n".join(lineas)
