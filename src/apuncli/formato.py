"""Formato Markdown de apuntes (para exportar, importar y generar temarios)."""

import re
from typing import Dict, List, Optional, Tuple

from .errores import ApuncliError


def a_markdown(apunte, etiquetas: List[str], recursos=None) -> str:
    """Convierte un apunte (sqlite3.Row o dict) en texto Markdown con cabecera."""
    cuerpo = apunte["contenido"] or ""
    lineas = [f"# {apunte['titulo']}", ""]
    metadatos = []
    if apunte["asignatura"]:
        metadatos.append(f"asignatura: {apunte['asignatura']}")
    if etiquetas:
        metadatos.append("etiquetas: " + ", ".join(etiquetas))
    if recursos:
        metadatos.append("recursos: " + ", ".join(
            r["url"] if not r["nombre"] else f"{r['nombre']}=<{r['url']}>"
            for r in recursos
        ))
    if metadatos:
        lineas += [*metadatos, ""]
    lineas.append(cuerpo)
    return "\n".join(lineas).rstrip() + "\n"


_CABECERA_RE = re.compile(r"^#\s+(?P<titulo>.+?)\s*$")
_METADATO_RE = re.compile(r"^(asignatura|etiquetas|recursos)\s*:\s*(?P<valor>.*)$")


def de_markdown(texto: str) -> Tuple[str, str, str, List[str]]:
    """Convierte texto Markdown en (titulo, contenido, asignatura, etiquetas).

    El primer '# Título' marca el título. Justo debajo, y hasta la primera
    línea que no sea un campo 'asignatura:', 'etiquetas:' o 'recursos:', se
    leen los metadatos. El resto es el contenido.

    Devuelve (titulo, contenido, asignatura, etiquetas, recursos).
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
    recursos: List[Tuple[str, str]] = []
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
        elif clave == "recursos":
            recursos = _parsear_recursos(valor)
        indice += 1

    contenido = "\n".join(lineas[indice:]).strip()
    return titulo, contenido, asignatura, etiquetas, recursos


def _parsear_recursos(valor: str) -> List[Tuple[str, str]]:
    """'nombre=<url>, otraurl' -> [('nombre', 'url'), ('', 'otraurl')]."""
    recursos = []
    for trozo in valor.split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        if "=" in trozo:
            nombre, _, url = trozo.partition("=")
            url = url.strip().strip("<>")
            recursos.append((nombre.strip(), url))
        else:
            recursos.append(("", trozo))
    return recursos


_BLOQUE_TEST_RE = re.compile(
    r"\*\*\s*Pregunta:\s*\*\*\s*(?P<pregunta>.*?)\s*\*\*\s*Respuesta:\s*\*\*\s*(?P<respuesta>.+?)(?=(\*\*\s*Pregunta:|\Z))",
    re.IGNORECASE | re.DOTALL,
)


def extraer_preguntas(texto: str) -> List[Tuple[str, str]]:
    """Extrae pares pregunta/respuesta escritos como **Pregunta:** … **Respuesta:** …"""
    pares = []
    for coincidencia in _BLOQUE_TEST_RE.finditer(texto):
        pregunta = " ".join(coincidencia.group("pregunta").split())
        respuesta = " ".join(coincidencia.group("respuesta").split())
        if pregunta and respuesta:
            pares.append((pregunta, respuesta))
    return pares


def analizar_fichero_test(texto: str) -> List[dict]:
    """Analiza un fichero de test: '# Apunte' + **Pregunta:**/**Respuesta:**.

    Devuelve una lista de {'apunte', 'pregunta', 'respuesta'}.
    """
    preguntas = []
    for linea_bloque in re.split(r"^#\s+(?=\S)", texto, flags=re.MULTILINE):
        bloque = linea_bloque.strip()
        if not bloque:
            continue
        titulo = bloque.split("\n", 1)[0].strip()
        for pregunta, respuesta in extraer_preguntas(bloque):
            preguntas.append({"apunte": titulo, "pregunta": pregunta,
                              "respuesta": respuesta})
    if not preguntas:
        raise ApuncliError(
            "El fichero no contiene ninguna pregunta. Formato esperado:\n"
            "  # Apunte de Programación\n"
            "  **Pregunta:** ¿Qué es una pila?\n"
            "  **Respuesta:** Una estructura LIFO."
        )
    return preguntas
