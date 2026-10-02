# 02 · Definición de temas

Los temas los defines tú (Claude) leyendo los comentarios, **nunca con palabras clave**.

## Principios

1. **Lee todos los comentarios anonimizados.** Hasta 385 comentarios es censo.
2. **Los temas salen de lo que dicen los comentarios**, pero cada uno debe ser coherente con la transformación del formulario. Su `componente` es, textualmente, uno de los "Componentes preliminares" de esa transformación en el documento marco, o una frase literal de su "Qué busca" (de 8 caracteres o más).
3. **Hay dos anclas especiales:**
   - `fuera_de_la_transformacion`: lo que no tiene anclaje en esa sección. Nunca se fuerza un anclaje.
   - `transformacion_en_general`: lo que se refiere a la transformación como un todo, como la conformidad ("ningún ajuste") o la claridad de sus conceptos.
4. **Haz una lista nueva por cada unidad.** No reutilices los temas de otra unidad, ni siquiera dentro de la misma transformación.

## Cuántos temas (decisión de Nicolás, 2026-10-02; `validar` lo exige)

| Regla | Valor |
|---|---|
| Máximo de temas por ejercicio | **10**. Fusiona los afines antes de crear uno nuevo. |
| Mínimo de comentarios de un tema anclado | **3 o el 5 % de N_s**, lo que sea mayor (`minimo_comentarios`) |
| Mínimo de un tema sobre la transformación en general | 2, porque es retroalimentación directa al texto de la transformación |
| Temas críticos (acoso, discriminación, seguridad) | Sin mínimo (`critico: true`) |
| Fuera de la transformación | **Un solo tema**, `id: otros_fuera` ("Otros asuntos fuera de la transformación"). Un asunto solo puede tener tema propio si reúne el **10 % de N_s** o más. |
| Solapamiento | Si dos temas se solapan con Jaccard > 0,5 en tu codificación, fusiónalos |

Con estas reglas, los 25 ejercicios de 2026 quedaron con entre 4 y 10 temas (212 en total, 342 antes de consolidar).

## Archivos que escribes

**`config/ejercicios/<slug>/temas.yaml`**
```yaml
transformacion: UC para la Vida
version: 2
temas:
  - id: convivencia_participacion           # minúsculas y guiones bajos; es la clave de Jev y de la caché
    nombre: "Convivencia, comunidad, participación y comunicación"   # lo que ve Nicolás
    componente: "Convivencia"               # literal del documento marco, o una de las dos anclas especiales
    otros_componentes: ["Valores democráticos"]   # opcional: los componentes de los temas fusionados
    justificacion: "Por qué este tema es de este componente."
    critico: false
    instruccion: "¿El `comentario` ...?"    # la pregunta sí/no que recibe Jev
    criterio_true: "Cuándo es sí."
    criterio_false: "Cuándo es no, con sus exclusiones."
    ejemplos_si: ["frase literal de un comentario", "otra"]
sin_contenido: "¿El `comentario` carece de contenido evaluable...?"
```
El "Qué incluye" del Excel de temas es el `criterio_true`, así que redáctalo para que lo entienda una persona.

**`logs/<slug>/codificacion.jsonl`**: una línea por comentario con contenido, incluidos los que no tienen ningún tema.
```
{"id_com": "123-P1", "temas": ["convivencia_participacion", "bienestar_salud_mental"]}
{"id_com": "124-P1", "temas": []}
```

## Redacción (lecciones aprendidas)

- **Exige una afirmación explícita en los temas generales y en los amplios.**
  - Ejemplos: "dice expresamente que no haría ningún ajuste"; en la exclusión, "pedir cualquier cosa concreta no cuenta".
  - Con redacción abierta, Jev los asigna a casi todo. En Girardot "conformidad" pasó de 40 a 7 al endurecerla, y "formación integral" en Ubaté pasó de 18 a 9, igual que la lectura.
- **Jev no ve la pregunta de la encuesta** ("¿Qué ajustaría en esta transformación?").
  - En los temas de conformidad, escríbela en la instrucción y da ejemplos de respuestas cortas: "nada", "ninguno", "ninguna, está perfecta", "no se me ocurre nada", "consideramos que sí se ajusta".
  - Sin eso, Jev no reconoce "Ninguna, está perfecta" (p = 0,04).
- **La `instruccion` debe cubrir lo mismo que el `criterio_true`.** Si la pregunta es más estrecha que el criterio, Jev se queda justo por debajo del 70 %.
- **Pon las exclusiones en `criterio_false`** cuando dos temas se tocan, por ejemplo: "pedir solo dinero tiene su propio tema".
- **"Menciona X" es literal para Jev.** Si basta con mencionarlo de paso, Jev lo asigna. Cuando importe, escribe "debe pedir o proponer X; mencionarlo de paso no basta".

## Fusionar temas

- El tema nuevo recibe un `id` nuevo, su `componente` es el del tema principal, y los demás componentes van en `otros_componentes`.
- **Conserva en `criterio_false` las exclusiones de los temas originales que apunten a temas que siguen aparte.** En Soacha · UC Inteligente, sin "hablar solo de IA tiene su propio tema", "Tecnología e infraestructura" subió a 44 frente a 25 de la lectura.
- Descarta las exclusiones que apuntaban a temas que quedaron dentro de la misma fusión.
- Traslada la codificación: cada comentario recibe el tema nuevo que contiene a sus temas anteriores.
- Antes de reemplazar una lista, guarda la anterior como `temas_vN.yaml` y `codificacion_vN.jsonl`, y los Excel en `outputs/<transformación>/version_N/`.

## Modelo a seguir

`config/ejercicios/ubate_2026-08-18_a_2026-08-19_uc_para_la_vida/temas.yaml` (versión 2.2) y su `temas_v1.yaml`, para comparar cómo era antes de consolidar.
