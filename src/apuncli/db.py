"""Capa de acceso a datos de apuncli (SQLite)."""

import os
import sqlite3
from datetime import datetime
from typing import List, Optional

from .errores import ApuncliError

FTS5_DISPONIBLE = True
try:
    _prueba = sqlite3.connect(":memory:")
    _prueba.execute("CREATE VIRTUAL TABLE _prueba USING fts5(texto)")
    _prueba.close()
except sqlite3.OperationalError:
    FTS5_DISPONIBLE = False


def base_datos_ruta() -> str:
    """Ruta de la base de datos. Se puede cambiar con la variable APUNCLI_DB."""
    override = os.environ.get("APUNCLI_DB")
    if override:
        return os.path.expanduser(override)
    return os.path.join(os.path.expanduser("~"), ".apuncli", "apuncli.db")


def conectar() -> sqlite3.Connection:
    """Abre la base de datos, creando el directorio si no existe."""
    ruta = base_datos_ruta()
    directorio = os.path.dirname(ruta)
    if directorio:
        os.makedirs(directorio, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    inicializar(conexion)
    return conexion


def inicializar(conexion: sqlite3.Connection) -> None:
    """Crea las tablas si no existen."""
    conexion.executescript(
        """
        CREATE TABLE IF NOT EXISTS apuntes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            contenido TEXT NOT NULL DEFAULT '',
            asignatura TEXT NOT NULL DEFAULT '',
            creado TEXT NOT NULL,
            modificado TEXT NOT NULL,
            veces_repasado INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS etiquetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
        );

        CREATE TABLE IF NOT EXISTS apuntes_etiquetas (
            apunte_id INTEGER NOT NULL REFERENCES apuntes(id) ON DELETE CASCADE,
            etiqueta_id INTEGER NOT NULL REFERENCES etiquetas(id) ON DELETE CASCADE,
            PRIMARY KEY (apunte_id, etiqueta_id)
        );

        CREATE TABLE IF NOT EXISTS recursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apunte_id INTEGER NOT NULL REFERENCES apuntes(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL,
            creado TEXT NOT NULL
        );
        """
    )
    if FTS5_DISPONIBLE:
        conexion.executescript(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS apuntes_busca
            USING fts5(titulo, contenido, content='apuntes', content_rowid='id');

            CREATE TRIGGER IF NOT EXISTS apuntes_fts_ai AFTER INSERT ON apuntes BEGIN
                INSERT INTO apuntes_busca(rowid, titulo, contenido)
                VALUES (new.id, new.titulo, new.contenido);
            END;

            CREATE TRIGGER IF NOT EXISTS apuntes_fts_ad AFTER DELETE ON apuntes BEGIN
                INSERT INTO apuntes_busca(apuntes_busca, rowid, titulo, contenido)
                VALUES ('delete', old.id, old.titulo, old.contenido);
            END;

            CREATE TRIGGER IF NOT EXISTS apuntes_fts_au AFTER UPDATE ON apuntes BEGIN
                INSERT INTO apuntes_busca(apuntes_busca, rowid, titulo, contenido)
                VALUES ('delete', old.id, old.titulo, old.contenido);
                INSERT INTO apuntes_busca(rowid, titulo, contenido)
                VALUES (new.id, new.titulo, new.contenido);
            END;
            """
        )
    conexion.commit()


def ahora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Etiquetas
# ---------------------------------------------------------------------------

def obtener_o_crear_etiqueta(conexion: sqlite3.Connection, nombre: str) -> int:
    nombre = nombre.strip().lower()
    fila = conexion.execute(
        "SELECT id FROM etiquetas WHERE nombre = ?", (nombre,)
    ).fetchone()
    if fila:
        return fila["id"]
    cursor = conexion.execute("INSERT INTO etiquetas (nombre) VALUES (?)", (nombre,))
    conexion.commit()
    return cursor.lastrowid


def asignar_etiquetas(conexion: sqlite3.Connection, apunte_id: int, nombres: List[str]) -> None:
    conexion.execute("DELETE FROM apuntes_etiquetas WHERE apunte_id = ?", (apunte_id,))
    for nombre in nombres:
        nombre = nombre.strip().lower()
        if not nombre:
            continue
        etiqueta_id = obtener_o_crear_etiqueta(conexion, nombre)
        conexion.execute(
            "INSERT OR IGNORE INTO apuntes_etiquetas (apunte_id, etiqueta_id) VALUES (?, ?)",
            (apunte_id, etiqueta_id),
        )


def etiquetas_del_apunte(conexion: sqlite3.Connection, apunte_id: int) -> List[str]:
    filas = conexion.execute(
        """
        SELECT e.nombre FROM etiquetas e
        JOIN apuntes_etiquetas ae ON ae.etiqueta_id = e.id
        WHERE ae.apunte_id = ?
        ORDER BY e.nombre
        """,
        (apunte_id,),
    ).fetchall()
    return [fila["nombre"] for fila in filas]


def todas_las_etiquetas(conexion: sqlite3.Connection) -> List[str]:
    """Etiquetas que siguen asociadas a al menos un apunte."""
    filas = conexion.execute(
        """
        SELECT DISTINCT e.nombre FROM etiquetas e
        JOIN apuntes_etiquetas ae ON ae.etiqueta_id = e.id
        ORDER BY e.nombre
        """
    ).fetchall()
    return [fila["nombre"] for fila in filas]


def limpiar_etiquetas_sin_uso(conexion: sqlite3.Connection) -> None:
    conexion.execute("DELETE FROM etiquetas WHERE id NOT IN (SELECT etiqueta_id FROM apuntes_etiquetas)")


def todas_las_asignaturas(conexion: sqlite3.Connection) -> List[str]:
    filas = conexion.execute(
        "SELECT DISTINCT asignatura FROM apuntes WHERE asignatura != '' ORDER BY asignatura"
    ).fetchall()
    return [fila["asignatura"] for fila in filas]


# ---------------------------------------------------------------------------
# Apuntes
# ---------------------------------------------------------------------------

def crear_apunte(
    conexion: sqlite3.Connection,
    titulo: str,
    contenido: str = "",
    asignatura: str = "",
    etiquetas: Optional[List[str]] = None,
) -> int:
    fecha = ahora()
    cursor = conexion.execute(
        "INSERT INTO apuntes (titulo, contenido, asignatura, creado, modificado) "
        "VALUES (?, ?, ?, ?, ?)",
        (titulo, contenido, asignatura, fecha, fecha),
    )
    apunte_id = cursor.lastrowid
    if etiquetas:
        asignar_etiquetas(conexion, apunte_id, etiquetas)
    try:
        conexion.commit()
    except sqlite3.Error as error:
        conexion.rollback()
        raise ApuncliError(f"No se pudo crear el apunte: {error}") from error
    return apunte_id


def obtener_apunte(conexion: sqlite3.Connection, apunte_id: int) -> Optional[sqlite3.Row]:
    return conexion.execute(
        "SELECT * FROM apuntes WHERE id = ?", (apunte_id,)
    ).fetchone()


def editar_apunte(
    conexion: sqlite3.Connection,
    apunte_id: int,
    titulo: Optional[str] = None,
    contenido: Optional[str] = None,
    asignatura: Optional[str] = None,
    etiquetas: Optional[List[str]] = None,
) -> None:
    actual = obtener_apunte(conexion, apunte_id)
    if actual is None:
        return
    conexion.execute(
        "UPDATE apuntes SET titulo = ?, contenido = ?, asignatura = ?, modificado = ? "
        "WHERE id = ?",
        (
            titulo if titulo is not None else actual["titulo"],
            contenido if contenido is not None else actual["contenido"],
            asignatura if asignatura is not None else actual["asignatura"],
            ahora(),
            apunte_id,
        ),
    )
    if etiquetas is not None:
        asignar_etiquetas(conexion, apunte_id, etiquetas)
        limpiar_etiquetas_sin_uso(conexion)
    conexion.commit()


def borrar_apunte(conexion: sqlite3.Connection, apunte_id: int) -> bool:
    cursor = conexion.execute("DELETE FROM apuntes WHERE id = ?", (apunte_id,))
    limpiar_etiquetas_sin_uso(conexion)
    conexion.commit()
    return cursor.rowcount > 0


def listar_apuntes(
    conexion: sqlite3.Connection,
    asignatura: Optional[str] = None,
    etiqueta: Optional[str] = None,
) -> List[sqlite3.Row]:
    sql = "SELECT DISTINCT a.* FROM apuntes a"
    condiciones = []
    parametros: list = []
    if etiqueta:
        sql += " JOIN apuntes_etiquetas ae ON ae.apunte_id = a.id " \
               "JOIN etiquetas e ON e.id = ae.etiqueta_id"
        condiciones.append("e.nombre = ?")
        parametros.append(etiqueta.strip().lower())
    if asignatura:
        condiciones.append("a.asignatura = ?")
        parametros.append(asignatura)
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += " ORDER BY a.id DESC"
    return conexion.execute(sql, parametros).fetchall()


def buscar_apuntes(conexion: sqlite3.Connection, consulta: str) -> List[sqlite3.Row]:
    """Busca por texto. Usa FTS5 si está disponible y no lanza errores."""
    if FTS5_DISPONIBLE:
        try:
            filas = conexion.execute(
                """
                SELECT a.* FROM apuntes_busca b
                JOIN apuntes a ON a.id = b.rowid
                WHERE apuntes_busca MATCH ?
                ORDER BY rank
                """,
                (consulta,),
            ).fetchall()
            return filas
        except sqlite3.OperationalError:
            pass  # consulta no válida para FTS: se cae al modo LIKE
    patron = f"%{consulta}%"
    return conexion.execute(
        "SELECT * FROM apuntes WHERE titulo LIKE ? OR contenido LIKE ? ORDER BY id DESC",
        (patron, patron),
    ).fetchall()


def marcar_repasado(conexion: sqlite3.Connection, apunte_id: int) -> None:
    conexion.execute(
        "UPDATE apuntes SET veces_repasado = veces_repasado + 1 WHERE id = ?",
        (apunte_id,),
    )
    conexion.commit()


# ---------------------------------------------------------------------------
# Recursos (enlaces y ficheros adjuntos a un apunte)
# ---------------------------------------------------------------------------

def adjuntar_recurso(conexion: sqlite3.Connection, apunte_id: int,
                     url: str, nombre: str = "") -> int:
    cursor = conexion.execute(
        "INSERT INTO recursos (apunte_id, nombre, url, creado) VALUES (?, ?, ?, ?)",
        (apunte_id, nombre.strip(), url.strip(), ahora()),
    )
    conexion.commit()
    return cursor.lastrowid


def recursos_del_apunte(conexion: sqlite3.Connection, apunte_id: int) -> List[sqlite3.Row]:
    return conexion.execute(
        "SELECT * FROM recursos WHERE apunte_id = ? ORDER BY id", (apunte_id,)
    ).fetchall()


def recurso(conexion: sqlite3.Connection, recurso_id: int) -> Optional[sqlite3.Row]:
    return conexion.execute("SELECT * FROM recursos WHERE id = ?", (recurso_id,)).fetchone()


def borrar_recurso(conexion: sqlite3.Connection, recurso_id: int) -> bool:
    cursor = conexion.execute("DELETE FROM recursos WHERE id = ?", (recurso_id,))
    conexion.commit()
    return cursor.rowcount > 0


def recursos_de_apuntes(conexion: sqlite3.Connection,
                        apunte_ids: List[int]) -> List[sqlite3.Row]:
    if not apunte_ids:
        return []
    marcas = ",".join("?" for _ in apunte_ids)
    return conexion.execute(
        f"SELECT * FROM recursos WHERE apunte_id IN ({marcas}) ORDER BY id",
        apunte_ids,
    ).fetchall()


def estadisticas(conexion: sqlite3.Connection) -> dict:
    total = conexion.execute("SELECT COUNT(*) AS n FROM apuntes").fetchone()["n"]
    sin_repasar = conexion.execute(
        "SELECT COUNT(*) AS n FROM apuntes WHERE veces_repasado = 0"
    ).fetchone()["n"]
    repasados = conexion.execute(
        "SELECT COUNT(*) AS n FROM apuntes WHERE veces_repasado > 0"
    ).fetchone()["n"]
    palabras = conexion.execute(
        "SELECT COALESCE(SUM(LENGTH(contenido) - LENGTH(REPLACE(contenido, ' ', '')) + 1), 0) AS n "
        "FROM apuntes WHERE contenido != ''"
    ).fetchone()["n"]
    por_asignatura = conexion.execute(
        "SELECT CASE WHEN asignatura = '' THEN '(sin asignatura)' ELSE asignatura END AS asignatura, "
        "COUNT(*) AS n FROM apuntes GROUP BY asignatura ORDER BY n DESC"
    ).fetchall()
    return {
        "total": total,
        "sin_repasar": sin_repasar,
        "repasados": repasados,
        "palabras": palabras,
        "por_asignatura": [(fila["asignatura"], fila["n"]) for fila in por_asignatura],
    }
