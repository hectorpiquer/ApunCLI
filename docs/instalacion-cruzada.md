# Instalación cruzada · checklist para quien prueba la CLI

Sigue **solo esta hoja y el README del repo**; si algo no está claro aquí,
esa es la primera incidencia a reportar. No hace falta saber nada del proyecto.

Repositorio: https://github.com/hectorpiquer/ApunCLI — usa la **última release** (en la página Releases).

## 1 · Instalar (necesitas uv o pipx; o pip)

```bash
uv tool install git+https://github.com/hectorpiquer/ApunCLI.git@<LA-ULTIMA-VERSIÓN>
# o:  pipx install git+https://github.com/hectorpiquer/ApunCLI.git@<LA-ULTIMA-VERSIÓN>
# o:  pip install --user git+https://github.com/hectorpiquer/ApunCLI.git@<LA-ULTIMA-VERSIÓN>
```

## 2 · Probar que existe

```bash
apuncli --help      # ayuda
apuncli version     # debe decir la versión (1.0.4)
```

## 3 · Jugar con la demo

```bash
apuncli demo        # crea 4 apuntes de ejemplo (etiqueta [demo])
apuncli listar      # los ves
apuncli buscar pila # busca (funciona aunque escribas sin tildes)
apuncli repasar -n 2
```

## 4 · Acciones externas (la parte del curso)

```bash
cp acciones.json ~/pruebas-cruzadas/   # copia el ejemplo del repo
cd ~/pruebas-cruzadas
apuncli validar                        # debe decir OK
apuncli ejecutar respaldo-pdfs --simular   # enseña qué haría, sin tocar
apuncli ejecutar ordenar-descargas --simular ~/Descargas
```

## 5 · IA (opcional; si estás en el centro)

```bash
apuncli comprobar-ia            # ¿está disponible el modelo?
apuncli ejecutar resumir-ia 1   # resume el apunte 1 (necesita ia.env del centro)
```
Sin IA, debe salir un aviso claro y **todo lo demás tiene que seguir
funcionando**. Eso también es una prueba: si revienta, es un fallo.

## 6 · Si algo falla o no se entiende → issue

Crea la issue en GitHub con esta plantilla (o `gh issue create`):

```markdown
### Qué hice
(el comando exacto, en orden, con tu sistema: Ubuntu 24 / Windows 11 / macOS…)

### Qué esperaba
(según el README/checklist)

### Qué pasó
(copia la salida o el mensaje de error)

### Notas
(ruta, versión de Python, si estabas dentro/fuera del centro…)
```

## 7 · Desinstalar

```bash
uv tool uninstall apuncli   # o: pipx uninstall apuncli
```

— El que reporta se lleva la gloria; el que arregla, un test. Los dos puntos.
