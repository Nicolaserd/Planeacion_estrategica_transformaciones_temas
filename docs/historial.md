# Historial de decisiones

Este es el resumen de las decisiones de Nicolás y de lo aprendido en el proyecto. El detalle completo, con cifras, está en `logs/decisiones.md`, y el de cada ejercicio en `logs/<ejercicio>/decisiones.md`.

## 2026-10-01 · Primer ejercicio y regla general

- **Primer ejercicio:** se ejecutó el prompt maestro (`PROMPT_clasificacion_jev_v2 (5).md`) con UC para la Vida en Ubaté (18 y 19 ago).
  - Solo había 44 comentarios con contenido, así que no se podía aplicar el diseño de muestras de 1.200 comentarios.
  - **Decisión:** censo (protocolo B), con la regla general N_s ≤ 385.
- **Unidad de análisis:** cada respuesta es de un **grupo de 5 a 8 personas**.
- **Entregables:** Nicolás pidió dos Excel, uno con la lista de temas y otro con la clasificación de **solo Jev** y su % de confianza. Se quitaron las columnas de la lectura de Claude.
- **Regla general por ejercicio:** archivo, transformación, unidad y fechas. Quedó en `CLAUDE.md` y `src/ejercicio.py` y define que:
  - los temas salen de los comentarios y se anclan a los componentes de la transformación del formulario;
  - hay una lista nueva por unidad;
  - el Excel de clasificación tiene una sola hoja con toda la encuesta, incluidos Nombre y Correo, para uso local;
  - los archivos se nombran por unidad, fechas y transformación.
- **Fechas:** se usan **solo las fechas indicadas**. En Ubaté se retiraron los ID 408 y 493, que eran de otra fecha.
- **UC para la Vida en las otras unidades:** se procesaron Zipaquirá (31 ago), Girardot (7-8 sep), Soacha (14-15 sep) y Chía (21-22 sep). Se agregó el ancla "la transformación en general".
- **Lección:** los temas generales deben exigir afirmaciones explícitas. En Girardot "conformidad" pasó de 40 a 7.
- **Umbral:** el de asignación de temas pasó de 50 % a **70 %**, calibrado contra la lectura de Claude (micro-F1 0,76 → 0,83).
- **Salidas:** se organizaron en una carpeta por transformación, `outputs/<transformación>/`.

## 2026-10-02 · Las 5 transformaciones y la versión 2

- **Lote completo:** se procesaron las 4 transformaciones restantes (UC Inteligente, UC Translocal, UC Digital y UC Emprendedora e Innovadora) en las 5 unidades.
  - Resultado: 25 ejercicios y 50 Excel.
  - Acuerdo con la lectura de Claude: 0,84. Costo: 0,20 USD.
- **Auditoría de temas:** había demasiados temas (13,7 por ejercicio, hasta 19). El 26 % tenía 3 comentarios o menos, el 25 % eran asuntos fuera de la transformación y había temas solapados.
- **Versión 2, aprobada por Nicolás:**
  - **Menos temas:**
    - máximo 10 por ejercicio;
    - mínimo 3 comentarios o el 5 % (2 para los temas sobre la transformación en general);
    - lo de fuera de la transformación en un solo tema, salvo los asuntos con el 10 % de los comentarios o más.
  - **Temas en columnas:** el Excel de clasificación lleva una columna por tema con el % de Jev, en lugar de "Otros temas" en una sola celda.
  - **Respaldo:** la versión 1 se conservó en `outputs/<transformación>/version_1/` y en `temas_v1.yaml` y `codificacion_v1.jsonl`.
  - **Resultado:**
    - temas: de 342 a 212;
    - temas con 3 comentarios o menos: de 90 a 16;
    - comentarios sin tema: de 204 a 191;
    - acuerdo: de 0,84 a 0,87.
    - Costo: 0,24 USD.
- **Lecciones:**
  - Jev **no ve la pregunta** de la encuesta. En los temas de conformidad hay que escribirla, o no reconoce "Ninguna, está perfecta".
  - Al fusionar temas hay que **conservar las exclusiones** ("la IA tiene su propio tema"). Sin ella, "Tecnología e infraestructura" de Soacha · UC Inteligente subió a 44 frente a 25.
- **Documentación:** se ordenó en `CLAUDE.md`, `.claude/rules/` y `docs/`. Después, a pedido de Nicolás, `CLAUDE.md` pasó a `.claude/CLAUDE.md`, junto a las reglas y los hooks. Las herramientas `scripts/lote.py` y `scripts/revisar_jev.py` pasaron a formar parte del proyecto.

- **Hooks (a pedido de Nicolás):**
  - **Autoría única en commit y push**, para quien hace el push y sin coautores ni atribución a Claude. Se aplica en `.claude/settings.json`, en el hook `.claude/hooks/autoria_git.py` y en los hooks de git `.githooks/commit-msg` y `pre-push`.
  - **Aprobación previa** para cualquier cambio en `.claude/`, mediante el hook `.claude/hooks/proteger_carpeta_claude.py`.
  - Hay pruebas en `tests/test_hooks.py`.

## Pendientes y puntos abiertos

- **Fusagasugá (28 sep):** falta en las 5 transformaciones.
- **Temas algo altos (versión 2):** Jev supera la lectura de referencia en 8 o más comentarios en estos temas:
  - Soacha · UC Digital, "Más tecnología y de vanguardia": 20 frente a 11;
  - Soacha · UC Inteligente, "Tecnología, infraestructura y espacios": 33 frente a 25;
  - Soacha · UC para la Vida, "Crecimiento personal": 24 frente a 15;
  - Ubaté · UC Inteligente, "Calidad y mejora continua": 17 frente a 9.
- **Respuestas como "ninguno", "nada" o "todo bien":** las respuestas que son solo eso se excluyen como "sin contenido" antes de Jev, así que **no** cuentan como conformidad. Son 64 de 2.036 respuestas en los 25 ejercicios. Nicolás puede decidir si deben contarse.
- **Exactitud real:** si se quiere medir, una persona que no haya visto los resultados de Jev etiqueta unos 30 comentarios por transformación (`.claude/rules/06_metodologia.md`).
