import os
"""El otro modo de apuncli: organizar ficheros, sin salir de la terminal.

Reutiliza el Motor (acciones) y los recursos (abrir con la app asociada).
Todo lo destructivo pasa por ver la lista y confirmar; nunca toca fuera de
la carpeta elegida.
"""

import hashlib
import os
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .errores import ApuncliError
from .motor import hash_de

CATEGORIAS: Dict[str, Tuple[str, List[str]]] = {
    "documentos": ("Documentos", [".pdf", ".doc", ".docx", ".odt", ".txt",
                                  ".md", ".rtf", ".epub"]),
    "imágenes": ("Imágenes", [".jpg", ".jpeg", ".png", ".gif", ".webp",
                              ".bmp", ".svg", ".heic"]),
    "comprimidos": ("Comprimidos", [".zip", ".rar", ".7z", ".tar", ".gz",
                                     ".tgz", ".bz2", ".xz"]),
    "instaladores": ("Instaladores", [".deb", ".rpm", ".appimage", ".exe",
                                       ".msi", ".apk", ".flatpak", ".snap"]),
    "código": ("Codigo", [".py", ".js", ".ts", ".sh", ".c", ".cpp", ".h",
                           ".java", ".sql", ".html", ".css", ".json", ".xml"]),
}

PLANTILLAS: Dict[str, str] = {
    "md": "# {titulo}\n\nasignatura: \netiquetas: \n\n",
    "txt": "",
    "py": '"""\n{titulo}\n"""\n\n\ndef main():\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
    "sh": "#!/usr/bin/env bash\nset -euo pipefail\n# {titulo}\n\n",
    "sql": "-- {titulo}\n\n",
    "html": ("<!doctype html>\n<html lang=\"es\">\n<head>\n"
             "  <meta charset=\"utf-8\">\n  <title>{titulo}</title>\n"
             "</head>\n<body>\n\n</body>\n</html>\n"),
}


# ---------------------------------------------------------------------------
# Explorador: listado puro (la navegación con flechas vive en ui.seleccionar)
# ---------------------------------------------------------------------------

def listar_contenido(carpeta: Path) -> List[Path]:
    """Hijos de la carpeta: carpetas primero, después alfabético sin mayúsculas."""
    try:
        hijos = [h for h in carpeta.iterdir() if not h.name.startswith(".")]
    except NotADirectoryError:
        raise ApuncliError(f"'{carpeta}' es un fichero, no una carpeta.")
    except FileNotFoundError:
        raise ApuncliError(f"No existe la carpeta: {carpeta}")
    except OSError as error:
        raise ApuncliError(f"No se puede leer {carpeta}: {error}")

    return sorted(hijos, key=lambda p: (not es_carpeta(p), p.name.lower()))


def es_archivo(ruta: Path) -> bool:
    """is_file() que nunca revienta (sockets/pipes sin permiso → False)."""
    try:
        return ruta.is_file()
    except OSError:
        return False


def es_carpeta(ruta: Path) -> bool:
    """is_dir() que nunca revienta (sockets/pipes sin permiso → False)."""
    try:
        return ruta.is_dir()
    except OSError:
        return False


_RUTAS_SISTEMA = ("/proc", "/sys", "/dev", "/run")


def _es_ruta_de_sistema(ruta: Path) -> bool:
    """Carpetas del sistema cuyo tamaño no informa y puede mentir/costar mucho."""
    texto = str(ruta)
    return texto in _RUTAS_SISTEMA or any(texto.startswith(x + "/") for x in _RUTAS_SISTEMA)


_FSTYPES_NO_REALES = {"proc", "sysfs", "devtmpfs", "devfs", "tmpfs", "cgroup",
                      "cgroup2", "pstore", "securityfs", "debugfs", "tracefs",
                      "configfs", "fusectl", "bpf", "autofs", "mqueue", "hugetlbfs",
                      "binfmt_misc", "rpc_pipefs", "nsfs", "fuse", "efivarfs"}


def _tipos_de_montaje(carpeta: Path) -> set:
    """Tipos de sistema de fichero montados (para no recorrer /proc ni /sys)."""
    tipos = set()
    try:
        for linea in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
            partes = linea.split(" - ", 1)
            if len(partes) == 2:
                tipos.add(partes[1].split(" ")[0])
    except OSError:
        pass
    return tipos


def _es_montaje_virtual(ruta: Path, fstypes: set) -> bool:
    """True si la ruta es un montaje de kernel (sin ficheros reales que contar)."""
    try:
        dev = ruta.stat().st_dev
    except OSError:
        return True
    try:
        padre = ruta.parent.stat().st_dev
    except OSError:
        padre = None
    if padre is not None and dev == padre:
        return False                     # mismo dispositivo: carpeta normal
    # dispositivo distinto: ¿es de los que no cuentan espacio real?
    try:
        for linea in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
            partes = linea.split(" - ")
            if len(partes) >= 2:
                ruta_mnt = partes[0].rsplit(" ", 1)[-1]
                tipo = partes[1].split(" ")[0]
                if ruta_mnt == str(ruta) and tipo in _FSTYPES_NO_REALES:
                    return True
    except OSError:
        pass
    return False


def registrar_ia(accion: str, detalle: str) -> None:
    from . import ajustes
    ajustes.registrar(accion, detalle)


def _ruta_de(texto: str) -> Path:
    """Path() con ~ expandido, sin que '~nombre' raro reviente en Python 3.10."""
    import os
    texto = (texto or "").strip() or "."
    if texto.startswith("~"):
        try:
            texto = os.path.expanduser(texto)
        except RuntimeError:
            pass                        # sin home: se queda '~…' y exist() dirá no
    return Path(texto)


def info_fichero(ruta: Path) -> str:
    """Ficha de una línea: tipo, tamaño legible y fecha."""
    try:
        datos = ruta.stat()
    except OSError as error:
        raise ApuncliError(f"No puedo leer la información de {ruta.name}: {error}")
    tipo = "carpeta" if es_carpeta(ruta) else (ruta.suffix.lower() or "sin extensión")
    return (f"{ruta.name}  ·  {tipo}  ·  {tamano_legible(datos.st_size)}  ·  "
            f"{datetime.fromtimestamp(datos.st_mtime):%Y-%m-%d %H:%M}")


def tamano_legible(n: int) -> str:
    """Bytes a texto: 532 B, 1.2 KB, 3.4 MB…"""
    tamano = float(n)
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if tamano < 1024 or unidad == "TB":
            return f"{tamano:.0f} {unidad}" if unidad == "B" else f"{tamano:.1f} {unidad}"
        tamano /= 1024
    return f"{tamano:.1f} TB"


def abrir(ruta: Path) -> None:
    """Abre un fichero o carpeta con la app asociada del sistema."""
    if os.name == "nt":
        if not os.path.exists(ruta):
            raise ApuncliError(f"Ya no existe: {ruta}")
        os.startfile(str(ruta))          # type: ignore[attr-defined]
        return
    from . import recursos
    recursos.abrir_recurso(str(ruta))


# ---------------------------------------------------------------------------
# Crear documentos
# ---------------------------------------------------------------------------

def crear_documento(carpeta: Path, nombre: str, tipo: str) -> Path:
    """Crea el documento desde plantilla; nunca pisa (añade -1, -2…)."""
    tipo = tipo.lower().lstrip(".")
    if tipo not in PLANTILLAS:
        raise ApuncliError(f"No conozco la plantilla '{tipo}'. "
                           f"Tipos: {', '.join(sorted(PLANTILLAS))}.")
    nombre = nombre.strip()
    if not nombre or "/" in nombre or "\\" in nombre or nombre in (".", ".."):
        raise ApuncliError("Nombre inválido (sin rutas ni vacíos).")
    if not nombre.endswith(f".{tipo}"):
        nombre = f"{nombre}.{tipo}"
    destino = carpeta / nombre
    contador = 1
    while destino.exists():
        destino = carpeta / f"{Path(nombre).stem}-{contador}{Path(nombre).suffix}"
        contador += 1
    contenido = PLANTILLAS[tipo].format(titulo=Path(nombre).stem)
    try:
        destino.write_text(contenido, encoding="utf-8")
    except OSError as error:
        raise ApuncliError(f"No se pudo crear {destino}: {error}")
    if tipo == "sh":
        destino.chmod(destino.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    from . import ajustes
    ajustes.registrar("crear-doc", str(destino))
    return destino


# ---------------------------------------------------------------------------
# Renombrar por fecha (reutiliza la plantilla del motor)
# ---------------------------------------------------------------------------

def renombrar_por_fecha(ruta: Path) -> Path:
    """Renombra con la convención AAAA-MM-DD_NNN.ext (la fecha del fichero)."""
    if not ruta.exists():
        raise ApuncliError(f"Ya no existe: {ruta}")
    if es_carpeta(ruta):
        raise ApuncliError("Eso es una carpeta; esto es para ficheros.")
    fecha = datetime.fromtimestamp(ruta.stat().st_mtime)
    base = f"{fecha:%Y-%m-%d}"
    contador = 1
    destino = ruta.with_name(f"{base}_{contador:03}{ruta.suffix}")
    while destino.exists():
        contador += 1
        destino = ruta.with_name(f"{base}_{contador:03}{ruta.suffix}")
    try:
        ruta.rename(destino)
    except OSError as error:
        raise ApuncliError(f"No se pudo renombrar {ruta.name}: {error}")
    from . import ajustes
    ajustes.registrar("renombrar", f"{ruta.name} → {destino.name}")
    return destino


# ---------------------------------------------------------------------------
# Duplicados
# ---------------------------------------------------------------------------

def grupos_duplicados(carpeta: Path) -> List[Tuple[str, List[Path]]]:
    """Grupos [hash, ficheros] con 2+ componentes.

    Solo ficheros REALES (no enlaces): un enlace apunta fuera de la carpeta
    pedida; contarlo o borrarlo tocaría ficheros ajenos. El enlace se informa
    como omitido si el llamador pasó `omitidos`.
    """
    por_hash: Dict[str, List[Path]] = {}
    for fichero in listar_contenido(carpeta):
        if not es_archivo(fichero):
            continue
        if fichero.is_symlink():
            continue                         # fuera del perímetro: ni se cuenta
        try:
            firma = _hash_seguro(fichero)
        except FileNotFoundError:
            continue                         # desapareció en mitad: omitido
        except OSError:
            continue                         # ilegible: omitido
        por_hash.setdefault(firma, []).append(fichero)
    return [(firma, lista) for firma, lista in por_hash.items() if len(lista) > 1]


def _hash_seguro(fichero: Path) -> str:
    digest = hashlib.sha256()
    with open(fichero, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(65536), b""):
            digest.update(bloque)
    return digest.hexdigest()


def borrar_menos_el_ancien(grupo: List[Path]) -> List[str]:
    """Deja el más antiguo (menor mtime) y borra el resto. Devuelve nombres."""
    if len(grupo) < 2:
        return []
    ordenados = sorted(grupo, key=lambda p: p.stat().st_mtime)
    borrados = []
    for ruta in ordenados[1:]:
        try:
            if ruta.is_symlink():
                continue          # un enlace apunta fuera: no lo borramos, no lo seguimos
            ruta.unlink()
            borrados.append(ruta.name)
        except FileNotFoundError:
            continue                       # ya no estaba: exactamente lo que queríamos
    if borrados:
        from . import ajustes
        ajustes.registrar("borrar-duplicados", f"{len(borrados)} ficheros")
    return borrados


# ---------------------------------------------------------------------------
# Uso de espacio
# ---------------------------------------------------------------------------

def uso_espacio(carpeta: Path, niveles: int = 2, tope: int = 200000) -> List[Tuple[Path, int]]:
    """Tamaño (bytes) de cada subcarpeta hasta N niveles, ordenado de mayor.

    Reglas de seguridad:
      · enlaces simbólicos y montajes (fifos, sockets, /proc, /sys, /dev): se
        cuentan como 0 y no se recorren — nunca se sale de la carpeta pedida
      · carpetas ilegibles: se ignoran (informar de espacio no debe romper)
      · tope de ficheros leídos: una carpeta enorme no congela el programa
    """
    resultados: List[Tuple[Path, int]] = []
    leidos = 0

    def no_es_arbol_real(r: Path) -> bool:
        try:
            if r.is_symlink():
                return True
            est = r.lstat()
            import stat as st
            if not st.S_ISDIR(est.st_mode):
                return True                    # fifo, socket… no se recorren
        except OSError:
            return True
        return False

    def tamano_arbol(r: Path) -> int:
        nonlocal leidos
        total = 0
        try:
            for hijo in r.iterdir():
                if leidos >= tope:
                    return total
                try:
                    if es_archivo(hijo):
                        try:
                            total += hijo.stat().st_size
                        except OSError:
                            continue
                        leidos += 1
                    elif es_carpeta(hijo) and not no_es_arbol_real(hijo):
                        total += tamano_arbol(hijo)
                except OSError:
                    continue
        except OSError:
            return 0
        return total

    try:
        hijos = listar_contenido(carpeta)
    except ApuncliError:
        return []
    fstypes = _tipos_de_montaje(carpeta)
    for hijo in hijos:
        if not es_carpeta(hijo) or no_es_arbol_real(hijo):
            continue
        if _es_ruta_de_sistema(hijo) or _es_montaje_virtual(hijo, fstypes):
            continue                     # /proc, /sys, /dev, fuse…: no es espacio real
        try:
            tam = tamano_arbol(hijo)
        except OSError:
            continue
        resultados.append((hijo, tam))
        if niveles >= 2:
            try:
                nietos = listar_contenido(hijo)
            except ApuncliError:
                nietos = []
            for nieto in nietos:
                if es_carpeta(nieto) and not no_es_arbol_real(nieto):
                    try:
                        resultados.append((nieto, tamano_arbol(nieto)))
                    except OSError:
                        continue
    return sorted(resultados, key=lambda t: -t[1])


# ---------------------------------------------------------------------------
# Ordenar descargas por categoría (guiado, con plan antes de actuar)
# ---------------------------------------------------------------------------

def plan_ordenar(carpeta: Path, categorias: Optional[List[str]] = None,
                 raiz: Optional[Path] = None,
                 omitidos: Optional[List[str]] = None
                 ) -> List[Tuple[Path, Path]]:
    """[(fichero, destino)] según CATEGORIAS. Solo lo que existe y coincide.

    `omitidos` recibe nombres de ficheros que no se pudieron leer (sin permiso):
    el plan se ejecuta igual, pero el usuario sabe que no estaba todo.
    """
    raiz = raiz or Path.home()
    plan: List[Tuple[Path, Path]] = []
    for categoria in (categorias or list(CATEGORIAS)):
        subcarpeta, extensiones = CATEGORIAS[categoria]
        destino_dir = raiz / subcarpeta
        for fichero in listar_contenido(carpeta):
            try:
                coincide = es_archivo(fichero) and fichero.suffix.lower() in extensiones
            except OSError as error:
                if omitidos is not None:
                    omitidos.append(f"{fichero.name} ({error.strerror})")
                continue
            if coincide:
                if fichero.is_symlink():
                    if omitidos is not None:
                        omitidos.append(f"{fichero.name} (enlace, se queda donde está)")
                    continue
                plan.append((fichero, destino_dir / fichero.name))
    return plan


def ejecutar_plan_ordenar(plan: List[Tuple[Path, Path]]) -> int:
    from .motor import Motor
    movidos = 0
    for origen, destino in plan:
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            from .motor import Motor as M
            destino = M._sin_colision(destino)
        try:
            shutil.move(str(origen), str(destino))
            movidos += 1
            from . import ajustes
            ajustes.registrar("mover", f"{origen.name} → {destino}")
        except OSError as error:
            raise ApuncliError(f"No se pudo mover {origen.name}: {error}")
    return movidos


def informe_plan(plan: List[Tuple[Path, Path]]) -> str:
    lineas = [f"  {origen.name}  →  {destino}" for origen, destino in plan]
    return "\n".join(lineas) if lineas else "  (nada que mover: sin coincidencias)"


# ---------------------------------------------------------------------------
# Temporales viejos
# ---------------------------------------------------------------------------

PATRONES_TEMPORAL = (".tmp", ".bak", ".log", ".old")


def temporales_viejos(carpeta: Path, dias: int = 30) -> List[Path]:
    """Temporales reales de más de N días (los enlaces simbólicos se ignoran)."""
    ahora = datetime.now().timestamp()
    corte = ahora - dias * 86400
    viejos = []
    for fichero in listar_contenido(carpeta):
        try:
            if (fichero.is_symlink()
                    or not es_archivo(fichero)
                    or fichero.suffix.lower() not in PATRONES_TEMPORAL):
                continue
            if fichero.stat().st_mtime < corte:
                viejos.append(fichero)
        except OSError:
            continue
    return viejos
