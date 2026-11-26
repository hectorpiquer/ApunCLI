"""Menú Organizador: ficheros del sistema, con flechas y simulación siempre.

La otra cara de apuncli: en vez de estudiar, organizar. Reutiliza el motor y
la capa de recursos; nunca toca fuera de la carpeta elegida.
"""

from pathlib import Path
from typing import Optional

from . import organizador, ui
from .errores import ApuncliError
from .ui import SeleccionCancelada

OPCIONES = [
    ("🗂️   Explorar una carpeta", "explorar"),
    ("📄  Crear un documento nuevo", "crear"),
    ("📥  Ordenar descargas por tipo", "ordenar"),
    ("👯  Buscar duplicados", "duplicados"),
    ("🧮  Uso de espacio (subcarpetas)", "espacio"),
    ("🧹  Limpiar temporales viejos", "temporales"),
    ("🪄  Renombrar un fichero con IA", "renombrar-ia"),
    ("🗃️   Clasificar una carpeta con IA", "clasificar-ia"),
    ("↩️   Volver al selector de modo", "volver"),
    ("🚪  Salir del programa", "salir"),
]


def _carpeta_inicial() -> Path:
    """Dónde empezar: la última carpeta usada o el home."""
    from . import ajustes
    recordada = ajustes.leer_ajustes().get("ultima_carpeta")
    if recordada:
        ruta = Path(recordada).expanduser()
        if ruta.is_dir():
            return ruta
    return Path.home()


def _recordar(carpeta: Path) -> None:
    from . import ajustes
    try:
        ajustes.guardar_ajustes(ultima_carpeta=str(carpeta))
    except ApuncliError:
        pass


def menu_organizador() -> int:
    print(ui.destacado("\n🗂️  apuncli — modo organizador"))
    print(ui.tenue("   (↑/↓ mover · Enter elegir · q volver; simulo antes de tocar)"))
    while True:
        try:
            indice = ui.seleccionar("¿Qué organizamos?", [a for a, _ in OPCIONES])
        except SeleccionCancelada:
            print("\n¡Hasta la próxima!")
            return 0
        accion = OPCIONES[indice][1]
        if accion == "salir":
            print("\n¡Hasta la próxima!")
            return 0
        if accion == "volver":
            return 2
        try:
            _ejecutar(accion)
        except ApuncliError as error:
            print(f"\nerror: {error}")
        except SeleccionCancelada:
            pass
        except EOFError:
            print("\n(entrada agotada, saliéndo)")
            return 0


# ---------------------------------------------------------------------------

def _preguntar_carpeta(mensaje: str = "¿Qué carpeta?") -> Path:
    texto = ui.pedir_texto(f"{mensaje} (Enter = {_carpeta_inicial()}): ").strip()
    ruta = Path(texto or _carpeta_inicial()).expanduser().resolve()
    if not ruta.is_dir():
        raise ApuncliError(f"No existe la carpeta: {ruta}")
    return ruta


def _ejecutar(accion: str) -> None:
    if accion == "explorar":
        explorar(_preguntar_carpeta())
    elif accion == "crear":
        crear()
    elif accion == "ordenar":
        ordenar()
    elif accion == "duplicados":
        duplicados()
    elif accion == "espacio":
        espacio()
    elif accion == "temporales":
        temporales()
    elif accion == "renombrar-ia":
        renombrar_ia()
    elif accion == "clasificar-ia":
        clasificar_ia()


# -- explorador --------------------------------------------------------------

ACCIONES_FICHERO = [
    ("↩️  Volver al listado", "volver"),
    ("📂 Entrar (solo carpetas)", "entrar"),
    ("🚀 Abrir con su aplicación", "abrir"),
    ("🪪 Ver información", "info"),
    ("🏷️  Renombrar con su fecha", "fecha"),
    ("🪄 renombrar con IA", "ia"),
    ("📄 Crear documento aquí", "crear"),
]


def explorar(carpeta: Path) -> None:
    while True:
        _recordar(carpeta)
        hijos = organizador.listar_contenido(carpeta)
        etiquetas = [
            ("📁 " if h.is_dir() else "   ") + h.name
            for h in hijos
        ] + [f"⬆️  Subir de nivel ({carpeta.name or carpeta})",
             "↩️  Salir del explorador"]
        try:
            indice = ui.seleccionar(f"📂 {carpeta}", etiquetas)
        except SeleccionCancelada:
            return
        if indice == len(etiquetas) - 1:        # salir
            return
        if indice == len(etiquetas) - 2:        # subir
            if carpeta.parent != carpeta:
                carpeta = carpeta.parent
            continue
        ruta = hijos[indice]
        if ruta.is_dir():
            carpeta = ruta
            continue
        _menu_fichero(carpeta, ruta)


def _menu_fichero(carpeta: Path, ruta: Path) -> None:
    opciones = list(ACCIONES_FICHERO)
    if ruta.is_dir():
        opciones = [opciones[0], opciones[2], opciones[3], opciones[5], opciones[6], opciones[1]]
    try:
        indice = ui.seleccionar(f"Qué hago con {ruta.name}:", [a for a, _ in opciones])
    except SeleccionCancelada:
        return
    accion = opciones[indice][1]
    if accion == "volver":
        return
    if accion == "entrar" and ruta.is_dir():
        explorar(ruta); return
    if accion == "abrir":
        organizador.abrir(ruta); print("✔ abierto")
    elif accion == "info":
        print(organizador.info_fichero(ruta))
    elif accion == "fecha":
        if ui.confirmar(f"¿Renombrar {ruta.name} con su fecha?"):
            nueva = organizador.renombrar_por_fecha(ruta)
            print(f"✔ {ruta.name} → {nueva.name}")
    elif accion == "ia":
        renombrar_ia(ruta)
    elif accion == "crear":
        crear(ruta if ruta.is_dir() else carpeta)


# -- crear / ordenar / duplicados / espacio / temporales ---------------------

def crear(carpeta: Optional[Path] = None) -> None:
    carpeta = carpeta or _preguntar_carpeta()
    tipos = sorted(organizador.PLANTILLAS)
    try:
        indice = ui.seleccionar("¿Qué tipo de documento?", tipos)
    except SeleccionCancelada:
        return
    nombre = ui.pedir_texto("Nombre del documento: ").strip()
    if not nombre:
        return
    destino = organizador.crear_documento(carpeta, nombre, tipos[indice])
    print(f"✔ Creado: {destino}")
    if ui.confirmar("¿Abrirlo ahora?"):
        organizador.abrir(destino)


def ordenar() -> None:
    carpeta = _preguntar_carpeta("¿Qué carpeta ordeno? (p. ej. tus descargas)")
    nombres = list(organizador.CATEGORIAS)
    try:
        indice = ui.seleccionar("¿Qué tipo muevo?", nombres + ["🌈 todo"])
    except SeleccionCancelada:
        return
    categorias = nombres if indice == len(nombres) else [nombres[indice]]
    raiz = _preguntar_carpeta("¿Dónde los muevo? (carpeta raíz)")
    plan = organizador.plan_ordenar(carpeta, categorias, raiz)
    print(f"\nPlan ({len(plan)} ficheros):\n{organizador.informe_plan(plan[:20])}")
    if len(plan) > 20:
        print(f"  … y {len(plan) - 20} más")
    if not plan:
        return
    if not ui.confirmar("¿Ejecutar el plan?"):
        print("Cancelado.")
        return
    print(f"✔ {organizador.ejecutar_plan_ordenar(plan)} ficheros movidos.")


def duplicados() -> None:
    carpeta = _preguntar_carpeta()
    grupos = organizador.grupos_duplicados(carpeta)
    if not grupos:
        print("Sin duplicados en " + str(carpeta))
        return
    etiquetas = [f"{len(lista)} × {lista[0].name}…  ({firma[:10]}…)"
                 for firma, lista in grupos]
    while True:
        try:
            indice = ui.seleccionar(f"{len(grupos)} grupo(s) de duplicados",
                                   etiquetas + ["↩️  Volver"])
        except SeleccionCancelada:
            return
        if indice >= len(grupos):
            return
        grupo = grupos[indice][1]
        print("\n" + "\n".join(
            f"  {f.name}  ({organizador.tamano_legible(f.stat().st_size)})"
            for f in grupo))
        try:
            accion = ui.seleccionar("¿Qué hago con el grupo?",
                                    ["🗑️  Borrar todos menos el más antiguo",
                                     "↩️  Volver a la lista"])
        except (SeleccionCancelada, IndexError):
            continue
        if accion == 0:
            if not ui.confirmar(f"¿Borrar {len(grupo) - 1} ficheros duplicados?"):
                continue
            borrados = organizador.borrar_menos_el_ancien(grupo)
            print(f"✔ Borrados: {', '.join(borrados)}")
            grupos = organizador.grupos_duplicados(carpeta)
            etiquetas = [f"{len(l)} × {l[0].name}…  ({h[:10]}…)"
                         for h, l in grupos]
            if not grupos:
                print("Ya no quedan duplicados."); return


def espacio() -> None:
    carpeta = _preguntar_carpeta()
    resultados = organizador.uso_espacio(carpeta, 2)
    ui.titulo_de_seccion(f"Uso de espacio en {carpeta}")
    if not resultados:
        print(ui.tenue("  (sin subcarpetas)")); return
    for ruta, bytes_ in resultados[:15]:
        print(f"  {organizador.tamano_legible(bytes_):>10}  {ruta}")


def temporales() -> None:
    carpeta = _preguntar_carpeta()
    viejos = organizador.temporales_viejos(carpeta, 30)
    if not viejos:
        print("Sin temporales de más de 30 días.")
        return
    print("\n".join(f"  {f.name}" for f in viejos[:30]))
    if len(viejos) > 30:
        print(f"  … y {len(viejos) - 30} más")
    if ui.confirmar(f"¿Borrar los {len(viejos)} temporales viejos?"):
        borrados = 0
        for f in viejos:
            try:
                f.unlink(); borrados += 1
            except OSError:
                continue
        print(f"✔ {borrados} borrados.")


# -- IA ----------------------------------------------------------------------

def renombrar_ia(ruta: Optional[Path] = None) -> None:
    from . import ai
    if ruta is None:
        carpeta = _preguntar_carpeta()
        ficheros = [h for h in organizador.listar_contenido(carpeta) if h.is_file()]
        if not ficheros:
            raise ApuncliError("No hay ficheros en esa carpeta.")
        try:
            indice = ui.seleccionar("¿Qué fichero renombró la IA?",
                                   [f.name for f in ficheros])
        except SeleccionCancelada:
            return
        ruta = ficheros[indice]
    if ruta.is_dir():
        raise ApuncliError("Es una carpeta; esto es para ficheros sueltos.")
    try:
        texto = ruta.read_text(encoding="utf-8", errors="replace")[:1500]
    except OSError as error:
        raise ApuncliError(f"No puedo leer el fichero: {error}")
    if not texto.strip():
        raise ApuncliError("El fichero está vacío; no de qué saca un nombre.")
    print(ui.tenue("Consultando al modelo…"))
    try:
        propuesta = ai.accion_renombrar(texto, ruta.name, ai.ProveedorIA())
    except Exception as error:                       # SinRedError y compañía
        raise ApuncliError(str(error))
    limpia = ai.a_nombre_seguro(propuesta, ruta.suffix)
    print(f"El modelo propone: {ui.destacado(limpia)}")
    if limpia == ruta.name:
        print("Ya se llama así."); return
    if not ui.confirmar("¿Renombrar?"):
        return
    destino = ruta.with_name(limpia)
    contador = 1
    while destino.exists():
        destino = destino.with_name(f"{Path(limpia).stem}-{contador}{Path(limpia).suffix}")
        contador += 1
    try:
        ruta.rename(destino)
        print(f"✔ {ruta.name} → {destino.name}")
    except OSError as error:
        raise ApuncliError(f"No se pudo renombrar: {error}")


def clasificar_ia(carpeta: Optional[Path] = None) -> None:
    from . import ai, ajustes
    carpeta = carpeta or _preguntar_carpeta()
    categorias = ai.categorias_configuradas()
    ficheros = [h for h in organizador.listar_contenido(carpeta) if h.is_file()]
    if not ficheros:
        raise ApuncliError("No hay ficheros que clasificar.")
    movidos = 0
    for ruta in ficheros:
        try:
            texto = ruta.read_text(encoding="utf-8", errors="replace")[:800]
            categoria = ai.accion_clasificar(texto, categorias, ai.ProveedorIA())
        except Exception:
            categoria = "sin-clasificar"
        destino_dir = carpeta / categoria
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / ruta.name
        contador = 1
        while destino.exists():
            destino = destino_dir / f"{ruta.stem}-{contador}{ruta.suffix}"
            contador += 1
        try:
            ruta.rename(destino)
            movidos += 1
            print(f"  {ruta.name} → {categoria}/")
        except OSError:
            continue
    print(f"✔ {movidos} ficheros clasificados.")
