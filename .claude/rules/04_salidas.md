# 04 · Salidas (los dos Excel)

## Dónde y cómo se nombran

- **Carpeta:** `outputs/<nombre oficial de la transformación>/`, por ejemplo `outputs/UC para la Vida/`. `exportar` la crea si no existe.
- **Nombres:**
  - `Temas_<Unidad>_<fechas>_<Transformacion>.xlsx`
  - `Clasificacion_<Unidad>_<fechas>_<Transformacion>.xlsx`

  El nombre va sin tildes y con guiones bajos, por ejemplo `Temas_Ubate_2026-08-18_a_2026-08-19_UC_para_la_Vida.xlsx`. Las fechas son las que dio Nicolás: `AAAA-MM-DD_a_AAAA-MM-DD`, o una sola fecha.
- **Versiones anteriores:** en `outputs/<transformación>/version_N/`, con los mismos nombres.
  - `version_1/` guarda la primera entrega: temas sin consolidar y "Otros temas" en una sola celda.
  - Nunca se borran. Antes de regenerar un ejercicio con **otros temas**, copia sus Excel a `version_<N+1>/`.
  - Si solo cambia el formato y los temas son los mismos, se puede sobrescribir.

## Excel 1 · Temas (1 hoja, "Temas")

- **Filas de título (1 a 3):**
  - transformación, unidad y fechas;
  - número de respuestas y de comentarios, y el modelo de Jev;
  - cómo leer la tabla: umbral, % sobre N_s, sin tema, grupos de 5 a 8 personas y que la confianza no es exactitud.
- **Tabla desde la fila 5.** Columnas:
  - Componente de la transformación, con "(también: …)" si el tema fusiona componentes;
  - Tema;
  - Qué incluye (el `criterio_true`);
  - Comentarios (n según Jev) y % de comentarios;
  - IC 95 % inferior y superior (Wilson);
  - Confianza media (Jev);
  - Comentario con mayor confianza (anonimizado).
- **Orden de las filas:**
  1. los componentes, en el orden del documento marco;
  2. las frases de "Qué busca";
  3. la transformación en general;
  4. fuera de la transformación.
- Se agrega una fila "— Ningún comentario de esta unidad trató este componente" por cada componente sin temas.

## Excel 2 · Clasificación (1 sola hoja, nombrada como "Ubaté 18-19 ago 2026")

- **Una fila por respuesta del ejercicio**, incluidas las que no tienen comentario.
- **Primero, todas las columnas de la encuesta** que no estén vacías, en su orden original: ID, horas, Correo, Nombre, "Rol (Tipo de actor)", programa, unidad, transformación, valoración y comentario original.
- **Después:**
  - **Tema principal (Jev)**: el de mayor confianza ≥ 70 %. En su defecto, uno de estos valores:
    - "(sin comentario)";
    - "(sin contenido: motivo)";
    - "Sin tema asignado (más cercano: X)".
  - **Componente de la transformación**: el del tema principal.
  - **% confianza (Jev)**.
  - **Una columna por tema**, en el mismo orden que el Excel 1. Lleva el % de Jev si asignó ese tema y queda vacía si no. Sirve para filtrar "todos los grupos que hablaron de X" o para sumar.
- **Contiene Nombre y Correo:** es solo para uso local (ver `05_privacidad.md`).

## Formato (`src/excel_estilo.py`)

- **Encabezado:** fondo azul `1F4E78`, letra blanca en negrita, texto ajustado y bordes grises.
- **Filas:** alternas en azul claro `DDEBF7`.
- **Columnas de %:** formato `0.0%` y escala de color (0,5 rojo, 0,75 amarillo, 1 verde).
- **Navegación:** filtros en el encabezado y panel inmovilizado bajo el encabezado.

## Verificaciones automáticas

`exportar` falla si:
- el Excel 2 no tiene una fila por respuesta;
- hay filas sin tema principal o algún % fuera de [0, 1];
- los conteos del Excel 1 o la suma de las columnas de tema no cuadran con las asignaciones.

Después corre `python scripts/lote.py verificar <filtro>`.
