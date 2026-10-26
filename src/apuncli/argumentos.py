"""Definición de los argumentos y el despacho de comandos de apuncli."""

import argparse
import sqlite3
import sys

from . import comandos, db
from .errores import ApuncliError

AYUDA_PRINCIPAL = """\
apuncli — gestor de apuntes de estudio desde la terminal

Ejemplos rápidos:
  apuncli crear "Tema 4: árbol binario" -a "ED" -t "estructuras,arbols"
  apuncli listar -a ED
  apuncli buscar "recursividad"
  apuncli ver 3
  apuncli repasar -n 5

Añade --help a lo que uses para ver los detalles (por ejemplo,
'apuncli crear --help').
"""

EPILOGO = "Usa 'apuncli <comando> --help' para ver los detalles de cada comando."


def _parsear_etiquetas(valor: str):
    return [e.strip().lower() for e in valor.split(",") if e.strip()]


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apuncli",
        description=AYUDA_PRINCIPAL,
        epilog=EPILOGO,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="apuncli 1.0.0")
    sub = parser.add_subparsers(dest="comando", metavar="COMANDO")

    # crear
    p = sub.add_parser("crear", help="crear un apunte nuevo",
                       description="Crea un apunte nuevo. El contenido se puede pasar con "
                                   "-c, con --editor, con --stdin o escribiéndolo a mano.")
    p.add_argument("titulo", help="título del apunte")
    p.add_argument("-c", "--contenido", help="contenido del apunte en una línea")
    p.add_argument("-a", "--asignatura", default="", help="asignatura (ej: Programación)")
    p.add_argument("-t", "--etiquetas", type=_parsear_etiquetas, default=[],
                   help="etiquetas separadas por comas (ej: temas,examen)")
    p.add_argument("-e", "--editor", action="store_true",
                   help="abrir el editor para escribir el contenido")
    p.add_argument("--stdin", action="store_true",
                   help="leer el contenido desde la entrada estándar")

    # listar
    p = sub.add_parser("listar", aliases=["ls"], help="listar los apuntes",
                       description="Lista los apuntes guardados, con filtros opcionales.")
    p.add_argument("-a", "--asignatura", help="filtrar por asignatura")
    p.add_argument("-t", "--etiqueta", help="filtrar por etiqueta")

    # ver
    p = sub.add_parser("ver", help="ver un apunte completo",
                       description="Muestra el título, los metadatos y el contenido del apunte.")
    p.add_argument("id", help="id del apunte (ver 'apuncli listar')")

    # buscar
    p = sub.add_parser("buscar", aliases=["search"], help="buscar apuntes por texto",
                       description="Busca por título y contenido. Admite sintaxis FTS5: "
                                   "'palabra', " '"varias palabras"' ", prefijos ( ejecu*) y "
                                   "booleanos (uno Y otro).")
    p.add_argument("consulta", help="texto a buscar")

    # editar
    p = sub.add_parser("editar", aliases=["edit"], help="editar un apunte existente",
                       description="Cambia título, contenido, asignatura o etiquetas. "
                                   "Sin opciones, no cambia nada.")
    p.add_argument("id", help="id del apunte")
    p.add_argument("-T", "--titulo", help="nuevo título")
    p.add_argument("-c", "--contenido", help="nuevo contenido (sustituye el anterior)")
    p.add_argument("--anadir", action="store_true",
                   help="añade el contenido al final en lugar de sustituir")
    p.add_argument("-a", "--asignatura", help="nueva asignatura")
    p.add_argument("-t", "--etiquetas", type=_parsear_etiquetas,
                   help="nuevas etiquetas (sustituyen a las anteriores)")
    p.add_argument("-e", "--editor", action="store_true",
                   help="abrir el editor para editar el contenido")
    p.add_argument("--stdin", action="store_true",
                   help="leer el contenido desde la entrada estándar")

    # borrar
    p = sub.add_parser("borrar", aliases=["rm"], help="borrar un apunte",
                       description="Borra un apunte. Pide confirmación salvo con --si.")
    p.add_argument("id", help="id del apunte")
    p.add_argument("--si", action="store_true", help="no pedir confirmación")

    # abrir
    p = sub.add_parser("abrir", aliases=["open"], help="abrir un apunte en el editor",
                       description="Abre el apunte en el editor configurado en $EDITOR "
                                   "(o nano/vi). Al guardar y cerrar, los cambios se guardan.")
    p.add_argument("id", help="id del apunte")

    # exportar
    p = sub.add_parser("exportar", help="exportar apuntes a Markdown",
                       description="Imprime en Markdown por la salida estándar. Redirige a "
                                   "un fichero con '>'.")
    p.add_argument("id", nargs="?", help="id del apunte a exportar (vacío = varios)")
    p.add_argument("--todos", action="store_true", help="exportar todos los apuntes")
    p.add_argument("-a", "--asignatura", help="exportar solo los de una asignatura")
    p.add_argument("-t", "--etiqueta", help="exportar solo los de una etiqueta")

    # importar
    p = sub.add_parser("importar", help="importar apuntes desde un fichero Markdown",
                       description="Crea apuntes desde un fichero Markdown. Cada bloque "
                                   "empezado por '# Título' se convierte en un apunte.")
    p.add_argument("fichero", help="ruta del fichero .md")

    # repasar
    p = sub.add_parser("repasar", aliases=["review"], help="repasar apuntes en modo ficha",
                       description="Muestra los títulos uno a uno para que intentes recordar "
                                   "el contenido antes de verlo. Prioriza los no repasados.")
    p.add_argument("-a", "--asignatura", help="repasar solo los de una asignatura")
    p.add_argument("-t", "--etiqueta", help="repasar solo los de una etiqueta")
    p.add_argument("-n", "--num", type=int, default=5, help="cuántos repasar (por defecto 5)")

    # etiquetas
    sub.add_parser("etiquetas", aliases=["tags"], help="listar todas las etiquetas",
                   description="Muestra las etiquetas que existen.")

    # asignaturas
    sub.add_parser("asignaturas", aliases=["materias"], help="listar las asignaturas",
                   description="Muestra las asignaturas que tienen apuntes.")

    # stats
    sub.add_parser("stats", help="ver estadísticas de estudio",
                   description="Resumen: total de apuntes, palabras, repasos y desglose "
                               "por asignatura.")

    return parser


def ejecutar(argv=None) -> int:
    parser = crear_parser()
    args = parser.parse_args(argv)

    if not args.comando:
        parser.print_help()
        return 0

    try:
        conexion = db.conectar()
    except sqlite3.Error as error:
        print(f"error: no se pudo abrir la base de datos ({db.base_datos_ruta()}): {error}",
              file=sys.stderr)
        return 1

    try:
        with conexion:
            _despachar(conexion, args, parser)
        return 0
    except ApuncliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelado.", file=sys.stderr)
        return 130
    except sqlite3.Error as error:
        print(f"error: problema con la base de datos: {error}", file=sys.stderr)
        return 1
    finally:
        conexion.close()


def _despachar(conexion, args, parser) -> None:
    comando = args.comando
    if comando == "crear":
        comandos.cmd_crear(conexion, args.titulo, args.contenido, args.asignatura,
                           args.etiquetas, args.editor, args.stdin)
    elif comando in ("listar", "ls"):
        comandos.cmd_listar(conexion, args.asignatura, args.etiqueta)
    elif comando == "ver":
        comandos.cmd_ver(conexion, comandos._parsear_id(args.id))
    elif comando in ("buscar", "search"):
        comandos.cmd_buscar(conexion, args.consulta)
    elif comando in ("editar", "edit"):
        comandos.cmd_editar(conexion, comandos._parsear_id(args.id),
                            args.titulo, args.contenido, args.asignatura,
                            args.etiquetas, args.editor, args.anadir, args.stdin)
    elif comando in ("borrar", "rm"):
        comandos.cmd_borrar(conexion, comandos._parsear_id(args.id), args.si)
    elif comando in ("abrir", "open"):
        comandos.cmd_abrir(conexion, comandos._parsear_id(args.id))
    elif comando == "exportar":
        comandos.cmd_exportar(conexion, args.id, args.asignatura, args.etiqueta, args.todos)
    elif comando == "importar":
        comandos.cmd_importar(conexion, args.fichero)
    elif comando in ("repasar", "review"):
        comandos.cmd_repasar(conexion, args.asignatura, args.etiqueta, args.num)
    elif comando in ("etiquetas", "tags"):
        comandos.cmd_etiquetas(conexion)
    elif comando in ("asignaturas", "materias"):
        comandos.cmd_asignaturas(conexion)
    elif comando == "stats":
        comandos.cmd_stats(conexion)
    else:
        parser.print_help()
