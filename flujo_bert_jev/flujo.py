"""Flujo combinado BERTopic → Jev, independiente de los dos flujos anteriores.

BERTopic encuentra el número óptimo de temas y los temas de cada transformación en cada unidad regional; Claude
ancla cada tema a un componente de la transformación y redacta la pregunta sí/no; Jev clasifica cada comentario con
esos temas (umbral 0,70, varios temas por comentario), igual que en el flujo por ejercicio.

Uso, desde la raíz del proyecto (con .venv):
  python flujo_bert_jev/flujo.py preparar             # crudo (todas las fechas) -> respuestas anonimizadas
  python flujo_bert_jev/flujo.py bert       [filtro]  # BERTopic por unidad × transformación
  python flujo_bert_jev/flujo.py borrador   [filtro]  # temas/<grupo>.yaml con los temas de BERT (sin pisar)
  (Claude completa en cada tema: componente, justificacion, instruccion, criterio_true, criterio_false, ejemplos_si)
  python flujo_bert_jev/flujo.py validar    [filtro]
  python flujo_bert_jev/flujo.py clasificar [filtro]  # Jev
  python flujo_bert_jev/flujo.py revisar    [filtro]  # Jev frente a la agrupación de BERT
  python flujo_bert_jev/flujo.py exportar   [filtro]  # Excel en flujo_bert_jev/salidas/

`filtro` es parte del id del grupo: "uc_digital", "fusagasuga", "uc_digital__seccional_girardot"...

Independencia: escribe solo en flujo_bert_jev/, data/flujo_bert_jev/ y cache/jev_flujo_bert_jev.jsonl. Del flujo de
Jev (src/) y del de BERTopic (scripts/bertopic_temas.py) solo importa funciones; no lee ni escribe sus resultados,
salvo los nombres legibles de config/bertopic/ como punto de partida cuando la firma del tema coincide.
Privacidad: a BERT, a Jev y a Claude solo llega texto anonimizado; el Excel de clasificación con Nombre y Correo es
de uso local y su copia _anonimizado.xlsx es la publicable.
"""
import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))
import bertopic_temas as bt  # noqa: E402
import ejercicio as ej  # noqa: E402
import metricas as m  # noqa: E402
from excel_estilo import ESCALA_CONF, tabla, titulo  # noqa: E402
from f03_limpieza_anonimizacion import anonimizar, motivo_exclusion, normalizar, tokens_nombres  # noqa: E402
from revisar_nombres import FIRMA, SECUENCIA, WHATSAPP, nombres_de_pila  # noqa: E402

CARPETA = RAIZ / "flujo_bert_jev"
DIR_TEMAS = CARPETA / "temas"
DIR_SALIDAS = CARPETA / "salidas"
BITACORA = CARPETA / "bitacora.md"
DIR_DATOS = RAIZ / "data" / "flujo_bert_jev"
DIR_BERT = DIR_DATOS / "bert"
DIR_JEV = DIR_DATOS / "jev"
CACHE_JEV = RAIZ / "cache" / "jev_flujo_bert_jev.jsonl"
FLUJO = "bert_jev"
CAMPOS = ("id", "nombre", "componente", "justificacion", "instruccion", "criterio_true", "criterio_false", "ejemplos_si")


# ---------------------------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------------------------

def bitacora(texto: str) -> None:
    nuevo = not BITACORA.exists()
    with BITACORA.open("a", encoding="utf-8") as f:
        if nuevo:
            f.write("# Bitácora · flujo combinado BERTopic → Jev\n\n")
        f.write(f"- **{date.today().isoformat()}** · {texto}\n")


def params() -> dict:
    return yaml.safe_load((RAIZ / "config" / "params.yaml").read_text(encoding="utf-8"))


def respuestas() -> pd.DataFrame:
    return pd.read_parquet(DIR_DATOS / "respuestas.parquet")


def grupos(res: pd.DataFrame) -> list[dict]:
    """Un grupo por transformación × unidad regional (las filas sin unidad no forman grupo)."""
    out = []
    for T in bt.ORDEN_T:
        unidades = sorted(u for u in res.loc[res.transformacion == T, "unidad"].unique() if u != bt.SIN_UNIDAD)
        out += [dict(id=f"{bt.slug(T)}__{bt.slug(U)}", T=T, U=U) for U in unidades]
    return out


def seleccion(filtro: str) -> list[dict]:
    lista = [g for g in grupos(respuestas()) if filtro in g["id"]]
    if not lista:
        raise SystemExit(f"Ningún grupo coincide con '{filtro}'.")
    return lista


def leer_json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def modelo_base(gid: str) -> dict:
    """Modelo BERT con el que se definen los temas del grupo (el propio o el de su transformación)."""
    info = leer_json(DIR_BERT / f"{gid}.json")
    return leer_json(DIR_BERT / f"{info['temas_de']}.json") if info.get("temas_de") else info


def etiquetas_bert(gid: str, ids_com) -> pd.Series:
    """Tema de BERT (número) de cada comentario del grupo."""
    base = modelo_base(gid)
    asig = pd.read_parquet(DIR_BERT / f"{base['id']}_asignaciones.parquet").set_index("id_com")
    return asig.loc[list(ids_com), "tema"]


def cargar_temas(gid: str) -> dict:
    ruta = DIR_TEMAS / f"{gid}.yaml"
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta.relative_to(RAIZ)}: correr 'borrador' y completar los temas.")
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def acuerdo_bert_jev(bert: pd.Series, asignados: dict, tema_de_bert: dict) -> float:
    """Proporción de comentarios cuyo tema de BERT está entre los temas que Jev asignó (≥ umbral)."""
    aciertos = [tema_de_bert.get(int(b)) in asignados.get(i, set()) for i, b in bert.items()]
    return float(np.mean(aciertos)) if aciertos else 0.0


def nombre_salida(prefijo: str, U: str, T: str) -> str:
    return f"{prefijo}_{bt.limpio(U)}_{bt.limpio(T)}.xlsx"


# ---------------------------------------------------------------------------------------------
# 1. preparar: crudo -> respuestas anonimizadas (todas las fechas)
# ---------------------------------------------------------------------------------------------

def preparar():
    mapeo = yaml.safe_load((RAIZ / "config" / "mapeo_columnas.yaml").read_text(encoding="utf-8"))
    (DIR_DATOS / "encuesta").mkdir(parents=True, exist_ok=True)
    filas, conteo, columnas = [], {}, {}
    for ruta in sorted((RAIZ / "data" / "raw").glob("*.xlsx")):
        T = bt.formulario_de_archivo(ruta)
        if T is None:
            continue
        df = pd.read_excel(ruta)
        col_txt = next(c for c in bt.PREGUNTAS_ABIERTAS if c in df.columns)
        toks = tokens_nombres(df) if "Nombre" in df.columns else set()
        cols_encuesta = [c for c in df.columns if df[c].notna().any()]   # sin las columnas vacías de Forms
        unidad = df[mapeo["unidad_regional"]].fillna(bt.SIN_UNIDAD).astype(str).str.strip()
        ids_com = [f"{bt.slug(T)}-{int(i)}" for i in df[mapeo["id_resp"]]]
        for (_, x), U, ic in zip(df.iterrows(), unidad, ids_com):
            motivo = motivo_exclusion(x[col_txt])
            texto = "" if motivo == "vacio" else str(x[col_txt]).strip()
            anon = anonimizar(texto, conteo) if texto else ""
            filas.append(dict(transformacion=T, unidad=U, id_resp=int(x[mapeo["id_resp"]]), id_com=ic,
                              fecha=pd.Timestamp(x[mapeo["fecha"]]).strftime("%Y-%m-%d"),
                              rol=x.get(mapeo["grupo"]), programa=x.get(mapeo["programa"]), comentario_anon=anon,
                              excluido=int(motivo is not None), motivo=motivo or "",
                              token_nombre=int(any(normalizar(w) in toks for w in re.findall(r"[^\W\d_]{4,}", anon)))))
        enc = df[cols_encuesta].copy()
        enc.insert(0, "id_com", ids_com)
        enc.to_parquet(DIR_DATOS / "encuesta" / f"{bt.slug(T)}.parquet", index=False)
        columnas[T] = dict(columnas=cols_encuesta, comentario=col_txt, archivo=ruta.name)
    res = pd.DataFrame(filas)
    pilas = nombres_de_pila()
    hallazgos = [x.id_com for x in res[res.excluido == 0].itertuples()
                 if WHATSAPP.search(x.comentario_anon) or FIRMA.search(x.comentario_anon)
                 or any(normalizar(mm.group(1)) in pilas for mm in SECUENCIA.finditer(x.comentario_anon))]
    res.to_parquet(DIR_DATOS / "respuestas.parquet", index=False)
    (DIR_DATOS / "preparar.json").write_text(json.dumps({"columnas": columnas, "anonimizacion": conteo,
                                                         "revision_nombres": len(hallazgos)}, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    tabla_n = res[res.excluido == 0].pivot_table(index="unidad", columns="transformacion", values="id_com",
                                                 aggfunc="count", fill_value=0)
    print(tabla_n[[t for t in bt.ORDEN_T if t in tabla_n.columns]].to_string())
    print(f"\n{len(res)} respuestas, {int((res.excluido == 0).sum())} con contenido · anonimización: {conteo} · "
          f"revisión de nombres: {len(hallazgos)}")
    bitacora(f"preparar: {len(res)} respuestas de {len(columnas)} formularios (todas las fechas), "
             f"{int((res.excluido == 0).sum())} con contenido; anonimización {conteo}; revisión de nombres {len(hallazgos)}.")
    if hallazgos:
        for h in hallazgos:
            print("  revisar:", h)
        raise SystemExit("Hay nombres sin anonimizar: ampliar src/f03_limpieza_anonimizacion.py antes de seguir.")


# ---------------------------------------------------------------------------------------------
# 2. bert: número óptimo de temas y temas por unidad × transformación
# ---------------------------------------------------------------------------------------------

def bert(filtro: str):
    bt.DIR_MODELOS = DIR_BERT          # los modelos de este flujo se guardan aparte (no tocan data/interim_bertopic)
    DIR_BERT.mkdir(parents=True, exist_ok=True)
    res = respuestas()
    com = res[res.excluido == 0]
    for g in seleccion(filtro):
        idx = com[(com.transformacion == g["T"]) & (com.unidad == g["U"])].index
        info = bt.modelar_grupo(dict(id=g["id"], nivel="unidad", T=g["T"], U=g["U"], idx=idx), com)
        if not info["modelado"]:
            pid = f"{bt.slug(g['T'])}__todas_las_unidades"
            if not (DIR_BERT / f"{pid}.json").exists():
                pinfo = bt.modelar_grupo(dict(id=pid, nivel="transformacion", T=g["T"], U=bt.TODAS,
                                              idx=com[com.transformacion == g["T"]].index), com)
                (DIR_BERT / f"{pid}.json").write_text(json.dumps(pinfo, ensure_ascii=False, indent=1), encoding="utf-8")
            info["temas_de"] = pid
        (DIR_BERT / f"{g['id']}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        base = modelo_base(g["id"])
        origen = f"temas de {base['id']} ({info['motivo']})" if info.get("temas_de") else "temas propios"
        print(f"OK  {g['id']:<56} N={info['N']:<4} k={base['k']} ({base['nivel_estabilidad']}) · {origen}")
        bitacora(f"bert {g['id']}: N={info['N']}, {base['k']} temas, estabilidad {base['estabilidad']:.2f} "
                 f"({base['nivel_estabilidad']}), {origen}.")


# ---------------------------------------------------------------------------------------------
# 3. borrador: temas de BERT -> temas/<grupo>.yaml (Claude completa la parte de Jev)
# ---------------------------------------------------------------------------------------------

def nombres_bert(base: dict) -> dict[int, str]:
    """Nombre legible de cada tema: el de config/bertopic/ si la firma coincide; si no, las palabras clave."""
    ruta = RAIZ / "config" / "bertopic" / f"{base['id']}.yaml"
    guardados = {}
    if ruta.exists():
        guardados = {int(t["tema"]): t for t in yaml.safe_load(ruta.read_text(encoding="utf-8"))["temas"]}
    return {t["tema"]: (guardados[t["tema"]]["nombre"] if t["tema"] in guardados
                        and guardados[t["tema"]]["firma"] == bt.firma(t["palabras"])
                        else ", ".join(t["palabras"][:3]).capitalize()) for t in base["temas"]}


def id_tema(numero: int, nombre: str) -> str:
    palabras = [w for w in bt.slug(nombre).split("_") if len(w) > 2][:4]
    return f"t{numero}_" + "_".join(palabras)


def borrador(filtro: str):
    DIR_TEMAS.mkdir(parents=True, exist_ok=True)
    res = respuestas().set_index("id_com")
    for g in seleccion(filtro):
        ruta = DIR_TEMAS / f"{g['id']}.yaml"
        if ruta.exists():
            print(f"--  {ruta.name} ya existe (no se pisa)")
            continue
        info, base = leer_json(DIR_BERT / f"{g['id']}.json"), modelo_base(g["id"])
        nombres = nombres_bert(base)
        ids_g = res[(res.transformacion == g["T"]) & (res.unidad == g["U"]) & (res.excluido == 0)].index
        bert_g = etiquetas_bert(g["id"], ids_g)
        temas = []
        for t in base["temas"]:
            ejemplos = [res.loc[c, "comentario_anon"] for c in t["representativos"] if c in ids_g][:3] or \
                       list(res.loc[bert_g[bert_g == t["tema"]].index[:3], "comentario_anon"])
            temas.append(dict(id=id_tema(t["tema"] + 1, nombres[t["tema"]]), nombre=nombres[t["tema"]],
                              tema_bert=t["tema"], firma=bt.firma(t["palabras"]), palabras=t["palabras"],
                              n_bert=int((bert_g == t["tema"]).sum()), componente="", justificacion="", instruccion="",
                              criterio_true="", criterio_false="", ejemplos_si=ejemplos, critico=False))
        datos = dict(grupo=g["id"], transformacion=g["T"], unidad=g["U"], temas_de=info.get("temas_de"),
                     bert=dict(N=info["N"], k=base["k"], estabilidad=round(base["estabilidad"], 3),
                               nivel=base["nivel_estabilidad"], modelo=bt.MODELO),
                     sin_contenido=ej.SIN_CONTENIDO, temas=temas)
        ruta.write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
        print(f"OK  {ruta.name}: {len(temas)} temas de BERT por completar")


# ---------------------------------------------------------------------------------------------
# 4. validar
# ---------------------------------------------------------------------------------------------

def errores_temas(temas: dict, base: dict) -> list[str]:
    trans = ej.resolver_transformacion(temas["transformacion"])
    lista, errores = temas["temas"], []
    ids = [t.get("id") for t in lista]
    if len(ids) != len(set(ids)):
        errores.append("ids de tema repetidos")
    for t in lista:
        vacios = [k for k in CAMPOS if not t.get(k)]
        if vacios:
            errores.append(f"{t.get('id')}: faltan o están vacíos {vacios}")
        for c in ej.componentes_del_tema(t) if t.get("componente") else []:
            if not ej.componente_valido(c, trans):
                errores.append(f"{t['id']}: el componente '{c}' no está en {trans['nombre_oficial']} (documento marco)")
    if len(lista) > ej.MAX_TEMAS:
        errores.append(f"{len(lista)} temas: el máximo es {ej.MAX_TEMAS}")
    esperados = {t["tema"]: bt.firma(t["palabras"]) for t in base["temas"]}
    if {t.get("tema_bert") for t in lista} != set(esperados):
        errores.append(f"los temas no son los de BERT: se esperan los números {sorted(esperados)}")
    errores += [f"{t['id']}: la firma no coincide con el modelo BERT (se volvió a modelar)"
                for t in lista if t.get("tema_bert") in esperados and t.get("firma") != esperados[t["tema_bert"]]]
    return errores


def validar(filtro: str, imprimir: bool = True) -> int:
    malos = 0
    for g in seleccion(filtro):
        errores = errores_temas(cargar_temas(g["id"]), modelo_base(g["id"]))
        if errores:
            malos += 1
            print(f"FALLA {g['id']}\n  - " + "\n  - ".join(errores))
        elif imprimir:
            print(f"OK    {g['id']}")
    if malos:
        raise SystemExit(f"{malos} grupo(s) con temas inválidos.")
    return 0


# ---------------------------------------------------------------------------------------------
# 5. clasificar con Jev
# ---------------------------------------------------------------------------------------------

def clasificar(filtro: str):
    from jev_cliente import Cache, cargar_clave, clasificar_preguntas, construir_preguntas_temas

    validar(filtro, imprimir=False)
    cargar_clave()
    p = params()
    modelo = p["modelo_jev"]
    res = respuestas()
    DIR_JEV.mkdir(parents=True, exist_ok=True)
    cache = Cache(CACHE_JEV)                       # caché propia de este flujo
    for g in seleccion(filtro):
        temas = cargar_temas(g["id"])
        lista, sin_cont = temas["temas"], temas["sin_contenido"]
        preguntas = construir_preguntas_temas(lista, sin_cont)
        ids_noul = [t["id"] for t in lista] + ["sin_contenido"]
        config = {"flujo": FLUJO, "sin_contenido": sin_cont,
                  "temas": [{k: t[k] for k in ("id", "instruccion", "criterio_true", "criterio_false")} for t in lista]}
        com = res[(res.transformacion == g["T"]) & (res.unidad == g["U"]) & (res.excluido == 0)].copy()
        mapa = {k: f"U{i + 1:03d}" for i, k in enumerate(dict.fromkeys(com.comentario_anon))}
        com["id_texto_unico"] = com.comentario_anon.map(mapa)
        unicos = com.drop_duplicates("id_texto_unico")[["id_texto_unico", "comentario_anon"]].to_dict("records")
        antes = len(cache._d)
        extra = {"flujo": FLUJO, "grupo": g["id"]}
        ok, errores = asyncio.run(clasificar_preguntas(unicos, preguntas, ids_noul, [], config, modelo, cache,
                                                       p["concurrencia_jev"], extra))
        if errores:
            pendientes = [u for u in unicos if u["id_texto_unico"] in {e[0] for e in errores}]
            ok2, errores = asyncio.run(clasificar_preguntas(pendientes, preguntas, ids_noul, [], config, modelo, cache, 2, extra))
            ok += ok2
        validas = {f["id_texto_unico"]: f for f in ok
                   if set(f["nouls"]) == set(ids_noul) and all(0 <= v <= 1 for v in f["nouls"].values())}
        if errores or len(validas) != len(unicos):
            raise SystemExit(f"{g['id']}: completitud fallida {len(validas)}/{len(unicos)}; errores={errores}")
        filas = [{"id_texto_unico": k, **{f"p_{q}": v for q, v in f["nouls"].items()}, "modelo": f["modelo"],
                  "input_tokens": f["input_tokens"]} for k, f in validas.items()]
        com.merge(pd.DataFrame(filas), on="id_texto_unico", how="left").to_parquet(DIR_JEV / f"{g['id']}.parquet", index=False)
        tokens = int(sum(f["input_tokens"] for f in validas.values()))
        nuevas = len(cache._d) - antes
        costo = tokens * p["precio_usd_por_millon_tokens"] / 1e6
        print(f"OK  {g['id']:<56} {len(validas)}/{len(unicos)} textos · llamadas nuevas {nuevas} · USD {costo:.5f}")
        bitacora(f"clasificar {g['id']}: Jev ({modelo}) · {len(validas)}/{len(unicos)} textos únicos válidos · "
                 f"{len(lista)} temas + sin_contenido · llamadas nuevas {nuevas} · tokens {tokens} · costo USD {costo:.5f}.")


# ---------------------------------------------------------------------------------------------
# 6. revisar: Jev frente a la agrupación de BERT
# ---------------------------------------------------------------------------------------------

def asignaciones(gid: str) -> tuple[pd.DataFrame, dict, list, float]:
    temas = cargar_temas(gid)
    lista = temas["temas"]
    tau = float(params().get("umbral_tema_ejercicio", ej.TAU_POR_DEFECTO))
    c = pd.read_parquet(DIR_JEV / f"{gid}.parquet")
    asig = {}
    for _, x in c.iterrows():
        ps = sorted(((t["id"], float(x[f"p_{t['id']}"])) for t in lista), key=lambda kv: -kv[1])
        asig[x.id_com] = {"asignados": [(k, pp) for k, pp in ps if pp >= tau], "max": ps[0]}
    return c, asig, lista, tau


def revision_grupo(gid: str) -> dict:
    c, asig, lista, _ = asignaciones(gid)
    bert_g = etiquetas_bert(gid, c.id_com)
    tema_de_bert = {t["tema_bert"]: t["id"] for t in lista}
    sets = {i: {k for k, _ in a["asignados"]} for i, a in asig.items()}
    filas = []
    for t in lista:
        n_jev = sum(t["id"] in s for s in sets.values())
        n_bert = int((bert_g == t["tema_bert"]).sum())
        ambos = sum(t["id"] in sets[i] for i in bert_g[bert_g == t["tema_bert"]].index)
        marca = ("INFLADO" if n_jev >= 2 * n_bert and n_jev - n_bert >= 8 else
                 "SUBDETECTADO" if n_bert - n_jev >= 4 and n_jev <= 0.5 * n_bert else
                 "ALTO" if n_jev - n_bert >= 8 else "")
        filas.append(dict(id=t["id"], nombre=t["nombre"], n_jev=n_jev, n_bert=n_bert, en_ambos=ambos, marca=marca))
    return dict(grupo=gid, N=len(c), temas=filas, acuerdo=acuerdo_bert_jev(bert_g, sets, tema_de_bert),
                sin_tema=sum(1 for s in sets.values() if not s))


def revisar(filtro: str):
    for g in seleccion(filtro):
        r = revision_grupo(g["id"])
        print(f"\n== {g['id']} · N={r['N']} · acuerdo BERT–Jev {r['acuerdo']:.0%} · sin tema (Jev) {r['sin_tema']}")
        for f in r["temas"]:
            print(f"   {f['id']:<42} Jev {f['n_jev']:>3} · BERT {f['n_bert']:>3} · en ambos {f['en_ambos']:>3} {f['marca']}")


# ---------------------------------------------------------------------------------------------
# 7. exportar: los dos Excel del flujo de Jev, con los temas de BERT
# ---------------------------------------------------------------------------------------------

def exportar(filtro: str):
    p = params()
    info_prep = leer_json(DIR_DATOS / "preparar.json")
    res = respuestas()
    resumen = []
    for g in seleccion(filtro):
        T, U, gid = g["T"], g["U"], g["id"]
        temas = cargar_temas(gid)
        trans = ej.resolver_transformacion(T)
        anclas, titulo_comp = ej.etiquetas_ancla(trans)
        general = bool(trans.get("general"))
        c, asig, lista, tau = asignaciones(gid)
        por_id = {t["id"]: t for t in lista}
        bert_g = etiquetas_bert(gid, c.id_com)
        tema_de_bert = {t["tema_bert"]: t["id"] for t in lista}
        rev = revision_grupo(gid)
        N_s = len(c)
        grupo = res[(res.transformacion == T) & (res.unidad == U)]
        N = len(grupo)
        modelo = ", ".join(sorted(c["modelo"].dropna().unique()))
        fechas = f"{grupo.fecha.min()} a {grupo.fecha.max()}"
        b = temas["bert"]
        origen = (f"temas del modelo de {T} con todas las unidades (la unidad tiene menos de {bt.N_MIN_GRUPO} comentarios)"
                  if temas.get("temas_de") else f"{b['k']} temas, estabilidad {b['estabilidad']:.2f} ({b['nivel']})")
        comp = lambda k: anclas.get(por_id[k]["componente"], por_id[k]["componente"])  # noqa: E731

        def comp_con_otros(k):
            otros = [x for x in por_id[k].get("otros_componentes", []) if x not in anclas]
            return comp(k) + (f" (también: {'; '.join(otros)})" if otros else "")

        # ---------- Excel 1: temas ----------
        orden_comp = trans["componentes"]
        grupo_orden = lambda cc: 0 if cc in orden_comp else {ej.GENERAL: 2, ej.FUERA: 3}.get(cc, 1)  # noqa: E731
        orden_temas = sorted(lista, key=lambda t: (grupo_orden(t["componente"]),
                                                   orden_comp.index(t["componente"]) if t["componente"] in orden_comp else 0,
                                                   t["tema_bert"]))
        filas1 = []
        for t in orden_temas:
            con_tema = [(i, pp) for i, a in asig.items() for kk, pp in a["asignados"] if kk == t["id"]]
            n = len(con_tema)
            lo, hi = m.wilson(n, N_s)
            mejor = max(con_tema, key=lambda ip: ip[1]) if con_tema else None
            texto = (f"({mejor[1]:.0%}) " + c.loc[c.id_com == mejor[0], "comentario_anon"].iloc[0]) if mejor else ""
            filas1.append([comp_con_otros(t["id"]), t["nombre"], t["criterio_true"], ", ".join(t["palabras"][:6]),
                           int((bert_g == t["tema_bert"]).sum()), n, n / N_s, lo, hi,
                           float(np.mean([pp for _, pp in con_tema])) if n else None, texto])
        cubiertos = {x for t in lista for x in ej.componentes_del_tema(t)}
        for vacio in [x for x in orden_comp if x not in cubiertos]:
            filas1.append([vacio, "— Ningún aporte trató esta transformación" if general
                           else "— Ningún tema de esta unidad trató este componente", "", "", 0, 0, 0.0, None, None, None, ""])
        sin_tema = sum(1 for a in asig.values() if not a["asignados"])
        wb = Workbook()
        ws = wb.active
        ws.title = "Temas"
        titulo(ws, [f"Temas (BERTopic + Jev) · {T} · {U} · todas las fechas",
                    f"{U} · {fechas} · {'Formulario' if general else 'Transformación'}: {T} · {N} respuestas, {N_s} con "
                    f"comentario · Temas: BERTopic ({b['modelo'].split('/')[-1]}; {origen}) · Clasificado por Jev ({modelo})",
                    f"Los temas y su número salen de BERTopic; cada uno se ancló a "
                    f"{'una de las 5 transformaciones' if general else 'un componente de ' + T} y Jev clasificó cada "
                    f"comentario (confianza ≥ {tau:.0%}; un comentario puede tener varios temas). «Según BERT» = comentarios "
                    f"que BERT puso en el tema (uno por comentario). % sobre {N_s} comentarios. Sin tema asignado por Jev: "
                    f"{sin_tema}. Acuerdo BERT–Jev: {rev['acuerdo']:.0%} de los comentarios tienen en Jev el tema que les dio "
                    "BERT. Cada respuesta es de un grupo de 5 a 8 personas. Confianza = probabilidad de Jev, no exactitud."], 11)
        ult = tabla(ws, 5, [titulo_comp, "Tema", "Qué incluye", "Palabras clave (BERT)", "Comentarios según BERT",
                            "Comentarios (Jev)", "% de comentarios (Jev)", "IC 95 % inf.", "IC 95 % sup.",
                            "Confianza media (Jev)", "Comentario con mayor confianza (anonimizado)"],
                    filas1, [30, 38, 55, 34, 11, 11, 11, 9, 9, 12, 75], pct_cols=(7, 8, 9, 10), wrap_cols=(1, 2, 3, 4, 11))
        ws.conditional_formatting.add(f"J6:J{ult}", ColorScaleRule(**ESCALA_CONF))
        carpeta = DIR_SALIDAS / re.sub(r'[<>:"/\\|?*]', " ", T).strip()
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta1 = carpeta / nombre_salida("Temas", U, T)
        wb.save(ruta1)

        # ---------- Excel 2: encuesta completa + tema de BERT + clasificación de Jev ----------
        col_info = info_prep["columnas"][T]
        cols, col_com = col_info["columnas"], col_info["comentario"]
        enc = pd.read_parquet(DIR_DATOS / "encuesta" / f"{bt.slug(T)}.parquet").set_index("id_com").loc[grupo.id_com]
        ids_orden = [t["id"] for t in orden_temas]
        encabezados = ["Rol (Tipo de actor)" if x == "Tipo de actor" else x for x in cols] + [
            "Tema (BERT)", "Tema principal (Jev)", titulo_comp, "% confianza (Jev)"] + [por_id[k]["nombre"] for k in ids_orden]
        info_g = grupo.set_index("id_com")
        filas2 = []
        for ic, e in enc.iterrows():
            x = info_g.loc[ic]
            por_tema = [None] * len(ids_orden)
            tema_bert = ""
            if x.excluido:
                principal = "(sin comentario)" if x.motivo == "vacio" else f"(sin contenido: {x.motivo})"
                componente, conf = "", None
            else:
                tema_bert = por_id[tema_de_bert[int(bert_g.loc[ic])]]["nombre"]
                a = asig[ic]
                if a["asignados"]:
                    k, pp = a["asignados"][0]
                    principal, componente, conf = por_id[k]["nombre"], comp(k), pp
                    for kk, pk in a["asignados"]:
                        por_tema[ids_orden.index(kk)] = pk
                else:
                    principal = f"Sin tema asignado (más cercano: {por_id[a['max'][0]]['nombre']})"
                    componente, conf = "", a["max"][1]
            valores = [None if (isinstance(v, float) and np.isnan(v)) else (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v)
                       for v in (e[cc] for cc in cols)]
            filas2.append(valores + [tema_bert, principal, componente, conf] + por_tema)
        formatos = {j: "yyyy-mm-dd hh:mm" for j, cc in enumerate(cols, start=1) if str(enc[cc].dtype).startswith("datetime")}
        wb2 = Workbook()
        ws2 = wb2.active
        ws2.title = re.sub(r"[\[\]:*?/\\]", " ", U)[:31]
        j_com = cols.index(col_com) + 1
        j_pct = len(cols) + 4
        j_temas = list(range(j_pct + 1, j_pct + 1 + len(ids_orden)))
        ult2 = tabla(ws2, 1, encabezados, filas2, [70 if cc == col_com else 18 for cc in cols] + [36, 40, 30, 11] + [18] * len(ids_orden),
                     pct_cols=(j_pct, *j_temas), wrap_cols=(j_com, len(cols) + 1, len(cols) + 2, len(cols) + 3), formatos=formatos)
        ws2.conditional_formatting.add(f"{get_column_letter(j_pct)}2:{get_column_letter(j_temas[-1])}{ult2}",
                                       ColorScaleRule(**ESCALA_CONF))
        ruta2 = carpeta / nombre_salida("Clasificacion", U, T)
        wb2.save(ruta2)
        ruta2_anon = ej.copia_anonimizada(ruta2, col_com, grupo)   # la que se puede publicar

        # Verificaciones (como en el flujo de Jev)
        n_asig = sum(len(a["asignados"]) for a in asig.values())
        assert len(filas2) == N, f"{gid}: el Excel 2 no tiene una fila por respuesta"
        assert all(f[len(cols) + 1] for f in filas2), f"{gid}: hay filas sin 'Tema principal'"
        assert sum(f[5] for f in filas1) == n_asig, f"{gid}: los conteos del Excel 1 no cuadran"
        assert sum(v is not None for f in filas2 for v in f[j_pct:]) == n_asig, f"{gid}: las columnas de tema no cuadran"
        assert sum(f[4] for f in filas1) == N_s, f"{gid}: los conteos de BERT no cuadran"
        bitacora(f"exportar {gid}: {ruta1.name}, {ruta2.name} (uso local, con Nombre y Correo) y {ruta2_anon.name} "
                 f"(publicable); {len(lista)} temas, {n_asig} asignaciones de Jev, {sin_tema} sin tema, "
                 f"acuerdo BERT–Jev {rev['acuerdo']:.0%}.")
        marcas = "; ".join(f"{f['nombre']} ({f['marca'].lower()}: Jev {f['n_jev']}, BERT {f['n_bert']})"
                           for f in rev["temas"] if f["marca"])
        resumen.append([T, U, N, N_s, "de la transformación" if temas.get("temas_de") else "propios", b["k"],
                        b["estabilidad"], b["nivel"], n_asig, sin_tema, sin_tema / N_s, rev["acuerdo"], marcas,
                        f"{T}/{ruta1.name}"])
        print(f"OK  {gid:<56} {len(lista)} temas · {n_asig} asignaciones · sin tema {sin_tema} · acuerdo {rev['acuerdo']:.0%}")
    if not filtro:
        wb = Workbook()
        ws = wb.active
        ws.title = "Resumen"
        enc = ["Transformación", "Unidad Regional", "Respuestas", "Comentarios", "Temas de BERT", "Número de temas",
               "Estabilidad (tema más débil)", "Nivel de estabilidad", "Asignaciones de Jev", "Sin tema (Jev)",
               "% sin tema (Jev)", "Acuerdo BERT–Jev", "Temas a vigilar (Jev frente a BERT)", "Archivo de temas"]
        titulo(ws, ["Flujo combinado BERTopic → Jev · resumen por transformación y unidad regional",
                    f"Datos en crudo de los formularios (todas las fechas) · temas y número de temas: BERTopic ({bt.MODELO}) · "
                    f"clasificación: Jev ({p['modelo_jev']}, confianza ≥ {p['umbral_tema_ejercicio']:.0%})",
                    "Acuerdo BERT–Jev: % de comentarios que tienen en Jev el tema que les dio BERT. «Temas a vigilar»: Jev "
                    "asigna el tema a muchos más (alto o inflado) o muchos menos (subdetectado) comentarios que BERT; Jev "
                    "puede dar varios temas a un comentario y BERT solo uno."], len(enc))
        estilo_fila = [r for r in resumen]
        tabla(ws, 5, enc, estilo_fila, [26, 22, 11, 12, 14, 10, 12, 12, 12, 10, 10, 11, 60, 60],
              pct_cols=(11, 12), wrap_cols=(13, 14), formatos={7: "0.00"})
        DIR_SALIDAS.mkdir(parents=True, exist_ok=True)
        wb.save(DIR_SALIDAS / "Resumen_flujo_BERT_Jev.xlsx")
        print(f"OK  Resumen_flujo_BERT_Jev.xlsx ({len(resumen)} grupos)")


# ---------------------------------------------------------------------------------------------
# Versión por rol (decisión de Nicolás, 2026-11-04): temas de BERT por rol × transformación (todas las unidades
# juntas) y una lista común por transformación que Jev aplica a todos los comentarios, para que unidad,
# transformación y rol se midan con las mismas categorías (sin ceros por diseño).
# ---------------------------------------------------------------------------------------------

DIR_BERT_ROLES = DIR_DATOS / "bert_roles"
DIR_JEV_ROLES = DIR_DATOS / "jev_roles"
DIR_TEMAS_ROLES = CARPETA / "temas_roles"
DIR_REVISION = CARPETA / "revision"
DIR_SALIDAS_ROLES = CARPETA / "salidas_roles"
ROLES = ["Estudiantes", "Docentes", "Administrativos", "Graduados"]
NOMBRE_ROL = {"Estudiantes": "Creadores de Oportunidades (estudiantes)",
              "Docentes": "Gestores del Conocimiento y el Aprendizaje (docentes)",
              "Administrativos": "Administrativos", "Graduados": "Graduados"}
ROL_FORMS = {"Creadores de Oportunidades (estudiantes)": "Estudiantes", "Creador de Oportunidades (estudiante)": "Estudiantes",
             "Gestores del Conocimiento y el Aprendizaje": "Docentes", "Gestor del Conocimiento y el Aprendizaje": "Docentes",
             "Administrativos": "Administrativos", "Administrativo": "Administrativos",
             "Graduados": "Graduados", "Graduado": "Graduados"}
SIN_ROL = "Sin rol declarado"


def rol_actor(serie: pd.Series) -> pd.Series:
    """Rol declarado por el grupo en el formulario -> uno de los 4 actores (o «Sin rol declarado»)."""
    return serie.map(ROL_FORMS).fillna(SIN_ROL)


def grupos_roles(filtro: str = "") -> list[dict]:
    lista = [dict(id=f"{bt.slug(T)}__rol_{bt.slug(r)}", T=T, rol=r) for T in bt.ORDEN_T for r in ROLES]
    return [g for g in lista if filtro in g["id"]]


def comentarios_con_rol() -> pd.DataFrame:
    res = respuestas()
    com = res[res.excluido == 0].copy()
    com["actor"] = rol_actor(com.rol)
    return com


def modelo_base_rol(gid: str) -> dict:
    info = leer_json(DIR_BERT_ROLES / f"{gid}.json")
    return leer_json(DIR_BERT_ROLES / f"{info['temas_de']}.json") if info.get("temas_de") else info


def bert_roles(filtro: str):
    """BERT por rol × transformación con las 7 unidades juntas (y las filas sin unidad)."""
    bt.DIR_MODELOS = DIR_BERT_ROLES
    DIR_BERT_ROLES.mkdir(parents=True, exist_ok=True)
    com = comentarios_con_rol()
    for g in grupos_roles(filtro):
        idx = com[(com.transformacion == g["T"]) & (com.actor == g["rol"])].index
        info = (bt.modelar_grupo(dict(id=g["id"], nivel="rol", T=g["T"], U=bt.TODAS, idx=idx), com) | {"rol": g["rol"]}
                if len(idx) >= bt.N_MIN_GRUPO else
                dict(id=g["id"], nivel="rol", T=g["T"], U=bt.TODAS, rol=g["rol"], N=int(len(idx)), modelado=False,
                     motivo=f"menos de {bt.N_MIN_GRUPO} comentarios"))
        if not info["modelado"]:      # grupo chico o sin un k válido: usa los temas de la transformación completa
            pid = f"{bt.slug(g['T'])}__todas_las_unidades"
            if not (DIR_BERT_ROLES / f"{pid}.json").exists():
                pinfo = bt.modelar_grupo(dict(id=pid, nivel="transformacion", T=g["T"], U=bt.TODAS,
                                              idx=com[com.transformacion == g["T"]].index), com)
                (DIR_BERT_ROLES / f"{pid}.json").write_text(json.dumps(pinfo, ensure_ascii=False, indent=1), encoding="utf-8")
            info["temas_de"] = pid
        (DIR_BERT_ROLES / f"{g['id']}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        base = modelo_base_rol(g["id"])
        origen = f"temas de {base['id']} ({info['motivo']})" if info.get("temas_de") else "temas propios"
        print(f"OK  {g['id']:<58} N={info['N']:<4} k={base['k']} ({base['nivel_estabilidad']}, "
              f"{base['estabilidad']:.2f}) · {origen}")
        bitacora(f"bert_roles {g['id']}: N={info['N']}, {base['k']} temas, estabilidad {base['estabilidad']:.2f} "
                 f"({base['nivel_estabilidad']}), {origen}.")


def centroides_roles(T: str) -> dict:
    """Centroide normalizado de cada tema de BERT de los roles de una transformación: {(gid, tema): vector}."""
    com = comentarios_con_rol().set_index("id_com")
    out = {}
    for g in grupos_roles(bt.slug(T) + "__rol_"):
        if g["T"] != T:
            continue
        base = modelo_base_rol(g["id"])
        asig = pd.read_parquet(DIR_BERT_ROLES / f"{base['id']}_asignaciones.parquet")
        E = bt.vectores(list(com.loc[asig.id_com, "comentario_anon"]))
        for t in base["temas"]:
            v = E[(asig.tema == t["tema"]).to_numpy()].mean(axis=0)
            out[(g["id"], t["tema"])] = v / (np.linalg.norm(v) or 1)
    return out


def mostrar_roles(filtro: str):
    """Temas de BERT por rol con palabras y comentarios representativos (anonimizados), y el tema más parecido de
    otro rol de la misma transformación, para redactar la lista común."""
    com = comentarios_con_rol().set_index("id_com")
    for T in bt.ORDEN_T:
        if filtro and filtro not in bt.slug(T):
            continue
        cen = centroides_roles(T)
        print(f"\n######## {T}")
        for g in grupos_roles(bt.slug(T) + "__rol_"):
            if g["T"] != T:
                continue
            info, base = leer_json(DIR_BERT_ROLES / f"{g['id']}.json"), modelo_base_rol(g["id"])
            print(f"\n=== {g['rol']} · N={info['N']} · k={base['k']} · estabilidad {base['estabilidad']:.2f} ({base['nivel_estabilidad']})"
                  + (f" · usa {base['id']}" if info.get("temas_de") else ""))
            asig = pd.read_parquet(DIR_BERT_ROLES / f"{base['id']}_asignaciones.parquet")
            for t in base["temas"]:
                k = (g["id"], t["tema"])
                otros = sorted(((float(cen[k] @ v), kk) for kk, v in cen.items() if kk[0] != g["id"]), reverse=True)[:2]
                print(f"  [{t['tema']}] n={t['n']} estab={t['estabilidad']:.2f} · {bt.firma(t['palabras'])} | {', '.join(t['palabras'][5:])}")
                print("      parecido a: " + "; ".join(f"{kk[0].split('__rol_')[1]}[{kk[1]}] {s:.2f}" for s, kk in otros))
                miembros = asig[asig.tema == t["tema"]].sort_values("afinidad", ascending=False).id_com
                for c in list(miembros[:4]):
                    print("      -", com.loc[c, "comentario_anon"][:230].replace("\n", " "))


def transformaciones(filtro: str = "") -> list[str]:
    return [T for T in bt.ORDEN_T if not filtro or filtro in bt.slug(T)]


def cargar_temas_roles(T: str) -> dict:
    ruta = DIR_TEMAS_ROLES / f"{bt.slug(T)}.yaml"
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta.relative_to(RAIZ)}: Claude redacta la lista común de {T}.")
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def origen_modelo(o: dict) -> str:
    """Modelo de BERT de un origen de la lista común ({grupo, tema_bert, firma}): el del grupo o el que usa."""
    return modelo_base_rol(o["grupo"])["id"]


def firmar_roles(filtro: str):
    """Completa la firma (palabras clave de BERT) de cada origen de la lista común, a partir de grupo y tema_bert."""
    for T in transformaciones(filtro):
        ruta = DIR_TEMAS_ROLES / f"{bt.slug(T)}.yaml"
        datos = cargar_temas_roles(T)
        for t in datos["temas"]:
            for o in t["origen"]:
                base = modelo_base_rol(o["grupo"])
                o["firma"] = bt.firma(next(x["palabras"] for x in base["temas"] if x["tema"] == int(o["tema_bert"])))
        ruta.write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
        print(f"OK  {ruta.name}: firmas completadas")


def temas_bert_roles(T: str) -> dict:
    """{(id del modelo base, número de tema): firma} de los modelos de BERT que usan los 4 roles de T."""
    out = {}
    for g in grupos_roles(bt.slug(T) + "__rol_"):
        if g["T"] == T:
            base = modelo_base_rol(g["id"])
            out |= {(base["id"], t["tema"]): bt.firma(t["palabras"]) for t in base["temas"]}
    return out


def errores_temas_roles(T: str) -> list[str]:
    temas = cargar_temas_roles(T)
    trans = ej.resolver_transformacion(T)
    lista, errores = temas["temas"], []
    ids = [t.get("id") for t in lista]
    if len(ids) != len(set(ids)):
        errores.append("ids de tema repetidos")
    for t in lista:
        vacios = [k for k in CAMPOS if not t.get(k)] + ([] if t.get("origen") else ["origen"])
        if vacios:
            errores.append(f"{t.get('id')}: faltan o están vacíos {vacios}")
        for c in ej.componentes_del_tema(t) if t.get("componente") else []:
            if not ej.componente_valido(c, trans):
                errores.append(f"{t['id']}: el componente '{c}' no está en {trans['nombre_oficial']} (documento marco)")
    if len(lista) > ej.MAX_TEMAS:
        errores.append(f"{len(lista)} temas: el máximo es {ej.MAX_TEMAS}")
    esperados = temas_bert_roles(T)
    cubiertos = [(origen_modelo(o), int(o["tema_bert"])) for t in lista for o in t.get("origen", [])]
    if sorted(cubiertos) != sorted(set(cubiertos)):
        errores.append("un tema de BERT está en el origen de más de un tema de la lista")
    if set(cubiertos) != set(esperados):
        errores.append(f"temas de BERT sin cubrir: {sorted(set(esperados) - set(cubiertos))}; "
                       f"sobrantes: {sorted(set(cubiertos) - set(esperados))}")
    errores += [f"{t['id']}: la firma de {o['grupo']}[{o['tema_bert']}] no coincide con BERT (correr firmar_roles si es nuevo)"
                for t in lista for o in t.get("origen", [])
                if (origen_modelo(o), int(o["tema_bert"])) in esperados
                and o.get("firma") != esperados[(origen_modelo(o), int(o["tema_bert"]))]]
    return errores


def validar_roles(filtro: str, imprimir: bool = True) -> int:
    malos = 0
    for T in transformaciones(filtro):
        errores = errores_temas_roles(T)
        if errores:
            malos += 1
            print(f"FALLA {T}\n  - " + "\n  - ".join(errores))
        elif imprimir:
            print(f"OK    {T}: {len(cargar_temas_roles(T)['temas'])} temas en la lista común")
    if malos:
        raise SystemExit(f"{malos} transformación(es) con temas inválidos.")
    return 0


def clasificar_roles(filtro: str):
    """Jev con la lista común de cada transformación, para todos sus comentarios (todas las unidades y roles)."""
    from jev_cliente import Cache, cargar_clave, clasificar_preguntas, construir_preguntas_temas

    validar_roles(filtro, imprimir=False)
    cargar_clave()
    p = params()
    modelo = p["modelo_jev"]
    com_all = comentarios_con_rol()
    DIR_JEV_ROLES.mkdir(parents=True, exist_ok=True)
    cache = Cache(CACHE_JEV)
    for T in transformaciones(filtro):
        temas = cargar_temas_roles(T)
        lista, sin_cont = temas["temas"], temas["sin_contenido"]
        preguntas = construir_preguntas_temas(lista, sin_cont)
        ids_noul = [t["id"] for t in lista] + ["sin_contenido"]
        config = {"flujo": FLUJO + "_roles", "sin_contenido": sin_cont,
                  "temas": [{k: t[k] for k in ("id", "instruccion", "criterio_true", "criterio_false")} for t in lista]}
        com = com_all[com_all.transformacion == T].copy()
        mapa = {k: f"U{i + 1:04d}" for i, k in enumerate(dict.fromkeys(com.comentario_anon))}
        com["id_texto_unico"] = com.comentario_anon.map(mapa)
        unicos = com.drop_duplicates("id_texto_unico")[["id_texto_unico", "comentario_anon"]].to_dict("records")
        antes = len(cache._d)
        extra = {"flujo": FLUJO + "_roles", "transformacion": T}
        ok, errores = asyncio.run(clasificar_preguntas(unicos, preguntas, ids_noul, [], config, modelo, cache,
                                                       p["concurrencia_jev"], extra))
        if errores:
            pendientes = [u for u in unicos if u["id_texto_unico"] in {e[0] for e in errores}]
            ok2, errores = asyncio.run(clasificar_preguntas(pendientes, preguntas, ids_noul, [], config, modelo, cache, 2, extra))
            ok += ok2
        validas = {f["id_texto_unico"]: f for f in ok
                   if set(f["nouls"]) == set(ids_noul) and all(0 <= v <= 1 for v in f["nouls"].values())}
        if errores or len(validas) != len(unicos):
            raise SystemExit(f"{T}: completitud fallida {len(validas)}/{len(unicos)}; errores={errores}")
        filas = [{"id_texto_unico": k, **{f"p_{q}": v for q, v in f["nouls"].items()}, "modelo": f["modelo"],
                  "input_tokens": f["input_tokens"]} for k, f in validas.items()]
        com.merge(pd.DataFrame(filas), on="id_texto_unico", how="left").to_parquet(
            DIR_JEV_ROLES / f"{bt.slug(T)}.parquet", index=False)
        nuevas = len(cache._d) - antes
        tokens = int(sum(f["input_tokens"] for f in validas.values()))
        costo = tokens * p["precio_usd_por_millon_tokens"] / 1e6
        print(f"OK  {T:<30} {len(validas)}/{len(unicos)} textos · {len(lista)} temas · llamadas nuevas {nuevas} · USD {costo:.5f}")
        bitacora(f"clasificar_roles {T}: Jev ({modelo}) · {len(validas)}/{len(unicos)} textos únicos válidos · "
                 f"lista común de {len(lista)} temas + sin_contenido · llamadas nuevas {nuevas} · tokens {tokens} · costo USD {costo:.5f}.")


def sin_contenido_revisado() -> dict:
    """{id_com: decisión} de la lectura de Claude (revision/sin_contenido.jsonl): 'sin_contenido' o 'con_contenido'."""
    ruta = DIR_REVISION / "sin_contenido.jsonl"
    if not ruta.exists():
        return {}
    filas = [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {f["id_com"]: f["decision"] for f in filas}


def asignaciones_roles(T: str) -> tuple[pd.DataFrame, list, float]:
    """Comentarios de T con su probabilidad por tema, sin los que Claude marcó como «sin contenido evaluable»."""
    lista = cargar_temas_roles(T)["temas"]
    tau = float(params().get("umbral_tema_ejercicio", ej.TAU_POR_DEFECTO))
    c = pd.read_parquet(DIR_JEV_ROLES / f"{bt.slug(T)}.parquet")
    revisado = sin_contenido_revisado()
    c["sin_contenido_revisado"] = c.id_com.map(lambda i: revisado.get(i) == "sin_contenido")
    for t in lista:
        c[f"a_{t['id']}"] = c[f"p_{t['id']}"] >= tau
    c["n_temas"] = c[[f"a_{t['id']}" for t in lista]].sum(axis=1)
    return c, lista, tau


def revisar_roles(filtro: str):
    """Jev (lista común) frente a la agrupación de BERT de cada rol, tema por tema."""
    for T in transformaciones(filtro):
        c, lista, _ = asignaciones_roles(T)
        c = c[~c.sin_contenido_revisado]
        de_origen = {(origen_modelo(o), int(o["tema_bert"])): t["id"] for t in lista for o in t["origen"]}
        print(f"\n######## {T} · N={len(c)} · sin tema (Jev) {int((c.n_temas == 0).sum())} ({(c.n_temas == 0).mean():.0%})")
        for t in lista:
            col = "a_" + t["id"]
            print(f"   {t['id']:<44} Jev {int(c[col].sum()):>4} ({c[col].mean():.0%})")
        for g in grupos_roles(bt.slug(T) + "__rol_"):
            if g["T"] != T:
                continue
            base = modelo_base_rol(g["id"])
            asig = pd.read_parquet(DIR_BERT_ROLES / f"{base['id']}_asignaciones.parquet").set_index("id_com")
            cr = c[(c.actor == g["rol"]) & c.id_com.isin(asig.index)]
            aciertos = [bool(cr.loc[i, f"a_{de_origen[(base['id'], int(asig.loc[cr.loc[i, 'id_com'], 'tema']))]}"])
                        for i in cr.index]
            print(f"   -- {g['rol']:<16} N={len(cr):<4} acuerdo BERT–Jev {np.mean(aciertos) if aciertos else 0:.0%}")
            for tb in base["temas"]:
                tid = de_origen[(base["id"], tb["tema"])]
                ids_b = asig[asig.tema == tb["tema"]].index
                n_bert = int(cr.id_com.isin(ids_b).sum())
                n_jev = int(cr[f"a_{tid}"].sum())
                ambos = int(cr[cr.id_com.isin(ids_b)][f"a_{tid}"].sum())
                marca = ("INFLADO" if n_jev >= 2 * n_bert and n_jev - n_bert >= 8 else
                         "SUBDETECTADO" if n_bert - n_jev >= 4 and n_jev <= 0.5 * n_bert else
                         "ALTO" if n_jev - n_bert >= 8 else "")
                print(f"      [{tb['tema']}] -> {tid:<40} BERT {n_bert:>3} · Jev {n_jev:>3} · en ambos {ambos:>3} {marca}")


def candidatos_sin_contenido(filtro: str):
    """Comentarios de 1 a 3 palabras o con p(sin_contenido) ≥ τ: Claude los lee y decide (texto anonimizado)."""
    for T in transformaciones(filtro):
        c, _, tau = asignaciones_roles(T)
        pal = c.comentario_anon.str.split().str.len()
        cand = c[(pal <= 3) | (c.p_sin_contenido >= tau)]
        print(f"\n######## {T}: {len(cand)} candidatos")
        for _, x in cand.drop_duplicates("comentario_anon").iterrows():
            print(f"  {x.id_com} | p_sc={x.p_sin_contenido:.2f} | temas={int(x.n_temas)} | {x.comentario_anon[:140]}")


def celdas_roles(T: str) -> pd.DataFrame:
    """Una fila por unidad × rol × tema: comentarios del rol en la unidad, asignados al tema y % (sin contenido revisado fuera)."""
    c, lista, _ = asignaciones_roles(T)
    c = c[~c.sin_contenido_revisado & (c.unidad != bt.SIN_UNIDAD)]
    filas = []
    for U in sorted(c.unidad.unique()):
        for r in ROLES:
            cr = c[(c.unidad == U) & (c.actor == r)]
            for t in lista:
                n = int(cr[f"a_{t['id']}"].sum())
                filas.append(dict(T=T, U=U, rol=r, tema=t["id"], N=len(cr), n=n, pct=(100 * n / len(cr)) if len(cr) else None))
    return pd.DataFrame(filas)


def ceros_verificados() -> dict:
    ruta = DIR_REVISION / "ceros.jsonl"
    if not ruta.exists():
        return {}
    filas = [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {(f["T"], f["U"], f["rol"], f["tema"]): f for f in filas}


def detectar_ceros(cel: pd.DataFrame, peso: dict, n_min: int = 5, umbral: float = 15.0) -> pd.DataFrame:
    """Celdas con n_min comentarios o más y 0 % en un tema cuyo peso en el conjunto es ≥ umbral (%)."""
    return cel[(cel.N >= n_min) & (cel.n == 0) & cel.tema.map(lambda k: peso.get(k, 0) >= umbral)]


def ceros_a_revisar(T: str) -> pd.DataFrame:
    """Celdas con 5 comentarios o más y 0 % en un tema que tiene ≥ 15 % en el conjunto de la transformación."""
    cel = celdas_roles(T)
    c, lista, _ = asignaciones_roles(T)
    c = c[~c.sin_contenido_revisado]
    # la conformidad (especial) se reporta aparte y no cuenta como tema que deba aparecer en cada celda
    return detectar_ceros(cel, {t["id"]: 100 * c[f"a_{t['id']}"].mean() for t in lista if not t.get("especial")})


def mostrar_ceros(filtro: str):
    """Comentarios (anonimizados) de cada celda en 0 % que hay que verificar, con la probabilidad del tema."""
    ver = ceros_verificados()
    for T in transformaciones(filtro):
        c, lista, _ = asignaciones_roles(T)
        nombres = {t["id"]: t["nombre"] for t in lista}
        for _, z in ceros_a_revisar(T).iterrows():
            if (z["T"], z["U"], z["rol"], z["tema"]) in ver:
                continue
            cr = c[(c.unidad == z.U) & (c.actor == z.rol) & ~c.sin_contenido_revisado]
            print(f"\n=== {T} · {z.U} · {z.rol} · tema «{nombres[z.tema]}» · {z.N} comentarios")
            for _, x in cr.sort_values(f"p_{z.tema}", ascending=False).iterrows():
                print(f"   p={x[f'p_{z.tema}']:.2f} | {x.comentario_anon[:170]}")


def coherencia(filtro: str):
    """Falla si hay comentarios sin probabilidad para algún tema, sumas que no cuadran o ceros sin verificar."""
    problemas = []
    ver = ceros_verificados()
    com_all = comentarios_con_rol()
    for T in transformaciones(filtro):
        c, lista, _ = asignaciones_roles(T)
        faltan = [t["id"] for t in lista if c[f"p_{t['id']}"].isna().any()]
        if faltan:
            problemas.append(f"{T}: comentarios sin probabilidad para {faltan}")
        if len(c) != int((com_all.transformacion == T).sum()):
            problemas.append(f"{T}: {len(c)} comentarios clasificados frente a {int((com_all.transformacion == T).sum())} con contenido")
        cel = celdas_roles(T)
        for (U, r), N in cel.groupby(["U", "rol"]).N.first().items():
            esperado = int(((c.unidad == U) & (c.actor == r) & ~c.sin_contenido_revisado).sum())
            if N != esperado:
                problemas.append(f"{T} · {U} · {r}: suma {N} ≠ {esperado}")
        pend = [z for _, z in ceros_a_revisar(T).iterrows() if (z["T"], z["U"], z["rol"], z["tema"]) not in ver]
        if pend:
            problemas.append(f"{T}: {len(pend)} celda(s) en 0 % sin verificar (python flujo_bert_jev/flujo.py mostrar_ceros)")
        n_min = {t["id"]: int(c[~c.sin_contenido_revisado][f"a_{t['id']}"].sum()) for t in lista if not t.get("especial")}
        bajos = [k for k, v in n_min.items() if v < 3]
        if bajos:
            problemas.append(f"{T}: temas con menos de 3 comentarios en Jev: {bajos}")
    if problemas:
        raise SystemExit("COHERENCIA: FALLA\n  - " + "\n  - ".join(problemas))
    print("COHERENCIA: OK (misma lista para todas las celdas, sumas cuadradas y ceros verificados)")


def roles_origen(T: str, t: dict) -> list[str]:
    """Roles cuyos temas de BERT dieron origen al tema de la lista común."""
    usa = {}
    for g in grupos_roles(bt.slug(T) + "__rol_"):
        if g["T"] == T:
            usa.setdefault(modelo_base_rol(g["id"])["id"], []).append(g["rol"])
    roles = {r for o in t["origen"] for r in usa.get(origen_modelo(o), [])}
    return [r for r in ROLES if r in roles]


def exportar_roles(filtro: str):
    """Un Excel por transformación (solo texto anonimizado): lista común, % por unidad y rol, y clasificación."""
    p = params()
    for T in transformaciones(filtro):
        c, lista, tau = asignaciones_roles(T)
        cc = c[~c.sin_contenido_revisado].copy()
        trans = ej.resolver_transformacion(T)
        anclas, titulo_comp = ej.etiquetas_ancla(trans)
        unidades = sorted(u for u in cc.unidad.unique() if u != bt.SIN_UNIDAD)
        wb = Workbook()
        ws = wb.active
        ws.title = "Temas"
        enc = [titulo_comp, "Tema", "Roles de origen (BERT)", "Qué incluye", "Comentarios (Jev)", "% del total"] + unidades
        titulo(ws, [f"Lista común de temas · {T} · todas las unidades y roles",
                    f"{len(cc)} comentarios con contenido · temas: BERT por rol con las 7 unidades juntas · "
                    f"clasificación: Jev ({p['modelo_jev']}, confianza ≥ {tau:.0%}) con la misma lista para todos los comentarios",
                    "Cada respuesta es de un grupo de 5 a 8 personas. Un comentario puede tener varios temas o ninguno; "
                    "% sobre los comentarios con contenido de cada unidad."], len(enc))
        filas = []
        for t in lista:
            a = cc[f"a_{t['id']}"]
            filas.append([anclas.get(t["componente"], t["componente"]), t["nombre"],
                          ", ".join(NOMBRE_ROL[r] for r in roles_origen(T, t)), t["criterio_true"], int(a.sum()), float(a.mean())]
                         + [float(cc[cc.unidad == U][f"a_{t['id']}"].mean()) for U in unidades])
        sin = cc.n_temas == 0
        filas.append(["—", "Sin tema asignado", "—", f"Ningún tema con confianza ≥ {tau:.0%}", int(sin.sum()), float(sin.mean())]
                     + [float((cc[cc.unidad == U].n_temas == 0).mean()) for U in unidades])
        pcols = (6, *range(7, 7 + len(unidades)))
        tabla(ws, 5, enc, filas, [26, 34, 30, 60, 12, 10] + [13] * len(unidades), pct_cols=pcols, wrap_cols=(1, 2, 3, 4))
        ws2 = wb.create_sheet("Por unidad y rol")
        enc2 = ["Unidad regional", "Actor", "Comentarios"] + [t["nombre"] for t in lista] + ["Sin tema"]
        filas2 = []
        for U in unidades:
            for r in ROLES:
                cr = cc[(cc.unidad == U) & (cc.actor == r)]
                filas2.append([U, NOMBRE_ROL[r], len(cr)]
                              + [(float(cr[f"a_{t['id']}"].mean()) if len(cr) else None) for t in lista]
                              + [float((cr.n_temas == 0).mean()) if len(cr) else None])
        tabla(ws2, 1, enc2, filas2, [22, 34, 12] + [18] * (len(lista) + 1), pct_cols=tuple(range(4, 5 + len(lista))),
              wrap_cols=tuple(range(1, 5 + len(lista))))
        ws3 = wb.create_sheet("Clasificación")
        enc3 = ["ID", "Unidad regional", "Fecha", "Actor", "Comentario (anonimizado)", "Tema principal (Jev)", "% confianza (Jev)"] \
            + [t["nombre"] for t in lista]
        filas3 = []
        for _, x in c.sort_values(["unidad", "fecha"]).iterrows():
            ps = sorted(((t["nombre"], float(x[f"p_{t['id']}"])) for t in lista), key=lambda kv: -kv[1])
            if x.sin_contenido_revisado:
                principal, conf = "(sin contenido evaluable, revisado)", None
            elif ps[0][1] >= tau:
                principal, conf = ps[0]
            else:
                principal, conf = f"Sin tema asignado (más cercano: {ps[0][0]})", ps[0][1]
            filas3.append([x.id_resp, x.unidad, str(x.fecha)[:10], NOMBRE_ROL.get(x.actor, x.actor), x.comentario_anon, principal, conf]
                          + [(float(x[f"p_{t['id']}"]) if x[f"p_{t['id']}"] >= tau and not x.sin_contenido_revisado else None) for t in lista])
        tabla(ws3, 1, enc3, filas3, [10, 20, 12, 30, 70, 40, 11] + [16] * len(lista),
              pct_cols=tuple(range(7, 8 + len(lista))), wrap_cols=(5, 6))
        carpeta = DIR_SALIDAS_ROLES / T
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"Temas_por_rol_{bt.limpio(T)}.xlsx"
        wb.save(ruta)
        print(f"OK  {ruta.relative_to(RAIZ)}")


def main():
    pasos = {"preparar": lambda f: preparar(), "bert": bert, "borrador": borrador, "validar": validar,
             "clasificar": clasificar, "revisar": revisar, "exportar": exportar,
             "bert_roles": bert_roles, "mostrar_roles": mostrar_roles, "firmar_roles": firmar_roles,
             "validar_roles": validar_roles,
             "clasificar_roles": clasificar_roles, "revisar_roles": revisar_roles,
             "candidatos_sin_contenido": candidatos_sin_contenido, "mostrar_ceros": mostrar_ceros,
             "coherencia": coherencia, "exportar_roles": exportar_roles}
    if len(sys.argv) < 2 or sys.argv[1] not in pasos:
        raise SystemExit(__doc__)
    pasos[sys.argv[1]](sys.argv[2] if len(sys.argv) > 2 else "")


if __name__ == "__main__":
    main()
