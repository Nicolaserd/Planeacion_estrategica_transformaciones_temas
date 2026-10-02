"""Fase 9 · Clasificación completa con Jev y asignación con umbrales fijos (protocolo B: censo)."""
import asyncio
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
import metricas as m  # noqa: E402
from f00_ficha_entorno import bitacora, cargar_ficha  # noqa: E402
from f05_preguntas_jev import cargar_config, verificar  # noqa: E402
from jev_cliente import Cache, cargar_clave, clasificar  # noqa: E402


def asignar(fila: dict, marco, tax, tau: float, c_estrella: float) -> dict:
    """Aplica los umbrales y las reglas de 9.4 a una respuesta de Jev."""
    ids_t = [t["id"] for t in marco]
    padre = {t["id"]: t["transformacion_padre"] for t in tax["temas"]}
    criticos = {t["id"] for t in tax["temas"] if t["critico"]}
    p_t = {t: fila["nouls"][f"trans_{t}"] for t in ids_t}
    p_tema = {t["id"]: fila["nouls"][t["id"]] for t in tax["temas"]}
    trans = {t for t, p in p_t.items() if p >= tau}
    temas = {t for t, p in p_tema.items() if p >= tau}
    ch_p, ch_t = fila["choices"]["transformacion_principal"], fila["choices"]["tipo"]
    principal = ch_p["eleccion"]
    sin_contenido = int(fila["nouls"]["sin_contenido"] >= tau)
    principal_incoherente = int(principal != "ninguna" and p_t[principal] < tau)
    coherente = m.coherente(temas, padre, trans, principal, p_t, tau)
    residual = int(not temas and not trans and not sin_contenido)
    motivos = []
    if residual:
        motivos.append("residual")
    if not coherente:
        motivos.append("incoherente")
    if principal_incoherente:
        motivos.append("principal_incoherente")
    if temas & criticos:
        motivos.append("tema_critico")
    if ch_p["conf"] < c_estrella:
        motivos.append("baja_confianza_principal")
    if ch_t["conf"] < c_estrella:
        motivos.append("baja_confianza_tipo")
    return {
        **{f"trans_{t}": int(t in trans) for t in ids_t},
        **{f"p_trans_{t}": p_t[t] for t in ids_t},
        "transformacion_principal": principal,
        "conf_principal": ch_p["conf"],
        **{f"p_principal_{k}": v for k, v in ch_p["prob"].items()},
        **{f"tema_{k}": int(k in temas) for k in p_tema},
        **{f"p_tema_{k}": v for k, v in p_tema.items()},
        "tipo": ch_t["eleccion"],
        "conf_tipo": ch_t["conf"],
        **{f"p_tipo_{k}": v for k, v in ch_t["prob"].items()},
        "p_sin_contenido": fila["nouls"]["sin_contenido"],
        "sin_contenido": sin_contenido,
        "residual": residual,
        "incoherente": int(not coherente),
        "principal_incoherente": principal_incoherente,
        "revisar": int(bool(motivos)),
        "motivo_revision": "; ".join(motivos),
        "modelo": fila["modelo"],
        "input_tokens": fila["input_tokens"],
    }


def main():
    cargar_clave()
    ficha = cargar_ficha()
    params, marco, tax, hashes = cargar_config()
    tau, c_est = params["censo"]["tau_fijo"], params["censo"]["c_estrella"]
    modelo = params["modelo_jev"]

    df = pd.read_parquet(RAIZ / "data" / "interim" / "comentarios.parquet")
    con = df[df.excluido == 0]
    unicos = con.drop_duplicates("id_texto_unico")[["id_texto_unico", "comentario_anon"]].to_dict("records")
    protocolo = m.protocolo_por_tamano(len(con), **params["regla_censo"])

    cache = Cache()
    extra = {"sha_taxonomia": hashes["taxonomia"], "slug_ejercicio": ficha["slug_ejercicio"]}
    ok, errores = asyncio.run(clasificar(unicos, marco, tax, modelo, cache, params["concurrencia_jev"], extra))
    if errores:  # reintento final de los que fallaron por causas transitorias
        pendientes = [u for u in unicos if u["id_texto_unico"] in {e[0] for e in errores}]
        ok2, errores = asyncio.run(clasificar(pendientes, marco, tax, modelo, cache, 2, extra))
        ok += ok2
    validas = {f["id_texto_unico"]: f for f in ok if not verificar(f, marco, tax)}
    if errores or len(validas) != len(unicos):
        raise SystemExit(f"Completitud fallida: {len(validas)}/{len(unicos)} válidas; errores={errores}")

    asign = pd.DataFrame([{"id_texto_unico": k, **asignar(f, marco, tax, tau, c_est)} for k, f in validas.items()])
    out = df.merge(asign, on="id_texto_unico", how="left")
    out.to_parquet(RAIZ / "data" / "interim" / "clasificacion.parquet", index=False)

    # Registro por llamada
    with (RAIZ / "logs" / "f09_llamadas.jsonl").open("w", encoding="utf-8") as f:
        for k, fila in validas.items():
            f.write(json.dumps({"id_texto_unico": k, "modelo": fila["modelo"], "input_tokens": fila["input_tokens"],
                                "marca_tiempo": fila.get("marca_tiempo"), "sha_taxonomia": hashes["taxonomia"],
                                "slug_ejercicio": ficha["slug_ejercicio"]}, ensure_ascii=False) + "\n")

    c = out[out.excluido == 0]
    N = len(c)
    ic = lambda k: [round(x, 3) for x in m.wilson(int(k), N)]  # noqa: E731
    tokens = int(c.drop_duplicates("id_texto_unico")["input_tokens"].sum())
    res = {
        "protocolo_segun_regla": protocolo,
        "completitud": f"{len(validas)}/{len(unicos)}",
        "modelos": sorted(c["modelo"].unique()),
        "por_transformacion_noul": {t["id"]: {"n": int(c[f"trans_{t['id']}"].sum()), "ic95": ic(c[f"trans_{t['id']}"].sum())} for t in marco},
        "principal": c["transformacion_principal"].value_counts().to_dict(),
        "por_tema": {t["id"]: {"n": int(c[f"tema_{t['id']}"].sum()), "ic95": ic(c[f"tema_{t['id']}"].sum())} for t in tax["temas"]},
        "tipo": c["tipo"].value_counts().to_dict(),
        "sin_contenido": int(c["sin_contenido"].sum()),
        "residual": {"n": int(c["residual"].sum()), "ic95": ic(c["residual"].sum())},
        "coherencia": {"n": int((1 - c["incoherente"]).sum()), "ic95": ic((1 - c["incoherente"]).sum())},
        "revisar": int(c["revisar"].sum()),
        "revisar_por_motivo": pd.Series([x for s in c["motivo_revision"] for x in s.split("; ") if x]).value_counts().to_dict(),
        "tokens_reales": tokens,
        "costo_real_usd": round(tokens * params["precio_usd_por_millon_tokens"] / 1e6, 5),
    }
    (RAIZ / "logs" / "f09_resumen.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    bitacora(f"Fase 9: Jev ({', '.join(res['modelos'])}) clasificó {res['completitud']} textos únicos; τ = {tau} fijo y c* = {c_est} "
             f"a priori (sin gold no se ajustan); residual {res['residual']['n']}/{N}; coherencia {res['coherencia']['n']}/{N}; "
             f"revisar {res['revisar']}/{N}; tokens {tokens}; costo real USD {res['costo_real_usd']}. "
             f"Regla de censo: {protocolo}.")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
