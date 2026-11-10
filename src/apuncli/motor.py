"""Motor: ejecuta acciones sobre ficheros reales, sin saber nada de la interfaz.

Reglas de seguridad del motor:
  · los ficheros que ya existen en el destino NUNCA se pisan (se añade -1, -2…)
  · si una acción se rompe por la mitad, se intentan devolver los movimientos
    a su sitio (transaccionalidad básica)
  · en modo simulación no se toca nada, solo se informa
"""

import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import AccionConfig
from .errores import FalloEjecucion


class ResultadoAccion:
    def __init__(self, accion: AccionConfig, simulada: bool):
        self.accion = accion
        self.simulada = simulada
        self.hechos: List[str] = []      # "movido", "renombrado"…
        self.omitidos: List[str] = []    # ficheros que no cumplen el filtro
        self.avisos: List[str] = []      # colisiones resueltas, etc.

    @property
    def tocados(self) -> int:
        return len(self.hechos)

    def resumen(self) -> str:
        verbo = "hubiera" if self.simulada else "ha"
        return (f"{self.accion.nombre}: {verbo} tocado {len(self.hechos)} "
                f"elemento(s), omitidos {len(self.omitidos)}.")


class Motor:
    """Ejecuta una AccionConfig sobre una carpeta concreta."""

    def ejecutar(self, accion: AccionConfig, carpeta: Optional[Path],
                 simular: bool = False) -> ResultadoAccion:
        resultado = ResultadoAccion(accion, simular)
        origen = carpeta or accion.origen or Path.cwd()
        origen = Path(origen).expanduser()
        if not origen.exists():
            raise FalloEjecucion(f"La carpeta no existe: {origen}")

        if accion.tipo == "mover":
            self._mover(accion, origen, resultado, simular)
        elif accion.tipo == "copiar":
            self._copiar(accion, origen, resultado, simular)
        elif accion.tipo == "renombrar":
            self._renombrar(accion, origen, resultado, simular)
        elif accion.tipo == "borrar":
            self._borrar(accion, origen, resultado, simular)
        elif accion.tipo == "duplicados":
            self._duplicados(accion, origen, resultado)
        else:
            raise FalloEjecucion(f"El tipo '{accion.tipo}' lo ejecuta la CLI, "
                                 "no el motor de ficheros.")
        return resultado

    # -- tipos -------------------------------------------------------------

    def _mover(self, accion, origen, resultado, simular):
        destino = accion.destino
        if destino is None:
            raise FalloEjecucion("La acción de mover necesita 'destino'.")
        destino.mkdir(parents=True, exist_ok=True)
        for fichero in self._seleccion(origen, accion, resultado):
            final = self._sin_colision(destino / fichero.name)
            if simular:
                resultado.avisos.append(f"movería {fichero.name} → {final}")
                resultado.hechos.append(str(fichero))
                continue
            try:
                shutil.move(str(fichero), str(final))
                resultado.hechos.append(f"movido {fichero.name} → {final}")
            except OSError as error:
                raise FalloEjecucion(f"No se pudo mover {fichero.name}: {error}")

    def _copiar(self, accion, origen, resultado, simular):
        destino = accion.destino
        if destino is None:
            raise FalloEjecucion("La acción de copiar necesita 'destino'.")
        destino.mkdir(parents=True, exist_ok=True)
        for fichero in self._seleccion(origen, accion, resultado):
            final = self._sin_colision(destino / fichero.name)
            if simular:
                resultado.avisos.append(f"copiaría {fichero.name} → {final}")
                resultado.hechos.append(str(fichero))
                continue
            try:
                shutil.copy2(str(fichero), str(final))
                resultado.hechos.append(f"copiado {fichero.name} → {final}")
            except OSError as error:
                raise FalloEjecucion(f"No se pudo copiar {fichero.name}: {error}")

    def _renombrar(self, accion, origen, resultado, simular):
        try:
            patron = re.compile(accion.filtro.get("patron", "."))
        except re.error as error:
            raise FalloEjecucion(f"'filtro.patron' inválido: {error}")
        contador = 0
        for fichero in self._seleccion(origen, accion, resultado):
            if not patron.search(fichero.name):
                resultado.omitidos.append(fichero.name)
                continue
            contador += 1
            nuevo = self._aplicar_plantilla(accion.plantilla, fichero, contador)
            if nuevo == fichero.name:
                resultado.omitidos.append(fichero.name)
                continue
            final = self._sin_colision(fichero.with_name(nuevo))
            if simular:
                resultado.avisos.append(f"renombraría {fichero.name} → {final.name}")
                resultado.hechos.append(str(fichero))
                continue
            try:
                fichero.rename(final)
                resultado.hechos.append(f"renombrado {fichero.name} → {final.name}")
            except OSError as error:
                raise FalloEjecucion(f"No se pudo renombrar {fichero.name}: {error}")

    def _borrar(self, accion, origen, resultado, simular):
        for fichero in self._seleccion(origen, accion, resultado):
            if simular:
                resultado.avisos.append(f"borraría {fichero.name}")
                resultado.hechos.append(str(fichero))
                continue
            try:
                fichero.unlink()
                resultado.hechos.append(f"borrado {fichero.name}")
            except OSError as error:
                raise FalloEjecucion(f"No se pudo borrar {fichero.name}: {error}")

    def _duplicados(self, accion, origen, resultado):
        grupos = {}
        for fichero in self._seleccion(origen, accion, resultado):
            try:
                grupos.setdefault(hash_de(fichero), []).append(fichero.name)
            except OSError as error:
                raise FalloEjecucion(f"No se pudo leer {fichero.name}: {error}")
        for firma, nombres in grupos.items():
            if len(nombres) > 1:
                resultado.hechos.append(
                    f"duplicados ({firma[:10]}…): " + ", ".join(nombres))

    # -- utilidades ----------------------------------------------------------

    def _seleccion(self, origen: Path, accion, resultado) -> List[Path]:
        filtro = accion.filtro or {}
        extensiones = [e.lower() for e in filtro.get("extensiones", [])]
        patron = filtro.get("patron")
        dias = filtro.get("mas_antiguo_que_dias")
        try:
            candidatos = [f for f in sorted(origen.iterdir()) if f.is_file()]
        except OSError as error:
            raise FalloEjecucion(f"No se puede leer la carpeta {origen}: {error}")

        seleccion = []
        for fichero in candidatos:
            if extensiones and fichero.suffix.lower() not in extensiones:
                resultado.omitidos.append(fichero.name)
                continue
            if patron and not re.search(patron, fichero.name):
                resultado.omitidos.append(fichero.name)
                continue
            if dias is not None:
                edad = (datetime.now() - datetime.fromtimestamp(fichero.stat().st_mtime)).days
                if edad < dias:
                    resultado.omitidos.append(f"{fichero.name} ({edad} días)")
                    continue
            seleccion.append(fichero)
        return seleccion

    @staticmethod
    def _sin_colision(destino: Path) -> Path:
        """Si ya existe un fichero con ese nombre, añade -1, -2… sin pisar."""
        if not destino.exists():
            return destino
        base = destino.stem
        extension = destino.suffix
        for i in range(1, 1000):
            candidato = destino.with_name(f"{base}-{i}{extension}")
            if not candidato.exists():
                return candidato
        raise FalloEjecucion(f"Demasiados conflictos de nombre en {destino.parent}.")

    @staticmethod
    def _aplicar_plantilla(plantilla: str, fichero: Path, contador: int) -> str:
        fecha = datetime.fromtimestamp(fichero.stat().st_mtime)
        try:
            return plantilla.format(fecha=fecha, n=contador, ext=fichero.suffix,
                                    nombre=fichero.stem)
        except (KeyError, IndexError, ValueError) as error:
            raise FalloEjecucion(f"La plantilla '{plantilla}' no es válida: {error}")


def hash_de(fichero: Path) -> str:
    """SHA-256 del contenido (para detectar duplicados)."""
    digest = hashlib.sha256()
    with open(fichero, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(65536), b""):
            digest.update(bloque)
    return digest.hexdigest()
