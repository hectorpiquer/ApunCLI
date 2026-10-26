"""Implementación de los comandos de apuncli."""

import os
import sqlite3
import sys
import tempfile
from typing import List, Optional

from . import db, formato, ui
from .errores import ApuncliError


# ---------------------------------------------------------------------------
# Crear
# ---------------------------------------------------------------------------

def cmd_crear(conexion, titulo: str, contenido: Optional[str], asignatura: str,
              etiquetas: List[str], desde_editor: bool, stdin: bool) -> int:
    if not titulo.strip():
        raise ApuncliError("El título no puede estar vacío.")

    if desde_editor:
        cuerpo = _editar_contenido_temporal(titulo, "")
    elif stdin:
        cuerpo = sys.stdin.read().strip()
    elif contenido is not None:
        cuerpo = contenido
    elif sys.stdin.isatty():
        cuerpo = ui.leer_multilinea()
    else:
        raise ApuncliError(
            "Falta el contenido: usa -c 'texto', --editor o redirige la entrada con --stdin: "
            "echo 'apunte' | apuncli crear 'Título' --stdin"
        )

    apunte_id = db.crear_apunte(conexion, titulo.strip(), cuerpo, asignatura.strip(), etiquetas)
    apunte = db.obtener_apunte(conexion, apunte_id)
    ui.titulo_de_seccion(f"✔ Apunte creado (id {apunte_id})")
    _imprimir_ficha(apunte, db.etiquetas_del_apunte(conexion, apunte_id))
    return apunte_id


# ---------------------------------------------------------------------------
# Listar
# ---------------------------------------------------------------------------

def cmd_listar(conexion, asignatura: Optional[str], etiqueta: Optional[str]) -> None:
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    filtros = []
    if asignatura:
        filtros.append(f"asignatura={asignatura}")
    if etiqueta:
        filtros.append(f"etiqueta={etiqueta}")
    sufijo = f" ({', '.join(filtros)})" if filtros else ""
    ui.titulo_de_seccion(f"Apuntes{sufijo} ({len(apuntes)})")
    if not apuntes:
        print("No hay apuntes que coincidan. Crea uno con: apuncli crear 'Título'")
        return
    print(f"{'ID':>4}  {'ASIGNATURA':<18} {'TÍTULO':<38} ETIQUETAS")
    for apunte in apuntes:
        etis = db.etiquetas_del_apunte(conexion, apunte["id"])
        print(
            f"{apunte['id']:>4}  "
            f"{(apunte['asignatura'] or '-')[:17]:<18} "
            f"{apunte['titulo'][:37]:<38} "
            f"{' '.join(f'[{e}]' for e in etis)}"
        )


# ---------------------------------------------------------------------------
# Ver
# ---------------------------------------------------------------------------

def cmd_ver(conexion, apunte_id: int) -> None:
    apunte = _apunte_obligatorio(conexion, apunte_id)
    _imprimir_ficha(apunte, db.etiquetas_del_apunte(conexion, apunte_id), contenido=True)


def _imprimir_ficha(apunte, etiquetas: List[str], contenido: bool = False) -> None:
    print(ui.destacado(f"[{apunte['id']}] {apunte['titulo']}"))
    print(ui.tenue(f"  Asignatura: {apunte['asignatura'] or '-'}  ·  "
                   f"Creado: {apunte['creado']}  ·  Modificado: {apunte['modificado']}  ·  "
                   f"Repasado: {apunte['veces_repasado']} veces"))
    if etiquetas:
        print(ui.tenue("  Etiquetas:  " + " ".join(f"[{e}]" for e in etiquetas)))
    if contenido:
        texto = (apunte["contenido"] or "").strip()
        print()
        print(texto if texto else ui.tenue("(el apunte está vacío)"))


# ---------------------------------------------------------------------------
# Buscar
# ---------------------------------------------------------------------------

def cmd_buscar(conexion, consulta: str) -> None:
    apuntes = db.buscar_apuntes(conexion, consulta)
    ui.titulo_de_seccion(f"Resultados para '{consulta}' ({len(apuntes)})")
    if not apuntes:
        print("Nada encontrado. Prueba con otras palabras.")
        return
    for apunte in apuntes:
        extracto = " ".join((apunte["contenido"] or "").split())[:80]
        print(f"[{apunte['id']}] {apunte['titulo']}")
        extra = f" ({extracto}…)" if extracto else ""
        print(ui.tenue(f"    {apunte['asignatura'] or '-'}{extra}"))


# ---------------------------------------------------------------------------
# Editar
# ---------------------------------------------------------------------------

def cmd_editar(conexion, apunte_id: int, titulo: Optional[str], contenido: Optional[str],
               asignatura: Optional[str], etiquetas: Optional[List[str]],
               en_editor: bool, agregar: bool, stdin: bool) -> None:
    apunte = _apunte_obligatorio(conexion, apunte_id)

    nuevo_contenido = contenido
    if stdin:
        texto_stdin = sys.stdin.read().strip()
        nuevo_contenido = (apunte["contenido"] + "\n\n" + texto_stdin).strip() if agregar else texto_stdin
    elif en_editor:
        actual = apunte["contenido"] if agregar else (contenido or "")
        nuevo_contenido = _editar_contenido_temporal(
            titulo or apunte["titulo"], actual
        )
    elif agregar and contenido is not None:
        nuevo_contenido = (apunte["contenido"] + "\n\n" + contenido).strip()

    db.editar_apunte(conexion, apunte_id, titulo=titulo, contenido=nuevo_contenido,
                     asignatura=asignatura, etiquetas=etiquetas)
    apunte = db.obtener_apunte(conexion, apunte_id)
    ui.titulo_de_seccion(f"✔ Apunte actualizado (id {apunte_id})")
    _imprimir_ficha(apunte, db.etiquetas_del_apunte(conexion, apunte_id))


def _editar_contenido_temporal(titulo: str, contenido: str) -> str:
    """Abre un fichero temporal con el contenido y devuelve lo editado."""
    ruta = None
    try:
        descriptor, ruta = tempfile.mkstemp(prefix="apuncli-", suffix=".md")
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            archivo.write(contenido)
        codigo = ui.abrir_en_editor(ruta)
        if codigo != 0:
            raise ApuncliError(f"El editor terminó con código {codigo}; cambios descartados.")
        with open(ruta, encoding="utf-8") as archivo:
            return archivo.read().strip()
    finally:
        if ruta and os.path.exists(ruta):
            os.remove(ruta)


# ---------------------------------------------------------------------------
# Borrar
# ---------------------------------------------------------------------------

def cmd_borrar(conexion, apunte_id: int, si: bool) -> None:
    apunte = _apunte_obligatorio(conexion, apunte_id)
    if not si:
        if not ui.confirmar(f"¿Borrar el apunte [{apunte_id}] '{apunte['titulo']}'?"):
            print("Cancelado.")
            return
    db.borrar_apunte(conexion, apunte_id)
    print(f"✔ Apunte [{apunte_id}] borrado.")


# ---------------------------------------------------------------------------
# Abrir en editor
# ---------------------------------------------------------------------------

def cmd_abrir(conexion, apunte_id: int) -> None:
    apunte = _apunte_obligatorio(conexion, apunte_id)
    etiquetas = db.etiquetas_del_apunte(conexion, apunte_id)
    ruta = None
    try:
        descriptor, ruta = tempfile.mkstemp(prefix=f"apuncli-{apunte_id}-", suffix=".md")
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            archivo.write(formato.a_markdown(apunte, etiquetas))
        print(ui.tenue(f"Abriendo '{apunte['titulo']}' en el editor…"))
        ui.abrir_en_editor(ruta)
        with open(ruta, encoding="utf-8") as archivo:
            titulo, contenido, asignatura, nuevas_etiquetas = formato.de_markdown(archivo.read())
        if not titulo:
            raise ApuncliError("El fichero ha perdido el título; cambios no guardados.")
        db.editar_apunte(conexion, apunte_id, titulo=titulo, contenido=contenido,
                        asignatura=asignatura, etiquetas=nuevas_etiquetas)
        print(f"✔ Cambios guardados en el apunte [{apunte_id}].")
    finally:
        if ruta and os.path.exists(ruta):
            os.remove(ruta)


# ---------------------------------------------------------------------------
# Exportar / importar
# ---------------------------------------------------------------------------

def cmd_exportar(conexion, destino: Optional[str], asignatura: Optional[str],
                 etiqueta: Optional[str], todos: bool) -> None:
    if destino:
        apunte = _apunte_obligatorio(conexion, _parsear_id(destino))
        sys.stdout.write(
            formato.a_markdown(apunte, db.etiquetas_del_apunte(conexion, apunte["id"]))
        )
        return
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    if not apuntes and not (todos or asignatura or etiqueta):
        raise ApuncliError(
            "Indica qué exportar: un id, --todos, -a ASIGNATURA o -t ETIQUETA. "
            "Ejemplo: apuncli exportar --todos > apuntes.md"
        )
    if not apuntes:
        print("No hay apuntes que exportar.")
        return
    bloques = [
        formato.a_markdown(apunte, db.etiquetas_del_apunte(conexion, apunte["id"]))
        for apunte in apuntes
    ]
    sys.stdout.write("\n".join(bloques) + "\n")


def cmd_importar(conexion, ruta_fichero: str) -> None:
    try:
        with open(os.path.expanduser(ruta_fichero), encoding="utf-8") as archivo:
            texto = archivo.read()
    except OSError as error:
        raise ApuncliError(f"No se pudo leer el fichero: {error}")

    partes = _dividir_bloques_markdown(texto)
    creados = 0
    for bloque in partes:
        titulo, contenido, asignatura, etiquetas = formato.de_markdown(bloque)
        if not titulo:
            continue
        db.crear_apunte(conexion, titulo, contenido, asignatura, etiquetas)
        creados += 1
    if creados == 0:
        raise ApuncliError("No se encontró ningún apunte con título '# Título' en el fichero.")
    print(f"✔ Importados {creados} apuntes desde {ruta_fichero}.")


def _dividir_bloques_markdown(texto: str) -> List[str]:
    """Divide un Markdown en bloques, uno por cada línea de título '# ...'."""
    partes: List[str] = []
    actual: List[str] = []
    for linea in texto.split("\n"):
        if linea.startswith("# "):
            if any(l.strip() for l in actual):
                partes.append("\n".join(actual))
            actual = [linea]
        else:
            actual.append(linea)
    if any(l.strip() for l in actual):
        partes.append("\n".join(actual))
    return partes


# ---------------------------------------------------------------------------
# Repasar
# ---------------------------------------------------------------------------

def cmd_repasar(conexion, asignatura: Optional[str], etiqueta: Optional[str],
                numero: int) -> None:
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    if not apuntes:
        raise ApuncliError("No hay apuntes para repasar.")
    por_repasar = [a for a in apuntes if a["veces_repasado"] == 0]
    cola = por_repasar if len(por_repasar) >= numero else apuntes
    seleccion = cola[:numero]

    print(ui.destacado(f"Modo repaso: {len(seleccion)} apunte(s). "
                       "Lee el título, recuerda el contenido y pulsa Enter."))
    for i, apunte in enumerate(seleccion, 1):
        print()
        print(ui.subrayado(f"─ Apunte {i}/{len(seleccion)} · [{apunte['id']}] {apunte['titulo']} "
                           f"({apunte['asignatura'] or '-'}) ─"))
        try:
            input(ui.tenue("Pulsa Enter para ver el contenido… "))
        except EOFError:
            break
        print((apunte["contenido"] or "(vacío)").strip())
        db.marcar_repasado(conexion, apunte["id"])
    print()
    print(ui.destacado("✔ Repaso terminado. ¡Bien hecho!"))


# ---------------------------------------------------------------------------
# Etiquetas, asignaturas y estadísticas
# ---------------------------------------------------------------------------

def cmd_etiquetas(conexion) -> None:
    etiquetas = db.todas_las_etiquetas(conexion)
    ui.titulo_de_seccion(f"Etiquetas ({len(etiquetas)})")
    print(" ".join(f"[{e}]" for e in etiquetas) if etiquetas else ui.tenue("(sin etiquetas)"))


def cmd_asignaturas(conexion) -> None:
    asignaturas = db.todas_las_asignaturas(conexion)
    ui.titulo_de_seccion(f"Asignaturas ({len(asignaturas)})")
    for asignatura in asignaturas:
        print(f"  · {asignatura}")
    if not asignaturas:
        print(ui.tenue("(sin asignaturas)"))


def cmd_stats(conexion) -> None:
    datos = db.estadisticas(conexion)
    ui.titulo_de_seccion("Estadísticas de estudio")
    print(f"  Apuntes totales:        {datos['total']}")
    print(f"  Palabras escritas:      {datos['palabras']}")
    print(f"  Sin repasar:            {datos['sin_repasar']}")
    print(f"  Repasados al menos 1x:  {datos['repasados']}")
    print()
    print("  Por asignatura:")
    for asignatura, cantidad in datos["por_asignatura"]:
        print(f"    {asignatura:<20} {cantidad}")
    if not datos["por_asignatura"]:
        print(ui.tenue("    (aún no hay apuntes)"))


# ---------------------------------------------------------------------------

def _parsear_id(valor: str) -> int:
    try:
        return int(valor)
    except ValueError:
        raise ApuncliError(f"'{valor}' no es un id válido. Usa un número, "
                           "ejemplo: apuncli ver 1 (mira los ids con 'apuncli listar')")


def _apunte_obligatorio(conexion, apunte_id: int):
    if apunte_id <= 0:
        raise ApuncliError(f"El id debe ser un número positivo, no {apunte_id}.")
    apunte = db.obtener_apunte(conexion, apunte_id)
    if apunte is None:
        raise ApuncliError(f"No existe ningún apunte con id {apunte_id}. "
                           "Lista los apuntes con: apuncli listar")
    return apunte
