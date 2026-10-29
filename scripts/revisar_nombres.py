"""Control de anonimización: busca nombres de personas que la anonimización automática no reemplazó.

Uso, desde la raíz del proyecto (después de `preparar` y antes de `clasificar`):
  .venv\\Scripts\\python.exe scripts/revisar_nombres.py [filtro]

Revisa `comentario_anon` de data/interim/<ejercicio>/comentarios.parquet y marca:
  whatsapp         encabezados de mensajes pegados ("[19/10, 10:06 a. m.] Nombre:") sin anonimizar
  firma            "Nombre Apellido, facultad/programa/docente..." sin anonimizar
  nombre_probable  3 o más palabras con mayúscula que empiezan por un nombre de pila de las columnas Nombre de data/raw
Nunca imprime el texto ni los nombres: solo el ejercicio y el id_com. Si hay hallazgos, revisa esos comentarios,
ajusta la anonimización (src/f03_limpieza_anonimizacion.py) y repite `preparar`.
"""
import re
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from f03_limpieza_anonimizacion import MAYUS, MINUS, normalizar  # noqa: E402

WHATSAPP = re.compile(r"\[\d{1,2}/\d{1,2}(?:/\d{2,4})?,?\s*\d{1,2}:\d{2}[^\]]*\]\s*(?!\[PERSONA\])[^:\[\]\n]{2,60}:")
FIRMA = re.compile(rf"\b[{MAYUS}][{MINUS}]+(?:\s+[{MAYUS}][{MINUS}]+){{1,4}}\s*,\s*"
                   r"(?i:facultad|programa|docente|gestor|coordinador|decano|director)")
SECUENCIA = re.compile(rf"\b([{MAYUS}][{MINUS}]+)(?:\s+[{MAYUS}][{MINUS}]+){{2,4}}\b")


def nombres_de_pila() -> set[str]:
    pilas = set()
    for f in (RAIZ / "data" / "raw").glob("*.xlsx"):
        df = pd.read_excel(f)
        col = next((c for c in df.columns if normalizar(str(c)) == "nombre"), None)
        if col is None:
            continue
        for v in df[col].dropna().astype(str):
            palabras = re.findall(r"[^\W\d_]+", v)
            if palabras and len(palabras[0]) >= 3:
                pilas.add(normalizar(palabras[0]))
    return pilas


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    pilas = nombres_de_pila()
    hallazgos = 0
    for f in sorted((RAIZ / "data" / "interim").glob("*/comentarios.parquet")):
        if filtro not in f.parent.name:
            continue
        for _, x in pd.read_parquet(f).iterrows():
            t = x.comentario_anon or ""
            tipos = [n for n, ok in (("whatsapp", WHATSAPP.search(t)), ("firma", FIRMA.search(t)),
                                     ("nombre_probable", any(normalizar(m.group(1)) in pilas for m in SECUENCIA.finditer(t))))
                     if ok]
            if tipos:
                hallazgos += 1
                print(f"  {f.parent.name} · {x.id_com} · {tipos}")
    print(f"{hallazgos} comentario(s) a revisar.")


if __name__ == "__main__":
    main()
