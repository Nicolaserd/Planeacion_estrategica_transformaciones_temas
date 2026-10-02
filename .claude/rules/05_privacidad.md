# 05 · Privacidad y seguridad (Ley 1581 de 2012)

## Qué datos hay y dónde

| Archivo | Datos personales | Uso |
|---|---|---|
| `data/raw/*.xlsx` (Forms) | Sí: Nombre y Correo | Solo lectura, local |
| `data/interim/<slug>/encuesta.parquet` | Sí: todas las columnas de la encuesta | Local; alimenta el Excel 2 |
| `data/interim/<slug>/comentarios.parquet` | No: texto anonimizado | Es lo único que leen Claude y Jev |
| `data/interim/<slug>/clasificacion*.parquet` | No | Probabilidades de Jev por comentario |
| `outputs/**/Clasificacion_*.xlsx` | **Sí: Nombre, Correo y comentario original** (decisión de Nicolás) | **Solo uso local**: nunca se sube ni se comparte fuera del equipo |
| `outputs/**/Clasificacion_*_anonimizado.xlsx` | No: "[NOMBRE]", "[CORREO]" y comentario anonimizado | Se publica en el repositorio |
| `outputs/**/Temas_*.xlsx` | No (comentarios anonimizados) | Se publica en el repositorio |
| `cache/jev_respuestas.jsonl` | No (texto anonimizado) | Caché de Jev |
| `.env` | Clave de TypeSafe | Nunca se imprime ni se copia |

El repositorio de GitHub es **público**. `.gitignore` excluye:
- `.env`, `.venv/`, `data/` y `cache/`;
- los Excel de clasificación originales;
- cualquier `Experiencia*.xlsx` de Forms;
- el PDF del Plan Estratégico.

De `outputs/` solo se suben los Excel de temas y las copias `…_anonimizado.xlsx`.

## Reglas

- **A Jev y a Claude solo llega el texto anonimizado.** Nicolás autorizó el 2026-10-01 que ese texto se procesara con Anthropic (Claude) y TypeSafe (Jev).
- **Nunca imprimas Nombre ni Correo en el chat**, ni en bitácoras o reportes. Para referirte a una respuesta, usa el `ID` o el `id_com`, por ejemplo `123-P1`.
- **Las columnas `Nombre` y `Correo` solo se leen** para armar el Excel 2 y para detectar nombres dentro de los comentarios (`tokens_nombres`). Esos tokens tampoco se imprimen.
- **Clave de TypeSafe:** `.env`, variable `plan_estrategico` o `TYPESAFE_API_KEY`. Nunca la muestres, ni siquiera en parte.
- **No borres archivos sin confirmarlo con Nicolás.**

## Anonimización (`src/f03_limpieza_anonimizacion.py`)

Antes de que nadie lea los comentarios, se reemplaza:

| Patrón | Reemplazo |
|---|---|
| Correos electrónicos | `[CORREO]` |
| Enlaces (`http…`, `www.…`) | `[URL]` |
| Celulares (`3xx xxx xxxx`, con o sin +57) y fijos | `[TELEFONO]` |
| Secuencias de 6 a 11 dígitos (cédulas, códigos), salvo montos con `$`, "pesos" o "mil" | `[NUMERO_ID]` |
| Título + nombre con mayúscula (profesor, docente, ingeniera, Dr., señor, coordinador, decano, rector…) | `título [PERSONA]` |

- Cuántos reemplazos hubo queda en `ficha.yaml` (`anonimizacion`) y en la bitácora.
- `preparar` marca con `<<token de nombre>>` los comentarios que contienen una palabra de la columna Nombre. **Revísalos al leer:** si es el nombre de una persona, no lo copies en los temas, los ejemplos ni los reportes.

## Exclusiones antes de Jev

`motivo_exclusion` saca del análisis:
- las respuestas vacías;
- las que son solo signos o números;
- las de menos de 3 letras;
- las "no respuestas" exactas: "ninguno", "nada", "no aplica", "todo bien", "ok", "gracias" y variantes con errores.

En el Excel 2 aparecen como "(sin comentario)" o "(sin contenido: motivo)".
