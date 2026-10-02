"""Genera la copia publicable (…_anonimizado.xlsx) de cada Excel de clasificación en outputs/, también en version_N/.

Uso, desde la raíz del proyecto:
  .venv\\Scripts\\python.exe scripts/anonimizar_outputs.py [filtro]

En la copia, Nombre pasa a "[NOMBRE]", el correo a "[CORREO]" y el comentario original a su versión anonimizada.
Los originales (con datos personales) no se tocan y nunca se suben al repositorio (ver .gitignore).
`exportar` ya genera la copia de la versión vigente; este script sirve para las versiones anteriores o para regenerarlas.
"""
import sys
from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
import ejercicio as ej  # noqa: E402

filtro = sys.argv[1] if len(sys.argv) > 1 else ""
n = 0
for ficha_ruta in sorted((RAIZ / "config" / "ejercicios").glob("*/ficha.yaml")):
    s = ficha_ruta.parent.name
    if filtro not in s:
        continue
    ficha = yaml.safe_load(ficha_ruta.read_text(encoding="utf-8"))
    com = pd.read_parquet(RAIZ / "data" / "interim" / s / "comentarios.parquet")
    carpeta = RAIZ / "outputs" / ficha["transformacion"]["nombre_oficial"]
    for sub in [carpeta, *sorted(carpeta.glob("version_*"))]:
        original = sub / ficha["archivos_salida"]["clasificacion"]
        if original.exists():
            destino = ej.copia_anonimizada(original, ficha["columna_comentario"], com)
            n += 1
            print(f"OK  {destino.relative_to(RAIZ)}")
print(f"{n} copia(s) anonimizada(s).")
