# 03 · Jev (TypeSafe)

## Cómo se usa

- **Modelo:** el fijado en `config/params.yaml` (`modelo_jev: jev-1.13.0`). Nunca uses `jev-latest`, porque los resultados dejarían de ser reproducibles.
- **SDK:** `typesafe-sdk 0.7.2`, envuelto en `src/jev_cliente.py`:
  - `AsyncTypeSafeClient.system_one`;
  - reintentos con `RetryPolicy(max_retries=4, backoff_max=20, timeout=120)`;
  - los errores 401 (clave) y 422 (pregunta mal formada) no se reintentan.
- **Qué recibe Jev:** `state = {"comentario": <texto anonimizado>}` y nada más: ni la unidad, ni el rol, ni la pregunta de la encuesta. Por eso los temas de conformidad llevan la pregunta escrita en la instrucción (ver `02_temas.md`).
- **Preguntas:** una **Noul** (probabilidad de sí) por tema, más `sin_contenido`, en una sola llamada por **texto único**. Los textos repetidos se envían una sola vez.
- **Concurrencia:** `concurrencia_jev: 8`. Si fallan textos, `clasificar` los reintenta con concurrencia 2, y se detiene si no quedan todos válidos.

## Asignación

- **Un tema se asigna si p ≥ 0,70** (`umbral_tema_ejercicio`). Se calibró contra la lectura de Claude en 5 unidades: con 0,50 el micro-F1 medio era 0,76 y con 0,70 sube a 0,83. La justificación está en `params.yaml`.
- **El tema principal** es el asignado de mayor p, y su % es esa p.
- **Si ningún tema llega al 70 %**, el principal queda como "Sin tema asignado (más cercano: X)", con la p más alta.
- **El % es la probabilidad que asigna Jev, no la exactitud.**
- La Noul `sin_contenido` se guarda, pero no se usa para asignar. Las respuestas vacías ya se excluyen en `preparar`.

## Caché y costo

- **Caché:** `cache/jev_respuestas.jsonl`, con clave `sha256(modelo + state + config)`.
  - `config` lleva solo `id`, `instruccion`, `criterio_true` y `criterio_false` de **todos** los temas, más `sin_contenido`.
  - Editar `nombre`, `justificacion` o `ejemplos_si` no genera llamadas nuevas.
  - Cambiar la pregunta de **un** tema vuelve a enviar **todo** el ejercicio.
- **Precio:** 0,042 USD por millón de tokens de entrada (`precio_usd_por_millon_tokens`). Un ejercicio de unos 100 comentarios y 10 temas consume unos 200.000 tokens, es decir, unos 0,01 USD.
- **Referencias:** procesar las 25 unidades de 2026 costó 0,20 USD; consolidar los temas (versión 2) costó 0,24 USD.
- **Registro del costo:** cada `clasificar` lo anota en `logs/<slug>/decisiones.md` ("llamadas nuevas · tokens · costo USD").

## Limitación conocida y revisión obligatoria

Jev tiende a asignar **más** temas que una lectura humana, sobre todo los amplios ("formación integral", "valores", "más tecnología", "conformidad" redactada de forma abierta). Por eso el umbral es 70 % y no 50 %.

Después de cada `clasificar`, corre `python scripts/revisar_jev.py <slug>`:

| Marca | Condición | Qué hacer |
|---|---|---|
| INFLADO | Jev ≥ 2 × lectura y Jev − lectura ≥ 8 | Endurecer la redacción: exigir afirmación explícita y agregar exclusiones. Reportarlo. |
| SUBDETECTADO | lectura − Jev ≥ 4 y Jev ≤ 0,5 × lectura | Alinear la `instruccion` con el `criterio_true`; si es conformidad, agregar el contexto de la pregunta |
| ALTO | Jev − lectura ≥ 8 sin llegar al doble | Informarlo a Nicolás como conteo algo alto |

Con `--tema <id>` ves los comentarios en desacuerdo y la p de Jev. Si p está entre 0,5 y 0,7, el problema suele ser una instrucción más estrecha que el criterio. Si Jev asigna con p > 0,9 lo que tu lectura no, el criterio es demasiado literal ("menciona X").

La lectura de Claude es una **referencia indicativa**, no un estándar de oro humano. El acuerdo medio de la versión 2 es micro-F1 0,87 (mínimo 0,80).

## La clave

Se carga de `.env`, con la variable `plan_estrategico` o `TYPESAFE_API_KEY` (`jev_cliente.cargar_clave`). Nunca se imprime ni se copia a otro archivo.
