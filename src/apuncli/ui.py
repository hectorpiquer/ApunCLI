"""Utilidades de presentación por consola."""

import os
import shutil
import subprocess
import sys

from .errores import ApuncliError

try:
    import termios as _termios_mod
    _TERMIOS_OK = True
except ImportError:  # Windows: los menús usarán la versión numérica
    _termios_mod = None
    _TERMIOS_OK = False


def color_activado() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _pinta(texto: str, codigo: str) -> str:
    if color_activado():
        return f"\033[{codigo}m{texto}\033[0m"
    return texto


def subrayado(texto: str) -> str:
    return _pinta(texto, "4")


def tenue(texto: str) -> str:
    return _pinta(texto, "2")


def destacado(texto: str) -> str:
    return _pinta(texto, "1")


def titulo_de_seccion(texto: str) -> None:
    print()
    print(subrayado(texto))


def editor_ambiente() -> str:
    """Devuelve la orden del editor preferido del usuario."""
    for variable in ("EDITOR", "VISUAL"):
        valor = os.environ.get(variable)
        if valor:
            return valor
    for candidato in ("nano", "vim", "vi"):
        if shutil.which(candidato):
            return candidato
    raise ApuncliError(
        "No se encontró ningún editor. Define la variable de entorno EDITOR "
        "(por ejemplo: export EDITOR=nano)."
    )


def abrir_en_editor(archivo: str) -> int:
    """Abre un fichero con el editor y devuelve el código de salida."""
    editor = editor_ambiente().split()
    try:
        completado = subprocess.run(editor + [archivo])
        return completado.returncode
    except FileNotFoundError:
        raise ApuncliError(f"No se pudo abrir el editor: {editor[0]!r} no existe.")


def confirmar(mensaje: str, por_defecto: bool = False) -> bool:
    """Pregunta sí/no por consola."""
    sufijo = "[S/n]" if por_defecto else "[s/N]"
    try:
        respuesta = input(f"{mensaje} {sufijo}: ").strip().lower()
    except EOFError:
        return por_defecto
    if not respuesta:
        return por_defecto
    return respuesta in ("s", "si", "sí", "y")


def pedir_texto(mensaje: str) -> str:
    try:
        return input(mensaje)
    except EOFError:
        return ""


def leer_multilinea() -> str:
    """Lee varias líneas hasta Ctrl+D (o Ctrl+Z+Enter en Windows)."""
    print(tenue("Escribe el contenido (termina con Ctrl+D):"))
    lineas = []
    while True:
        try:
            lineas.append(input())
        except EOFError:
            break
    return "\n".join(lineas).strip()


def leer_bloque(fin: str = ".") -> str:
    """Lee varias líneas hasta escribir una línea con solo 'fin' (o Ctrl+D).

    Más fiable que Ctrl+D en terminales con modo crudo.
    """
    lineas = []
    while True:
        try:
            linea = input()
        except EOFError:
            break
        if linea.strip() == fin:
            break
        lineas.append(linea)
    return "\n".join(lineas).strip()


# ---------------------------------------------------------------------------
# Selector con flechas (menús interactivos de la TUI)
# ---------------------------------------------------------------------------


class SeleccionCancelada(Exception):
    """El usuario ha cancelado la selección (Ctrl+C o Esc)."""


def seleccionar(titulo: str, opciones, por_defecto: int = 0) -> int:
    """Menú interactivo: ↑/↓ o j/k mueven, Enter confirma, q/Esc cancela.

    Usa únicamente la librería estándar (termios/tty/select). La terminal se
    pone en modo crudo SIN ISIG (para que Ctrl+C sea una tecla y no mate el
    programa) y SIN OPOST (los '\n' salen crudos: así el cálculo de filas del
    cursor coincide exactamente con lo que pinta el programa). Si la terminal
    no es interactiva (tuberías, tests), se elige tecleando número.
    """
    if not opciones:
        raise SeleccionCancelada()

    if not _terminal_interactiva():
        return _seleccionar_numerica(titulo, opciones, por_defecto)

    import tty

    sys.stdout.write(f"\n{_pinta(titulo, '4')}\n")
    sys.stdout.flush()
    cursor = max(0, min(por_defecto, len(opciones) - 1))
    pintadas = 0

    def pintar() -> None:
        nonlocal pintadas
        if pintadas:
            sys.stdout.write(f"\033[{pintadas}F")
        for i, opcion in enumerate(opciones):
            marca = "❯ " if i == cursor else "  "
            estilo = "\033[1m" if i == cursor else ""
            sys.stdout.write(f"\r\033[2K{marca}{estilo}{opcion[:68]}\033[0m\r\n")
        sys.stdout.flush()
        pintadas = len(opciones)

    fd = sys.stdin.fileno()
    guardado = _termios_mod.tcgetattr(fd)
    try:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        _modo_menu(fd)
        pintar()
        while True:
            tecla = _leer_tecla(fd)
            anterior = cursor
            if tecla in ("flecha_arriba", "k"):
                cursor = (cursor - 1) % len(opciones)
            elif tecla in ("flecha_abajo", "j"):
                cursor = (cursor + 1) % len(opciones)
            elif tecla in ("inicio", "g"):
                cursor = 0
            elif tecla in ("flecha_fin", "G"):
                cursor = len(opciones) - 1
            elif tecla == "intro":
                return cursor
            elif tecla in ("q", "escape", "ctrl_c"):
                raise SeleccionCancelada()
            elif tecla == "eof":
                raise EOFError
            elif tecla == "espera":
                continue
            if anterior != cursor:
                pintar()
    finally:
        _termios_mod.tcsetattr(fd, _termios_mod.TCSADRAIN, guardado)
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


def _modo_menu(fd: int) -> None:
    """Modo crudo para el menú: tecla a tecla, sin eco y CON onlcr.

    setraw() apaga OPOST, así que los '\r\n' crudos no bajarían de línea en
    la terminal y la salida parecería congelarse. Reactivamos OPOST|ONLCR:
    cada '\n' se convierte en '\r\n' y el cursor real coincide con el nuestro.
    ISIG queda apagado, así que Ctrl+C es una tecla más (cancela el menú).
    """
    import tty

    tty.setraw(fd)
    modo = _termios_mod.tcgetattr(fd)
    modo[1] |= _termios_mod.OPOST | _termios_mod.ONLCR
    modo[6][_termios_mod.VMIN] = 1
    modo[6][_termios_mod.VTIME] = 0
    _termios_mod.tcsetattr(fd, _termios_mod.TCSANOW, modo)


def _leer_tecla(fd: int) -> str:
    """Lee una tecla en modo crudo y la traduce ('intro', 'flecha_arriba'…).

    Debe llamarse con la terminal ya en modo crudo (OPOST conservado para
    que el '\\n' del menú se escriba como CRLF).
    Devuelve 'fin' si la entrada se agota (Ctrl+D), para no colgarse.
    """
    import select

    listo, _, _ = select.select([fd], [], [], 15.0)
    if not listo:
        return "espera"
    try:
        byte = os.read(fd, 1)
    except OSError:
        return "eof"
    if not byte:
        return "eof"

    if byte in (b"\r", b"\n"):
        return "intro"
    if byte == b"\x03":
        return "ctrl_c"
    if byte == b"\x04":
        return "eof"
    if byte == b"\x1b":
        lista, _, _ = select.select([fd], [], [], 0.05)
        if not lista:
            return "escape"
        resto = os.read(fd, 2)
        if resto == b"[A":
            return "flecha_arriba"
        if resto == b"[B":
            return "flecha_abajo"
        if resto == b"[H":
            return "inicio"
        if resto == b"[F":
            return "flecha_fin"
        return "escape"
    return byte.decode("utf-8", "replace")


def _terminal_interactiva() -> bool:
    return (_TERMIOS_OK
            and sys.stdin.isatty() and sys.stdout.isatty()
            and os.environ.get("TERM") not in (None, "dumb"))


def terminal_interactiva() -> bool:
    """True si hay una terminal real donde navegar con flechas."""
    return _terminal_interactiva()


def _seleccionar_numerica(titulo: str, opciones, por_defecto: int) -> int:
    """Versión para tuberías/tests: se elige tecleando el número."""
    print(f"\n{titulo}")
    for i, opcion in enumerate(opciones):
        print(f"  {i + 1}. {opcion}")
    while True:
        try:
            eleccion = input(f"Escribe el número [1-{len(opciones)}] "
                             f"(Enter = {por_defecto + 1}): ").strip()
        except EOFError:
            return por_defecto
        if not eleccion:
            return por_defecto
        if eleccion.isdigit() and 1 <= int(eleccion) <= len(opciones):
            return int(eleccion) - 1
        print("No vale. Prueba otra vez.")
