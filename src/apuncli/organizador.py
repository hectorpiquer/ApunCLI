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
    except OSError as error:
        raise ApuncliError(f"No se puede leer {carpeta}: {error}")
    return sorted(hijos, key=lambda p: (not p.is_dir(), p.name.lower()))


def info_fichero(ruta: Path) -> str:
    """Ficha de una línea: tipo, tamaño legible y fecha."""
    datos = ruta.stat()
    tipo = "carpeta" if ruta.is_dir() else (ruta.suffix.lower() or "sin extensión")
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
    return destino


# ---------------------------------------------------------------------------
# Renombrar por fecha (reutiliza la plantilla del motor)
# ---------------------------------------------------------------------------

def renombrar_por_fecha(ruta: Path) -> Path:
    """Renombra con la convención AAAA-MM-DD_NNN.ext (la fecha del fichero)."""
    if not ruta.exists():
        raise ApuncliError(f"Ya no existe: {ruta}")
    if ruta.is_dir():
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
    return destino


# ---------------------------------------------------------------------------
# Duplicados
# ---------------------------------------------------------------------------

def grupos_duplicados(carpeta: Path) -> List[Tuple[str, List[Path]]]:
    """Grupos [hash, ficheros] con 2+ componentes (solo ficheros)."""
    por_hash: Dict[str, List[Path]] = {}
    for fichero in listar_contenido(carpeta):
        if not fichero.is_file():
            continue
        try:
            por_hash.setdefault(hash_de(fichero), []).append(fichero)
        except OSError:
            continue
    return [(firma, lista) for firma, lista in por_hash.items() if len(lista) > 1]


def borrar_menos_el_ancien(grupo: List[Path]) -> List[str]:
    """Deja el más antiguo (menor mtime) y borra el resto. Devuelve nombres."""
    if len(grupo) < 2:
        return []
    ordenados = sorted(grupo, key=lambda p: p.stat().st_mtime)
    borrados = []
    for ruta in ordenados[1:]:
        try:
            ruta.unlink()
            borrados.append(ruta.name)
        except OSError as error:
            raise ApuncliError(f"No se pudo borrar {ruta.name}: {error}")
    return borrados


# ---------------------------------------------------------------------------
# Uso de espacio
# ---------------------------------------------------------------------------

def uso_espacio(carpeta: Path, niveles: int = 2) -> List[Tuple[Path, int]]:
    """Tamaño (bytes) de cada subcarpeta hasta N niveles, ordenado de mayor.

    Las subcarpetas ilegibles (permisos) se ignoran: informar de espacio no
    debe romper por un directorio privado del sistema.
    """
    resultados: List[Tuple[Path, int]] = []

    def tamano_arbol(r: Path) -> int:
        total = 0
        try:
            for hijo in r.iterdir():
                try:
                    if hijo.is_file():
                        total += hijo.stat().st_size
                    elif hijo.is_dir():
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
    for hijo in hijos:
        if not hijo.is_dir():
            continue
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
                if nieto.is_dir():
                    try:
                        resultados.append((nieto, tamano_arbol(nieto)))
                    except OSError:
                        continue
    return sorted(resultados, key=lambda t: -t[1])


# ---------------------------------------------------------------------------
# Ordenar descargas por categoría (guiado, con plan antes de actuar)
# ---------------------------------------------------------------------------

def plan_ordenar(carpeta: Path, categorias: Optional[List[str]] = None,
                 raiz: Optional[Path] = None) -> List[Tuple[Path, Path]]:
    """[(fichero, destino)] según CATEGORIAS. Solo lo que existe y coincide."""
    raiz = raiz or Path.home()
    plan: List[Tuple[Path, Path]] = []
    for categoria in (categorias or list(CATEGORIAS)):
        subcarpeta, extensiones = CATEGORIAS[categoria]
        destino_dir = raiz / subcarpeta
        for fichero in listar_contenido(carpeta):
            if fichero.is_file() and fichero.suffix.lower() in extensiones:
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
    ahora = datetime.now().timestamp()
    corte = ahora - dias * 86400
    viejos = []
    for fichero in listar_contenido(carpeta):
        try:
            if (fichero.is_file()
                    and fichero.suffix.lower() in PATRONES_TEMPORAL
                    and fichero.stat().st_mtime < corte):
                viejos.append(fichero)
        except OSError:
            continue
    return viejos
