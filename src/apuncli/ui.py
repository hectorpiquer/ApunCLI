"""Utilidades de presentación por consola."""

import os
import shutil
import subprocess
import sys

from .errores import ApuncliError


def color_activado() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _pinta(texto: str, codigo: str) -> str:
    if color_activado():
        return f"\033[{codigo}m{texto}\033[0m"
    return texto


def subrayado(texto: str) -> str:
    return _pinta(texto, "4")


def tenue(texto: str) -> str:
    return _pinta(texto, "2")


def destacado(texto: str) -> str:
    return _pinta(texto, "1")


def titulo_de_seccion(texto: str) -> None:
    print()
    print(subrayado(texto))


def editor_ambiente() -> str:
    """Devuelve la orden del editor preferido del usuario."""
    for variable in ("EDITOR", "VISUAL"):
        valor = os.environ.get(variable)
        if valor:
            return valor
    for candidato in ("nano", "vim", "vi"):
        if shutil.which(candidato):
            return candidato
    raise ApuncliError(
        "No se encontró ningún editor. Define la variable de entorno EDITOR "
        "(por ejemplo: export EDITOR=nano)."
    )


def abrir_en_editor(archivo: str) -> int:
    """Abre un fichero con el editor y devuelve el código de salida."""
    editor = editor_ambiente().split()
    try:
        completado = subprocess.run(editor + [archivo])
        return completado.returncode
    except FileNotFoundError:
        raise ApuncliError(f"No se pudo abrir el editor: {editor[0]!r} no existe.")


def confirmar(mensaje: str, por_defecto: bool = False) -> bool:
    """Pregunta sí/no por consola."""
    sufijo = "[S/n]" if por_defecto else "[s/N]"
    try:
        respuesta = input(f"{mensaje} {sufijo}: ").strip().lower()
    except EOFError:
        return por_defecto
    if not respuesta:
        return por_defecto
    return respuesta in ("s", "si", "sí", "y")


def pedir_texto(mensaje: str) -> str:
    try:
        return input(mensaje)
    except EOFError:
        return ""


def leer_multilinea() -> str:
    """Lee varias líneas hasta Ctrl+D (o Ctrl+Z+Enter en Windows)."""
    print(tenue("Escribe el contenido (termina con Ctrl+D):"))
    lineas = []
    while True:
        try:
            lineas.append(input())
        except EOFError:
            break
    return "\n".join(lineas).strip()
