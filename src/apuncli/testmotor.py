"""Motor de test: genera preguntas a partir de los apuntes y puntúa."""

import re
import unicodedata
from typing import List

from . import db
from .errores import ApuncliError

_BLOQUE_RE = re.compile(
    r"\*\*\s*Pregunta\s*:\s*\*\*\s*(?P<pregunta>.*?)\s*\*\*\s*Respuesta\s*:\s*\*\*\s*(?P<respuesta>.+?)(?=(\*\*\s*Pregunta\s*:)|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def preparar_preguntas(conexion, asignatura=None, etiqueta=None,
                      numero: int = 10) -> List[dict]:
    """Busca pares **Pregunta:**/**Respuesta:** en los apuntes filtrados."""
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    if not apuntes:
        raise ApuncliError("No hay apuntes que coincidan con el filtro.")

    preguntas: List[dict] = []
    for apunte in apuntes:
        for coincidencia in _BLOQUE_RE.finditer(apunte["contenido"] or ""):
            pregunta = " ".join(coincidencia.group("pregunta").split())
            respuesta = " ".join(coincidencia.group("respuesta").split())
            if pregunta and respuesta:
                preguntas.append({
                    "apunte_id": apunte["id"],
                    "apunte": apunte["titulo"],
                    "pregunta": pregunta,
                    "respuesta": respuesta,
                })

    if not preguntas:
        raise ApuncliError(
            "Ningún apunte tiene preguntas. Añádelas dentro del contenido así:\n"
            "  **Pregunta:** ¿Qué es una pila?\n"
            "  **Respuesta:** Una estructura LIFO.\n"
            "Pista: apuncli editar 1 --anadir -c '**Pregunta:** ...'"
        )
    return preguntas[:numero]


def _normalizar(texto: str) -> str:
    """Minúsculas, sin puntuación ni acentos, para comparar respuestas."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^\w\s]", " ", texto)
    return " ".join(texto.split())


def es_correcta(respuesta_usuario: str, respuesta_ok: str) -> bool:
    """Acierto aproximado: ignora mayúsculas, acentos y puntuación."""
    usuario = _normalizar(respuesta_usuario)
    ok = _normalizar(respuesta_ok)
    if not usuario or not ok:
        return False
    if usuario in ok or ok in usuario:
        return True
    palabras_ok = set(ok.split())
    compartidas = set(usuario.split()) & palabras_ok
    return len(compartidas) >= min(3, len(palabras_ok))
