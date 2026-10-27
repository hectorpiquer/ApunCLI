"""Generación de temarios e índices de apuntes en Markdown."""

from typing import List, Optional

from . import db, formato
from .errores import ApuncliError

PLANTILLA = """\
# 📚 {titulo}

_Apuntes de {total} · {palabras} palabras · repasados {repasados}/{total}_

{indice_bloque}
## Apuntes

{apuntes_bloque}
"""


def generar_temario(conexion, asignatura: Optional[str] = None,
                    etiqueta: Optional[str] = None,
                    titulo: Optional[str] = None,
                    con_recursos: bool = True) -> str:
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    if not apuntes:
        raise ApuncliError("No hay apuntes para el temario (revisa el filtro).")

    datos = db.estadisticas(conexion)
    if titulo is None:
        filtro = asignatura or etiqueta
        titulo = f"Temario de {filtro}" if filtro else "Temario completo"

    indice_bloque = _indice_por_asignatura(apuntes)
    apuntes_bloque = "\n\n".join(
        _bloque_apunte(conexion, apunte, con_recursos) for apunte in apuntes
    )

    return PLANTILLA.format(
        titulo=titulo,
        total=len(apuntes),
        palabras=_palabras_de(apuntes),
        repasados=sum(1 for a in apuntes if a["veces_repasado"] > 0),
        indice_bloque=indice_bloque,
        apuntes_bloque=apuntes_bloque,
    )


def _palabras_de(apuntes) -> int:
    total = 0
    for apunte in apuntes:
        contenido = (apunte["contenido"] or "").strip()
        if contenido:
            total += len(contenido.split())
    return total


def _slug(texto: str) -> str:
    """Convierte un título en ancla Markdown (minúsculas, sin acentos ni espacios)."""
    import unicodedata

    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = "".join(c if c.isalnum() else "-" for c in texto)
    return "-" .join(part for part in texto.split("-") if part)


def _indice_por_asignatura(apuntes) -> str:
    lineas = ["## Índice", ""]
    por_asignatura: dict = {}
    for apunte in apuntes:
        clave = apunte["asignatura"] or "(sin asignatura)"
        por_asignatura.setdefault(clave, []).append(apunte)

    for asignatura, grupo in por_asignatura.items():
        lineas.append(f"**{asignatura}**")
        for apunte in grupo:
            ancla = _slug(f"apunte-{apunte['id']}-{apunte['titulo']}")
            lineas.append(f"- [{apunte['titulo']}](#{ancla})")
        lineas.append("")
    return "\n".join(lineas) + "\n"


def _bloque_apunte(conexion, apunte, con_recursos: bool) -> str:
    etiquetas = db.etiquetas_del_apunte(conexion, apunte["id"])
    ancla = _slug(f"apunte-{apunte['id']}-{apunte['titulo']}")
    bloque = formato.a_markdown(apunte, etiquetas)
    bloque = bloque.replace(f"# {apunte['titulo']}",
                            f'# <a id="{ancla}"></a>{apunte["titulo"]}', 1)

    if con_recursos:
        recursos = db.recursos_del_apunte(conexion, apunte["id"])
        if recursos:
            bloque += "\n**Recursos:**\n"
            for recurso in recursos:
                nombre = recurso["nombre"] or recurso["url"]
                bloque += f"- [{nombre}]({recurso['url']})\n"

    estado = "✅" if apunte["veces_repasado"] > 0 else "🔴"
    bloque += f"\n> {estado} {apunte['veces_repasado']} repasos · id {apunte['id']}"
    return bloque
