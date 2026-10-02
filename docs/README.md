# Clasificación de comentarios · Plan Estratégico 2027-2037 (UdeC)

Guía para el equipo de Planeación.

## Qué hace este proyecto

En los encuentros "Transformaciones que nos conectan", grupos de 5 a 8 personas respondieron un formulario por cada transformación del Plan. La pregunta abierta fue **"¿Qué ajustaría en esta transformación?"**.

El proyecto toma esas respuestas por **unidad regional y fechas** y:
1. **define los temas** de los que hablaron los grupos, ligados a los componentes de la transformación según el documento marco (`contexto/Transformaciones_estrategicas_5_frentes.md`);
2. **clasifica cada respuesta** en esos temas con Jev, un modelo de clasificación de TypeSafe, e indica qué tan seguro está (% de confianza);
3. **entrega dos Excel** por unidad.

## Cómo pedir un ejercicio

Basta con decirle a Claude, en este proyecto, cuatro datos:

> "Archivo: el de UC Digital en data/raw. Transformación: UC Digital. Unidad: Fusagasugá. Fechas: 28 de septiembre de 2026."

Claude hace el resto con las reglas de `.claude/CLAUDE.md` y `.claude/rules/`, y al final reporta:
- los temas, con el número de comentarios;
- lo que quedó fuera de la transformación;
- los componentes que nadie mencionó;
- las respuestas de otras fechas que no se incluyeron;
- el costo.

## Qué se entrega

Los dos Excel quedan en `outputs/<transformación>/`, por ejemplo `outputs/UC Digital/`.

### 1. `Temas_<Unidad>_<fechas>_<Transformación>.xlsx`

Es la lista de temas de esa unidad, con un tema por fila (10 como máximo). Columnas:

| Columna | Qué significa |
|---|---|
| Componente de la transformación | A qué componente del Plan se liga el tema. "La transformación en general" son los comentarios sobre la transformación como un todo. "Fuera de la transformación" son los asuntos que no son de esta transformación. |
| Tema | Nombre del tema |
| Qué incluye | Qué cuenta como parte del tema |
| Comentarios y % de comentarios | Cuántos grupos tocaron el tema. Un grupo puede tocar varios temas, así que los % no suman 100. |
| IC 95 % inf. y sup. | Rango probable del %. Si los rangos de dos temas se cruzan, no se puede decir que uno sea más frecuente que el otro. |
| Confianza media (Jev) | Qué tan seguro estuvo Jev, en promedio |
| Comentario con mayor confianza | Un ejemplo representativo (anonimizado) |

Al final aparecen los componentes de la transformación que **ningún** grupo mencionó.

### 2. `Clasificacion_<Unidad>_<fechas>_<Transformación>.xlsx`

Es toda la encuesta, con una fila por respuesta, más la clasificación de Jev al final:
- **Tema principal (Jev)**, su **componente** y su **% de confianza**;
- **una columna por tema**, con el % de Jev si asignó ese tema y vacía si no.

Para ver todos los grupos que hablaron de un tema, filtra la columna de ese tema por "no vacías". Para contarlos, usa CONTAR en esa columna.

Otros valores posibles del tema principal:
- "(sin comentario)": el grupo no escribió nada;
- "(sin contenido: …)": el grupo escribió algo como "ninguno" o "ok";
- "Sin tema asignado (más cercano: …)": ningún tema llegó al 70 % de confianza.

⚠️ **Este archivo trae Nombre y Correo. Es solo para uso interno**, de acuerdo con la Ley 1581 de 2012. No lo envíes fuera del equipo.

Junto a él está su **copia anonimizada**, `Clasificacion_…_anonimizado.xlsx`. Tiene las mismas columnas, pero Nombre y Correo aparecen como "[NOMBRE]" y "[CORREO]", y el comentario está anonimizado. Esa es la que se publica en GitHub y la que puedes compartir.

### Versiones anteriores

`outputs/<transformación>/version_1/` guarda la primera entrega. Allí había más temas (hasta 19 por unidad) y los temas secundarios iban en una sola celda. No se borra.

## Estado actual (2 de octubre de 2026)

Cada celda indica el número de temas y, entre paréntesis, los comentarios con contenido.

| Transformación | Ubaté (18-19 ago) | Zipaquirá (31 ago) | Girardot (7-8 sep) | Soacha (14-15 sep) | Chía (21-22 sep) |
|---|---|---|---|---|---|
| UC Digital | 8 (56) | 6 (23) | 10 (118) | 10 (71) | 8 (93) |
| UC Emprendedora e Innovadora | 8 (50) | 6 (21) | 9 (98) | 9 (75) | 9 (78) |
| UC Inteligente | 9 (40) | 6 (21) | 10 (119) | 10 (76) | 10 (92) |
| UC para la Vida | 9 (43) | 5 (20) | 10 (106) | 10 (77) | 10 (81) |
| UC Translocal | 9 (42) | 4 (17) | 9 (117) | 8 (64) | 10 (86) |

Pendiente: **Fusagasugá (28 sep)**, en las cinco transformaciones.

## Cómo leer los resultados con cuidado

- **Son grupos, no personas.** "12 comentarios" quiere decir 12 grupos de 5 a 8 personas.
- **El % de confianza no es el % de acierto.** Es qué tan seguro estuvo Jev. Para medir la calidad, se compara a Jev con una lectura de referencia: el acuerdo promedio es de 0,87 en una escala de 0 a 1, con un mínimo de 0,80 según la unidad.
- **Los temas amplios pueden salir algo altos.** Jev tiende a asignar de más los temas amplios, como "crecimiento personal" o "más tecnología". Claude lo revisa y lo informa en cada entrega.
- **Las unidades no se suman tema por tema.** Cada unidad tiene su propia lista de temas. Para comparar unidades, usa la columna "Componente de la transformación".
- **Las unidades pequeñas tienen poca precisión.** En Zipaquirá, con unos 20 comentarios, los porcentajes tienen rangos (IC) muy anchos.

## Estructura del proyecto

```
.claude/CLAUDE.md             Reglas esenciales para Claude (se leen solas en cada sesión)
.claude/rules/                Reglas detalladas: procedimiento, temas, Jev, salidas, privacidad, metodología
.claude/settings.json         Configuración de Claude Code: sin atribución en commits y PR, y registro de hooks
.claude/hooks/                Hooks: piden aprobación para cambiar .claude/ y exigen autoría única en commit y push
.githooks/                    Hooks de git para todo el equipo (commit-msg y pre-push): autoría única
docs/                         Esta guía y el historial de decisiones
contexto/                     Documento marco de las 5 transformaciones y PDF del Plan
data/raw/                     Archivos originales de Forms (uno por transformación)
data/interim/<ejercicio>/     Datos de trabajo: encuesta, comentarios anonimizados y clasificación
config/params.yaml            Parámetros: modelo de Jev, umbral de 70 %, regla de censo, precio
config/ejercicios/<ejercicio>/  Ficha del ejercicio y lista de temas (temas.yaml; temas_v1.yaml = versión 1)
logs/decisiones.md            Bitácora general del proyecto
logs/<ejercicio>/             Bitácora del ejercicio y lectura de referencia (codificacion.jsonl)
outputs/<transformación>/     Los Excel entregados (version_1/ = primera entrega)
src/ejercicio.py              Programa principal: preparar, validar, clasificar y exportar
scripts/                      Herramientas: lote.py (varios ejercicios) y revisar_jev.py (control de calidad)
tests/                        Pruebas automáticas
cache/                        Respuestas de Jev guardadas (evitan pagar dos veces)
```

Un **ejercicio** se nombra `unidad_fechas_transformación`, por ejemplo `girardot_2026-09-07_a_2026-09-08_uc_digital`.

## Reglas de trabajo con git y con Claude

- **Repositorio público.** El proyecto está en `github.com/Nicolaserd/Planeacion_estrategica_transformaciones_temas`. Allí nunca se suben los datos con Nombre o Correo (`data/`, los Excel de clasificación originales, los Excel de Forms), ni `cache/`, `.env` o el PDF del Plan Estratégico. Ya están excluidos en `.gitignore`. De `outputs/` se publican los Excel de temas y las copias `…_anonimizado.xlsx`.
- **Autoría única.** Los commits y los push quedan solo a nombre de quien hace el push, sin coautores ni atribución a Claude. Quien clone el repositorio ejecuta una vez `git config core.hooksPath .githooks`. Desde ese momento:
  - el mensaje de cada commit se limpia solo;
  - el push se cancela si incluye commits de otra persona o con coautores.
- **La carpeta `.claude/` está protegida.** Claude debe pedir aprobación antes de cambiar sus reglas, hooks o configuración.

## Glosario

| Término | Significado |
|---|---|
| Jev | Modelo de TypeSafe que responde preguntas sí/no sobre cada comentario, con una probabilidad |
| Umbral (70 %) | Confianza mínima de Jev para asignar un tema |
| Censo | Se leen y clasifican **todos** los comentarios (con 385 o menos no se usan muestras) |
| Componente | Cada parte de una transformación según el documento marco, por ejemplo "Convivencia" en UC para la Vida |
| Fuera de la transformación | Lo que los grupos dijeron que pertenece a otra transformación o a otros asuntos |
| IC 95 % | Rango dentro del cual está, con 95 % de confianza, el porcentaje real |
| Anonimización | Antes de cualquier análisis se reemplazan correos, teléfonos, cédulas y nombres de personas |
