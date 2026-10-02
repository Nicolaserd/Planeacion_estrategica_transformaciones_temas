"""Fase 5 · Preguntas para Jev y prueba piloto (10 comentarios)."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from f00_ficha_entorno import bitacora, cargar_ficha  # noqa: E402
from jev_cliente import Cache, cargar_clave, clasificar, construir_preguntas  # noqa: E402

LIMITE_ESTADO_MAS_PREGUNTA = 32_000
LIMITE_PETICION = 64_000


def cargar_config():
    params = yaml.safe_load((RAIZ / "config" / "params.yaml").read_text(encoding="utf-8"))
    marco = yaml.safe_load((RAIZ / "config" / "marco_estrategico.yaml").read_text(encoding="utf-8"))
    ruta_tax = sorted((RAIZ / "config").glob("taxonomia_v*.yaml"))[-1]
    tax = yaml.safe_load(ruta_tax.read_text(encoding="utf-8"))
    hashes = {"marco": hashlib.sha256((RAIZ / "config" / "marco_estrategico.yaml").read_bytes()).hexdigest(),
              "taxonomia": hashlib.sha256(ruta_tax.read_bytes()).hexdigest(), "version_taxonomia": tax["version"]}
    return params, marco, tax, hashes


def verificar(fila: dict, marco, tax) -> list[str]:
    """Devuelve la lista de fallas de una respuesta (vacía si todo está bien)."""
    fallas = []
    esperadas = {f"trans_{t['id']}" for t in marco} | {t["id"] for t in tax["temas"]} | {"sin_contenido"}
    if set(fila["nouls"]) != esperadas:
        fallas.append(f"claves Noul: faltan {esperadas - set(fila['nouls'])}")
    for k, v in fila["nouls"].items():
        if not 0 <= v <= 1:
            fallas.append(f"{k} fuera de [0,1]: {v}")
    opciones = {"transformacion_principal": {t["id"] for t in marco} | {"ninguna"}, "tipo": set(tax["tipo"])}
    for c, ops in opciones.items():
        ch = fila["choices"].get(c)
        if ch is None:
            fallas.append(f"falta Choice {c}")
            continue
        if ch["eleccion"] not in ops or set(ch["prob"]) != ops:
            fallas.append(f"{c}: opción inválida")
        # La API redondea cada probabilidad a 2 decimales: el error máximo de la suma es 0,005 por opción.
        tolerancia = max(0.01, 0.005 * len(ops)) + 1e-9
        if abs(sum(ch["prob"].values()) - 1) > tolerancia:
            fallas.append(f"{c}: probabilidades suman {sum(ch['prob'].values()):.3f}")
        if not 0 <= ch["conf"] <= 1:
            fallas.append(f"{c}: confidence fuera de rango")
    return fallas


def main():
    cargar_clave()
    ficha = cargar_ficha()
    params, marco, tax, hashes = cargar_config()
    modelo = params["modelo_jev"]
    preguntas = construir_preguntas(marco, tax)

    df = pd.read_parquet(RAIZ / "data" / "interim" / "comentarios.parquet")
    unicos = df[df.excluido == 0].drop_duplicates("id_texto_unico")
    rng = np.random.default_rng(params["seed"])
    piloto = unicos.iloc[rng.choice(len(unicos), size=min(10, len(unicos)), replace=False)]
    items = piloto[["id_texto_unico", "comentario_anon"]].to_dict("records")

    extra = {"sha_taxonomia": hashes["taxonomia"], "slug_ejercicio": ficha["slug_ejercicio"]}
    ok, errores = asyncio.run(clasificar(items, marco, tax, modelo, Cache(), params["concurrencia_jev"], extra))
    if errores:
        raise SystemExit(f"Errores en el piloto: {errores}")

    fallas = {f["id_texto_unico"]: verificar(f, marco, tax) for f in ok}
    fallas = {k: v for k, v in fallas.items() if v}
    tokens = [f["input_tokens"] for f in ok]
    modelos = sorted({f["modelo"] for f in ok})
    costo_total = float(np.mean(tokens)) * len(unicos) * params["precio_usd_por_millon_tokens"] / 1e6

    tau = params["censo"]["tau_fijo"]
    tabla = []
    for _, r in piloto.iterrows():
        f = next(x for x in ok if x["id_texto_unico"] == r.id_texto_unico)
        tabla.append({
            "id_com": r.id_com,
            "comentario": r.comentario_anon[:90] + ("…" if len(r.comentario_anon) > 90 else ""),
            "transformaciones_p>=0.5": {k[6:]: round(v, 2) for k, v in f["nouls"].items() if k.startswith("trans_") and v >= tau},
            "principal": f"{f['choices']['transformacion_principal']['eleccion']} ({f['choices']['transformacion_principal']['conf']:.2f})",
            "temas_p>=0.5": {k: round(v, 2) for k, v in f["nouls"].items() if not k.startswith("trans_") and k != "sin_contenido" and v >= tau},
            "tipo": f"{f['choices']['tipo']['eleccion']} ({f['choices']['tipo']['conf']:.2f})",
            "sin_contenido": round(f["nouls"]["sin_contenido"], 2),
        })

    res = {"modelo_pedido": modelo, "modelos_respondieron": modelos, "n_preguntas_por_peticion": len(preguntas),
           "piloto_n": len(ok), "fallas": fallas,
           "input_tokens": {"media": float(np.mean(tokens)), "max": int(max(tokens))},
           "bajo_limites": max(tokens) < LIMITE_ESTADO_MAS_PREGUNTA and max(tokens) < LIMITE_PETICION,
           "textos_unicos": len(unicos), "costo_estimado_usd": round(costo_total, 5), "hashes": hashes, "tabla": tabla}
    (RAIZ / "logs" / "f05_piloto.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    bitacora(f"Fase 5: {len(preguntas)} preguntas por petición (5 Nouls de transformación, Choice principal, "
             f"{len(tax['temas'])} Nouls de tema, Choice tipo, Noul sin_contenido). Piloto 10: fallas={len(fallas)}, "
             f"modelo={modelos}, tokens medios={np.mean(tokens):.0f} (máx {max(tokens)}), costo estimado total "
             f"USD {costo_total:.5f}. Los ejemplos de la taxonomía no se envían a Jev.")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
