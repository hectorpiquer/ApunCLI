"""Definición de los argumentos y el despacho de comandos de apuncli."""

import argparse
import sqlite3
import sys

from . import __version__, comandos, db, ui
from .errores import ApuncliError, ConfigError

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
    parser.add_argument("--version", action="version", version=f"apuncli {__version__}")
    parser.add_argument("--config", metavar="RUTA",
                        help="otro fichero de acciones (por defecto ./acciones.json)")
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
    p.add_argument("--json", action="store_true",
                   help="salida en JSON (para tuberías y otros programas)")

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

    # limpiar
    p = sub.add_parser("limpiar", help="borrar en bloque apuntes por filtro",
                       description="Borra todos los apuntes de una asignatura o etiqueta. "
                                   "Muestra la lista y pide confirmación salvo con --si.")
    p.add_argument("-a", "--asignatura", help="asignatura a borrar")
    p.add_argument("-t", "--etiqueta", help="etiqueta a borrar")
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

    # test
    p = sub.add_parser("test", help="hacerte un test a partir de tus apuntes",
                       description="Busca preguntas escritas como '**Pregunta:** … "
                                   "**Respuesta:** …' dentro de los apuntes y te las hace. "
                                   "Corrige con tolerancia (ignora acentos y mayúsculas) y "
                                   "te da la nota sobre 10.")
    p.add_argument("-a", "--asignatura", help="solo de una asignatura")
    p.add_argument("-t", "--etiqueta", help="solo de una etiqueta")
    p.add_argument("-n", "--num", type=int, default=10, help="nº de preguntas (por defecto 10)")
    p.add_argument("--auto", action="store_true",
                   help="solo preguntas generadas automáticamente (ignora las escritas a mano)")

    # recurso
    p = sub.add_parser("recurso", aliases=["rec"], help="gestionar enlaces y ficheros de un apunte",
                       description="Adjunta y abre recursos (web, PDFs, imágenes, apuntes en "
                                   "el disco). Las URLs y rutas que escribes en el contenido "
                                   "se detectan y adjuntan solas.")
    recursos = p.add_subparsers(dest="accion", metavar="ACCIÓN")
    pr = recursos.add_parser("listar", help="listar los recursos de un apunte")
    pr.add_argument("apunte", help="id del apunte")
    pr = recursos.add_parser("anadir", help="añadir un recurso a un apunte")
    pr.add_argument("apunte", help="id del apunte")
    pr.add_argument("url", help="URL o ruta del fichero")
    pr.add_argument("-n", "--nombre", default="", help="nombre visible (opcional)")
    pr = recursos.add_parser("abrir", help="abrir un recurso (navegador o programa asociado)")
    pr.add_argument("recurso", help="id del recurso")
    pr = recursos.add_parser("borrar", help="borrar un recurso")
    pr.add_argument("recurso", help="id del recurso")

    # temario
    p = sub.add_parser("temario", help="generar un temario/índice Markdown de tus apuntes",
                       description="Crea un único documento Markdown con índice, enlaces a "
                                   "cada apunte, recursos y estado de repaso. Perfecto para "
                                   "imprimir, pasar a PDF o subir a GitHub.")
    p.add_argument("-a", "--asignatura", help="solo los de una asignatura")
    p.add_argument("-t", "--etiqueta", help="solo los de una etiqueta")
    p.add_argument("-T", "--titulo", help="título del temario")

    # etiquetas
    p = sub.add_parser("etiquetas", aliases=["tags"], help="listar etiquetas oretoquear las de un apunte",
                       description="Sin argumentos lista todas las etiquetas. Con --anadir/--quitar "
                                   "cambia las etiquetas de un apunte sin reescribir el resto.")
    p.add_argument("--anadir", metavar="ID", type=int, help="id del apunte al que añadir etiquetas")
    p.add_argument("--quitar", metavar="ID", type=int, help="id del apunte al que quitar etiquetas")
    p.add_argument("nombres", nargs="*", help="nombres de las etiquetas")

    # asignaturas
    sub.add_parser("asignaturas", aliases=["materias"], help="listar las asignaturas",
                   description="Muestra las asignaturas que tienen apuntes.")

    # stats
    sub.add_parser("stats", help="ver estadísticas de estudio",
                   description="Resumen: total de apuntes, palabras, repasos y desglose "
                               "por asignatura.")

    # hoy
    sub.add_parser("hoy", help="plan rápido de qué estudiar hoy",
                   description="Te dice qué apuntes no has repasado aún, cuáles tienen "
                               "preguntas para test y cuáles tocaste hace poco.")

    # respaldo
    p = sub.add_parser("respaldo", aliases=["backup"], help="copia de seguridad de tus apuntes",
                       description="Guarda o restaura una copia de la base de datos. "
                                   "Las copias se guardan junto a la base de datos.")
    respaldos_sub = p.add_subparsers(dest="accion", metavar="ACCIÓN")
    respaldos_sub.add_parser("hacer", help="crear una copia de seguridad ahora")
    respaldos_sub.add_parser("listar", help="listar las copias existentes")
    pr = respaldos_sub.add_parser("restaurar", help="restaurar desde una copia")
    pr.add_argument("fichero", nargs="?", help="fichero de copia (vacío = la más reciente)")

    # completar
    sub.add_parser("completar", help="guion de autocompletado para tu terminal",
                   description="Imprime el código de autocompletado (TAB) para bash. "
                               "Se configura una vez en tu ~/.bashrc.")

    # demo
    p = sub.add_parser("demo", help="crear apuntes de ejemplo para probar",
                       description="Inserta 4 apuntes de muestra (ED y Matemáticas) con "
                                   "negritas, listas y preguntas para que pruebes el test, "
                                   "el repaso y el temario. Todos llevan etiqueta [demo].")
    p.add_argument("--si", action="store_true", help="sin confirmar")

    # acciones / validar / ejecutar / comprobar-ia (el sistema de acciones)
    p = sub.add_parser("acciones", help="listar las acciones de acciones.json",
                       description="Muestra las acciones definidas en el fichero de "
                                   "configuración con su descripción.")
    p.add_argument("--json", action="store_true", help="salida en JSON")

    p = sub.add_parser("validar", help="comprobar acciones.json (código 3 si falla)",
                       description="Valida el fichero de configuración y dice "
                                   "exactamente qué campo falla. Sale con código 3 "
                                   "si el JSON no es válido.")

    p = sub.add_parser("ejecutar", help="ejecutar una acción del fichero de acciones",
                       description="Ejecuta la acción NOMBRE sobre CARPETA (o el origen "
                                   "de la acción). --simular enseña qué haría sin tocar "
                                   "nada; --si no pregunta. Las acciones con IA piden el "
                                   "id del apunte en lugar de carpeta.")
    p.add_argument("nombre", help="nombre de la acción (ver 'apuncli acciones')")
    p.add_argument("carpeta", nargs="?",
                   help="carpeta sobre la que trabajar (o id del apunte en acciones IA)")
    p.add_argument("--simular", action="store_true", help="enseña qué haría, sin tocar nada")
    p.add_argument("--si", action="store_true", help="no preguntar (para scripts)")
    p.add_argument("--json", action="store_true", help="salida en JSON")

    p = sub.add_parser("comprobar-ia", help="probar la conexión con el modelo de IA",
                       description="Comprueba si el proveedor de IA del .env/ia.env "
                                   "responde. Sin IA la CLI sigue funcionando con "
                                   "todo lo demás.")
    p.add_argument("--json", action="store_true", help="salida en JSON")

    return parser


def ejecutar(argv=None) -> int:
    parser = crear_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as salida:
        # argparse ya imprime el mensaje; codificamos según la rúbrica:
        # --help sale con 0; un error de uso, con 2.
        return 0 if (salida.code == 0 or salida.code is None) else 2

    try:
        conexion = db.conectar()
    except sqlite3.Error as error:
        print(f"error: no se pudo abrir la base de datos ({db.base_datos_ruta()}): {error}",
              file=sys.stderr)
        return 1

    try:
        if not args.comando:
            if ui.terminal_interactiva():
                try:
                    with conexion:
                        from . import interfaz
                        return interfaz.menu_principal(conexion)
                finally:
                    sys.stdout.flush()
            parser.print_help()
            return 0
        with conexion:
            return _despachar(conexion, args, parser) or 0
    except ConfigError as error:
        print("error de configuración:", file=sys.stderr)
        for problema in error.problemas:
            print(f"  · {problema}", file=sys.stderr)
        return 3
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
        comandos.cmd_listar(conexion, args.asignatura, args.etiqueta, args.json)
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
    elif comando == "limpiar":
        comandos.cmd_limpiar(conexion, args.asignatura, args.etiqueta, args.si)
    elif comando in ("abrir", "open"):
        comandos.cmd_abrir(conexion, comandos._parsear_id(args.id))
    elif comando == "exportar":
        comandos.cmd_exportar(conexion, args.id, args.asignatura, args.etiqueta, args.todos)
    elif comando == "importar":
        comandos.cmd_importar(conexion, args.fichero)
    elif comando in ("repasar", "review"):
        comandos.cmd_repasar(conexion, args.asignatura, args.etiqueta, args.num)
    elif comando == "test":
        comandos.cmd_test(conexion, args.asignatura, args.etiqueta, args.num, args.auto)
    elif comando in ("recurso", "rec"):
        if args.accion == "listar":
            comandos.cmd_recurso_listar(conexion, comandos._parsear_id(args.apunte))
        elif args.accion == "anadir":
            comandos.cmd_recurso(conexion, "anadir", comandos._parsear_id(args.apunte),
                                 None, args.url, args.nombre)
        elif args.accion == "abrir":
            comandos.cmd_recurso(conexion, "abrir", None,
                                 comandos._parsear_id(args.recurso), None, "")
        elif args.accion == "borrar":
            comandos.cmd_recurso(conexion, "borrar", None,
                                 comandos._parsear_id(args.recurso), None, "")
        else:
            parser.parse_args(["recurso", "--help"])
    elif comando == "temario":
        comandos.cmd_temario(conexion, args.asignatura, args.etiqueta, args.titulo)
    elif comando in ("etiquetas", "tags"):
        comandos.cmd_etiquetas(conexion, args.anadir, args.quitar, args.nombres)
    elif comando in ("asignaturas", "materias"):
        comandos.cmd_asignaturas(conexion)
    elif comando == "stats":
        comandos.cmd_stats(conexion)
    elif comando == "hoy":
        comandos.cmd_hoy(conexion)
    elif comando in ("respaldo", "backup"):
        accion = args.accion or "hacer"
        comandos.cmd_respaldo(conexion, accion, getattr(args, "fichero", None))
    elif comando == "completar":
        comandos.cmd_completar()
    elif comando == "demo":
        comandos.cmd_demo(conexion, args.si)
    elif comando == "acciones":
        comandos.cmd_acciones(comandos._cargar_config(args.config), args.json)
    elif comando == "validar":
        return comandos.cmd_validar(args.config)
    elif comando == "ejecutar":
        config = comandos._cargar_config(args.config)
        comandos.cmd_ejecutar(conexion, config, args.nombre, args.carpeta,
                              args.simular, args.si, args.json)
    elif comando == "comprobar-ia":
        return comandos.cmd_comprobar_ia(args.json)
    else:
        parser.print_help()
