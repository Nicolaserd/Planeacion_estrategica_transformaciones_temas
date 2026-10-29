# Temas con BERT (BERTopic) · análisis paralelo

Este análisis es **paralelo e independiente** de la clasificación por ejercicio con Jev. Parte **solo de los datos en crudo** (`data/raw/`, los 6 formularios de Forms). No usa:
- los ejercicios ni sus fechas;
- los temas definidos por lectura;
- las clasificaciones de Jev.

Para cada **unidad regional × transformación** y para cada **transformación** (todas las unidades juntas) responde dos preguntas:
1. **¿Cuántos temas hay?** El número óptimo de temas, con la curva que lo justifica.
2. **¿Cuáles son?** Sus palabras clave, un nombre legible y el tema de cada comentario.

Las salidas están en `outputs_bertopic/`. El código es `scripts/bertopic_temas.py`.

## Cómo funciona

| Paso | Qué se hace |
|---|---|
| 1. Preparar | Se leen los formularios **sin cargar Nombre ni Correo**. Se excluyen las respuestas vacías o sin contenido ("ninguno", "ok"…) y se anonimiza el texto con las mismas reglas del proyecto (Ley 1581). Al final se revisan los nombres no detectados, y la revisión debe dar 0. |
| 2. Vectores (BERT) | Un modelo BERT multilingüe (`paraphrase-multilingual-mpnet-base-v2`) convierte cada comentario en un vector de significado: dos comentarios que dicen lo mismo con otras palabras quedan cerca. Corre en el equipo, así que ningún texto sale del computador. |
| 3. Número óptimo de temas | Se prueban de 2 a 15 temas, agrupando con KMeans sobre los vectores. Para cada número se mide la **estabilidad de cada tema**: se reagrupan 20 submuestras del 80 % de los comentarios y se verifica que cada tema reaparezca (Jaccard medio con su mejor pareja). **Se elige el mayor número de temas en el que todos los temas son estables** (≥ 0,75) y cada uno tiene al menos 5 comentarios o el 3 % del grupo. Si ninguno lo logra, se toma el mayor con estabilidad moderada (≥ 0,60). Si tampoco, el más estable, marcado como "débil, orientativo". Los umbrales son de Hennig (2007). |
| 4. Temas (BERTopic) | Con el número elegido, BERTopic agrupa los comentarios y extrae las palabras que caracterizan cada tema (c-TF-IDF, con diversidad MMR). |
| 5. Nombres | Claude lee las palabras clave y los 3 comentarios más representativos de cada tema y redacta un nombre corto (`config/bertopic/<grupo>.yaml`). El número de temas y su composición son de BERT. |

**Referencia automática.** También se corre BERTopic en su modo automático (UMAP + HDBSCAN), que decide solo cuántos temas hay pero deja comentarios "sin tema". Se reporta para comparar.

**Por qué la estabilidad y no la "mejor métrica".** En la primera versión el número se elegía con el mejor promedio de separación (silhouette) y coherencia (NPMI), y casi todos los grupos daban 2 temas. Al revisarlo se vio que:
- ninguna métrica tenía un pico claro;
- la separación es baja con cualquier número de temas (0,06 a 0,13), porque los comentarios comparten mucho vocabulario;
- NPMI, calculado sobre pocos comentarios, castiga los temas pequeños;
- con UMAP, la primera división separaba comentarios cortos de largos, es decir, el estilo y no el tema.

La estabilidad responde a una pregunta más útil: *¿cuántos temas aparecen siempre, aunque cambie la muestra?* Por eso los temas se agrupan sobre los vectores completos, sin UMAP.

## Cómo leer los Excel

**Por unidad × transformación:** `outputs_bertopic/<Transformación>/BERTopic_<Unidad>_<Transformación>.xlsx`

**Por transformación:** `BERTopic_<Transformación>_todas_las_unidades.xlsx`

| Hoja | Contenido |
|---|---|
| **Temas** | Nombre del tema, palabras clave, comentarios (n), % con intervalo de confianza del 95 % (Wilson), **estabilidad del tema**, afinidad media y el comentario más representativo. |
| **Clasificación** | Una fila por comentario con contenido: ID, fecha, rol, programa, comentario anonimizado, tema y **afinidad** (de 0 a 1: qué tan cerca está el comentario del centro de su tema). |
| **Número de temas** | La curva: para cada número de temas probado, la estabilidad del tema más débil y la media, el nivel (estable, moderada o débil), la separación, la coherencia, la diversidad, si cumple el tamaño mínimo y cuál se eligió. |
| **Por unidad** (solo en el de la transformación) | El % de los comentarios de cada unidad en cada tema. Así se comparan las unidades con una misma lista de temas. |

`outputs_bertopic/Resumen_BERTopic.xlsx` tiene una fila por grupo: comentarios, número óptimo de temas, métricas y la referencia HDBSCAN.

**Cómo interpretar las métricas:**
- **Estabilidad (0 a 1):** si el tema reaparece al cambiar la muestra.
  - ≥ 0,75: estable;
  - 0,60 a 0,75: un patrón que conviene leer con cautela;
  - < 0,60: no se sostiene.
- **Silhouette (−1 a 1):** qué tan separados están los temas. Con textos cortos y parecidos es normal que sea bajo, entre 0,05 y 0,15.
- **NPMI (−1 a 1):** qué tanto aparecen juntas las palabras de un tema en los mismos comentarios.

Silhouette y NPMI son solo descriptivas.

## Limitaciones

- **Un tema por comentario.** Un comentario que habla de dos asuntos queda en el más cercano.
- **El número óptimo es una elección razonada, no un valor único.** Si la curva es plana, números vecinos son casi igual de buenos.
- **Grupos pequeños.** Las unidades con menos de 20 comentarios no se modelan solas; entran en el modelo de su transformación. Con 20 a 40 comentarios los temas son orientativos.
- **Anclaje al Plan.** Los temas salen solo del texto: no están anclados a los componentes del Plan.
- **Fechas.** Se usan todas las fechas de cada unidad tal como vienen en el crudo, así que los conteos pueden diferir de los ejercicios.

## Cómo correrlo

Desde la raíz del proyecto, con `.venv`:
```
.venv\Scripts\python.exe scripts/bertopic_temas.py preparar
.venv\Scripts\python.exe scripts/bertopic_temas.py modelar  [filtro]
.venv\Scripts\python.exe scripts/bertopic_temas.py mostrar  [filtro]   # para redactar los nombres
.venv\Scripts\python.exe scripts/bertopic_temas.py exportar [filtro]
```

- **Filtro:** `filtro` es parte del id del grupo, por ejemplo `uc_digital`, `fusagasuga` o `todas_las_unidades`.
- **Reproducibilidad:** las semillas están fijas y los vectores quedan en `cache/bertopic_embeddings.npz`.
- **Nombres desactualizados:** si al volver a modelar cambian las palabras de un tema, `exportar` avisa y usa las palabras clave en lugar del nombre guardado.
