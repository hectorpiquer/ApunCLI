"""Menú interactivo de apuncli (se abre al escribir 'apuncli' a secas).

Usa solo la librería estándar: la navegación con flechas vive en ui.seleccionar().
"""

import sys

from . import comandos, db, formato, ui
from .errores import ApuncliError
from .ui import SeleccionCancelada

ACCIONES = [
    ("📅  ¿Qué estudio hoy?", "hoy"),
    ("📋  Ver todos mis apuntes", "listar"),
    ("👀  Ver un apunte", "ver"),
    ("➕  Crear un apunte nuevo", "crear"),
    ("✏️   Editar un apunte", "editar"),
    ("🔎  Buscar texto", "buscar"),
    ("🧠  Repasar (modo ficha)", "repasar"),
    ("📝  Hazme un test (autogenerado)", "test"),
    ("🔗  Recursos de un apunte", "recurso"),
    ("📚  Generar temario Markdown", "temario"),
    ("📊  Estadísticas", "stats"),
    ("🏷️   Ver etiquetas", "etiquetas"),
    ("📦  Exportar todo a Markdown", "exportar"),
    ("🚪  Salir del programa", "salir"),
]


class SalirDelMenu(Exception):
    """El usuario ha elegido la opción de salir del menú."""


def menu_principal(conexion) -> int:
    print(ui.destacado("\n📚 apuncli — menú de estudio"))
    print(ui.tenue("   (usa ↑/↓ y Enter; q para volver/salir)"))

    while True:
        try:
            indice = ui.seleccionar("¿Qué quieres hacer?", [a for a, _ in ACCIONES])
        except SeleccionCancelada:
            print("\n¡Hasta la próxima!")
            return 0

        accion = ACCIONES[indice][1]
        if accion == "salir":
            print("\n¡Hasta la próxima!")
            return 0
        try:
            _ejecutar(conexion, accion)
        except ApuncliError as error:
            print(f"\nerror: {error}")
        except SeleccionCancelada:
            pass
        except EOFError:
            print("\n(entrada agotada, saliéndo)")
            return 0


def _ejecutar(conexion, accion: str) -> None:
    if accion == "hoy":
        comandos.cmd_hoy(conexion)
    elif accion == "listar":
        comandos.cmd_listar(conexion, None, None)
    elif accion == "ver":
        apunte = _elegir_apunte(conexion, "Elige el apunte que ver")
        comandos.cmd_ver(conexion, apunte["id"])
    elif accion == "crear":
        titulo = ui.pedir_texto("\nTítulo del apunte: ")
        if not titulo.strip():
            raise ApuncliError("Sin título, no creo nada.")
        asignatura = ui.pedir_texto("Asignatura (opcional): ")
        etiquetas = [e for e in ui.pedir_texto(
            "Etiquetas separadas por comas (opcional): ").split(",") if e.strip()]
        print(ui.tenue("Escribe el contenido (termina con una línea con solo '.'):"))
        cuerpo = ui.leer_bloque()
        comandos.cmd_crear(conexion, titulo, cuerpo, asignatura, etiquetas, False, False)
    elif accion == "editar":
        _editar(conexion)
    elif accion == "buscar":
        consulta = ui.pedir_texto("\n¿Qué buscas? ")
        comandos.cmd_buscar(conexion, consulta)
    elif accion == "repasar":
        comandos.cmd_repasar(conexion, None, None, 5)
    elif accion == "test":
        comandos.cmd_test(conexion, None, None, 10, False)
    elif accion == "recurso":
        apunte = _elegir_apunte(conexion, "Elige el apunte")
        comandos.cmd_recurso_listar(conexion, apunte["id"])
        opcion = ui.pedir_texto("¿Añadir un recurso? Pega la URL o ruta (Enter para no): ").strip()
        if opcion:
            comandos.cmd_recurso(conexion, "anadir", apunte["id"], None, opcion, "")
    elif accion == "temario":
        comandos.cmd_temario(conexion, None, None, None)
    elif accion == "stats":
        comandos.cmd_stats(conexion)
    elif accion == "etiquetas":
        comandos.cmd_etiquetas(conexion)
    elif accion == "exportar":
        texto = "\n".join(
            formato.a_markdown(
                apunte, db.etiquetas_del_apunte(conexion, apunte["id"]),
                db.recursos_del_apunte(conexion, apunte["id"]))
            for apunte in db.listar_apuntes(conexion)
        )
        archivo = ui.pedir_texto("Fichero destino (Enter para imprimir): ").strip()
        if archivo:
            with open(archivo, "w", encoding="utf-8") as f:
                f.write(texto + "\n")
            print(f"✔ Guardado en {archivo}")
        else:
            sys.stdout.write(texto + "\n")


def _editar(conexion) -> None:
    """Edición desde el menú: nunca sustituye contenido sin preguntar."""
    apunte = _elegir_apunte(conexion, "Elige el apunte que editar")
    print(ui.tenue(f"\nVas a editar [{apunte['id']}] {apunte['titulo']}"))

    opciones_contenido = ["➕ Añadir texto al final (lo de arriba se conserva)",
                          "✏️  Escribir el contenido nuevo desde cero",
                          "↩️  No tocar el contenido"]
    indice = ui.seleccionar("¿Qué hacemos con el contenido?", opciones_contenido)

    nuevo_contenido = None
    if indice == 0:
        print(ui.tenue("Escribe el texto a añadir (termina con una línea con solo '.'):"))
        anadido = ui.leer_bloque()
        if anadido:
            anterior = (apunte["contenido"] or "").strip()
            nuevo_contenido = (anterior + "\n\n" + anadido).strip()
    elif indice == 1:
        if ui.confirmar("⚠️  Esto BORRA el contenido actual. ¿Continuar?"):
            print(ui.tenue("Escribe el contenido nuevo (termina con una línea con solo '.'):"))
            nuevo_contenido = ui.leer_bloque()
        else:
            print(ui.tenue("Contenido conservado."))

    titulo = ui.pedir_texto("Nuevo título (Enter para mantener): ").strip()
    asignatura = ui.pedir_texto("Nueva asignatura (Enter para mantener): ").strip()
    etiquetas_raw = ui.pedir_texto(
        "Nuevas etiquetas separadas por comas (Enter para mantener): ")
    etiquetas = [e.strip().lower() for e in etiquetas_raw.split(",") if e.strip()] or None

    if titulo or asignatura or etiquetas or nuevo_contenido is not None:
        comandos.cmd_editar(conexion, apunte["id"],
                            titulo or None, nuevo_contenido,
                            asignatura or None, etiquetas, False, False, False)
    else:
        print(ui.tenue("No has cambiado nada."))


def _elegir_apunte(conexion, mensaje: str):
    apuntes = db.listar_apuntes(conexion)
    if not apuntes:
        raise ApuncliError("No tienes apuntes todavía. Crea uno primero.")
    opciones = [f"[{a['id']}] {a['titulo']} ({a['asignatura'] or '—'})" for a in apuntes]
    indice = ui.seleccionar(mensaje, opciones)
    return apuntes[indice]
