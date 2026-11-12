---
description: Añade una acción nueva a acciones.json con todos los pasos del proyecto.
---

# /nueva-accion $ARGUMENTS

Añade una acción nueva (descrita por el usuario) siguiendo SIEMPRE estos pasos:

1. Pregúntame el tipo si no está claro (mover/renombrar/copiar/borrar/duplicados/resumir-ia/generar-preguntas-ia/generar-temario).
2. Añade la entrada a `acciones.json` respetando las reglas del skill acciones-json.
3. Ejecuta `python3 -m apuncli validar` (con PYTHONPATH=src) para comprobar el JSON.
4. Si el tipo es nuevo para el motor: escribe primero el test en `tests/test_acciones.py`
   (carpeta temporal, incluye un caso feo) y luego la implementación en `motor.py`.
5. Actualiza el README (sección "acciones") con un ejemplo de uso con `--simular`.
6. Dime el commit sugerido. No hagas commit tú.
