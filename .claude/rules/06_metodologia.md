# 06 · Metodología

## Unidad de análisis

Cada fila de la encuesta es la respuesta de un **grupo de 5 a 8 personas**, no de una persona. Por eso:
- reporta "grupos" o "comentarios", nunca "personas";
- los porcentajes son sobre **comentarios con contenido** (N_s), no sobre participantes;
- la columna "Rol (Tipo de actor)" es el rol declarado del grupo.

## Regla de censo (`metricas.protocolo_por_tamano`, `params.yaml > regla_censo`)

| Comentarios con contenido (N_s) | Protocolo |
|---|---|
| ≤ 385 | **Censo**: se leen y clasifican todos (todos los ejercicios de 2026 tienen entre 17 y 119) |
| 386 a 1.199 | Muestreo reducido: no alcanzan muestras disjuntas de descubrimiento, validación y estándar de oro |
| ≥ 1.200 | Diseño completo del prompt maestro (`PROMPT_clasificacion_jev_v2 (5).md`) |

Con 385 o menos, la muestra necesaria para ±5 pp con 95 % de confianza sería más de la mitad de N_s, así que conviene leerlos todos.

## Cifras de los Excel

- **n y %:** comentarios que Jev clasificó en el tema con confianza ≥ 70 %, sobre N_s. Un comentario puede tener varios temas, así que los % no suman 100.
- **IC 95 %:** intervalo de Wilson (`metricas.wilson`). Con N_s pequeño los intervalos son anchos; en Zipaquirá, con unos 20 comentarios, compara temas solo si los intervalos no se solapan.
- **Confianza:** la probabilidad que asigna Jev. **No es la exactitud.**
- **Temas por unidad:** cada unidad tiene su propia lista, así que los temas no se suman entre unidades. Lo comparable entre unidades es el **componente** de la transformación.

## Calidad de la clasificación

- **Referencia:** la lectura de Claude (`logs/<slug>/codificacion.jsonl`), comparada con `scripts/revisar_jev.py`.
- **Resultado:** acuerdo micro-F1 medio de 0,87 en la versión 2 (mínimo 0,80).
- **Es indicativo:** la lectura de Claude no es un etiquetado humano a ciegas. Si Nicolás quiere una medida de exactitud real, una persona que no haya visto los resultados de Jev etiqueta unos 30 comentarios por transformación y se compara.

## Validación metodológica completa (opcional)

El pipeline del prompt maestro (`src/f00`…`f11`, `PROMPT_clasificacion_jev_v2 (5).md`) sigue disponible para validar Jev contra un etiquetado humano a ciegas, con:
- κ por tema;
- calibración (ECE);
- coherencia jerárquica;
- los umbrales de aceptación de `params.yaml > aceptacion`.

Úsalo solo si Nicolás lo pide. Se aplicó una vez a Ubaté · UC para la Vida (2026-10-01); sus archivos son `logs/f0*.json` y `config/taxonomia_v1.yaml`, entre otros.

## Pruebas

```
.venv\Scripts\python.exe -m pytest -q tests
```
- `tests/test_ejercicio.py`: transformaciones, componentes, nombres, filtro de Ubaté y mínimos de temas.
- `tests/test_metricas.py`: Wilson, κ, F1, Benjamini-Hochberg y otras métricas.

Corre las pruebas después de cambiar `src/`.
