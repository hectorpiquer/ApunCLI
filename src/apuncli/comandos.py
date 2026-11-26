"""Implementación de los comandos de apuncli."""

import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from . import ai, config as config_mod, db, formato, motor as motor_mod
from . import recursos as recursos_mod, temario, testmotor, ui
from . import organizador as organizador_mod
from .errores import AccionNoValida, ApuncliError, ConfigError, FalloEjecucion, SinRedError


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

def cmd_listar(conexion, asignatura: Optional[str], etiqueta: Optional[str],
               como_json: bool = False) -> None:
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    if como_json:
        datos = []
        for apunte in apuntes:
            fila = dict(apunte)
            fila["etiquetas"] = db.etiquetas_del_apunte(conexion, apunte["id"])
            datos.append(fila)
        print(json.dumps(datos, ensure_ascii=False, indent=2))
        return
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

def cmd_ver(conexion, apunte_id: int, como_json: bool = False) -> None:
    apunte = _apunte_obligatorio(conexion, apunte_id)
    etiquetas = db.etiquetas_del_apunte(conexion, apunte_id)
    if como_json:
        datos = dict(apunte)
        datos["etiquetas"] = etiquetas
        datos["recursos"] = [dict(r) for r in db.recursos_del_apunte(conexion, apunte_id)]
        print(json.dumps(datos, ensure_ascii=False, indent=2))
        return
    _imprimir_ficha(apunte, etiquetas, contenido=True)
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
    try:
        intervalo = apunte["intervalo"]
    except (IndexError, KeyError):
        intervalo = 0
    if intervalo:
        print(ui.tenue(f"  Repaso espaciado: intervalo {intervalo} días"))
    if etiquetas:
        print(ui.tenue("  Etiquetas:  " + " ".join(f"[{e}]" for e in etiquetas)))
    if contenido:
        texto = (apunte["contenido"] or "").strip()
        print()
        print(texto if texto else ui.tenue("(el apunte está vacío)"))


# ---------------------------------------------------------------------------
# Buscar
# ---------------------------------------------------------------------------

def cmd_buscar(conexion, consulta: str, como_json: bool = False) -> None:
    apuntes = db.buscar_apuntes(conexion, consulta)
    if como_json:
        print(json.dumps([dict(a) for a in apuntes], ensure_ascii=False, indent=2))
        return
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


def cmd_limpiar(conexion, asignatura: Optional[str],
                etiqueta: Optional[str], si: bool) -> None:
    """Borra en bloque los apuntes que coincidan con los filtros."""
    if not asignatura and not etiqueta:
        raise ApuncliError("Indica un filtro: -a ASIGNATURA o -t ETIQUETA. "
                           "Ejemplo: apuncli limpiar -t sin-usar")
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    if not apuntes:
        print("No hay apuntes que coincidan con el filtro.")
        return
    nombres = ", ".join(f"[{a['id']}] {a['titulo']}" for a in apuntes[:8])
    sufijo = "…" if len(apuntes) > 8 else ""
    if not si:
        print(f"Vas a borrar {len(apuntes)} apuntes: {nombres}{sufijo}")
        if not ui.confirmar("¿Borrarlos todos?"):
            print("Cancelado.")
            return
    for apunte in apuntes:
        db.borrar_apunte(conexion, apunte["id"])
    print(f"✔ {len(apuntes)} apuntes borrados.")


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

def _dia_de_hoy() -> int:
    from datetime import date
    return date.today().toordinal()


def cmd_repasar(conexion, asignatura: Optional[str], etiqueta: Optional[str],
                numero: int, solo_cola: bool = False) -> None:
    apuntes = db.listar_apuntes(conexion, asignatura=asignatura, etiqueta=etiqueta)
    if not apuntes:
        raise ApuncliError("No hay apuntes para repasar.")
    if solo_cola:
        cola = [a for a in db.cola_de_repaso(conexion, _dia_de_hoy())
                if not asignatura or a["asignatura"] == asignatura]
        if not cola:
            print(ui.destacado("Nada que repasar hoy. ¡El siguiente toca pronto!"))
            return
    else:
        por_repasar = [a for a in apuntes if a["veces_repasado"] == 0]
        cola = por_repasar if len(por_repasar) >= numero else apuntes
    seleccion = cola[:numero]

    print(ui.destacado(f"Modo repaso: {len(seleccion)} apunte(s). "
                       "Lee el título, recuerda el contenido y pulsa Enter."))
    hoy = _dia_de_hoy()
    for i, apunte in enumerate(seleccion, 1):
        print()
        print(ui.subrayado(f"─ Apunte {i}/{len(seleccion)} · [{apunte['id']}] {apunte['titulo']} "
                           f"({apunte['asignatura'] or '-'}) ─"))
        try:
            input(ui.tenue("Pulsa Enter para ver el contenido… "))
        except EOFError:
            break
        print((apunte["contenido"] or "(vacío)").strip())
        db.marcar_repasado(conexion, apunte["id"], hoy=hoy)
        actualizado = db.obtener_apunte(conexion, apunte["id"])
        print(ui.tenue(f"   → siguiente repaso en {actualizado['intervalo']} días"))
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
        if not recursos_mod.es_url(url) and not os.path.exists(ruta):
            raise ApuncliError(f"El fichero no existe: {ruta}. "
                               "Un recurso debe existir cuando se añade (o usa una URL).")
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
            ui.tenue(f"Has fallado {len(falladas)}: repásalas con 'apuncli repasar'.")
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

def cmd_etiquetas(conexion, anadir: Optional[int] = None, quitar: Optional[int] = None,
                  nombres: Optional[List[str]] = None) -> None:
    if anadir is not None or quitar is not None:
        _retoque_etiquetas(conexion, anadir, quitar, nombres or [])
        return
    etiquetas = db.todas_las_etiquetas(conexion)
    ui.titulo_de_seccion(f"Etiquetas ({len(etiquetas)})")
    print(" ".join(f"[{e}]" for e in etiquetas) if etiquetas else ui.tenue("(sin etiquetas)"))


def _retoque_etiquetas(conexion, anadir: Optional[int], quitar: Optional[int],
                       nombres: List[str]) -> None:
    if not nombres:
        raise ApuncliError("Indica las etiquetas. Ejemplo: apuncli etiquetas --anadir 3 examen repaso")
    apunte_id = anadir if anadir is not None else quitar
    _apunte_obligatorio(conexion, apunte_id)
    actuales = db.etiquetas_del_apunte(conexion, apunte_id)
    nuevas = [n.strip().lower() for n in nombres if n.strip()]
    if anadir is not None:
        result = sorted(set(actuales) | set(nuevas))
    else:
        result = sorted(set(actuales) - set(nuevas))
    db.editar_apunte(conexion, apunte_id, etiquetas=result)
    accion = "añadidas" if anadir is not None else "quitadas"
    print(f"✔ Etiquetas {accion} en el apunte {apunte_id}: " +
          (" ".join(f"[{e}]" for e in result) if result else ui.tenue("(ninguna)")))


def cmd_asignaturas(conexion) -> None:
    asignaturas = db.todas_las_asignaturas(conexion)
    ui.titulo_de_seccion(f"Asignaturas ({len(asignaturas)})")
    for asignatura in asignaturas:
        print(f"  · {asignatura}")
    if not asignaturas:
        print(ui.tenue("(sin asignaturas)"))


def cmd_stats(conexion, como_json: bool = False) -> None:
    datos = db.estadisticas(conexion)
    if como_json:
        print(json.dumps(datos, ensure_ascii=False, indent=2))
        return
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
    pendientes_hoy = db.cola_de_repaso(conexion, _dia_de_hoy())
    recientes = sorted(apuntes, key=lambda a: a["modificado"], reverse=True)[:3]
    con_recuerdos = [a for a in apuntes
                     if testmotor.preguntas_manuales(a["contenido"])]

    print()
    nombres = ", ".join(f"[{a['id']}] {a['titulo']}" for a in pendientes_hoy[:5])
    sufijo = "…" if len(pendientes_hoy) > 5 else ""
    print(f"  🧠 Te tocan hoy ({len(pendientes_hoy)}): {nombres or 'ninguno. ¡Repasado!'}{sufijo}")
    if sin_repasar:
        print(f"  🔴 Nunca repasados ({len(sin_repasar)}) — entran primero en la cola")

    if con_recuerdos:
        print(f"  📝 Con preguntas para test: {len(con_recuerdos)} apuntes. "
              "Prueba: apuncli test")

    if recientes:
        print("  🆕 Recientes/actualizados:")
        for apunte in recientes:
            print(f"     [{apunte['id']}] {apunte['titulo']} "
                  f"({apunte['asignatura'] or '—'}) · modificado {apunte['modificado']}")

    print()
    sugerencia = "apuncli repasar --cola" if pendientes_hoy else "apuncli test"
    print("  Sugerencia: " + sugerencia)


# ---------------------------------------------------------------------------
# Respaldo
# ---------------------------------------------------------------------------

def cmd_respaldo(conexion, sub: str, ruta_fichero: Optional[str]) -> None:
    if sub == "hacer":
        ruta = db.respaldo()
        print(f"✔ Copia de seguridad hecha: {ruta}")
    elif sub == "listar":
        respaldos = db.lista_de_respaldos()
        ui.titulo_de_seccion(f"Copias de seguridad ({len(respaldos)})")
        if not respaldos:
            print(ui.tenue("(ninguna). Haz una con: apuncli respaldo hacer"))
            return
        for ruta in respaldos:
            print(f"  · {ruta}")
    elif sub == "restaurar":
        if not ruta_fichero:
            respaldos = db.lista_de_respaldos()
            if not respaldos:
                raise ApuncliError("No hay copias de seguridad. Usa 'apuncli respaldo hacer'.")
            ruta_fichero = respaldos[0]
            print(ui.tenue(f"Usando la copia más reciente: {ruta_fichero}"))
        if not ui.confirmar(f"¿Restaurar tus apuntes desde {ruta_fichero}? "
                            "Se perderán los cambios posteriores a esa copia."):
            print("Cancelado.")
            return
        db.restaurar(conexion, ruta_fichero)
        print("✔ Apuntes restaurados. Vuelve a listar (la sesión actual usa la copia vieja).")


# ---------------------------------------------------------------------------
# Autocompletado de la terminal
# ---------------------------------------------------------------------------

COMPLETADOR_BASH = """\
# Autocompletado de apuncli (solo bash; zsh/PowerShell: sin guion, a tu ritmo).
# Añade esta línea a ~/.bashrc:
#   eval "$(apuncli completar)"
_apuncli_completar() {
    local opcion="${COMP_WORDS[1]}"
    local         lista_comandos="crear listar ls ver buscar search editar edit borrar rm limpiar abrir open exportar \
importar repasar review test recurso rec temario hoy stats etiquetas tags asignaturas materias completar \
respaldo demo version"
    local lista_asignaturas=""
    local lista_etiquetas=""
    if command -v apuncli >/dev/null 2>&1; then
        lista_asignaturas="$(apuncli asignaturas 2>/dev/null | sed 's/^ *· //')"
        lista_etiquetas="$(apuncli etiquetas 2>/dev/null | tr -d '[]')"
    fi
    case "$opcion" in
        ver|abrir|open|borrar|rm|editar|edit|exportar)
            COMPREPLY=( $(compgen -W "$(apuncli listar 2>/dev/null | awk 'NR>2 {print $1}')" -- "${COMP_WORDS[COMP_CWORD]}") ) ;;
        -a|--asignatura)
            COMPREPLY=( $(compgen -W "$lista_asignaturas" -- "${COMP_WORDS[COMP_CWORD]}") ) ;;
        -t|--etiqueta)
            COMPREPLY=( $(compgen -W "$lista_etiquetas" -- "${COMP_WORDS[COMP_CWORD]}") ) ;;
        *)
            if [ "$COMP_CWORD" -eq 1 ]; then
                COMPREPLY=( $(compgen -W "$lista_comandos" -- "${COMP_WORDS[COMP_CWORD]}") )
            else
                COMPREPLY=( $(compgen -W "$lista_comandos $lista_asignaturas $lista_etiquetas" \
                              -- "${COMP_WORDS[COMP_CWORD]}") )
            fi ;;
    esac
}
complete -F _apuncli_completar apuncli
"""


def cmd_completar() -> None:
    sys.stdout.write(COMPLETADOR_BASH)


# ---------------------------------------------------------------------------
# Acciones externas (acciones.json) · acciones / validar / ejecutar
# ---------------------------------------------------------------------------

def _cargar_config(ruta: Optional[str]) -> config_mod.Configuracion:
    donde = Path(ruta).expanduser() if ruta else Path("acciones.json")
    return config_mod.Configuracion.cargar(donde)


def cmd_acciones(config: config_mod.Configuracion, como_json: bool = False) -> None:
    if como_json:
        datos = [{"nombre": a.nombre, "tipo": a.tipo, "descripcion": a.descripcion,
                  "ia": a.con_ia, "confirmar": a.confirmar} for a in config.acciones]
        print(json.dumps({"config": str(config.ruta), "acciones": datos},
                         ensure_ascii=False, indent=2))
        return
    ui.titulo_de_seccion(f"Acciones en {config.ruta} ({len(config.acciones)})")
    for accion in config.acciones:
        marca = " 🤖" if accion.con_ia else ""
        print(f"  {accion.nombre:<24} {accion.descripcion}{marca}")
    print(ui.tenue("\nEjecuta una: apuncli ejecutar <nombre> [carpeta|apunte] --simular"))


def cmd_validar(ruta: Optional[str], como_json: bool = False) -> int:
    """Devuelve 0 si todo vale; lanza ConfigError con TODOS los fallos."""
    config = _cargar_config(ruta)
    if como_json:
        print(json.dumps({"valido": True, "config": str(config.ruta),
                          "version": config.version,
                          "acciones": [{"nombre": a.nombre, "tipo": a.tipo}
                                       for a in config.acciones]},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"✔ {config.ruta} es válido: {len(config.acciones)} acción(es), "
          f"esquema versión {config.version}.")
    for accion in config.acciones:
        print(f"  ✓ {accion.nombre} ({accion.tipo})")
    return 0


def cmd_ejecutar(conexion, config: config_mod.Configuracion, nombre: str,
                 carpeta: Optional[str], simular: bool, si: bool,
                 como_json: bool = False) -> None:
    try:
        accion = config.buscar(nombre)
    except ConfigError as error:
        raise AccionNoValida(str(error))

    if accion.con_ia:
        _ejecutar_accion_ia(conexion, accion, carpeta, simular, si)
        return
    if accion.tipo == "generar-temario":
        texto = temario.generar_temario(conexion, asignatura=carpeta or None)
        print(texto)
        return
    if accion.tipo in ("renombrar-ia", "clasificar-ia"):
        from . import organizador_menu
        if accion.tipo == "renombrar-ia":
            if not carpeta:
                raise ApuncliError("renombrar-ia necesita el fichero: "
                                   "apuncli ejecutar renombrar-ia <fichero>")
            organizador_menu.renombrar_ia(Path(carpeta).expanduser())
        else:
            organizador_menu.clasificar_ia(
                Path(carpeta).expanduser() if carpeta else None)
        return
    if accion.tipo in ("temporales", "ordenar-descargas", "espacio"):
        cmd_organizar(accion.tipo, Path(carpeta).expanduser() if carpeta
                      else Path.cwd(), borrar=simular is False and si,
                      dias=30, simular=simular, categorias=None)
        return

    ruta = Path(carpeta).expanduser() if carpeta else (accion.origen or Path.cwd())
    motor = motor_mod.Motor()
    if accion.confirmar and not simular and not si:
        if not ui.confirmar(f"La acción '{accion.nombre}' puede modificar o borrar "
                            f"ficheros en {ruta}. ¿Continuar?"):
            print("Cancelado.")
            return
    resultado = motor.ejecutar(accion, ruta, simular=simular)
    if como_json:
        print(json.dumps({"accion": nombre, "simulada": simular,
                          "hechos": resultado.hechos, "avisos": resultado.avisos,
                          "omitidos": resultado.omitidos}, ensure_ascii=False, indent=2))
        return
    ui.titulo_de_seccion(("SIMULACIÓN · " if simular else "") + resultado.resumen())
    for aviso in resultado.avisos:
        print(f"  · {aviso}")
    for hecho in resultado.hechos:
        print(f"  ✔ {hecho}" if not simular else f"  → {hecho}")
    if not resultado.hechos:
        print(ui.tenue("  Nada que hacer: ningún fichero cumple el filtro."))


def _ejecutar_accion_ia(conexion, accion, carpeta: Optional[str],
                        simular: bool, si: bool) -> None:
    proveedor = ai.ProveedorIA()
    if simular:
        print(f"[SIMULACIÓN] '{accion.nombre}' enviaría el apunte elegido al modelo "
              f"'{proveedor.modelo}' de {proveedor.url} y escribiría el resultado. "
              "Sin IA disponible, avisa y no rompe nada.")
        return
    try:
        _apunte_obligatorio(conexion, _parsear_id(carpeta or ""))
    except ApuncliError:
        raise ApuncliError(f"Las acciones con IA necesitan el id del apunte: "
                           f"apuncli ejecutar {accion.nombre} <id-de-apunte> "
                           "(mira los ids con 'apuncli listar')")
    apunte = db.obtener_apunte(conexion, int(carpeta))
    texto = f"{apunte['titulo']}\n\n{apunte['contenido'] or ''}"
    if accion.tipo == "resumir-ia":
        salida = ai.accion_resumir(texto, proveedor)
    else:
        salida = ai.accion_generar_preguntas(texto, proveedor)
    if accion.tipo == "generar-preguntas-ia" and (si or ui.confirmar(
            "¿Guardar las preguntas generadas en el apunte "
            "(se añaden al final y entran en 'apuncli test')?")):
        db.editar_apunte(conexion, apunte["id"],
                        contenido=(apunte["contenido"] + "\n\n" + salida).strip())
        print(f"✔ Preguntas guardadas en el apunte {apunte['id']}.")
    else:
        print(salida)


def cmd_comprobar_ia(como_json: bool = False) -> int:
    prueba = ai.ProveedorIA().comprobar()
    if como_json:
        print(json.dumps({"disponible": prueba.disponible, "proveedor": prueba.proveedor,
                          "modelo": prueba.modelo, "origen": prueba.origen,
                          "detalle": prueba.detalle},
                         ensure_ascii=False, indent=2))
        return 0 if prueba.disponible else 1
    estado = ui.destacado("✅ IA disponible") if prueba.disponible else ui.tenue("⚠️  IA no disponible")
    print(f"{estado}\n  proveedor: {prueba.proveedor}\n  modelo:    {prueba.modelo}"
          f"\n  config:    {prueba.origen}\n  detalle:   {prueba.detalle}")
    if not prueba.disponible:
        print("\n  Sin IA la CLI sigue funcionando: solo las dos acciones 🤖 la necesitan.")
    return 0 if prueba.disponible else 1


# ---------------------------------------------------------------------------
# Demo (base de datos de ejemplo, no toca tus apuntes)
# ---------------------------------------------------------------------------

DEMO_APUNTES = [
    ("Tema 1: arrays", "ED", "tema1,examen",
     "Un array es una colección de elementos contiguos en memoria.\n\n"
     "## Operaciones\n- acceso por índice O(1)\n- inserción O(n)\n- borrado O(n)\n- recorrido O(n)\n\n"
     "En Java, ArrayList crece un 50% cuando se llena."),
    ("Tema 2: pilas y colas", "ED", "tema1,examen",
     "La **pila** es una estructura LIFO: el último en entrar es el primero en salir.\n"
     "La **cola** es una estructura FIFO: el primero en entrar es el primero en salir.\n\n"
     "## Operaciones de pila\n- push mete arriba\n- pop saca de arriba\n- peek mira el de arriba\n\n"
     "**Pregunta:** ¿Qué coste tiene push en una pila?\n"
     "**Respuesta:** O(1)."),
    ("Tema 3: recursion", "ED", "tema2",
     "La **recursión** es una técnica donde una función se llama a sí misma.\n\n"
     "## Componentes\n- caso base\n- caso recursivo\n- progreso hacia el base\n\n"
     "**Pregunta:** ¿Qué pasa si falta el caso base?\n"
     "**Respuesta:** El programa entra en bucle infinito y revienta la pila."),
    ("Tema 4: Pitágoras", "Matemáticas", "geometría",
     "El **teorema de Pitágoras** es la relación a² + b² = c² entre los catetos y la hipotenusa.\n\n"
     "## Aplicaciones\n- calcular la diagonal de un rectángulo\n- distancia entre dos puntos\n- verificar triángulos rectángulos"),
]


def cmd_demo(conexion, si: bool) -> None:
    """Crea apuntes de ejemplo para probar la herramienta sin riesgo."""
    existentes = {a["titulo"] for a in db.listar_apuntes(conexion)}
    pendientes = [a for a in DEMO_APUNTES if a[0] not in existentes]
    if not pendientes:
        print("Los apuntes de ejemplo ya existen. Bórralos con: apuncli limpiar -t demo")
        return
    if not si and not ui.confirmar(
            f"¿Crear {len(pendientes)} apuntes de ejemplo en TU base de datos? "
            "(luego puedes borrarlos todos con: apuncli limpiar -t demo)"):
        print("Cancelado.")
        return
    for titulo, asignatura, etiquetas, cuerpo in pendientes:
        db.crear_apunte(conexion, titulo, cuerpo, asignatura,
                        [e.strip() for e in etiquetas.split(",") if e.strip()] + ["demo"])
    print(f"✔ {len(pendientes)} apuntes de ejemplo creados (etiqueta [demo]).")
    print("  Pruébalo todo sin riesgo: apuncli listar · apuncli test · apuncli repasar")
    print("  Y para quitarlos: apuncli limpiar -t demo --si")

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


# ---------------------------------------------------------------------------
# Organizador: comandos CLI espejo del modo organizador
# ---------------------------------------------------------------------------

def cmd_organizar(sub: str, carpeta: Path, borrar: bool = False,
                  dias: int = 30, simular: bool = False,
                  categorias: Optional[List[str]] = None,
                  como_json: bool = False) -> None:
    carpeta = Path(carpeta).expanduser()
    if not carpeta.is_dir():
        raise ApuncliError(f"No existe la carpeta: {carpeta}")
    if sub == "espacio":
        datos = [(str(p), n) for p, n in organizador_mod.uso_espacio(carpeta, 2)]
        if como_json:
            print(json.dumps(datos, ensure_ascii=False, indent=2))
            return
        ui.titulo_de_seccion(f"Uso de espacio en {carpeta}")
        for ruta, bytes_ in datos[:20]:
            print(f"  {organizador_mod.tamano_legible(bytes_):>10}  {ruta}")
        return
    if sub == "duplicados":
        grupos = organizador_mod.grupos_duplicados(carpeta)
        if como_json:
            print(json.dumps([{"hash": h, "ficheros": [str(f) for f in fs]}
                              for h, fs in grupos], ensure_ascii=False, indent=2))
            return
        if not grupos:
            print(f"Sin duplicados en {carpeta}")
            return
        for firma, grupo in grupos:
            print(f"  {firma[:10]}…: " + ", ".join(g.name for g in grupo))
        if borrar and not simular:
            total = 0
            for _, grupo in grupos:
                total += len(organizador_mod.borrar_menos_el_ancien(grupo))
            print(f"✔ {total} duplicados borrados (se conserva el más antiguo).")
        elif not simular:
            print(ui.tenue("  (usa --borrar para eliminarlos, conservando el más antiguo)"))
        return
    if sub == "temporales":
        viejos = organizador_mod.temporales_viejos(carpeta, dias)
        if como_json:
            print(json.dumps([str(v) for v in viejos], ensure_ascii=False, indent=2))
            return
        if not viejos:
            print(f"Sin temporales de más de {dias} días en {carpeta}")
            return
        for v in viejos:
            print(f"  {v.name}  ({organizador_mod.tamano_legible(v.stat().st_size)})")
        if simular:
            print(ui.tenue(f"  [simulación] se borrarían {len(viejos)} ficheros."))
        elif borrar:
            total = 0
            for v in viejos:
                try:
                    v.unlink(); total += 1
                except OSError:
                    continue
            print(f"✔ {total} temporales borrados.")
        else:
            if not ui.confirmar(f"¿Borrar los {len(viejos)} temporales?"):
                print("Cancelado."); return
            total = 0
            for v in viejos:
                try:
                    v.unlink(); total += 1
                except OSError:
                    continue
            print(f"✔ {total} temporales borrados.")
        return
    if sub == "ordenar-descargas":
        plan = organizador_mod.plan_ordenar(carpeta, categorias)
        if como_json:
            print(json.dumps([{"origen": str(o), "destino": str(d)}
                              for o, d in plan], ensure_ascii=False, indent=2))
            return
        print(f"Plan para {carpeta.name}:\n{organizador_mod.informe_plan(plan[:30])}")
        if simular:
            print(ui.tenue(f"  [simulación] {len(plan)} ficheros se moverían."))
        else:
            if not ui.confirmar(f"¿Mover {len(plan)} ficheros?"):
                print("Cancelado."); return
            print(f"✔ {organizador_mod.ejecutar_plan_ordenar(plan)} ficheros movidos.")
        return
    if sub == "crear-doc":
        nombre = categorias[0] if categorias else "documento"
        tipo = categorias[1] if categorias and len(categorias) > 1 else "md"
        destino = organizador_mod.crear_documento(carpeta, nombre, tipo)
        print(f"✔ Creado: {destino}")
        return
    raise ApuncliError(f"Subcomando organizador desconocido: {sub}")


def cmd_crear_doc_ruta(ruta_fichero: str, tipo: str = "md") -> None:
    """Crea un documento con ruta completa: ~/Documentos/tema-4.md"""
    ruta = Path(ruta_fichero).expanduser()
    tipo = tipo or (ruta.suffix.lstrip(".") or "md")
    destino = organizador_mod.crear_documento(ruta.parent, ruta.stem, tipo)
    print(f"✔ Creado: {destino}")


def cmd_abrir_fichero(ruta_fichero: str) -> None:
    ruta = Path(ruta_fichero).expanduser()
    if not ruta.exists():
        raise ApuncliError(f"No existe: {ruta}")
    organizador_mod.abrir(ruta)
    print(f"✔ Abierto: {ruta.name}")
