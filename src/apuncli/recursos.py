"""Detección y apertura de recursos (enlaces web y ficheros locales)."""

import os
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import url2pathname

_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
_RUTA_RE = re.compile(r"(?<!\S)((?:[~/][\w.\-/]*|[\w.\-/]+\.[A-Za-z0-9]{1,10}))(?![\w.\-/])")

_EXTENSIONES = {
    ".pdf": "documento",
    ".png": "imagen", ".jpg": "imagen", ".jpeg": "imagen", ".gif": "imagen",
    ".webp": "imagen", ".svg": "imagen",
    ".md": "texto", ".txt": "texto", ".rst": "texto",
    ".py": "código", ".java": "código", ".c": "código", ".cpp": "código",
    ".js": "código", ".html": "código", ".sql": "código", ".sh": "código",
    ".zip": "archivo", ".rar": "archivo", ".7z": "archivo",
    ".mp4": "vídeo", ".mkv": "vídeo", ".webm": "vídeo",
    ".mp3": "audio",
    ".ods": "documento", ".odt": "documento", ".xlsx": "documento",
    ".docx": "documento", ".pptx": "documento",
}


def clasificar(texto: str) -> str:
    """Devuelve el tipo de recurso: web, imagen, documento, vídeo, audio, texto, código…"""
    if es_url(texto):
        return "web"
    extension = os.path.splitext(urlparse(texto).path or texto)[1].lower()
    return _EXTENSIONES.get(extension, "fichero")


def es_url(texto: str) -> bool:
    return bool(re.match(r"^https?://", texto))


def detectar_en_texto(texto: str):
    """Busca en un texto URLs y rutas de ficheros que existen en el disco.

    Devuelve una lista de tuplas (url, nombre).
    """
    encontrados = []
    vistos = set()

    for coincidencia in _URL_RE.finditer(texto):
        url = coincidencia.group(0).rstrip(".,;:")
        if url not in vistos:
            vistos.add(url)
            encontrados.append((url, ""))

    for coincidencia in _RUTA_RE.finditer(texto):
        ruta = os.path.expanduser(coincidencia.group(1))
        if os.path.exists(ruta) and os.path.abspath(ruta) not in vistos:
            vistos.add(os.path.abspath(ruta))
            encontrados.append((os.path.abspath(ruta), os.path.basename(ruta)))

    return encontrados


def abrir_recurso(url: str) -> None:
    """Abre un recurso con el programa que el sistema tenga asociado."""
    if es_url(url):
        abrir_en_navegador(url)
    else:
        abrir_en_sistema(os.path.expanduser(url))


def abrir_en_navegador(url: str) -> None:
    orden = None
    if sys.platform.startswith("win"):
        orden = ["cmd", "/c", "start", "", url]
    elif sys.platform == "darwin":
        orden = ["open", url]
    else:
        for candidato in ("xdg-open", "wslview"):
            if shutil.which(candidato):
                orden = [candidato, url]
                break
    if not orden:
        raise FileNotFoundError("No he encontrado cómo abrir el navegador (instala xdg-open).")
    _lanzar(orden)


def abrir_en_sistema(ruta: str) -> None:
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"El fichero no existe: {ruta}")
    if sys.platform.startswith("win"):
        orden = ["cmd", "/c", "start", "", os.path.abspath(ruta)]
    elif sys.platform == "darwin":
        orden = ["open", os.path.abspath(ruta)]
    else:
        if not shutil.which("xdg-open"):
            raise FileNotFoundError("No he encontrado cómo abrir ficheros (instala xdg-open).")
        orden = ["xdg-open", os.path.abspath(ruta)]
    _lanzar(orden)


def _lanzar(orden) -> None:
    subprocess.Popen(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def nombre_para(ruta_o_url: str) -> str:
    """Nombre sugerido para un recurso: el título del fichero o el dominio."""
    if es_url(ruta_o_url):
        dominio = urlparse(ruta_o_url).netloc
        return dominio.replace("www.", "")
    return os.path.basename(os.path.expanduser(ruta_o_url))
