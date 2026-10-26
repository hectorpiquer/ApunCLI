"""Formato Markdown de apuntes (para exportar e importar)."""

import re
from typing import Dict, List, Optional, Tuple


def a_markdown(apunte, etiquetas: List[str]) -> str:
    """Convierte un apunte (sqlite3.Row o dict) en texto Markdown con cabecera."""
    cuerpo = apunte["contenido"] or ""
    lineas = [f"# {apunte['titulo']}", ""]
    metadatos = []
    if apunte["asignatura"]:
        metadatos.append(f"asignatura: {apunte['asignatura']}")
    if etiquetas:
        metadatos.append("etiquetas: " + ", ".join(etiquetas))
    if metadatos:
        lineas += [*metadatos, ""]
    lineas.append(cuerpo)
    return "\n".join(lineas).rstrip() + "\n"


_CABECERA_RE = re.compile(r"^#\s+(?P<titulo>.+?)\s*$")
_METADATO_RE = re.compile(r"^(asignatura|etiquetas)\s*:\s*(?P<valor>.*)$")


def de_markdown(texto: str) -> Tuple[str, str, str, List[str]]:
    """Convierte texto Markdown en (titulo, contenido, asignatura, etiquetas).

    El primer '# Título' marca el título. Justo debajo, y hasta la primera
    línea que no sea un campo 'asignatura:' o 'etiquetas:', se leen los
    metadatos. El resto es el contenido.
    """
    lineas = texto.replace("\r\n", "\n").split("\n")

    titulo = ""
    indice = 0
    for indice, linea in enumerate(lineas):
        coincidencia = _CABECERA_RE.match(linea)
        if coincidencia:
            titulo = coincidencia.group("titulo").strip()
            indice += 1
            break

    asignatura = ""
    etiquetas: List[str] = []
    while indice < len(lineas):
        desnuda = lineas[indice].strip()
        if not desnuda:
            indice += 1
            continue
        coincidencia = _METADATO_RE.match(desnuda)
        if not coincidencia:
            break
        clave = desnuda.split(":", 1)[0].strip().lower()
        valor = coincidencia.group("valor").strip()
        if clave == "asignatura":
            asignatura = valor
        elif clave == "etiquetas":
            etiquetas = [e.strip().lower() for e in valor.split(",") if e.strip()]
        indice += 1

    contenido = "\n".join(lineas[indice:]).strip()
    return titulo, contenido, asignatura, etiquetas
