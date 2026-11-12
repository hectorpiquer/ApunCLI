# ADR-0002 · Capa IA opcional con modo sin red

**Fecha**: 2026-11-11 · **Estado**: Aceptado

## Contexto

El proyecto pide acciones con IA (resumir apuntes, generar preguntas de examen)
usando los modelos del centro, sin filtrar claves y sin dejar la herramienta
inutilizable cuando no hay red.

## Decisión

1. **Proveedor OpenAI-compatible** (`POST /v1/chat/completions`) con URL configurable:
   funciona con Ollama del centro (`http://<ip-del-centro>:11434/v1`), con Ollama local
   y con cualquier API OpenAI-compatible. Implementado con `urllib` de la stdlib:
   cero dependencias.
2. **La clave jamás en el repo**: se lee de `ia.env`/`.env` (ambos en `.gitignore`,
   con `.env.example` documentado) o de variables de entorno. El fichero real solo
   existe en el portátil del usuario.
3. **Todo o nada, nunca traceback**: si falta la clave, el modelo o la conexión,
   la capa lanza `SinRedError` y la CLI lo explica en una frase. El resto de
   comandos y acciones siguen funcionando igual (la IA es opcional por diseño:
   el test y el repaso locales no la necesitan).
4. **`apuncli comprobar-ia`** prueba la conexión real y explica qué falta; es el
   diagnóstico para el aula ("¿por qué no va lo de la IA?").

## Consecuencias

- ✅ En casa sin red: las 2 acciones IA avisan y todo lo demás funciona.
- ✅ Historial git limpio: ninguna clave ha entrado nunca (verificado con grep).
- ⚠️ El formato de las preguntas generadas se normaliza en `ai.py` (guiones y `=>`)
  para que entre en `apuncli test` sin tocar nada más.
- ⚠️ Respuestas lentas (modelos del centro): 60 s de máximo por petición, con
  mensaje claro si se agotan.
