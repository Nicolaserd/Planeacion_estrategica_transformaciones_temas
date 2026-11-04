# Flujo combinado BERTopic → Jev

Este flujo une los dos análisis anteriores:
- **BERTopic** encuentra los temas de cada transformación en cada unidad regional y cuántos son;
- **Jev** clasifica cada comentario con esos temas, con las mismas reglas del flujo por ejercicio.

Es **independiente** de los otros dos: tiene su propia carpeta, sus propios datos intermedios y su propia caché de Jev. No cambia ni lee sus resultados.

| | Flujo por ejercicio (Jev) | Análisis con BERT | **Este flujo (BERT → Jev)** |
|---|---|---|---|
| Datos | Fechas de cada ejercicio | Crudo, todas las fechas | Crudo, todas las fechas |
| Quién define los temas | Claude, leyendo los comentarios | BERTopic | **BERTopic** |
| Número de temas | Lectura (máx. 10) | Estabilidad al remuestrear | **Estabilidad al remuestrear** |
| Anclaje al Plan | Componente de la transformación | No | **Componente de la transformación** |
| Clasificación | Jev, varios temas por comentario (≥ 70 %) | Un tema por comentario | **Jev, varios temas por comentario (≥ 70 %)** |
| Salidas | `outputs/` | `outputs_bertopic/` | **`flujo_bert_jev/salidas/`** |

## Pasos

Se corren desde la raíz del proyecto con `.venv\Scripts\python.exe`. `filtro` es parte del id del grupo, por ejemplo `uc_digital`, `fusagasuga` o `uc_digital__seccional_girardot`.

| Paso | Comando | Qué hace |
|---|---|---|
| 1 | `python flujo_bert_jev/flujo.py preparar` | Lee los 6 formularios en crudo, excluye las respuestas vacías o sin contenido, anonimiza y revisa nombres (debe dar 0). |
| 2 | `python flujo_bert_jev/flujo.py bert [filtro]` | Corre BERTopic en cada unidad × transformación: número óptimo de temas por estabilidad y temas. Una unidad con menos de 20 comentarios usa los temas de su transformación con todas las unidades. |
| 3 | `python flujo_bert_jev/flujo.py borrador [filtro]` | Escribe `temas/<grupo>.yaml` con los temas de BERT: nombre, palabras, comentarios típicos y firma. No pisa archivos existentes. |
| 4 | (Claude) | Completa cada tema: `componente`, `justificacion`, `instruccion`, `criterio_true` y `criterio_false`. |
| 5 | `python flujo_bert_jev/flujo.py validar [filtro]` | Verifica la plantilla (detalle abajo). |
| 6 | `python flujo_bert_jev/flujo.py clasificar [filtro]` | Jev responde una pregunta sí/no por tema y por comentario. Caché propia: `cache/jev_flujo_bert_jev.jsonl`. |
| 7 | `python flujo_bert_jev/flujo.py revisar [filtro]` | Compara Jev con la agrupación de BERT, tema por tema. |
| 8 | `python flujo_bert_jev/flujo.py exportar [filtro]` | Genera los Excel en `salidas/<Transformación>/` y el resumen. |

En el paso 4 se aplican las lecciones del flujo de Jev:
- la pregunta cubre lo mismo que el criterio;
- se ponen exclusiones hacia los temas vecinos;
- "mencionarlo de paso no basta";
- en los temas de conformidad va la pregunta de la encuesta, porque Jev no la ve.

`validar` comprueba que:
- estén todos los campos;
- el componente sea literal del documento marco (`contexto/Transformaciones_estrategicas_5_frentes.md`) o una de las dos anclas: "la transformación en general" o "fuera de la transformación";
- los temas sean exactamente los de BERT, con la misma firma.

## Salidas (`salidas/`)

Por cada unidad × transformación hay tres archivos, con el formato del flujo de Jev:

- **`Temas_<Unidad>_<Transformación>.xlsx`** (1 hoja). Columnas:
  - componente y tema;
  - qué incluye;
  - palabras clave de BERT;
  - **comentarios según BERT**: uno por comentario;
  - **comentarios según Jev**: pueden ser varios por comentario;
  - % con intervalo de confianza, confianza media y comentario con mayor confianza.
- **`Clasificacion_<Unidad>_<Transformación>.xlsx`** (1 hoja). Lleva toda la encuesta más el tema de BERT, el tema principal de Jev, el componente, el % de confianza y una columna por tema. **Trae Nombre y Correo: es solo para uso local** y nunca se sube (está en `.gitignore`).
- **`Clasificacion_…_anonimizado.xlsx`**: la copia publicable, con Nombre y Correo reemplazados y el comentario anonimizado.

`Resumen_flujo_BERT_Jev.xlsx` tiene una fila por grupo. Columnas:
- respuestas y comentarios;
- número de temas y estabilidad;
- asignaciones de Jev y comentarios sin tema;
- **acuerdo BERT–Jev**: el % de comentarios que tienen en Jev el tema que les dio BERT;
- temas a vigilar.

## Cómo leer el acuerdo y las marcas

BERT asigna **un** tema por comentario y Jev puede asignar **varios**, así que es normal que Jev cuente más comentarios en un tema. `revisar` marca los casos a revisar con los mismos criterios de `scripts/revisar_jev.py`:

| Marca | Condición | Qué significa |
|---|---|---|
| INFLADO | Jev ≥ 2 × BERT y la diferencia es de 8 o más | Jev asigna el tema a muchos más comentarios: endurecer la pregunta |
| SUBDETECTADO | BERT − Jev ≥ 4 y Jev ≤ la mitad de BERT | Jev reconoce el tema en pocos comentarios: alinear la pregunta con el criterio |
| ALTO | Jev − BERT ≥ 8 sin llegar al doble | Conteo algo alto: informarlo |

## Archivos de este flujo

| Ruta | Contenido | ¿Se sube? |
|---|---|---|
| `flujo_bert_jev/flujo.py` | Código del flujo | Sí |
| `flujo_bert_jev/temas/` | Temas de BERT con su componente y su pregunta para Jev | Sí |
| `flujo_bert_jev/salidas/` | Excel de temas, copias anonimizadas y resumen | Sí, salvo `Clasificacion_*.xlsx` sin anonimizar |
| `flujo_bert_jev/bitacora.md` | Registro de cada paso, con el costo de Jev | Sí |
| `flujo_bert_jev/informe/` | Informe Word del flujo con mapas de vectores y matrices BERT × Jev, y sus figuras | Sí |
| `data/flujo_bert_jev/` | Respuestas, modelos BERT y respuestas de Jev | No (`data/` está en `.gitignore`) |
| `cache/jev_flujo_bert_jev.jsonl` | Caché de Jev de este flujo | No |
