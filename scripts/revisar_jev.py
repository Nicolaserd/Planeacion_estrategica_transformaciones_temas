"""Compara la clasificación de Jev con la lectura de Claude (logs/<slug>/codificacion.jsonl), tema por tema.

Uso, desde la raíz del proyecto:
  .venv\\Scripts\\python.exe scripts/revisar_jev.py [filtro]
      Por ejercicio: acuerdo (micro-F1), conteo de Jev (J) y de la lectura (L) por tema, y temas a revisar.
  .venv\\Scripts\\python.exe scripts/revisar_jev.py <slug> --tema <id_tema>
      Comentarios (anonimizados) donde Jev y la lectura no coinciden en ese tema, con la probabilidad de Jev.

Marcas (regla de .claude/rules/03_jev.md):
  INFLADO        Jev ≥ 2 × lectura y Jev − lectura ≥ 8      → endurecer la redacción del tema
  SUBDETECTADO   lectura − Jev ≥ 4 y Jev ≤ 0,5 × lectura     → alinear la instrucción con el criterio
  ALTO           Jev − lectura ≥ 8 sin llegar al doble       → informar a Nicolás como conteo algo alto
La lectura de Claude es una referencia indicativa, no un etiquetado humano.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
import metricas as m  # noqa: E402


def cargar(s: str):
    tau = yaml.safe_load((RAIZ / "config" / "params.yaml").read_text(encoding="utf-8"))["umbral_tema_ejercicio"]
    temas = yaml.safe_load((RAIZ / "config" / "ejercicios" / s / "temas.yaml").read_text(encoding="utf-8"))["temas"]
    c = pd.read_parquet(RAIZ / "data" / "interim" / s / "clasificacion.parquet")
    c = c[c.excluido == 0].set_index("id_com")
    lineas = (RAIZ / "logs" / s / "codificacion.jsonl").read_text(encoding="utf-8").splitlines()
    cod = {x["id_com"]: set(x["temas"]) for x in map(json.loads, filter(str.strip, lineas))}
    return tau, temas, c, cod


def resumen(s: str) -> None:
    tau, temas, c, cod = cargar(s)
    ids = [t["id"] for t in temas]
    Y = np.array([[int(t in cod[i]) for t in ids] for i in c.index])
    Yh = (c[[f"p_{t}" for t in ids]].values >= tau).astype(int)
    print(f"\n{s} · N_s={len(c)} · micro-F1={m.micro_f1(Y, Yh):.2f} · sin tema (Jev)={int((Yh.sum(axis=1) == 0).sum())}")
    for j, t in enumerate(temas):
        J, L = int(Yh[:, j].sum()), int(Y[:, j].sum())
        marca = ("INFLADO" if J >= 2 * L and J - L >= 8 else
                 "SUBDETECTADO" if L - J >= 4 and J <= 0.5 * L else
                 "ALTO" if J - L >= 8 else "")
        print(f"  {t['id']:<40} J={J:>3} L={L:>3}  {marca}")


def desacuerdos(s: str, tema: str) -> None:
    tau, temas, c, cod = cargar(s)
    t = next((x for x in temas if x["id"] == tema), None)
    if t is None:
        raise SystemExit(f"El tema '{tema}' no está en {s}. Temas: {[x['id'] for x in temas]}")
    print(f"[{s}] {tema}\n  instrucción: {t['instruccion']}\n  sí: {t['criterio_true']}\n  no: {t['criterio_false']}")
    for i, x in c.iterrows():
        L, p = tema in cod[i], float(x[f"p_{tema}"])
        if L != (p >= tau):
            quien = "SOLO LECTURA" if L else "SOLO JEV    "
            print(f"  {quien} p={p:.2f} [{i}] {x.comentario_anon.strip()[:300]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--tema" in args:
        k = args.index("--tema")
        desacuerdos(args[0], args[k + 1])
    else:
        filtro = args[0] if args else ""
        slugs = sorted(p.parent.name for p in (RAIZ / "config" / "ejercicios").glob("*/ficha.yaml") if filtro in p.parent.name)
        if not slugs:
            raise SystemExit(f"Ningún ejercicio coincide con '{filtro}'.")
        for s in slugs:
            resumen(s)
