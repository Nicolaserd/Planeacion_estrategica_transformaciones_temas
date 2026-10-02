# Proyecto · Clasificación de comentarios por ejercicio (UdeC · Plan Estratégico 2027-2037)

Este proyecto clasifica los comentarios abiertos de la encuesta "Experiencia: Transformaciones que nos conectan" de la Universidad de Cundinamarca. Lo hace con Jev (TypeSafe), dentro de la transformación del formulario. Cada **ejercicio** combina una transformación, una unidad regional y unas fechas, y produce dos Excel: la lista de temas y la clasificación de cada respuesta.

Lo pide Nicolás (Planeación UdeC). Le gustan las aprobaciones cortas, las opciones cerradas y las salidas en Excel.

Este archivo (`.claude/CLAUDE.md`) resume lo esencial. Las reglas detalladas están en `.claude/rules/` (se cargan solas) y la guía para el equipo en `docs/`. Todas las rutas son relativas a la raíz del proyecto.

## Cuando Nicolás pida un ejercicio

Necesitas cuatro datos: **archivo** (.xlsx de Forms en `data/raw/`), **transformación**, **unidad regional** y **fechas**. Pregunta solo los que falten; lo demás ya está decidido aquí y en `.claude/rules/`.

| Paso | Qué hacer | Detalle |
|---|---|---|
| 1 | `python src/ejercicio.py preparar --archivo … --transformacion "…" --unidad "…" --fechas …` | `01_procedimiento.md` |
| 2 | Leer **todos** los comentarios anonimizados, definir los temas y codificar cada comentario | `02_temas.md` |
| 3 | `python src/ejercicio.py validar --ejercicio <slug>`, y corregir hasta que pase | `02_temas.md` |
| 4 | `python src/ejercicio.py clasificar --ejercicio <slug>` | `03_jev.md` |
| 5 | `python scripts/revisar_jev.py <slug>` y corregir la redacción de los temas marcados | `03_jev.md` |
| 6 | `python src/ejercicio.py exportar --ejercicio <slug>` | `04_salidas.md` |
| 7 | Reportar a Nicolás: archivos, temas por componente (n y %), temas fuera de la transformación, componentes sin comentarios, filas fuera de fecha y costo | `01_procedimiento.md` |

Usa siempre `.venv\Scripts\python.exe`. Para varios ejercicios a la vez: `python scripts/lote.py validar|clasificar|exportar|verificar [filtro]`.

## Reglas que nunca se rompen

- **Grupos, no personas.** Cada fila es la respuesta de un grupo de 5 a 8 personas. Reporta "grupos" o "comentarios".
- **Solo las fechas que dio Nicolás.** Las filas de otras fechas se reportan, pero no se incluyen salvo que él lo pida (`--incluir-ids`).
- **Temas:**
  - salen de los comentarios y se anclan a un componente de la transformación del formulario (`contexto/Transformaciones_estrategicas_5_frentes.md`);
  - hay una **lista nueva por unidad**;
  - **máximo 10 temas**;
  - lo que está fuera de la transformación va en **un solo tema**.
- **Umbral de Jev: 70 %.** El % es la probabilidad que asigna Jev, no la exactitud.
- **Censo** si hay 385 comentarios o menos.
- **Privacidad (Ley 1581 de 2012):**
  - a Jev y a ti solo llega texto anonimizado;
  - nunca imprimas Nombre ni Correo en el chat;
  - el Excel de clasificación es solo para uso local.
- **Clave de TypeSafe:** se lee de `.env` y nunca se imprime.
- **Modelo fijo:** `jev-1.13.0` (`config/params.yaml`), nunca `jev-latest`.
- **No borres nada sin confirmar.** Antes de regenerar con temas distintos, respalda los Excel en `outputs/<transformación>/version_N/`.
- **Bitácora:** registra cada decisión de Nicolás en `logs/<slug>/decisiones.md`, y las generales en `logs/decisiones.md`.

## Git y la carpeta `.claude/` (hooks)

### Única autoría en commit y push
Cada commit y cada push quedan **solo a nombre de la persona que hace el push**:
- no se agregan líneas `Co-Authored-By`;
- no se agrega "Generated with Claude Code" ni ninguna otra atribución a Claude o a herramientas;
- no se usa `--author` para firmar con otro nombre;
- los PR tampoco llevan atribución.

Esto se aplica en tres capas:

| Capa | Archivo | Qué hace |
|---|---|---|
| Configuración de Claude Code | `.claude/settings.json` | `attribution` vacío (`commit` y `pr`) e `includeCoAuthoredBy: false`: Claude no agrega atribución |
| Hook de Claude (PreToolUse, Bash/PowerShell) | `.claude/hooks/autoria_git.py` | **Bloquea** un `git commit` con coautores, atribución o `--author`, y un `git push` si algún commit por subir es de otro autor o trae coautores |
| Hooks de git (cualquier persona) | `.githooks/commit-msg` y `.githooks/pre-push` | `commit-msg` **quita** las líneas de coautoría y atribución; `pre-push` **cancela** el push si algún commit es de otro autor o tiene coautores |

### Repositorio (público)
El remoto es `https://github.com/Nicolaserd/Planeacion_estrategica_transformaciones_temas` (rama `main`) y es **público**. Quien clone el repositorio debe activar los hooks de git una vez:
```
git config core.hooksPath .githooks
```
**Nunca se suben** (decisión de Nicolás, 2026-10-02; ya están en `.gitignore`):
- datos con Nombre o Correo: `data/`, `outputs/` y cualquier `Experiencia*.xlsx` de Forms;
- `cache/` y `.env`;
- el PDF "06. PLAN ESTRATÉGICO 2027-2037…".

Antes de cada commit, revisa con `git diff --cached --name-only` que no se cuele nada de eso. Todo lo que se suba debe estar anonimizado.

### La carpeta `.claude/` no se toca sin preguntar
**Antes de crear, editar o borrar cualquier archivo en `.claude/`**, pide aprobación a Nicolás. Esto incluye este `CLAUDE.md`, las reglas, los hooks y la configuración. El hook `.claude/hooks/proteger_carpeta_claude.py` lo exige: ante un `Edit`, `Write` o un comando que escriba en `.claude/`, responde "ask" y Claude Code pide confirmación. `docs/` y el resto del proyecto no requieren aprobación.

Las pruebas de los hooks están en `tests/test_hooks.py`. Si cambias los hooks, revísalos con `/hooks` o reinicia la sesión.

## Dónde está cada cosa

| Necesito… | Archivo |
|---|---|
| Lo esencial (este archivo) | `.claude/CLAUDE.md` |
| El paso a paso con comandos, entradas y reporte | `.claude/rules/01_procedimiento.md` |
| Cómo definir, redactar, fusionar y validar temas | `.claude/rules/02_temas.md` |
| Cómo se usa Jev: umbral, caché, costo, límites y revisión | `.claude/rules/03_jev.md` |
| El formato de los dos Excel, los nombres, las carpetas y las versiones | `.claude/rules/04_salidas.md` |
| Privacidad, anonimización y clave | `.claude/rules/05_privacidad.md` |
| Unidad de análisis, censo, intervalos y validación completa | `.claude/rules/06_metodologia.md` |
| La guía para el equipo de Planeación | `docs/README.md` |
| La historia de decisiones del proyecto | `docs/historial.md` y `logs/decisiones.md` |
| La configuración y los hooks de Claude Code | `.claude/settings.json` y `.claude/hooks/` |
| Los hooks de git (commit y push) | `.githooks/` |
| El ejercicio modelo | `config/ejercicios/ubate_2026-08-18_a_2026-08-19_uc_para_la_vida/` |
