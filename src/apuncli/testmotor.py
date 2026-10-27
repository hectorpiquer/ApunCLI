"""Motor del test automático de apuncli.

Dos formas de conseguir preguntas, ambas gratis y sin IA externa:

1. Preguntas a medida: bloques escritos a mano dentro del contenido con el
   formato '**Pregunta:** … **Respuesta:** …'.
2. Generación automática: reglas heurísticas que leen el contenido del apunte
   (definiciones 'X es Y', listas con '-', negritas, secciones '## …') y
   fabrican preguntas de hueco, definición, verdadero/falso o opción múltiple.
"""

import random
import re
import unicodedata
from typing import List

from . import db
from .errores import ApuncliError

# --- preguntas escritas a mano ------------------------------------------------

_BLOQUE_RE = re.compile(
    r"\*\*\s*Pregunta\s*:\s*\*\*\s*(?P<pregunta>.*?)\s*\*\*\s*Respuesta\s*:\s*\*\*\s*(?P<respuesta>.+?)"
    r"(?=(\*\*\s*Pregunta\s*:)|\Z)",
    re.IGNORECASE | re.DOTALL,
)

_MANUAL_CLAVE = "manual"
_HUECO = "\u0000hueco\u0000"


def sin_marcas_test(texto: str) -> str:
    """Quita los bloques '**Pregunta:**/**Respuesta:**' del texto para generar."""
    return _BLOQUE_RE.sub(" ", texto)


def preguntas_manuales(contenido: str) -> List[dict]:
    pares = []
    for coincidencia in _BLOQUE_RE.finditer(contenido or ""):
        pregunta = " ".join(coincidencia.group("pregunta").split())
        respuesta = " ".join(coincidencia.group("respuesta").split())
        if pregunta and respuesta:
            pares.append({"tipo": _MANUAL_CLAVE, "pregunta": pregunta,
                          "respuesta": respuesta})
    return pares


# --- generación automática ----------------------------------------------------

_DEFINICION_RE = re.compile(
    r"^(?:El|La|Los|Las|Lo|Un|Una|Unos|Unas)\s+"
    r"(?P<sujeto>[\wÁÉÍÓÚÜÑáéíóúüñ][\wÁÉÍÓÚÜÑáéíóúüñ ()/·-]{0,70}?)\s+"
    r"(?P<verbo>es|son|significa|consiste en|se define como|se definen como)\s+"
    r"(?P<atributo>.{3,}?)\s*[.;:]?\s*$",
    re.IGNORECASE,
)
_LISTA_RE = re.compile(r"^\s*[-•*]\s+(?P<elemento>.{2,120})$", re.MULTILINE)
_NEGRITA_RE = re.compile(r"\*\*([^*\n]{2,80})\*\*")
_SECCION_RE = re.compile(r"^##\s+(?P<titulo>.+)$", re.MULTILINE)

_ACENTOS_RE = re.compile(r"[\u0300-\u036f]")


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^\w\s]", " ", texto)
    return " ".join(texto.split())


def _primera_frase(texto: str, maximo: int = 140) -> str:
    texto = " ".join(texto.split())
    return texto[:maximo].strip()


def _frase_con(texto: str, marca: str, maximo: int = 160) -> str:
    """Devuelve solo la línea que contiene 'marca' (sin cabeceras Markdown)."""
    for linea in texto.split("\n"):
        if marca in linea:
            frase = " ".join(linea.split())
            if frase.startswith("#"):
                return ""
            return frase[:maximo].strip()
    return ""


def _secciones(contenido: str):
    """Divide el contenido en pares (nombre, cuerpo) por cada '## Título'."""
    partes = re.split(r"^##\s+(?=\S)", contenido, flags=re.MULTILINE)
    resultado = []
    for numero, parte in enumerate(partes):
        if numero == 0:
            if parte.strip():
                resultado.append(("", parte))
            continue
        nombre, _, cuerpo = parte.partition("\n")
        resultado.append((nombre.strip(), cuerpo))
    return resultado


def generar_preguntas(apunte) -> List[dict]:
    """Genera preguntas automáticamente a partir del contenido de un apunte.

    Devuelve una lista de {'tipo', 'pregunta', 'respuesta', 'opciones'}.
    """
    contenido = (apunte["contenido"] or "").strip()
    titulo = apunte["titulo"]
    preguntas: List[dict] = []
    vistos = set()

    def anadir(dic: dict) -> None:
        firma = _normalizar(dic["pregunta"])
        if firma and firma not in vistos and len(dic["respuesta"]) >= 2:
            vistos.add(firma)
            preguntas.append(dic)

    # 1) Huecos sobre negritas (términos remarcados a propósito).
    limpio = sin_marcas_test(contenido)
    for coincidencia in _NEGRITA_RE.finditer(limpio):
        termino = coincidencia.group(1).strip()
        hueco = limpio.replace(f"**{termino}**", _HUECO, 1)
        frase = _frase_con(hueco, _HUECO)
        if not frase:
            continue
        anadir({
            "tipo": "hueco",
            "pregunta": f"Completa: {frase.replace(_HUECO, '______')}",
            "respuesta": termino,
        })

    # 2) Definiciones 'X es/son Y' sobre líneas sueltas.
    for linea in limpio.split("\n"):
        coincidencia = _DEFINICION_RE.match(linea.strip())
        if not coincidencia:
            continue
        sujeto = coincidencia.group("sujeto").strip()
        verbo = coincidencia.group("verbo").lower()
        atributo = " ".join(coincidencia.group("atributo").split())
        if len(atributo) < 3 or len(sujeto) < 2:
            continue
        verbo_frase = "qué es" if verbo in ("es", "significa", "se define como") \
            else "qué son"
        anadir({
            "tipo": "definicion",
            "pregunta": f"¿{verbo_frase} {sujeto}?",
            "respuesta": atributo,
        })

    # 3) Listas '- elemento' sobre un apartado '## Título' → pregunta de ideas.
    for nombre, cuerpo in _secciones(contenido):
        elementos = [e.strip().rstrip(".;") for e in _LISTA_RE.findall(cuerpo)]
        elementos = [e for e in elementos if _tiene_letra(e)]
        if len(elementos) >= 3:
            muestra = elementos[:4]
            respuesta = ", ".join(muestra)
            pregunta = (f"Nombra elementos/ideas de «{nombre.strip()}» "
                        f"(pista: hay {len(elementos)})" if nombre else
                        f"Nombra elementos/ideas de «{titulo}» "
                        f"(pista: hay {len(elementos)})")
            opciones = _opciones_multiples(elementos, muestra)
            anadir({"tipo": "lista", "pregunta": pregunta,
                    "respuesta": respuesta, "opciones": opciones})

    random.shuffle(preguntas)
    return preguntas


def _tiene_letra(texto: str) -> bool:
    return bool(re.search(r"\w", texto, re.UNICODE))


def _opciones_multiples(elementos, muestra) -> List[str]:
    """Construye 4 opciones falsas plausibles a partir de otros elementos."""
    falsas = [e for e in elementos if e not in muestra]
    if len(falsas) < 3:
        return []
    opciones = muestra[:1] + random.sample(falsas, 3)
    random.shuffle(opciones)
    return opciones


# --- orquestación -------------------------------------------------------------

def preparar_preguntas(conexion, asignatura=None, etiqueta=None,
                      numero: int = 10, solo_automaticas: bool = False) -> List[dict]:
    """Reúne preguntas (manuales + automáticas) de los apuntes filtrados.

    Orden determinista: las manuales primero (son las que tú preparaste) y
    después las generadas automáticamente.
    """
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    if not apuntes:
        raise ApuncliError("No hay apuntes que coincidan con el filtro.")

    manuales: List[dict] = []
    automaticas: List[dict] = []
    for apunte in apuntes:
        para_apunte = []
        if not solo_automaticas:
            para_apunte = preguntas_manuales(apunte["contenido"])
        for pregunta in para_apunte:
            pregunta["apunte_id"] = apunte["id"]
            pregunta["apunte"] = apunte["titulo"]
        manuales.extend(para_apunte)
        auto = generar_preguntas(apunte)
        for pregunta in auto:
            pregunta["apunte_id"] = apunte["id"]
            pregunta["apunte"] = apunte["titulo"]
        automaticas.extend(auto)

    preguntas = manuales + automaticas
    if not preguntas:
        raise ApuncliError(
            "No he podido generar preguntas con estos apuntes.\n"
            "Consejos para que funcionen bien:\n"
            "  · escribe definiciones: 'La pila es una estructura LIFO.'\n"
            "  · remarca términos con **negrita**\n"
            "  · usa listas con '-' y apartados con '## Título'\n"
            "  · o añade preguntas a mano: **Pregunta:** … **Respuesta:** …"
        )
    return preguntas[:numero]


# --- corrección tolerante ------------------------------------------------------

def es_correcta(respuesta_usuario: str, respuesta_ok: str) -> bool:
    usuario = _normalizar(respuesta_usuario)
    ok = _normalizar(respuesta_ok)
    if not usuario or not ok:
        return False
    if usuario in ok or ok in usuario:
        return True
    palabras_ok = ok.split()
    usuario_set = set(usuario.split())
    compartidas = usuario_set & set(palabras_ok)
    # Umbral dinámico: preguntas largas aceptan menos palabras exactas.
    minimo = min(3, len(palabras_ok)) if len(palabras_ok) <= 12 else 2
    return len(compartidas) >= minimo
