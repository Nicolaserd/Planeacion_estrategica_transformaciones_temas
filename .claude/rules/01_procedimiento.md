# 01 · Procedimiento de un ejercicio

Un **ejercicio** es una transformación, en una unidad regional y unas fechas. Su identificador (slug) es `<unidad>_<fecha1>_a_<fechaN>_<transformación>`, por ejemplo `girardot_2026-09-07_a_2026-09-08_uc_digital`. Con una sola fecha queda, por ejemplo, `zipaquira_2026-08-31_uc_digital`.

## Entradas

| Dato | Ejemplo | Si falta |
|---|---|---|
| Archivo de origen (.xlsx de Forms) | `data/raw/experiencia_uc_para_la_vida.xlsx` | preguntar |
| Transformación (nombre de la sección del documento marco) | `UC para la Vida` | preguntar |
| Unidad regional | `Ubaté` | preguntar |
| Fechas de desarrollo (una o varias) | `2026-08-18 2026-08-19` | preguntar |

- **Documento marco**, la única fuente de las transformaciones: `contexto/Transformaciones_estrategicas_5_frentes.md`. Hay 5 transformaciones: UC Inteligente, UC Translocal, UC Digital, UC Emprendedora e Innovadora y UC para la Vida.
- **Archivos de Forms.** Hay uno por transformación en `data/raw/`. Sus nombres originales traen espacios raros (espacio duro `\xa0`), así que búscalos con `glob`, por ejemplo `*(UC DIGITAL)*.xlsx`, o cópialos con un nombre simple.
- **Fechas usadas hasta hoy:**

  | Unidad | Fechas |
  |---|---|
  | Ubaté | 18 y 19 ago 2026 |
  | Zipaquirá | 31 ago |
  | Girardot | 7 y 8 sep |
  | Soacha | 14 y 15 sep |
  | Chía | 21 y 22 sep |
  | Fusagasugá | 28 sep (sin procesar) |

## Pasos (con `.venv\Scripts\python.exe`)

### 1. Preparar
```
python src/ejercicio.py preparar --archivo <xlsx> --transformacion "<T>" --unidad "<U>" --fechas <F1> [<F2> ...]
```
El script:
- filtra la unidad, las fechas y la transformación. Si la columna Transformación viene vacía y el archivo es de un solo formulario, asume ese formulario;
- excluye las respuestas vacías y anonimiza el texto;
- aplica la regla de censo;
- crea `config/ejercicios/<slug>/ficha.yaml` y los archivos `data/interim/<slug>/encuesta.parquet` y `comentarios.parquet`;
- imprime los componentes de la transformación y los comentarios anonimizados (con `--silencioso` no los imprime).

Usa **solo las fechas que dio Nicolás**. Si el script reporta filas de la unidad en otras fechas (`fuera_de_fecha_no_incluidas`), menciónalas en el reporte, pero no las incluyas salvo que Nicolás lo pida. Si lo pide, repite el paso con `--incluir-ids <ID> ...`.

### 2. Definir los temas y codificar
Lee todos los comentarios y escribe `config/ejercicios/<slug>/temas.yaml` y `logs/<slug>/codificacion.jsonl`. Las reglas están en `02_temas.md`.

### 3. Validar
```
python src/ejercicio.py validar --ejercicio <slug>
```
Corrige hasta que pase. El script revisa:
- campos y componentes literales;
- máximo 10 temas y mínimos de comentarios;
- un solo tema para lo que está fuera de la transformación;
- solapamiento (Jaccard ≤ 0,5);
- que la codificación cubra exactamente los comentarios con contenido (N_s).

### 4. Clasificar con Jev
```
python src/ejercicio.py clasificar --ejercicio <slug>
```
Envía una pregunta sí/no (Noul) por tema, más `sin_contenido`, por cada texto único. Las respuestas se guardan en caché. Detalles en `03_jev.md`.

### 5. Revisar a Jev contra tu lectura
```
python scripts/revisar_jev.py <slug>
python scripts/revisar_jev.py <slug> --tema <id_tema>     # comentarios en desacuerdo
```
Si un tema sale INFLADO o SUBDETECTADO, corrige su redacción en `temas.yaml` y vuelve a los pasos 3 y 4. Si sale ALTO, infórmalo en el reporte.

### 6. Exportar
```
python src/ejercicio.py exportar --ejercicio <slug>
```
Genera los dos Excel en `outputs/<transformación>/`. El formato está en `04_salidas.md`. Si ya existían Excel de ese ejercicio con **otros temas**, respáldalos antes en `outputs/<transformación>/version_N/`.

### 7. Reportar a Nicolás
- la ruta de los dos archivos;
- los temas por componente, con n y %;
- los temas fuera de la transformación;
- los componentes sin comentarios;
- las filas fuera de fecha (ID y fecha) que no se incluyeron;
- los temas marcados como ALTO;
- el costo (está en la bitácora del ejercicio).

Reporta en "grupos" o "comentarios", nunca en "personas", y nunca incluyas Nombre ni Correo.

## Varios ejercicios a la vez

```
python scripts/lote.py validar    [filtro]
python scripts/lote.py clasificar [filtro]
python scripts/lote.py exportar   [filtro]
python scripts/lote.py verificar  [filtro]    # Excel: 1 hoja, una fila por respuesta, una columna por tema
python scripts/revisar_jev.py     [filtro]
```
`filtro` es cualquier parte del slug, por ejemplo `ubate`, `uc_digital` o `chia`. Para preparar varios ejercicios, repite el paso 1 en un ciclo con `--silencioso` y lee los comentarios desde `data/interim/<slug>/comentarios.parquet` (columna `comentario_anon`, filas con `excluido == 0`).

## Bitácora

- Cada subcomando escribe solo en `logs/<slug>/decisiones.md`.
- Agrega a mano, con `ejercicio.bitacora(slug, texto)`, cada decisión de Nicolás y cada cambio de redacción de un tema.
- Las decisiones que valen para todo el proyecto van en `logs/decisiones.md` y en `docs/historial.md`.
