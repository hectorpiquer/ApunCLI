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
    if ruta.is_file():
        try:
            contenido = ruta.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            contenido = ""          # .env ilegible: seguimos con variables de entorno
        for linea in contenido.splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            valores[clave.strip()] = valor.strip().strip("'\"")
    for clave in ("APUNCLI_IA_URL", "APUNCLI_IA_CLAVE", "APUNCLI_IA_MODELO",
                  "CENTRO_IA_URL", "CENTRO_IA_KEY", "CENTRO_IA_CA"):
        if os.environ.get(clave):
            valores[clave] = os.environ[clave]
    return valores


class ProveedorIA:
    """Cliente mínimo de la API /chat/completions (como la de OpenAI/Ollama)."""

    REINTENTOS = 2          # los modelos del centro a veces tardan en despertar
    TIMEOUT_PETICION = 60   # segundos por intento
    TIMEOUT_COMPROBACION = 6

    def __init__(self, url: Optional[str] = None, clave: Optional[str] = None,
                 modelo: Optional[str] = None, env_ruta: Optional[Path] = None):
        valores = leer_env(env_ruta)
        self.url = (url or valores.get("APUNCLI_IA_URL")
                    or valores.get("CENTRO_IA_URL")
                    or "http://127.0.0.1:11434/v1").rstrip("/")
        self.clave = (clave or valores.get("APUNCLI_IA_CLAVE")
                      or valores.get("CENTRO_IA_KEY") or "")
        self.modelo = modelo or valores.get("APUNCLI_IA_MODELO") or valores.get(
            "CENTRO_IA_MODELO") or _MODELO_POR_DEFECTO
        self.certificado = valores.get("CENTRO_IA_CA") or os.environ.get(
            "NODE_EXTRA_CA_CERTS") or ""
        self._donde = (str(_ruta_env_preferida(env_ruta).name)
                       if _ruta_env_preferida(env_ruta).exists() else "variables de entorno")

    @property
    def _url_chat(self) -> str:
        return self.url + "/chat/completions"

    def preguntar(self, consigna: str, texto: str, largo_max: int = 16000) -> str:
        if self.url.startswith("file://"):            # modo de prueba sin red
            with open(self.url[len("file://"):], encoding="utf-8") as f:
                return f.read().strip()
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
        contexto = None
        if self.url.startswith("https"):
            import ssl
            contexto = ssl.create_default_context(cafile=self.certificado or None)
        for intento in range(self.REINTENTOS):
            tiempo = self.TIMEOUT_PETICION if intento == 0 else 8
            try:
                with urllib.request.urlopen(peticion, timeout=tiempo,
                                            context=contexto) as respuesta:
                    datos = json.loads(respuesta.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as error:
                if error.code in (401, 403):
                    raise SinRedError("La clave de IA no es válida (HTTP "
                                      f"{error.code}). Revisa APUNCLI_IA_CLAVE en .env.")
                raise SinRedError(f"El proveedor de IA respondió mal (HTTP {error.code}).")
            except (urllib.error.URLError, TimeoutError, OSError):
                if intento + 1 < self.REINTENTOS:
                    continue
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
        except Exception as error:  # noqa: BLE001 — comprobar-ia nunca explota
            return PruebaIA(False, self._donde, self.url, self.modelo,
                            f"error inesperado: {error}")
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

_CONSINA_RENOMBRAR = (
    "Eres un asistente que pone nombres de fichero. A partir del contenido de "
    "un documento, responde SOLO con un nombre de fichero en minúsculas, sin "
    "tildes, sin espacios (usa guiones), sin acentos y de 4 palabras máximo, "
    "sin extensión. Nada más."
)

_CONSINA_CLASIFICAR = (
    "Eres un asistente de clasificación. Responde SOLO con una de estas "
    "categorías, exacta: {categorias}. Si no encaja ninguna, responde "
    "'sin-clasificar'. Sin explicaciones."
)

_CATEGORIAS_POR_DEFECTO = "apuntes,admin,trabajo,other"
_SEP_PREGUNTA = "=>"


def a_nombre_seguro(propuesta: str, sugerida: str = "") -> str:
    """Sanea el nombre que propone el modelo: minúsculas, guiones, sin rutas.

    La extensión final siempre es la del fichero original (sugerida): si el
    modelo la añade ('informe.pdf'), se quita y se vuelve a poner normalizada
    para que nunca salga duplicada ni se pierda. Vacío → 'sin-nombre'.
    """
    import unicodedata
    extension = Path(sugerida).suffix.lower() if sugerida else ""
    nombre = unicodedata.normalize("NFKD", (propuesta or "").strip().lower())
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    if extension and nombre.endswith(extension):
        nombre = nombre[: -len(extension)]              # quita la extensión que añada
    nombre = re.sub(r"[^a-z0-9]+", "-", nombre)         # todo lo demás → guiones
    nombre = re.sub(r"-+", "-", nombre).strip("-")      # sin -- ni extremos
    if not nombre:
        nombre = "sin-nombre"
    return (nombre + extension)[:60]


def categorias_configuradas() -> list:
    from . import ajustes
    crudo = (os.environ.get("APUNCLI_IA_CATEGORIAS")
             or ajustes.leer_ajustes().get("categorias") or _CATEGORIAS_POR_DEFECTO)
    return [c.strip() for c in crudo.split(",") if c.strip()]


def accion_renombrar(texto: str, nombre_actual: str,
                     proveedor: Optional[ProveedorIA] = None) -> str:
    proveedor = proveedor or ProveedorIA()
    consigna = _CONSINA_RENOMBRAR
    respuesta = proveedor.preguntar(consigna,
                                    f"nombre actual: {nombre_actual}\n\n{texto}")
    primera = respuesta.strip().splitlines()[0] if respuesta.strip() else ""
    return primera


def accion_clasificar(texto: str, categorias: list,
                      proveedor: Optional[ProveedorIA] = None) -> str:
    proveedor = proveedor or ProveedorIA()
    consigna = _CONSINA_CLASIFICAR.replace("{categorias}", ", ".join(categorias))
    respuesta = proveedor.preguntar(consigna, texto)
    eleccion = respuesta.strip().strip(".- ").lower()
    return eleccion if eleccion in categorias else "sin-clasificar"


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
