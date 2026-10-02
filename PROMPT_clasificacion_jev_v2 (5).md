# Prompt maestro v2 · Clasificación de comentarios en las Transformaciones Estratégicas con Jev (TypeSafe)

> **Versión:** 2.0 · **Fecha:** 30-sep-2026
> **Novedades frente a la v1:** ficha del ejercicio (fecha y lugar de desarrollo), marco de las 5 transformaciones estratégicas como macrotemas, clasificación jerárquica (transformación → tema) y reutilización en ejercicios posteriores.
> **API verificada contra:** docs.typesafe.ai (`api.md`, `models.md`, `model-jaggedness/jev-1.13.md`, `sdk/python.md`, `agent-skill.md`). Modelo vigente a esa fecha: `jev-1.13.0`.
> **Ejecutor:** Claude Code · **Responsable humano:** Nicolás (Dirección de Planeación Institucional, Universidad de Cundinamarca)

Este archivo tiene tres partes:

- **Resultado final:** qué entrega el proceso completo.
- **Parte A:** preparación. La haces tú.
- **Parte B:** el prompt que ejecuta Claude Code.

---

## Resultado final (qué entrega este proceso)

Al terminar tendrás:

1. **Clasificación de cada comentario** en tres niveles:
   - **Transformación estratégica:** a cuáles de las 5 se relaciona el comentario (puede ser más de una) y cuál es la principal, o "ninguna".
   - **Tema:** los temas concretos que menciona, descubiertos a partir de los propios comentarios y ubicados dentro de su transformación.
   - **Tipo de aporte:** oportunidad de mejora, reconocimiento o neutro.
2. **Distribución por transformación:** cuántos comentarios aporta la comunidad a cada una de las 5, con intervalo de confianza del 95 %, y qué temas la componen.
3. **Temas fuera del marco:** lo que la comunidad plantea y que no encaja en ninguna de las 5 transformaciones. Es un insumo directo para revisar el plan.
4. **Cruces** por grupo de interés, sede y ejercicio (fecha y lugar), con pruebas de asociación y tamaño del efecto.
5. **Voces representativas:** 3 comentarios anonimizados por tema, elegidos con una regla explícita y no a dedo.
6. **Validación estadística:** precisión, sensibilidad, F1 y kappa de Jev frente a tu etiquetado humano, con intervalos de confianza y un veredicto de aceptación.
7. **Archivos:**
   - `outputs/resultados_<fecha>_<lugar>.xlsx`, el Excel con todo lo anterior;
   - `outputs/registro_comentarios_<fecha>_<lugar>.xlsx`, el Excel de registro: una hoja por transformación, titulada con la unidad regional y el nombre de la transformación, con cada comentario, su tema y su % de confianza (uno por unidad regional en Opción A);
   - gráficos PNG;
   - `outputs/informe_metodologico_<fecha>_<lugar>.md`, con la ficha del ejercicio, el método, las métricas y las limitaciones.

---

## Parte A · Preparación (la haces tú)

### A.1 Ficha del ejercicio (obligatoria antes de empezar)

Llena `config/ficha_ejercicio.yaml`. Si dejas algún campo vacío, Claude Code te lo preguntará antes de empezar.

```yaml
nombre_ejercicio: "<p. ej. Consulta sobre Transformaciones Estratégicas - Plan 2027-2037>"
fechas_desarrollo: ["<AAAA-MM-DD>", "<AAAA-MM-DD>"]   # una o varias fechas en que se desarrolló el ejercicio
lugar_desarrollo: "<unidad regional específica (p. ej. 'Fusagasugá'), 'todas las unidades regionales', o 'virtual'>"
poblacion: "<p. ej. estudiantes, docentes, administrativos, graduados>"
archivo_datos: "data/raw/<nombre_del_excel>.xlsx"
columna_transformacion: "<nombre de la columna del Excel que dice a qué transformación (frente) pertenece cada comentario>"
documento_marco: "contexto/Transformaciones_estrategicas_5_frentes.md"   # las 5 transformaciones y sus definiciones
observaciones: "<opcional>"
```

**Qué trae el Excel de entrada y qué indicas tú**

- **El Excel trae, por cada comentario:** el texto del comentario y la **transformación (frente) a la que pertenece**, es decir, el frente en el que se hizo el comentario. Puede traer además grupo de interés, sede o pregunta.
- **Tú indicas en la ficha:** la **fecha o fechas** del ejercicio (`fechas_desarrollo`, una lista) y el **lugar de desarrollo**. Esos dos datos no se leen del Excel: valen para todos los comentarios del archivo y rotulan todos los resultados.
- Si un mismo Excel mezcla varios lugares o varias fechas y el Excel tiene una columna que los distingue, indícala en `observaciones` (p. ej. `"columna_unidad_regional: 'Sede'"`, `"columna_fecha: 'Fecha'"`); la ficha entonces declara el conjunto y Claude Code los separa en la Fase 2.
- La transformación que trae el Excel se llama aquí **transformación declarada**. Es el frente donde se comentó, **no necesariamente de qué habla el comentario**: por eso Jev sigue clasificando el contenido por su cuenta y se mide cuánto coinciden ambas (ver Fases 5 y 11).

**Para múltiples unidades regionales (frentes por unidad):**

Si el Excel incluye comentarios de varias unidades regionales y quieres procesarlas como frentes separados (la configuración por defecto):

1. Escribe `lugar_desarrollo: "todas las unidades regionales"`.
2. En `observaciones`, indica cuál columna las distingue: `"columna_unidad_regional: 'Sede'"` (o el nombre que tenga).
3. Claude Code detectará las unidades regionales en la Fase 2 y presume **Opción A**: un ejercicio por unidad regional, con una taxonomía de temas compartida entre todas ellas.
4. Si en cambio quieres Opción B (un solo ejercicio con análisis comparativo), responde "Opción B" cuando Claude Code lo pregunta.

Con Opción A (default):
- Cada unidad regional obtiene su propio Excel: `resultados_2026-09-30_fusagasuga.xlsx`, `resultados_2026-09-30_madrid.xlsx`, etc.
- La taxonomía se descubre una sola vez y se valida en el dev con el 40 % de los comentarios (repartidos proporcionalmente entre todas las unidades).
- Tú etiquetas 400 comentarios por unidad regional (el estándar de oro).

### A.2 Carpeta del proyecto

```
clasificacion_jev/
├── PROMPT_clasificacion_jev_v2.md      ← este archivo
├── .env                                ← tu clave de Jev (ver A.3)
├── config/
│   └── ficha_ejercicio.yaml            ← la ficha de A.1
├── contexto/
│   └── Transformaciones_estrategicas_5_frentes.md   ← las 5 transformaciones (frentes) y su definición
└── data/
    └── raw/
        └── encuesta.xlsx               ← el Excel original, sin modificar
```

### A.3 Clave de la API (en .env)

Crea en la raíz un archivo `.env` (archivo de texto sin extensión adicional, solo el nombre `.env`). Dentro, una sola línea:

```
TYPESAFE_API_KEY=pega_aqui_tu_clave
```

**Reglas:**

- La clave se pega una sola vez, aquí. **Nunca** en el chat de Claude Code ni dentro de ningún script.
- El código la carga automáticamente con `python-dotenv`. Aparecerá en `logs/decisiones.md` que se cargó desde `.env`, pero sin mostrar su valor.
- Asegúrate de que `.env` está en el archivo `.gitignore` (junto con `data/`, `cache/` y `outputs/`). Si lo subes a git por error, cambia la clave en TypeSafe.
- Si olvidas crear `.env` o la clave no está, Claude Code se detiene en la Fase 0 con un error explícito: "TYPESAFE_API_KEY not found in .env".

### A.4 Instalar la skill oficial de TypeSafe en Claude Code

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

### A.5 Arrancar

1. Abre la terminal en `clasificacion_jev/`.
2. Ejecuta `claude`.
3. Escribe:

> Lee `PROMPT_clasificacion_jev_v2.md` completo. Ejecuta la Parte B desde la Fase 0, usando la skill de TypeSafe. Detente en cada PUNTO DE CONTROL y espera mi aprobación antes de seguir.

### A.6 Lo que te toca a ti

Por defecto, si hay múltiples unidades regionales, se procesan como **frentes separados (Opción A)**.

| Momento | Tu tarea | Tiempo aprox. |
|---|---|---|
| Fase 0 | Completar la ficha; si hay múltiples unidades, se presume Opción A (responde solo si quieres Opción B) | 5–10 min |
| Fase 1 | Confirmar que las 5 transformaciones se extrajeron bien | 15–30 min |
| Fase 2 | Revisar perfil de datos y confirmar las unidades regionales y el procesamiento por frentes | 15–30 min |
| Fase 4 | Revisar y editar los temas y su ubicación en las transformaciones (compartida para todas las unidades) | 1–2 h |
| Fase 6 | Etiquetar a mano 400 comentarios por cada unidad regional (transformaciones, temas y tipo), sin ver predicciones de Jev | 4–6 h × n_unidades |
| Fase 10 (solo si aparece un tema nuevo) | Etiquetar esa única columna en los 400 de esa unidad | 20–40 min |
| Ejercicios posteriores | Etiquetar 100 comentarios nuevos de la misma fecha pero unidad distinta, para verificar desempeño | 1–1,5 h |

### A.7 Antes de empezar

Confirma que la universidad autoriza procesar estos comentarios, ya anonimizados, con dos servicios externos:

- **Anthropic:** Claude Code lee los textos para descubrir temas.
- **TypeSafe:** Jev los clasifica.

Referencia legal: Ley 1581 de 2012.

---

## Parte B · Prompt para Claude Code

### B.1 Rol y objetivo

Actúa como analista de datos y metodólogo de investigación cualitativa y cuantitativa, al servicio de la Planeación Estratégica 2027-2037 de la Universidad de Cundinamarca. Con Nicolás vas a construir un pipeline reproducible en Python para:

1. **Extraer el marco:** tomar las 5 transformaciones estratégicas del documento de contexto. Son los macrotemas, el nivel deductivo.
2. **Descubrir los temas:** encontrar los temas presentes en los comentarios abiertos (nivel inductivo) y ubicar cada uno dentro de una transformación, o marcarlo como "fuera del marco".
3. **Clasificar con Jev** todos los comentarios, en una sola petición por comentario:
   - las 5 transformaciones (multi-etiqueta) y la transformación principal;
   - los temas (multi-etiqueta);
   - el tipo de aporte.
4. **Validar** contra un estándar de oro humano, con métricas e intervalos de confianza.
5. **Entregar** los resultados rotulados con la fecha y el lugar del ejercicio.

Los comentarios tienen errores de ortografía y de redacción. **No se corrigen**.

División del trabajo:

| Tarea | Responsable |
|---|---|
| Extraer las 5 transformaciones del documento | Tú; Nicolás las confirma |
| Descubrir temas (lectura cualitativa) | Tú, leyendo textos anonimizados |
| Clasificar todos los comentarios | Jev |
| Etiquetas de referencia (estándar de oro) | Nicolás, a ciegas |
| Conteos, porcentajes, métricas y pruebas | Código Python (nunca Jev, nunca "a ojo") |
| Aprobar cada fase | Nicolás |

### B.2 Reglas no negociables

1. **Fases y puntos de control.** Ejecuta una fase a la vez. Al final de cada una, muestra el resumen que pide su PUNTO DE CONTROL y espera "aprobado" (o cambios) de Nicolás. No avances sin aprobación.
2. **Fuente de verdad de la API.** Usa la skill de TypeSafe y la documentación oficial. El índice está en `https://docs.typesafe.ai/llms.txt`; lee en especial:
   - `api.md`, `models.md`, `confidence.md`
   - `primitives/noul.md`, `primitives/choice.md`, `concepts/state.md`
   - `model-jaggedness/jev-1.13.md`
   - `sdk/python.md`, `sdk/python/usage.md`

   No inventes campos, parámetros ni excepciones. Si este prompt contradice la documentación vigente, gana la documentación; anota la discrepancia en `logs/decisiones.md`.
3. **Clave.** Se carga automáticamente desde el archivo `.env` con `python-dotenv`. El código nunca la imprime ni la pasa a logs o outputs. Registra en `logs/decisiones.md` que se cargó desde `.env`, pero nunca su valor. Si la clave es inválida, el cliente de TypeSafe lanzará un error 401 en la Fase 0.
4. **Privacidad.** Ningún comentario se lee (por ti) ni se envía (a Jev) sin anonimizar primero (Fase 3). El texto original nunca sale del computador de Nicolás.
5. **El marco no se inventa.** Las 5 transformaciones (los 5 frentes) salen del archivo `contexto/Transformaciones_estrategicas_5_frentes.md`, con su nombre y su definición textuales. Ese archivo es la única fuente: no uses conocimiento propio sobre el Plan 2027-2037 para completarlo. No las parafrasees como si fueran otras, no agregues una sexta y no fusiones dos. Si el documento no muestra con claridad 5 transformaciones, detente y pregunta.
6. **Primero lo inductivo, después el marco.** En la codificación abierta (Fase 4) lees los comentarios sin forzarlos a encajar en las 5 transformaciones; la ubicación en el marco se hace después. Así se evita el sesgo de confirmación y lo que queda fuera del marco se vuelve visible.
7. **Cada método en su papel.** Regex y listas de palabras solo para filtrar ruido y anonimizar. Está prohibido clasificar temas o transformaciones con palabras clave.
8. **Aritmética en código.** Todo conteo, porcentaje, umbral y métrica se calcula en Python. A Jev nunca se le pide contar ni comparar números.
9. **El estándar de oro es humano.** Nunca generes tú sus etiquetas. Mientras Nicolás etiqueta, no le muestres predicciones de Jev ni tuyas.
10. **El test se usa una sola vez** (Fase 8). Si después de verlo cambias algo, queda contaminado y hace falta un test nuevo.
11. **Reproducibilidad.**
    - Semilla fija (`seed`) en todo muestreo y bootstrap.
    - El modelo se fija por su versión (por ejemplo `jev-1.13.0`), nunca por `jev-latest`.
    - La taxonomía se versiona y su hash SHA-256 queda registrado en cada resultado.
12. **Caché e idempotencia.** Cada respuesta de Jev va a `cache/jev_respuestas.jsonl` con la clave `sha256(modelo + state + preguntas serializadas)`. Si el proceso se interrumpe, se reanuda sin repetir llamadas. Nada se descarta en silencio.
13. **Constantes en un solo lugar:** `config/ficha_ejercicio.yaml`, `config/marco_estrategico.yaml`, `config/taxonomia_vX.yaml` y `config/params.yaml`.
14. **Metadatos fuera de Jev.** La fecha, el lugar, el grupo y la sede nunca van en el `state` de Jev: el contexto irrelevante reduce la precisión. Se usan en código para rotular y cruzar.
15. **Bitácora.** Toda decisión metodológica se registra con fecha en `logs/decisiones.md`: qué se decidió, por qué y con qué evidencia.
16. **Honestidad estadística.** Toda proporción o métrica se reporta con su n y su IC del 95 %. Si un n es insuficiente, se dice explícitamente.
17. **Idioma.** Salidas, hojas y reportes en español.

### B.3 Estructura del proyecto

```
clasificacion_jev/
├── .env
├── .gitignore                      # .env, data/, cache/, outputs/
├── requirements.txt
├── config/
│   ├── ficha_ejercicio.yaml
│   ├── marco_estrategico.yaml      # las 5 transformaciones (Fase 1)
│   ├── params.yaml
│   └── taxonomia_v1.yaml           # temas con su transformación (Fase 4)
├── contexto/                       # documento de transformaciones (solo lectura)
├── data/
│   ├── raw/                        # Excel original (solo lectura)
│   ├── interim/                    # limpio y anonimizado (parquet)
│   └── gold/                       # plantilla y etiquetas humanas
├── src/
│   ├── f00_ficha_entorno.py
│   ├── f01_marco.py
│   ├── f02_perfil.py
│   ├── f03_limpieza_anonimizacion.py
│   ├── f04_descubrimiento.py
│   ├── f05_preguntas_jev.py
│   ├── f06_gold.py
│   ├── f07_dev.py
│   ├── f08_test.py
│   ├── f09_clasificacion.py
│   ├── f10_residual.py
│   ├── f11_analisis_entregables.py
│   ├── jev_cliente.py
│   └── metricas.py
├── tests/test_metricas.py
├── cache/jev_respuestas.jsonl
├── logs/decisiones.md
└── outputs/
```

### B.4 Parámetros (`config/params.yaml`)

```yaml
seed: 2026
z: 1.959964
n_descubrimiento: 500
lote_lectura: 50
min_leidos_saturacion: 300
max_descubrimiento: 800
n_validacion_cobertura: 300
n_gold: 400
proporcion_dev: 0.60                  # 240 dev / 160 test
min_estrato: 20
min_positivos_umbral: 15              # para umbral propio (tema o transformación)
min_positivos_metricas_test: 10
bootstrap_B: 2000
max_rondas_redaccion: 3
max_iteraciones_residual: 2
residual_max: 0.10
frecuencia_min_tema_nuevo: 0.01
mejora_min_ab: 0.02
concurrencia_jev: 8
n_verificacion_transferencia: 100     # ejercicios posteriores
n_voces_por_tema: 3
incluir_original_en_registro: false   # true solo si el archivo de registro se queda en tu equipo
umbral_revisar_confianza: null        # se fija en la Fase 7 con los umbrales por elemento
precio_usd_por_millon_tokens: 0.042   # verificar en docs.typesafe.ai/models
modelo_jev: null                      # se fija en la Fase 0
aceptacion:
  micro_f1_transformaciones: 0.80
  kappa_por_transformacion: 0.61
  kappa_transformacion_principal: 0.61
  micro_f1_temas: 0.80
  macro_f1_temas: 0.70
  kappa_por_tema: 0.61
  kappa_tipo: 0.61
  ece_max: 0.10
  coherencia_jerarquica_min: 0.90
  cobertura_min: 0.90
  falsos_descartes_max: 0.03
```

Estos valores son el punto de partida. Nicolás puede cambiarlos en cualquier punto de control, y cada cambio se registra en la bitácora.

---

### Fase 0 · Ficha, entorno y verificación de la API

1. **Verifica .env y la clave.** Antes de cualquier otra cosa:
   - Busca el archivo `.env` en la raíz de la carpeta del proyecto.
   - Si no existe, detente y pide que Nicolás lo cree con una sola línea: `TYPESAFE_API_KEY=...`.
   - Verifica que la línea contiene `TYPESAFE_API_KEY=` seguido de un valor no vacío (no importa si es la verdadera clave o un placeholder por ahora; en la Fase 0 lo verificarás conectando).
   - Si falta o está vacía, detente y reporta: "Archivo .env no encontrado o TYPESAFE_API_KEY vacía. Crea el archivo .env con tu clave antes de continuar."
2. **Ficha del ejercicio.** Lee `config/ficha_ejercicio.yaml`.
   - Si falta alguna fecha, el lugar, el archivo de datos, la columna de transformación o el documento del marco, **pregúntale a Nicolás y espera su respuesta**. No supongas ninguno.
   - `fechas_desarrollo` es una lista (una o varias fechas). Normaliza cada una a `AAAA-MM-DD`. Si aceptas un rango, escríbelo `AAAA-MM-DD_a_AAAA-MM-DD`.
   - Crea el identificador `slug_ejercicio = <fecha o rango>_<lugar en minúsculas, sin tildes, espacios como _>`. Con una sola fecha, `<fecha>`; con varias, la primera y la última (`<primera>_a_<última>`) y la lista completa queda en el Resumen. Se usa en todos los nombres de salida.
   - Confirma que el Excel de `archivo_datos` existe y que la `columna_transformacion` está en él.
2. **Entorno.** Crea un entorno virtual con Python 3.10 o superior e instala:
   `typesafe-sdk pandas numpy scipy scikit-learn statsmodels openpyxl matplotlib python-dotenv pyyaml tqdm pyarrow pytest pdfplumber python-docx`
   Opcional, para detectar nombres de personas: `spacy` y `es_core_news_md`.
3. Crea `.gitignore`, `requirements.txt` con versiones exactas y `logs/decisiones.md`.
4. Lee la documentación listada en la regla 2.
5. **Prueba de humo** con un texto ficticio (por ejemplo `"los baños del bloque B no tienen agua hace 2 semanas"`), usando una Noul y una Choice. Verifica:
   - modelo que respondió y una respuesta por clave;
   - `noul` en [0, 1];
   - `choice` válida y `probabilities` que suman 1 ± 0,01;
   - `confidence` en [0, 1] y uso de tokens.

   Si algún atributo del SDK se llama distinto, ajústalo según la referencia oficial y anótalo.
6. Consulta `GET /v1/models`. Fija en `params.yaml` → `modelo_jev` el identificador **versionado** que devolvió la respuesta.
7. Escribe `src/metricas.py` (Apéndice A) y `tests/test_metricas.py`. Incluye como mínimo:
   - Wilson con p = 0,9 y n = 300 → [0,861; 0,929];
   - tamaño de muestra con N = 6.000 → 361,1.

   Todas las pruebas deben pasar.

> **PUNTO DE CONTROL 0.** Confirma que .env se cargó (sin mostrar su valor). Luego muestra:
> - La ficha completa y normalizada (con `slug_ejercicio`);
> - las versiones del entorno (Python y paquetes principales);
> - la prueba de humo (sin la clave, sin tokens sensibles);
> - el modelo fijado (por ejemplo `jev-1.13.0`);
> - el resultado de `pytest`.

### Fase 1 · Marco estratégico: las 5 transformaciones

1. **Lectura del documento.** Lee completo `contexto/Transformaciones_estrategicas_5_frentes.md` (lectura directa, es Markdown; los encabezados y listas indican la estructura). Si el archivo no existe o está vacío, detente y avisa. Si en `config/ficha_ejercicio.yaml` el `documento_marco` apunta a otro archivo (PDF o Word), úsalo con pdfplumber o python-docx, pero el .md manda si existe.
2. **Lectura.** Léelo completo e identifica las transformaciones estratégicas. Para cada una registra:
   - su nombre oficial, textual (el del encabezado en el .md);
   - su **definición tal como aparece en el archivo**: propósito, alcance, líneas o ejes, conceptos clave; cópiala textualmente en `definicion_textual` y haz aparte la síntesis;
   - el encabezado o la sección del .md donde aparece (y el número de línea), para que Nicolás pueda verificarla.
3. **Verificación del número.** Si no encuentras exactamente 5, o si hay ambigüedad (por ejemplo, un eje que podría ser transformación o sublínea), **detente y pregunta**.
4. **Archivo del marco.** Construye `config/marco_estrategico.yaml`:

```yaml
- id: T1
  nombre_oficial: "<textual, como aparece en el documento>"
  referencia: "<encabezado o sección del .md, y línea>"
  definicion_textual: "<la definición copiada tal cual del archivo, sin resumir>"
  sintesis_documento: "<2-4 frases fieles a la definición, sin agregar ideas>"
  conceptos_clave: ["<…>", "<…>"]
  instruccion: "¿El `comentario` se relaciona con <definición operativa en una frase, en lenguaje llano>?"
  criterio_true: "<qué asuntos concretos cuentan como sí; se enriquece con los temas hijos en la Fase 4>"
  criterio_false: "<qué no cuenta, incluidas las fronteras con las otras 4 transformaciones>"
# … T2 a T5
```

5. **Matriz de fronteras.** Para cada par de transformaciones (10 pares), escribe una frase que diga cómo distinguirlas. Esas frases alimentan los `criterio_false`.
6. **Reglas de redacción** (por la lectura literal de Jev):
   - La instrucción usa lenguaje llano, no la jerga del documento. Un comentario de un estudiante casi nunca dirá el nombre oficial de la transformación.
   - Una sola decisión por pregunta y ninguna doble negación.
   - Los casos límite van en los criterios.

> **PUNTO DE CONTROL 1.** Muestra las 5 transformaciones con su nombre oficial, su referencia en el documento, la síntesis, la instrucción y los criterios, y la matriz de fronteras. Nicolás confirma o corrige. La versión aprobada se congela con su hash.

### Fase 2 · Perfil de los datos

1. Abre el Excel en modo solo lectura. Lista hojas, columnas, tipos, filas, nulos y duplicados.
2. Propón el mapeo de:
   - el identificador de respuesta (si no existe, crea `id_resp` estable);
   - las columnas de comentario y la pregunta que responde cada una;
   - el grupo de interés, la sede y **la unidad regional** (si existe);
   - **la transformación declarada** (`columna_transformacion` de la ficha). Lista los valores distintos que trae y propón la equivalencia con T1…T5 del marco (por nombre, número o abreviatura). Si algún valor no se puede asignar con certeza a una de las 5, o hay comentarios sin transformación, **pregunta a Nicolás**; los vacíos quedan como `sin_frente_declarado`. Guarda la equivalencia en `config/equivalencia_transformaciones.yaml`;
   - la columna que distingue ejercicios (fecha o lugar), si el Excel mezcla varios.
3. **Detección de unidades regionales.** Si detectas que:
   - la ficha dice `lugar_desarrollo: "todas las unidades regionales"`, y
   - el Excel tiene una columna de unidad regional,
   
   entonces:
   - lista las unidades regionales únicas, con el n de comentarios de cada una;
   - **sugiere Opción A como default** (procesarlas como frentes separados con taxonomía compartida), y pregunta si quiere cambiar a Opción B:
     - **Opción A (recomendada):** procesar cada unidad regional como un ejercicio separado (genera N_u Excel distintos, una taxonomía compartida);
     - **Opción B (si quieres compararlas):** procesar todas juntas como un ejercicio único, con análisis comparativo por unidad regional en el Excel y los gráficos.
   - espera su respuesta (o aprobación de A) antes de seguir.
4. **Coherencia con la ficha.** Si el Excel trae fechas o lugares, compáralos con la ficha e informa cualquier diferencia.
5. Si hay varias columnas de comentarios, pasa a formato largo: una fila por (`id_resp`, `pregunta`, `comentario`), con un `id_com` único.
6. Reporta:
   - N total, y N por transformación declarada, grupo, unidad regional, sede y fecha;
   - longitud de los comentarios: mediana, p25, p75, p95 y máximo;
   - porcentaje de comentarios vacíos.

> **PUNTO DE CONTROL 2.** Muestra el mapeo de columnas, las diferencias con la ficha, la(s) unidad(es) regional(es) detectada(s) con su n, y el perfil. Si hay múltiples unidades regionales, presume **Opción A** (frentes separados, taxonomía compartida) y pregunta si Nicolás quiere cambiar a Opción B. Luego confirma el mapeo y el plan.

### Fase 3 · Limpieza, filtro de ruido y anonimización

**3.1 Columnas de trabajo.**

- `comentario_original`: se conserva intacto.
- `texto_norm`: minúsculas, sin tildes y con espacios colapsados. Solo se usa para filtrar.
- `comentario_anon`: el resultado de 3.3. Es lo único que se lee y se envía.

**3.2 Filtro de ruido.** Marca `excluido = 1`, con su `motivo`, si el comentario:

- está vacío o solo tiene signos o números;
- tiene menos de 3 caracteres alfabéticos;
- coincide completo (sobre `texto_norm`) con una no-respuesta: `ninguno, ninguna, nada, no, na, n/a, no aplica, no tengo, sin comentarios, ningun comentario, todo bien, todo esta bien, bien, ok, gracias, ninguna observacion`, o variantes con errores obvios.

Ante la duda, **no se excluye**.

Auditoría: toma 100 excluidos al azar y calcula la tasa de falsos descartes con IC de Wilson. Si supera 0,03, corrige las reglas y repite.

**3.3 Anonimización**, en este orden:

1. Correos → `[CORREO]`.
2. URLs → `[URL]`.
3. Teléfonos colombianos → `[TELEFONO]` (celulares `3\d{2}[\s.-]?\d{3}[\s.-]?\d{4}` y fijos con indicativo).
4. Secuencias de 6 a 11 dígitos, con o sin puntos → `[NUMERO_ID]`. Excepción: montos con `$`, `pesos` o `mil`.
5. Nombres de personas → `[PERSONA]`: spaCy (`PER`) si está disponible, más la regla "título + palabra con mayúscula inicial" (profesor/a, profe, docente, ingeniero/a, doctor/a, señor/a, coordinador/a, decano/a, rector/a).

Auditoría: lee 200 comentarios anonimizados al azar. Si encuentras 0 con datos personales, reporta la cota superior del 95 % por la regla de tres (1,5 %). Si encuentras alguno, corrige y repite con una muestra nueva.

**3.4 Duplicados.** No se eliminan. Agrupa los pares idénticos (`pregunta`, `comentario_anon`) bajo un `id_texto_unico`: Jev se llama una vez por texto único y el resultado se replica.

**3.5 Resultado.** Guarda `data/interim/comentarios.parquet`. N_s es el número de comentarios con contenido.

> **PUNTO DE CONTROL 3.** Muestra N_s (total y por ejercicio), las exclusiones por motivo, los falsos descartes con IC, los reemplazos de datos personales, la auditoría de anonimización y el número de textos únicos.

### Fase 4 · Descubrimiento de temas dentro del marco

**4.1 Muestra de descubrimiento (D).** 500 comentarios de N_s, estratificados proporcionalmente por **transformación declarada** y por grupo (y por sede o fecha, si existen), con mínimo 20 por estrato cuando el estrato lo permita. Así cada frente queda representado y los temas propios de uno no se pierden por ser pocos. Orden aleatorio con la semilla.

**4.2 Codificación abierta.**

1. Muestra los comentarios en lotes de 50 y **léelos tú**, sin palabras clave ni scripts.
2. En esta etapa **no** los fuerces a las 5 transformaciones (regla 6). Anota los códigos de cada comentario en `logs/codificacion_abierta.jsonl`.
3. Después de cada lote, registra los temas nuevos.
4. **Saturación:** tras al menos 300 leídos, dos lotes seguidos sin temas nuevos. Lee los 500 de todas formas; si no hay saturación, sigue hasta 800.
5. Grafica la curva de saturación en `outputs/f04_curva_saturacion.png`.

**4.3 Consolidación y ubicación en el marco.**

1. Agrupa los códigos en temas; como guía, entre 10 y 30.
2. Asigna a cada tema **una** `transformacion_padre`: T1 a T5, o `fuera_del_marco` si no encaja razonablemente en ninguna. Justifica cada asignación con una frase que cite el concepto del documento que la sustenta.
3. Si un tema cabe en dos transformaciones, divídelo en dos temas o elige la principal y deja constancia en `nota_frontera`.
4. Fusiona los temas con frecuencia en D menor al 1 %, pero solo con otro tema de la **misma** transformación. Excepción: los temas críticos (acoso, discriminación, seguridad o riesgo para personas) se conservan siempre, con `critico: true`.
5. Solapamiento: si dos temas tienen Jaccard > 0,5 en D, fusiónalos o precisa su frontera.
6. Cada tema se registra en `config/taxonomia_v1.yaml` con esta estructura:

```yaml
- id: infraestructura_fisica
  nombre: "Infraestructura y planta física"
  transformacion_padre: T3            # T1…T5 o fuera_del_marco
  justificacion_marco: "<concepto del documento que lo sustenta>"
  nota_frontera: "<opcional>"
  critico: false
  instruccion: "¿El `comentario` se refiere al estado, la falta o el mantenimiento de salones, baños, edificios o mobiliario de la universidad?"
  criterio_true: "Menciona salones, baños, edificios, sillas, techos, pintura, goteras o espacios físicos, aunque sea de forma breve o con errores de ortografía."
  criterio_false: "No menciona espacios físicos, o solo habla de internet, laboratorios o parqueaderos, que tienen su propio tema."
  ejemplos_si: ["<texto anonimizado real de D>", "<…>"]
  ejemplos_no_cercanos: ["<comentario de un tema vecino que NO es este>"]
  frecuencia_D: {n: 0, pct: 0.0}
```

**4.4 Enriquecer el marco.** Agrega a `criterio_true` de cada transformación, en lenguaje llano, los asuntos concretos de sus temas hijos. Así Jev reconoce la transformación aunque el comentario no use el vocabulario del documento.

**4.5 Preguntas fijas.**

- `transformacion_principal` (Choice): "¿Con cuál de las cinco transformaciones se relaciona principalmente el `comentario`?" Opciones: T1 a T5, cada una con su definición operativa, más `ninguna` ("no se relaciona con ninguna de las cinco").
- `tipo` (Choice):
  - `oportunidad_de_mejora`: contiene al menos una queja, problema o sugerencia; si además felicita, sigue siendo esta opción.
  - `reconocimiento`: solo felicita o valora positivamente, sin pedir cambios.
  - `neutro_observacion`: describe o comenta sin queja, sugerencia ni felicitación.
- `sin_contenido` (Noul): "¿El `comentario` carece de contenido evaluable, por ejemplo una respuesta vacía, un 'nada', un 'todo bien' sin más detalle o un texto sin sentido?"

**4.6 Validación de cobertura (V).**

1. Lee 300 comentarios nuevos, disjuntos de D, y asigna cada uno a temas o a "no encaja".
2. Calcula la cobertura de temas con IC de Wilson.
3. Calcula el porcentaje que queda en `fuera_del_marco`, con IC.
4. Criterio: cobertura ≥ 0,90 y ningún tema candidato nuevo con frecuencia ≥ 1 %. Si falla, ajusta y valida con 200 más.

Entregables de la fase: `outputs/f04_taxonomia_v1.xlsx` (con columnas Transformación → Tema, legible para Nicolás) y `outputs/f04_resumen_descubrimiento.md`.

> **PUNTO DE CONTROL 4.** Muestra el árbol Transformación → Temas con la frecuencia de cada tema en D, los temas fuera del marco, la curva de saturación, la cobertura con IC y los pares con J > 0,5. Nicolás edita: fusiona, renombra y reubica. La versión aprobada se congela con su hash.

### Fase 5 · Preguntas para Jev y prueba piloto

1. **Preguntas.** `src/f05_preguntas_jev.py` construye, desde los YAML, **una sola petición por comentario** (fan-out) con:
   - 5 Nouls de transformación (`trans_T1` … `trans_T5`);
   - la Choice `transformacion_principal`;
   - una Noul por tema;
   - la Choice `tipo`;
   - la Noul `sin_contenido`.
2. **Por qué Nouls y Choice a la vez.** Según la documentación de Jev, la Choice es relativa: decide *cuál* opción es la principal. Cada Noul es absoluta: decide *si* la transformación aplica, y puede ser baja para todas. Por eso las Nouls deciden la pertenencia y la Choice elige la principal. Los umbrales de una no se trasladan a la otra.
3. **Estado (`state`):** `{"comentario": <comentario_anon>}`, y `"pregunta"` solo si la encuesta tiene varias preguntas. Nunca fecha, lugar, grupo, sede **ni la transformación declarada** (regla 14): Jev clasifica el contenido sin saber en qué frente se comentó, y así la comparación posterior entre lo declarado y lo detectado es honesta.
4. **Tokens.** Verifica con `usage` que estado + pregunta más larga quede por debajo de 32k y la petición completa por debajo de 64k.
5. **Piloto** con 10 comentarios de D. Verifica que estén todas las claves, que los valores estén en rango y que las probabilidades de cada Choice sumen 1 ± 0,01.
6. **Costo estimado** en USD: tokens medios × textos únicos × precio / 10⁶.

> **PUNTO DE CONTROL 5.** Muestra una tabla de las 10 respuestas (comentario, transformaciones con p ≥ 0,5, principal, temas con p ≥ 0,5, tipo), los tokens medios y el costo estimado.

### Fase 6 · Estándar de oro humano (etiquetado ciego)

**6.1 Tamaño.**

```
n0 = z² · p(1−p) / e² = 1,96² · 0,25 / 0,0025 ≈ 384,1
n  = n0 / (1 + (n0 − 1)/N_s)
```

Con N_s = 6.000, n ≈ 361. Se usan 400, que cubren el peor caso para cualquier N_s:

| Conjunto | Tamaño | Margen aprox. (p = 0,5) |
|---|---|---|
| dev | 240 | ±6,3 % |
| test | 160 | ±7,7 % |

La división es estratificada por grupo (y por ejercicio, si hay varios).

**6.2 Muestreo.** Aleatorio estratificado desde N_s, **excluyendo D y V**.

**6.3 Plantilla** `data/gold/plantilla_gold.xlsx`:

- **Etiquetar.** Columnas:
  - `id_gold`, `pregunta`, `comentario_anon`;
  - una columna 0/1 por transformación (T1…T5, con su nombre oficial en el encabezado);
  - `transformacion_principal`, con lista desplegable T1…T5 o `ninguna`;
  - una columna 0/1 por tema, agrupadas y coloreadas por transformación;
  - `tipo`, con lista desplegable;
  - `sin_contenido` (0/1) y `observaciones`.

  Filas aleatorias, paneles inmovilizados y ninguna salida de Jev.
- **Guía.** El marco (con referencias al documento) y la taxonomía completa.
- **Instrucciones.**
  - Marca todas las transformaciones y temas que el comentario toque; pueden ser varios o ninguno.
  - La principal es aquella a la que más aporta el comentario.
  - No consultes a Claude ni a Jev mientras etiquetas.

**6.4 Recomendado.** Una segunda persona etiqueta, de forma independiente, 100 de los 400. El κ entre humanos (por transformación, por tema y para la principal) marca el techo realista.

**6.5 Importación.** Valida que no haya celdas vacías ni valores inválidos. Reporta los positivos por transformación y por tema, en dev y en test.

> **PUNTO DE CONTROL 6.** Entrega la plantilla y **espera** a que Nicolás la devuelva etiquetada. Luego muestra la validación y los positivos.

### Fase 7 · Evaluación en dev, calibración y ajuste

Ejecuta Jev **solo sobre dev**.

**7.1 Métricas por transformación y por tema** (predicción = 1 si p ≥ τ):

- VP, FP, FN y VN;
- precisión, sensibilidad y especificidad, cada una con IC de Wilson;
- F1 y κ de Cohen;
- AUC-ROC, AUC-PR y Brier;
- prevalencia en el estándar de oro frente a la predicha.

**7.2 Globales.** Por separado para transformaciones y para temas:

- micro-F1;
- macro-F1 (sobre elementos con 10 o más positivos, y aparte sobre todos);
- Hamming loss;
- exact match;
- Jaccard promedio.

**7.3 Choices (`transformacion_principal` y `tipo`):**

- exactitud, F1 macro, κ y matriz de confusión (6×6 y 3×3);
- curva exactitud-cobertura por `confidence`. Elige c* como el menor c que logra exactitud ≥ 0,90 en los casos retenidos, y reporta la cobertura.

**7.4 Calibración.** ECE (10 intervalos) y diagrama de fiabilidad de las Nouls; Brier por elemento.

**7.5 Coherencia jerárquica** (calculada en código). Un comentario es coherente si la `transformacion_padre` de cada tema asignado (salvo `fuera_del_marco`) está entre sus transformaciones asignadas, y si su principal (cuando no es `ninguna`) supera su umbral de Noul.

- Reporta la tasa de coherencia con IC.
- Reporta también el acuerdo (κ por transformación) entre la transformación **asignada directamente** por Jev y la **derivada** de los temas. Es una medida de validez convergente.

**7.6 Umbrales:**

- τ global de transformaciones y τ global de temas: la rejilla 0,05…0,95 que maximiza el micro-F1 en dev.
- τ propio: solo con 15 o más positivos en dev **y** una mejora de F1 de 0,03 o más.
- τ de `sin_contenido`: igual, sobre su propia columna.

**7.7 Ajuste de redacción** (máximo 3 rondas). Para cada transformación o tema con F1 < 0,70:

1. Lee sus falsos positivos y falsos negativos.
2. Identifica la ambigüedad.
3. Reescribe la instrucción o los criterios. Para las transformaciones, apóyate en la matriz de fronteras.
4. Sube la versión y vuelve a correr solo dev.

**7.8 Pruebas A/B pareadas en dev:**

- (a) instrucciones y criterios en español vs. en inglés. La documentación indica que el inglés es el idioma principal de entrenamiento de Jev.
- (b) estado con `pregunta` vs. sin `pregunta`.

Se adopta B solo si mejora el micro-F1 en 0,02 o más **y** el IC 95 % del bootstrap pareado (B = 2000) excluye 0. Si no, se conserva la variante más simple.

> **PUNTO DE CONTROL 7.** Muestra las métricas con IC, la coherencia jerárquica, los umbrales, los cambios por ronda y las pruebas A/B. Nicolás aprueba congelar la configuración.

### Fase 8 · Evaluación final en test (una sola vez)

1. Con la configuración congelada, corre Jev sobre test y calcula las métricas de 7.1 a 7.5.
2. IC 95 %: Wilson para proporciones; bootstrap percentil (B = 2000, remuestreando comentarios) para F1, κ y ECE.
3. Los elementos con menos de 10 positivos en test se marcan "n insuficiente", con su IC.
4. **Criterios de aceptación:**

| Métrica | Umbral |
|---|---|
| micro-F1 de transformaciones | ≥ 0,80 |
| κ por transformación (≥ 10 positivos) | ≥ 0,61 |
| κ de `transformacion_principal` | ≥ 0,61 |
| micro-F1 de temas | ≥ 0,80 |
| macro-F1 de temas (≥ 10 positivos) | ≥ 0,70 |
| κ por tema (≥ 10 positivos) | ≥ 0,61 |
| κ de `tipo` | ≥ 0,61 |
| ECE (Nouls agrupadas) | ≤ 0,10 |
| Coherencia jerárquica | ≥ 0,90 |

   El κ ≥ 0,61 corresponde a acuerdo "sustancial" (Landis y Koch, 1977). Si existe acuerdo entre humanos, reporta también la razón κ(Jev-humano) / κ(humano-humano).
5. Si todo se cumple, pasa a la Fase 9. Si no, reporta qué falla. Volver a ajustar exige un **test nuevo** de 160, etiquetado por Nicolás.

> **PUNTO DE CONTROL 8.** Muestra la tabla final en test con IC y el veredicto de cada criterio.

### Fase 9 · Clasificación completa

1. **Ejecución.** Corre Jev sobre todos los textos únicos de N_s con el cliente asíncrono: concurrencia 8, timeouts, caché escrita tras cada respuesta, barra de progreso y reanudación.
2. **Errores:**

| Código | Acción |
|---|---|
| 401 (clave) | detener todo y reportar; no reintentar |
| 422 (petición inválida) | detener todo y reportar; no reintentar |
| 429 (límite) | reintentar con espera exponencial; el SDK lo hace y respeta `retry-after` |
| 529 (sobrecarga) | ídem |

   Si se agotan los reintentos, marca `estado_jev = "error"` y reintenta al final.
3. **Completitud.** Las respuestas válidas deben ser iguales a los textos únicos. Si no, no se avanza.
4. **Asignación**, con los umbrales congelados:
   - `trans_Ti = 1` si p ≥ τ_T.
   - `transformacion_principal`: la opción elegida por la Choice. Se marca `principal_incoherente = 1` si esa transformación no supera su umbral de Noul.
   - `tema_k = 1` si p ≥ τ_k.
   - `sin_contenido = 1` si p ≥ τ_sc.
   - `residual = 1` si no tiene temas ni transformaciones y `sin_contenido = 0`.
   - `incoherente = 1` si falla la coherencia jerárquica de 7.5.
   - `revisar = 1` si cumple cualquiera de estas condiciones: residual, incoherente, principal incoherente, tema crítico, o `confidence` de alguna Choice menor que su c*.
5. **Registro por llamada:** id, modelo devuelto, `input_tokens`, marca de tiempo, hash de la taxonomía y `slug_ejercicio`. Reporta tokens y costo reales.

> **PUNTO DE CONTROL 9.** Muestra la completitud, la distribución por transformación y por tema, el residual con IC, la coherencia, los casos para revisar por motivo y el costo real.

### Fase 10 · Residual e iteración

1. **Tasa de residual** r (excluyendo `sin_contenido`), con IC de Wilson.
2. **Lectura.** Lee todos los residuales si son 600 o menos; si son más, una muestra estratificada de 600 (y dilo). Clasifica cada uno como:
   - **(a)** tema existente que Jev pasó por alto (falso negativo);
   - **(b)** tema candidato nuevo, con su transformación padre o `fuera_del_marco`;
   - **(c)** no clasificable.
3. **Tema nuevo:** se acepta si su frecuencia estimada es de al menos 1 % de N_s, o si es crítico.
4. **Si r > 10 % o hay temas nuevos:**
   1. crea la taxonomía v+1;
   2. Nicolás etiqueta solo la columna nueva en los 400;
   3. calcula el umbral del tema nuevo en dev y sus métricas en test (primera y única vez);
   4. vuelve a correr la clasificación completa;
   5. verifica que las asignaciones previas coincidan en al menos el 99 %; si no, repórtalo antes de seguir.
5. **Parada:** máximo 2 iteraciones. Se detiene cuando r ≤ 10 % y no hay temas nuevos que cumplan el criterio.

> **PUNTO DE CONTROL 10.** Muestra el residual antes y después, los temas nuevos con su justificación y la composición del residual final.

### Fase 11 · Análisis y entregables

**11.1 Unidad de análisis.** Si una persona respondió varias preguntas, las pruebas de asociación se hacen **por respondiente**: un respondiente toca una transformación o un tema si alguno de sus comentarios lo hace. Las prevalencias se reportan en los dos niveles, con el denominador explícito.

**11.2 Prevalencias:**

- **Por transformación declarada:** conteo exacto de comentarios de cada frente (no se estima; viene del Excel), con su % sobre N_s.
- **Concordancia declarada vs. detectada:** % de comentarios cuya transformación principal según Jev coincide con la declarada, con IC de Wilson, y la matriz declarada × detectada. Repórtala también contra el estándar de oro. Interpreta: una discordancia alta en un frente indica que ahí se comenta sobre otros frentes.
- **Por transformación (contenido, según Jev):** p̂ = n / N_s, con IC de Wilson. Se reporta también la distribución de la principal, que sí suma 100 % con `ninguna`.
- **Por tema:** igual, agrupados por transformación.
- **Fuera del marco:** porcentaje de comentarios que solo tienen temas `fuera_del_marco`, más los que caen en `ninguna` como principal.
- Aclara que transformaciones y temas son multi-etiqueta, así que suman más del 100 %.

**11.3 Prevalencia corregida (Rogan-Gladen)** para transformaciones y temas con al menos 10 positivos en test y J = Se + Sp − 1 ≥ 0,5:

```
p̃ = (p̂ + Sp − 1) / (Se + Sp − 1),   truncada a [0, 1]
```

Su IC se obtiene por bootstrap (B = 2000), remuestreando test y datos completos en cada réplica.

**11.4 Tipo de aporte por transformación:** porcentaje de oportunidad de mejora, reconocimiento y neutro dentro de cada transformación y de cada tema, con IC. Sirve para priorizar.

**11.5 Cruces:** transformación declarada × grupo, × sede y × fecha (si hay varias); tema × transformación declarada, tema × grupo y tema × sede. Porcentajes con denominador explícito e IC.

**11.6 Asociación:** χ² de independencia por transformación y por tema frente a grupo, sede y ejercicio.

- Si más del 20 % de las celdas tienen esperado menor que 5, usa una prueba de permutación (10.000 permutaciones).
- Tamaño del efecto: V de Cramér.
- Comparaciones múltiples: Benjamini-Hochberg (q = 0,05) sobre todas las pruebas.
- Interpreta el tamaño del efecto, no solo la significancia.

**11.7 Voces representativas.** Por tema, 3 comentarios anonimizados, elegidos por esta regla fija: entre los asignados al tema, los 3 con mayor probabilidad; si hay empates, al azar con la semilla. Se excluyen los marcados para revisar. Nunca se eligen a mano.

**11.8 Coocurrencia:** matrices de conteo y de Jaccard entre transformaciones y entre temas.

**11.9 Excel(s)** 

- **Si hay una sola unidad regional (o si se procesa opción B con todas juntas):** `outputs/resultados_<slug_ejercicio>.xlsx`.
- **Si hay múltiples unidades regionales (opción A):** un Excel por unidad: `outputs/resultados_<fecha>_<unidad1>.xlsx`, `outputs/resultados_<fecha>_<unidad2>.xlsx`, etc. La taxonomía es compartida; cada Excel tiene sus propias métricas y cruces.

Cada Excel contiene estas hojas:

| Hoja | Contenido |
|---|---|
| Resumen | Ficha del ejercicio, N total, N_s, excluidos, residual, casos para revisar, modelo, versiones del marco y de la taxonomía, veredicto |
| Por_Transformacion | Por cada una de las 5: nombre oficial, n, % con IC, % corregido, % como principal, tipo de aporte y sus 5 temas más frecuentes |
| Arbol_Temas | Transformación → Tema, con n, % con IC y tipo de aporte |
| Fuera_del_marco | Temas y comentarios que no encajan en las 5 transformaciones, con frecuencia e IC |
| Detalle | Una fila por comentario: ids, grupo, sede, unidad regional, pregunta, `comentario_original`, `comentario_anon`, `trans_T1…T5` (0/1) con probabilidades, principal con confianza, temas (0/1) con probabilidades, tipo con confianza, sin_contenido, residual, incoherente, revisar y motivo |
| Transformacion_x_Grupo, Transformacion_x_Sede, Tema_x_Grupo | Conteos y porcentajes con fórmula |
| **[Si opción B]** Transformacion_x_UnidadRegional, Tema_x_UnidadRegional | Comparación entre unidades regionales |
| Asociaciones | χ², gl, p, q (BH), V de Cramér y método |
| Voces | 3 comentarios por tema, agrupados por transformación |
| Coocurrencia | Conteos y Jaccard |
| Validacion | Métricas de dev y test con IC, coherencia, umbrales, pruebas A/B |
| Marco_y_Taxonomia | Las 5 transformaciones y la taxonomía final |
| Cola_revision | Casos con `revisar = 1`, ordenados por motivo |
| Control | Matrices calculadas en pandas |

Detalles de construcción:

- Fórmulas escritas en inglés con openpyxl (`COUNTIFS`, `IFERROR`); Excel en español las muestra como `CONTAR.SI.CONJUNTO` y `SI.ERROR`. Porcentajes envueltos en `IFERROR`.
- Estilo: encabezados azul oscuro (`1F4E78`) con texto blanco en negrita, filas alternas blanco / azul claro (`DDEBF7`), bordes grises finos, primera fila inmovilizada, filtros automáticos y anchos ajustados.
- Si LibreOffice está disponible, recalcula en modo headless y verifica que las fórmulas coincidan con la hoja Control.

**11.9b Excel de registro de comentarios** `outputs/registro_comentarios_<slug_ejercicio>.xlsx`. Es un archivo aparte del de resultados, pensado para leer y revisar comentario por comentario. Con Opción A se genera uno por unidad regional (`registro_comentarios_<fecha>_<unidad>.xlsx`); con Opción B, uno solo con la columna `unidad_regional`.

*Estructura de hojas:*

| Hoja | Contenido |
|---|---|
| `Indice` | Unidad regional, fechas, modelo, N, y una tabla con una fila por hoja: transformación, n de comentarios, % del total, confianza media, % de concordancia con Jev, n marcados para revisar. Cada nombre de hoja es un hipervínculo. |
| `T1 <nombre corto>` … `T5 <nombre corto>` | Una hoja por transformación, con los comentarios cuya **transformación declarada** (la que trae el Excel) es esa. |
| `Sin_frente_declarado` | Solo si hay comentarios sin transformación en el Excel; se muestran con la transformación detectada por Jev. |
| `Sin_contenido` | Comentarios excluidos o con `sin_contenido = 1`, con su motivo (con su transformación declarada). |

Nombres de hoja: máximo 31 caracteres, sin `[ ] : * ? / \`. Si el nombre oficial es largo, usa `T<n> ` + las primeras palabras y deja el nombre completo en el título de la hoja. Cada pestaña lleva un color distinto por transformación.

*Encabezado de cada hoja (antes de la tabla):*

- **Fila 1 (combinada, texto grande y en negrita):** `Unidad regional: <unidad> | <T#>: <nombre oficial completo de la transformación>`. En `Fuera_del_marco` y `Sin_contenido`, el segundo bloque es el nombre de la hoja.
- **Fila 2:** `Ejercicio: <fecha o fechas> · <lugar> · n = <comentarios en la hoja> · Modelo: <modelo versionado> · Taxonomía v<x>`.
- **Fila 3:** una línea de lectura: "Confianza = probabilidad que asigna Jev, no es la exactitud del acierto; la exactitud se reporta en la hoja Validacion del Excel de resultados".
- **Fila 5:** encabezados de la tabla. Datos desde la fila 6.

*Columnas de la tabla (en este orden):*

| Columna | Contenido |
|---|---|
| `id_com` | Identificador estable del comentario |
| `unidad_regional` | Solo en Opción B (en Opción A va en el título) |
| `grupo`, `sede` | Del Excel original, si existen |
| `pregunta` | Pregunta a la que respondió, si hay varias |
| `comentario` | `comentario_anon` (anonimizado). El original solo se incluye si `params.yaml` tiene `incluir_original_en_registro: true`, y se avisa que ese archivo contiene datos sin anonimizar. |
| `tema_principal` | El tema asignado de mayor probabilidad **cuyo padre es la transformación de la hoja**. Si no hay ninguno: `(sin tema específico)`. Si el tema es `fuera_del_marco`, se muestra como `Fuera del marco: <tema>`. |
| `confianza_tema` (%) | Probabilidad del `tema_principal` |
| `otros_temas` | Otros temas asignados, en texto, cada uno con su %, ej. `Infraestructura (82 %); Internet (64 %)`. Se marcan con `*` los de otra transformación. |
| `transformacion_detectada` y `confianza_transformacion` (%) | Transformación principal que asignó Jev al contenido y su probabilidad |
| `concuerda` | Sí/No: si la detectada coincide con la declarada (hoja de la fila) |
| `tambien_aporta_a` | Otras transformaciones con Noul positivo, con su % |
| `tipo_aporte` y `confianza_tipo` (%) | Oportunidad de mejora, reconocimiento o neutro, con su probabilidad |
| `revisar` y `motivo` | Sí/No y la razón (baja confianza, incoherente, residual, frontera) |

*Reglas de construcción:*

- Cada comentario aparece **una sola vez**, en la hoja de su transformación declarada; lo que Jev detecta de otras transformaciones se ve en `transformacion_detectada` y `tambien_aporta_a`. Así los totales de las hojas suman N_s sin duplicados.
- Las confianzas se guardan como número (0–1) con formato de porcentaje `0,0 %`, nunca como texto, para que se puedan filtrar y ordenar.
- Orden por defecto: `tema_principal` (alfabético) y, dentro de cada tema, `confianza_tema` descendente.
- Formato condicional: escala de color de tres tonos sobre las columnas de confianza (rojo bajo → verde alto) y relleno ámbar en las filas con `revisar = Sí`.
- Estilo: encabezados `1F4E78` con texto blanco en negrita, filas alternas blanco / `DDEBF7`, texto del comentario con ajuste de línea y ancho de 70, primera fila de la tabla inmovilizada (con el título visible), filtros automáticos.
- Los conteos de la hoja `Indice` se escriben como fórmulas (`COUNTA`, `AVERAGE`, `COUNTIF`) sobre cada hoja, y el total debe coincidir con N_s; verifica con pandas y registra el resultado en `logs/decisiones.md`.
- Verificación final: la suma de filas de todas las hojas = comentarios clasificados (N_s menos los excluidos más los de `Sin_contenido`), sin ids repetidos.

**11.10 Gráficos** (PNG a 150 dpi, ejes desde cero en las barras, títulos que enuncian el hallazgo; en todos, un subtítulo con la fecha y el lugar del ejercicio):

- barras por transformación con IC;
- barras apiladas Transformación → Tema;
- tipo de aporte por transformación;
- mapa de calor transformación × grupo;
- curva de saturación y diagrama de fiabilidad.

**Si hay múltiples unidades regionales (opción B),** agregar:

- comparación lado a lado o paneles: barras por transformación en cada unidad, con IC;
- mapa de calor transformación × unidad regional;
- temas más frecuentes por unidad, en gráfico de barras horizontal.

**11.11 Informe metodológico** `outputs/informe_metodologico_<slug_ejercicio>.md`, con:

- la ficha del ejercicio;
- el marco (las 5 transformaciones con su referencia al documento);
- datos y definiciones, con sus denominadores;
- el método por fase;
- los resultados de validación con IC;
- los hallazgos principales por transformación y lo que queda fuera del marco;
- supuestos y limitaciones: idioma, n por tema, anonimización, autoselección de quienes comentan y la interpretación del documento marco;
- reproducibilidad: modelo, hashes, semilla y `requirements.txt`.

**11.12 Control de calidad.** Recorre el Apéndice C antes de declarar terminado.

> **PUNTO DE CONTROL FINAL.** Entrega la lista de archivos (incluido el Excel de registro, con una captura de texto de la fila 1 de cada hoja), un resumen ejecutivo de máximo 10 líneas (encabezado con la fecha y el lugar) y el checklist del Apéndice C marcado.

---

### Ejercicios posteriores (otra fecha, otro lugar u otra unidad regional)

Cuando Nicolás traiga un nuevo dataset de otro ejercicio con el mismo marco, **no se repite todo**. La configuración ya validada (marco, taxonomía, modelo, umbrales) se reutiliza.

**Por defecto: Opción A (frentes por unidad regional con taxonomía compartida).**

**Caso 1: Una nueva unidad regional (misma fecha).**

1. **Fase 0:** si es una unidad regional nueva en la misma fecha, Claude Code detecta el `slug_ejercicio` nuevo basado en la unidad.
2. **Fases 2 y 3:** perfil, limpieza y anonimización del dataset de esa unidad.
3. **Verificación de transferencia:** Nicolás etiqueta 100 comentarios de la nueva unidad, a ciegas. Se calcula el micro-F1 de transformaciones y el de temas, con IC.
   - Si ambos quedan dentro del IC 95 % obtenido en test (de las unidades ya procesadas), se continúa.
   - Si caen por debajo del límite inferior, se reporta la posible deriva.
4. **Fases 9, 10 y 11:** clasificación, residual y entregables.

**Caso 2: Nueva fecha (mismas unidades regionales).**

Repite el mismo flujo para todas las unidades de la nueva fecha, reutilizando la taxonomía.

**Caso 3: Cambiar a Opción B (análisis comparativo) después de Opción A.**

Si Nicolás decide en un segundo ejercicio comparar todas las unidades en un solo dataset con análisis comparativo, no es un cambio de configuración medio: implica revalidar con muestras mixtas entre unidades. Avisa en este caso.

---

## Apéndice A · Fórmulas (implementar en `src/metricas.py`)

```
Proporciones e intervalos
  Wilson 95 %:  [ p̂ + z²/(2n)  ±  z·√( p̂(1−p̂)/n + z²/(4n²) ) ] / (1 + z²/n)
  Regla de tres (0 eventos en n):  cota superior 95 % ≈ 3/n
  Tamaño de muestra:  n0 = z²·p(1−p)/e² ;  n = n0 / (1 + (n0−1)/N)

Clasificación binaria (por transformación o tema)
  Precisión P = VP/(VP+FP)          Sensibilidad Se = R = VP/(VP+FN)
  Especificidad Sp = VN/(VN+FP)     F1 = 2PR/(P+R)
  κ de Cohen = (p_o − p_e)/(1 − p_e),   p_e = Σ_c p_A(c)·p_B(c)

Multi-etiqueta (n comentarios, K elementos)
  micro-F1 = 2·ΣVP / (2·ΣVP + ΣFP + ΣFN)
  macro-F1 = (1/K') · Σ F1_k        (K' = elementos incluidos; indicar cuáles)
  Hamming loss = (1/(n·K)) · Σ_i Σ_k 1[ŷ_ik ≠ y_ik]
  Exact match = (1/n) · Σ_i 1[Ŷ_i = Y_i]
  Jaccard promedio = (1/n) · Σ_i |Y_i ∩ Ŷ_i| / |Y_i ∪ Ŷ_i|     (= 1 si ambos vacíos)

Coherencia jerárquica
  coherente_i = 1 si { padre(k) : tema_k asignado, padre(k) ≠ fuera_del_marco } ⊆ { T : trans_T asignada }
                  y (principal_i = ninguna  o  p_trans(principal_i) ≥ τ_T)
  tasa = (1/n) · Σ coherente_i   (con IC de Wilson)

Calibración
  Brier = (1/n) · Σ (p_i − y_i)²
  ECE = Σ_b (n_b/n) · | frecuencia_de_positivos_b − p_media_b |     (10 intervalos iguales)

Prevalencia corregida (Rogan-Gladen)
  p̃ = (p̂ + Sp − 1)/(Se + Sp − 1), truncada a [0, 1]

Asociación
  χ² = Σ (O − E)²/E ;   V de Cramér = √( χ² / (n·(min(f, c) − 1)) )
  Benjamini-Hochberg: ordenar p(1) ≤ … ≤ p(m);
    rechazar H(1)…H(i*), con i* = máx{ i : p(i) ≤ (i/m)·q }
    q-valor ajustado de i = mín_{j ≥ i} ( m·p(j)/j ), acotado a 1

Bootstrap percentil
  B réplicas remuestreando comentarios con reemplazo (semilla fija);
  IC 95 % = percentiles 2,5 y 97,5.
  Bootstrap pareado A/B: la misma remuestra para ambas variantes; IC de la diferencia.
```

## Apéndice B · Esqueleto de referencia del cliente Jev

Es un punto de partida, no código final. Verifica cada nombre de clase, parámetro y atributo contra `docs.typesafe.ai/sdk/python` antes de usarlo.

```python
# src/jev_cliente.py
import asyncio, hashlib, json
from dotenv import load_dotenv
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul

# Carga TYPESAFE_API_KEY desde .env automáticamente.
# Si no existe .env o la clave no está, load_dotenv() no falla,
# pero el cliente de TypeSafe lanzará un error cuando se intente conectar.
load_dotenv()  # busca .env en el directorio actual


def construir_preguntas(marco: list, tax: dict) -> dict:
    """Una sola petición: 5 Nouls de transformación + Choice principal
    + Nouls de temas + Choice 'tipo' + Noul 'sin_contenido'."""
    q = {}
    for t in marco:                                   # T1…T5
        q[f"trans_{t['id']}"] = Noul(
            instructions=t["instruccion"],
            criteria={"true": t["criterio_true"], "false": t["criterio_false"]},
        )
    opciones = {t["id"]: t["instruccion"] for t in marco}
    opciones["ninguna"] = "El comentario no se relaciona con ninguna de las cinco transformaciones."
    q["transformacion_principal"] = Choice(
        instructions="¿Con cuál de las cinco transformaciones se relaciona principalmente el `comentario`?",
        criteria=opciones,
    )
    for tema in tax["temas"]:
        q[tema["id"]] = Noul(
            instructions=tema["instruccion"],
            criteria={"true": tema["criterio_true"], "false": tema["criterio_false"]},
        )
    q["tipo"] = Choice(instructions="¿Qué tipo de aporte hace el `comentario`?",
                       criteria=tax["tipo"])
    q["sin_contenido"] = Noul(instructions=tax["sin_contenido"])
    return q


def clave_cache(modelo: str, state: dict, config_serializada: dict) -> str:
    payload = json.dumps({"m": modelo, "s": state, "q": config_serializada},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def clasificar(items, marco, tax, modelo, cache, concurrencia=8):
    preguntas = construir_preguntas(marco, tax)
    ids_noul = ([f"trans_{t['id']}" for t in marco]
                + [tm["id"] for tm in tax["temas"]] + ["sin_contenido"])
    ids_choice = ["transformacion_principal", "tipo"]
    config = {"marco": marco, "tax": tax}
    sem = asyncio.Semaphore(concurrencia)

    async with AsyncTypeSafeClient(model=modelo) as client:

        async def uno(item):
            state = {"comentario": item["comentario_anon"]}   # sin fecha, lugar, grupo ni sede
            k = clave_cache(modelo, state, config)
            if cache.contiene(k):
                return cache.obtener(k)
            async with sem:
                r = await client.system_one(state=state, questions=preguntas)
            fila = {
                "clave": k,
                "id_texto_unico": item["id_texto_unico"],
                "modelo": r.model,
                "nouls": {q: r.nouls[q].noul for q in ids_noul},
                "choices": {c: {"eleccion": r.choices[c].choice,
                                "prob": dict(r.choices[c].probabilities),
                                "conf": r.choices[c].confidence} for c in ids_choice},
                "input_tokens": r.usage.input_tokens,
            }
            cache.guardar(fila)          # append inmediato a cache/jev_respuestas.jsonl
            return fila

        resultados = await asyncio.gather(*(uno(i) for i in items),
                                          return_exceptions=True)

    # Separar éxitos y errores: los 401/422 detienen el proceso (Fase 9);
    # los demás se listan y se reintentan al final. Ninguno se descarta.
    return resultados
```

## Apéndice C · Checklist de calidad antes de entregar

- [ ] La ficha está completa, y la fecha y el lugar aparecen en el nombre de los archivos, en el Resumen, en los gráficos y en el informe.
- [ ] Las 5 transformaciones coinciden textualmente con el documento marco y tienen su referencia de página o sección.
- [ ] El número de filas de Detalle es igual al número de comentarios de entrada; no se perdió ninguno.
- [ ] Cada texto único tiene respuesta válida o está listado como error.
- [ ] Ninguna probabilidad es NaN ni está fuera de [0, 1]; las probabilidades de cada Choice suman 1 ± 0,01.
- [ ] La distribución de la transformación principal (T1…T5 + ninguna) suma 100 % de N_s.
- [ ] Todos los porcentajes están en [0 %, 100 %], con denominadores explícitos y no nulos.
- [ ] Las matrices hechas con fórmulas coinciden con la hoja Control.
- [ ] Se revisaron a mano 10 filas al azar de Detalle (comentario vs. transformaciones y temas asignados) y el resultado quedó en la bitácora.
- [ ] El test se evaluó una sola vez; la configuración congelada está documentada.
- [ ] El modelo versionado, los hashes del marco y de la taxonomía y la semilla aparecen en el Resumen y en el informe.
- [ ] Ningún output contiene la clave.
- [ ] El archivo `.env` está en el directorio raíz y contiene `TYPESAFE_API_KEY=<valor>` (sin espacios).
- [ ] `.env` está en `.gitignore` y nunca se ha subido a git.
- [ ] Los logs de la Fase 0 confirman que se cargó TYPESAFE_API_KEY desde `.env`, sin mostrar el valor.
- [ ] En el Excel de registro, cada hoja tiene en la fila 1 la unidad regional y el nombre oficial de la transformación; la suma de filas de todas las hojas coincide con los comentarios clasificados, sin ids repetidos.
- [ ] En el Excel de registro, las confianzas son números (0–1) con formato de porcentaje y no hay celdas vacías en `tema_principal` ni en `confianza_tema`.
- [ ] `comentario_anon` no contiene datos personales.
- [ ] El informe declara las limitaciones: idioma (Jev rinde mejor en inglés), n insuficiente en algunos temas, autoselección de quienes comentan e interpretación del documento marco.
- [ ] `pytest` pasa.

---

*Fin del prompt.*
