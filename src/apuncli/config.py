"""Lectura y validación de acciones.json (configuración externa).

El validador es estricto a propósito: si algo falla, dice exactamente qué
campo está mal en lugar de romper el programa. Los problemas se recogen
TODOS de golpe, no solo el primero.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .errores import ConfigError

# nombre de acción: minúsculas, dígitos y guiones (el que se teclea)
_NOMBRE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

TIPOS_VALIDOS = {
    "mover", "renombrar", "copiar", "borrar", "duplicados",
    "resumir-ia", "generar-preguntas-ia", "generar-temario",
}
# tipos que modifican ficheros/apuntes y por tanto piden simulación o confirmación
TIPOS_DESTRUCTIVOS = {"mover", "renombrar", "copiar", "borrar"}


class Configuracion:
    """La configuración cargada y validada, con sus acciones indexadas."""

    def __init__(self, ruta: Path, datos: dict, acciones: List["AccionConfig"]):
        self.ruta = ruta
        self.version = datos["version"]
        self.acciones = acciones

    @classmethod
    def cargar(cls, ruta: Path) -> "Configuracion":
        ruta = Path(ruta).expanduser()
        if not ruta.exists():
            raise ConfigError([f"El fichero de configuración no existe: {ruta}"])
        try:
            texto = ruta.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ConfigError([f"{ruta} no está en UTF-8; guárdalo con codificación UTF-8."])
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as error:
            raise ConfigError([f"El JSON está mal formado: {error}"])
        acciones = validar_esquema(datos)
        return cls(ruta, datos, acciones)

    def buscar(self, nombre: str) -> "AccionConfig":
        for accion in self.acciones:
            if accion.nombre == nombre:
                return accion
        disponibles = ", ".join(a.nombre for a in self.acciones) or "(ninguna)"
        raise ConfigError([f"La acción '{nombre}' no existe en {self.ruta}. "
                           f"Acciones disponibles: {disponibles}"])


class AccionConfig:
    """Una acción del fichero, ya validada y con sus partes resueltas."""

    def __init__(self, datos: dict):
        self.nombre: str = datos["nombre"]
        self.descripcion: str = datos["descripcion"]
        self.tipo: str = datos["tipo"]
        self.origen: Optional[Path] = _como_ruta(datos.get("origen"))
        self.destino: Optional[Path] = _como_ruta(datos.get("destino"))
        self.filtro: dict = datos.get("filtro", {})
        self.plantilla: Optional[str] = datos.get("plantilla")
        self.confirmar: bool = datos.get("confirmar", self.tipo in TIPOS_DESTRUCTIVOS)
        self.con_ia: bool = self.tipo.endswith("-ia")

    @classmethod
    def desde_config(cls, datos: dict) -> "AccionConfig":
        """Fábrica: construye la acción solo si el esquema ya es válido."""
        return cls(datos)

    @property
    def destructiva(self) -> bool:
        return self.tipo in TIPOS_DESTRUCTIVOS

    def resumen(self) -> str:
        return f"{self.nombre}: {self.descripcion} [tipo {self.tipo}]"


def _como_ruta(valor: Optional[str]) -> Optional[Path]:
    if valor is None:
        return None
    return Path(str(valor).replace("~", str(Path.home())))


def validar_esquema(datos: Any) -> List[AccionConfig]:
    """Devuelve las acciones validadas o lanza ConfigError con TODOS los fallos.

    Cada problema señala el campo exacto: 'acciones[2].nombre: …'.
    """
    problemas: List[str] = []

    if not isinstance(datos, dict):
        raise ConfigError(["El fichero debe contener un objeto JSON { … }. "
                           "Comprueba las llaves externas."])

    if "version" not in datos:
        problemas.append("Falta el campo 'version' (número entero, empieza por 1).")
    elif not isinstance(datos["version"], int):
        problemas.append("El campo 'version' debe ser un número entero.")

    if "acciones" not in datos:
        problemas.append("Falta el campo 'acciones' (una lista con [ … ]).")
        raise ConfigError(problemas)
    lista = datos["acciones"]
    if not isinstance(lista, list):
        problemas.append("El campo 'acciones' debe ser una lista [ … ].")
        raise ConfigError(problemas)

    vistos = set()
    acciones_validas: List[AccionConfig] = []
    for i, item in enumerate(lista):
        campo = f"acciones[{i}]"
        if not isinstance(item, dict):
            problemas.append(f"{campo}: debe ser un objeto {{ … }}.")
            continue
        accion, fallos = _validar_accion(item, campo, vistos)
        problemas.extend(fallos)
        if not fallos and accion is not None:
            vistos.add(accion.nombre)
            acciones_validas.append(accion)

    if problemas:
        raise ConfigError(problemas)
    if not acciones_validas:
        raise ConfigError(["No hay ninguna acción definida. Añade al menos una en "
                           "'acciones': [ … ]."])
    return acciones_validas


def _validar_accion(item: dict, campo: str, vistos: set) -> Tuple[Optional[AccionConfig], List[str]]:
    fallos: List[str] = []

    def falta(nombre: str, esperado: str) -> None:
        fallos.append(f"{campo}.{nombre}: falta (esperado {esperado}).")

    nombre = item.get("nombre")
    if nombre is None:
        falta("nombre", "ej: 'ordenar-apuntes'")
    elif not isinstance(nombre, str) or not _NOMBRE_RE.match(nombre):
        fallos.append(f"{campo}.nombre: '{nombre}' no vale; usa minúsculas, dígitos "
                      "y guiones (ej: 'ordenar-apuntes').")
    elif nombre in vistos:
        fallos.append(f"{campo}.nombre: '{nombre}' está repetido; debe ser único.")

    descripcion = item.get("descripcion")
    if descripcion is None:
        falta("descripcion", "una frase de lo que hace")
    elif not isinstance(descripcion, str) or not descripcion.strip():
        fallos.append(f"{campo}.descripcion: debe ser una frase sin vaciar.")

    tipo = item.get("tipo")
    if tipo is None:
        falta("tipo", "uno de: " + ", ".join(sorted(TIPOS_VALIDOS)))
    elif tipo not in TIPOS_VALIDOS:
        fallos.append(f"{campo}.tipo: '{tipo}' no existe; "
                      "válidos: " + ", ".join(sorted(TIPOS_VALIDOS)) + ".")

    # requisitos por tipo
    if tipo == "mover":
        if "origen" not in item and "destino" not in item:
            fallos.append(f"{campo}: un 'mover' necesita al menos 'destino'.")
    elif tipo == "renombrar" and not item.get("plantilla"):
        fallos.append(f"{campo}.plantilla: un 'renombrar' necesita una plantilla "
                      "(ej: '{fecha:%Y-%m-%d}_{n:03}{ext}').")
    elif tipo == "borrar" and not item.get("filtro"):
        fallos.append(f"{campo}.filtro: un 'borrar' necesita un filtro; "
                      "sin filtro borraría todo.")

    filtro = item.get("filtro", {})
    if not isinstance(filtro, dict):
        fallos.append(f"{campo}.filtro: debe ser un objeto {{ }} con 'extensiones', "
                      "'patron' o 'mas_antiguo_que_dias'.")
    else:
        if "extensiones" in filtro and not isinstance(filtro["extensiones"], list):
            fallos.append(f"{campo}.filtro.extensiones: debe ser una lista "
                          '[ej: [".pdf", ".md"]].')
        if "patron" in filtro:
            try:
                re.compile(filtro["patron"])
            except re.error as error:
                fallos.append(f"{campo}.filtro.patron: expresión regular inválida ({error}).")
        if "mas_antiguo_que_dias" in filtro and not isinstance(
                filtro["mas_antiguo_que_dias"], int):
            fallos.append(f"{campo}.filtro.mas_antiguo_que_dias: debe ser un "
                          "número entero de días.")

    for clave in ("origen", "destino", "plantilla"):
        if clave in item and not isinstance(item[clave], str):
            fallos.append(f"{campo}.{clave}: debe ser un texto de ruta o plantilla.")

    if "confirmar" in item and not isinstance(item["confirmar"], bool):
        fallos.append(f"{campo}.confirmar: debe ser true o false.")

    if fallos:
        return None, fallos
    return AccionConfig.desde_config(item), []
