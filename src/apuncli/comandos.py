"""Implementación de los comandos de apuncli."""

import os
import re
import sqlite3
import sys
import tempfile
from typing import List, Optional

from . import db, formato, recursos as recursos_mod, temario, testmotor, ui
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
    _adjuntar_detectados(conexion, apunte_id, cuerpo)
    apunte = db.obtener_apunte(conexion, apunte_id)
    ui.titulo_de_seccion(f"✔ Apunte creado (id {apunte_id})")
    _imprimir_ficha(apunte, db.etiquetas_del_apunte(conexion, apunte_id))
    return apunte_id


def _adjuntar_detectados(conexion, apunte_id: int, cuerpo: str) -> None:
    """Guarda como recursos las URLs y ficheros que aparecen en el contenido."""
    existentes = {r["url"] for r in db.recursos_del_apunte(conexion, apunte_id)}
    for url, nombre in recursos_mod.detectar_en_texto(cuerpo):
        if url not in existentes:
            db.adjuntar_recurso(conexion, apunte_id, url, nombre)


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
    recursos = db.recursos_del_apunte(conexion, apunte_id)
    if recursos:
        print()
        print(ui.subrayado("  Recursos"))
        for recurso in recursos:
            tipo = recursos_mod.clasificar(recurso["url"])
            nombre = recurso["nombre"] or recurso["url"]
            print(f"    · {nombre}  ({tipo})")
        print(ui.tenue(f"    Abre uno con: apuncli recurso abrir {recursos[0]['id']}"))


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
    if nuevo_contenido is not None:
        _adjuntar_detectados(conexion, apunte_id, nuevo_contenido)
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
            archivo.write(formato.a_markdown(
                apunte, etiquetas, db.recursos_del_apunte(conexion, apunte_id)))
        print(ui.tenue(f"Abriendo '{apunte['titulo']}' en el editor…"))
        ui.abrir_en_editor(ruta)
        with open(ruta, encoding="utf-8") as archivo:
            titulo, contenido, asignatura, nuevas_etiquetas, nuevas_recursos = \
                formato.de_markdown(archivo.read())
        if not titulo:
            raise ApuncliError("El fichero ha perdido el título; cambios no guardados.")
        db.editar_apunte(conexion, apunte_id, titulo=titulo, contenido=contenido,
                        asignatura=asignatura, etiquetas=nuevas_etiquetas)
        _adjuntar_detectados(conexion, apunte_id, contenido)
        for nombre, url in nuevas_recursos:
            if url:
                db.adjuntar_recurso(conexion, apunte_id, url, nombre)
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
        sys.stdout.write(formato.a_markdown(
            apunte, db.etiquetas_del_apunte(conexion, apunte["id"]),
            db.recursos_del_apunte(conexion, apunte["id"])))
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
        formato.a_markdown(
            apunte, db.etiquetas_del_apunte(conexion, apunte["id"]),
            db.recursos_del_apunte(conexion, apunte["id"]))
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
        titulo, contenido, asignatura, etiquetas, recursos_md = formato.de_markdown(bloque)
        if not titulo:
            continue
        apunte_id = db.crear_apunte(conexion, titulo, contenido, asignatura, etiquetas)
        _adjuntar_detectados(conexion, apunte_id, contenido)
        existentes = {r["url"] for r in db.recursos_del_apunte(conexion, apunte_id)}
        for nombre, url in recursos_md:
            if url and url not in existentes:
                db.adjuntar_recurso(conexion, apunte_id, url, nombre)
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
# Recursos (enlaces y ficheros adjuntos)
# ---------------------------------------------------------------------------

def cmd_recurso(conexion, accion: str, apunte_id: Optional[int],
                recurso_id: Optional[int], url: Optional[str],
                nombre: str) -> None:
    if accion == "anadir":
        if apunte_id is None or not url:
            raise ApuncliError("Uso: apuncli recurso anadir <apunte> <url-o-fichero> [--nombre 'X']")
        _apunte_obligatorio(conexion, apunte_id)
        ruta = os.path.abspath(os.path.expanduser(url)) if not recursos_mod.es_url(url) else url
        id_recurso = db.adjuntar_recurso(conexion, apunte_id, ruta,
                                         nombre or recursos_mod.nombre_para(url))
        print(f"✔ Recurso añadido (id {id_recurso}) al apunte {apunte_id}.")
    elif accion == "abrir":
        recurso = _recurso_obligatorio(conexion, recurso_id)
        try:
            recursos_mod.abrir_recurso(recurso["url"])
        except FileNotFoundError as error:
            raise ApuncliError(str(error))
        print(f"✔ Abierto: {recurso['nombre'] or recurso['url']}")
    elif accion == "borrar":
        _recurso_obligatorio(conexion, recurso_id)
        db.borrar_recurso(conexion, recurso_id)
        print(f"✔ Recurso {recurso_id} borrado.")


def _recurso_obligatorio(conexion, recurso_id: Optional[int]):
    if recurso_id is None:
        raise ApuncliError("Falta el id del recurso "
                           "(los ids salen con 'apuncli recurso listar <apunte>')")
    recurso = db.recurso(conexion, recurso_id)
    if recurso is None:
        raise ApuncliError(f"No existe el recurso {recurso_id}.")
    return recurso


def cmd_recurso_listar(conexion, apunte_id: int) -> None:
    _apunte_obligatorio(conexion, apunte_id)
    recursos = db.recursos_del_apunte(conexion, apunte_id)
    ui.titulo_de_seccion(f"Recursos del apunte {apunte_id} ({len(recursos)})")
    if not recursos:
        print(ui.tenue("(ninguno). Añade uno: apuncli recurso anadir {} https://ejemplo.com".format(apunte_id)))
        return
    for recurso in recursos:
        tipo = recursos_mod.clasificar(recurso["url"])
        print(f"  {recurso['id']:>3}  {recurso['nombre'] or '-':<28} {recurso['url']}  ({tipo})")


# ---------------------------------------------------------------------------
# Temario
# ---------------------------------------------------------------------------

def cmd_temario(conexion, asignatura: Optional[str], etiqueta: Optional[str],
                titulo: Optional[str]) -> None:
    texto = temario.generar_temario(conexion, asignatura=asignatura,
                                    etiqueta=etiqueta, titulo=titulo)
    sys.stdout.write(texto)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def cmd_test(conexion, asignatura: Optional[str], etiqueta: Optional[str],
             numero: int, automaticas: bool) -> None:
    preguntas = testmotor.preparar_preguntas(conexion, asignatura=asignatura,
                                             etiqueta=etiqueta, numero=numero,
                                             solo_automaticas=automaticas)
    print(ui.destacado(f"Test con {len(preguntas)} pregunta(s). "
                       "Responde con tus palabras (Enter vacío para saltar, 'q' para salir)."))
    correctas = 0
    respondidas = 0
    falladas = []
    for i, pregunta in enumerate(preguntas, 1):
        print()
        print(ui.subrayado(f"─ Pregunta {i}/{len(preguntas)} · de '{pregunta['apunte']}' ─"))
        print(ui.destacado(pregunta["pregunta"]))
        if pregunta.get("opciones"):
            letras = "abcd"
            for letra, opcion in zip(letras, pregunta["opciones"]):
                print(f"   {letra}) {opcion}")
            print(ui.tenue("   (responde con la letra, o escribe tu respuesta)"))
        try:
            respuesta = input(ui.tenue("Tu respuesta: "))
        except EOFError:
            break
        if respuesta.strip().lower() in ("q", "salir"):
            break
        respondidas += 1
        acertada = _corregir_pregunta(respuesta, pregunta)
        if acertada:
            correctas += 1
            print(ui.destacado("✔ ¡Correcto!"))
        else:
            falladas.append(pregunta)
            print(ui.tenue(f"✘ Respuesta esperada: {pregunta['respuesta']}"))
        db.marcar_repasado(conexion, pregunta["apunte_id"])

    print()
    if respondidas:
        nota = round(10 * correctas / respondidas, 1)
        ui.titulo_de_seccion(f"Resultado: {correctas}/{respondidas} · nota {nota}/10")
        if falladas:
            ui.tenue(f"Has fallado {len(falladas)}: repasálias con 'apuncli repasar'.")
    else:
        print("Test sin respuestas. ¡Otra vez otro día!")


def _corregir_pregunta(respuesta: str, pregunta: dict) -> bool:
    respuesta = respuesta.strip()
    opciones = pregunta.get("opciones") or []
    if opciones and re.fullmatch(r"[a-dA-D]", respuesta):
        eleccion = opciones["abcd".index(respuesta.lower())]
        return testmotor.es_correcta(eleccion, pregunta["respuesta"]) or \
            eleccion in pregunta["respuesta"]
    return testmotor.es_correcta(respuesta, pregunta["respuesta"])


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


def cmd_hoy(conexion) -> None:
    """Plan rápido de qué estudiar hoy."""
    apuntes = db.listar_apuntes(conexion)
    ui.titulo_de_seccion("📅 Tu plan de hoy")
    if not apuntes:
        print("  No tienes apuntes todavía. Empieza con: apuncli crear 'Tema 1'")
        return

    sin_repasar = [a for a in apuntes if a["veces_repasado"] == 0]
    recientes = sorted(apuntes, key=lambda a: a["modificado"], reverse=True)[:3]
    con_recuerdos = [a for a in apuntes
                     if testmotor.preguntas_manuales(a["contenido"])]

    print()
    if sin_repasar:
        nombres = ", ".join(f"[{a['id']}] {a['titulo']}" for a in sin_repasar[:5])
        print(f"  🔴 Todavía no repasados ({len(sin_repasar)}): {nombres}")
    else:
        print("  ✅ Lo tienes todo repasado al menos una vez. ¡Bien!")

    if con_recuerdos:
        print(f"  📝 Con preguntas para test: {len(con_recuerdos)} apuntes. "
              "Prueba: apuncli test")

    if recientes:
        print("  🆕 Recientes/actualizados:")
        for apunte in recientes:
            print(f"     [{apunte['id']}] {apunte['titulo']} "
                  f"({apunte['asignatura'] or '—'}) · modificado {apunte['modificado']}")

    print()
    print("  Sugerencia: " + ("apuncli repasar -n 5" if sin_repasar else "apuncli test"))


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
