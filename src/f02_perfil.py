"""Fase 2 · Perfil de los datos.

No muestra ni lee el texto de los comentarios: solo estructura, conteos y longitudes.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from f00_ficha_entorno import bitacora, cargar_ficha, slug  # noqa: E402

COL_ID = "ID"
COL_FECHA = "Hora de inicio"
COL_FIN = "Hora de finalización"
COL_GRUPO = "Tipo de actor"
COL_PROGRAMA = "De que programa eres graduado"
COL_UNIDAD = "Unidad Regional"
COL_VALORACION = "¿Consideran que esta transformación responde a lo que la UCundinamarca necesita del 2027 al 2037?"
COL_COMENTARIO = "¿Qué ajustaría en esta transformación?"
COLS_PERSONALES = ["Correo electrónico", "Nombre"]


def perfil(d: pd.DataFrame, col_t: str) -> dict:
    com = d[COL_COMENTARIO]
    texto = com.dropna().astype(str).str.strip()
    no_vacio = texto[texto != ""]
    largo = no_vacio.str.len()
    dur = (d[COL_FIN] - d[COL_FECHA]).dt.total_seconds()
    cols_dup = [c for c in d.columns if c not in (COL_ID, COL_FECHA, COL_FIN) and d[c].notna().any()]
    vc = lambda s: s.fillna("(vacío)").value_counts().to_dict()  # noqa: E731
    return {
        "N_filas": len(d),
        "N_con_comentario": int(len(no_vacio)),
        "pct_vacios": round(100 * (1 - len(no_vacio) / len(d)), 1) if len(d) else None,
        "por_transformacion_declarada": vc(d[col_t]),
        "por_grupo": vc(d[COL_GRUPO]),
        "por_unidad_regional": vc(d[COL_UNIDAD]),
        "por_fecha": d[COL_FECHA].dt.strftime("%Y-%m-%d").value_counts().sort_index().to_dict(),
        "por_valoracion": vc(d[COL_VALORACION]),
        "programas_distintos": int(d[COL_PROGRAMA].nunique()),
        "programa_vacio": int(d[COL_PROGRAMA].isna().sum()),
        "longitud_comentario": {
            "p25": float(largo.quantile(.25)), "mediana": float(largo.median()),
            "p75": float(largo.quantile(.75)), "p95": float(largo.quantile(.95)), "max": int(largo.max()),
        } if len(largo) else None,
        "comentarios_texto_repetido": int(no_vacio.duplicated().sum()),
        "filas_identicas_salvo_id_y_hora": int(d.duplicated(subset=cols_dup).sum()),
        "respuestas_menos_30s": int((dur < 30).sum()),
        "duracion_mediana_s": float(dur.median()),
    }


def main():
    ficha = cargar_ficha()
    col_t = ficha["columna_transformacion"]
    df = pd.read_excel(RAIZ / ficha["archivo_datos"])  # solo lectura: no se escribe sobre data/raw

    hojas = pd.ExcelFile(RAIZ / ficha["archivo_datos"]).sheet_names
    estructura = [{"columna": c, "tipo": str(df[c].dtype), "nulos": int(df[c].isna().sum()),
                   "unicos": int(df[c].nunique())} for c in df.columns]
    vacias = [c for c in df.columns if df[c].isna().all()]

    # Mapeo propuesto
    mapeo = {
        "id_resp": COL_ID,
        "comentarios": [{"columna": COL_COMENTARIO, "pregunta": "P1",
                         "texto_pregunta": COL_COMENTARIO}],
        "grupo": COL_GRUPO,
        "programa": COL_PROGRAMA,
        "unidad_regional": COL_UNIDAD,
        "sede": COL_UNIDAD,
        "fecha": COL_FECHA,
        "transformacion_declarada": col_t,
        "valoracion_cerrada": COL_VALORACION,
        "columnas_personales_descartar": COLS_PERSONALES,
        "columnas_vacias_ignorar": vacias,
        "nota": ("Una sola pregunta abierta: no hace falta formato largo; id_com = '<ID>-P1'. "
                 "'De que programa eres graduado' contiene el programa de todos los tipos de actor, "
                 "no solo de graduados. 'Unidad Regional' cumple el papel de sede."),
    }
    (RAIZ / "config" / "mapeo_columnas.yaml").write_text(
        yaml.safe_dump(mapeo, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")

    valores_t = df[col_t].dropna().unique().tolist()
    equivalencia = {"UC para la Vida": "T5"}
    sin_asignar = [v for v in valores_t if v not in equivalencia]
    if sin_asignar:
        raise SystemExit(f"Valores de transformación sin equivalencia segura: {sin_asignar}. Preguntar.")
    (RAIZ / "config" / "equivalencia_transformaciones.yaml").write_text(yaml.safe_dump(
        {"equivalencia": equivalencia, "vacio": "sin_frente_declarado"},
        allow_unicode=True, sort_keys=False), encoding="utf-8")

    # Subconjunto del ejercicio según la ficha
    dia = df[COL_FECHA].dt.strftime("%Y-%m-%d")
    es_lugar = df[COL_UNIDAD].fillna("").map(slug).str.contains(slug(ficha["lugar_desarrollo"]))
    en_fechas = dia.isin(ficha["fechas_desarrollo"])
    sub = df[es_lugar & en_fechas]
    diferencias = {
        "lugar_fuera_de_fechas": df.loc[es_lugar & ~en_fechas, [COL_ID]].assign(
            fecha=dia[es_lugar & ~en_fechas]).to_dict("records"),
        "fechas_de_otro_lugar": int((~es_lugar & en_fechas).sum()),
        "unidad_vacia_en_fechas": int((df[COL_UNIDAD].isna() & en_fechas).sum()),
    }

    res = {
        "hojas": hojas,
        "dimensiones": list(df.shape),
        "columnas_vacias": len(vacias),
        "estructura": estructura,
        "mapeo": mapeo,
        "equivalencia": {"UC para la Vida": "T5", "(vacío)": "sin_frente_declarado"},
        "diferencias_con_ficha": diferencias,
        "perfil_ejercicio": perfil(sub, col_t),
        "perfil_archivo_completo": perfil(df, col_t),
        "unidades_archivo_completo": {
            u: {"n_filas": int((df[COL_UNIDAD] == u).sum()),
                "n_comentarios": int(df.loc[df[COL_UNIDAD] == u, COL_COMENTARIO].notna().sum()),
                "fechas": sorted(dia[df[COL_UNIDAD] == u].unique().tolist())}
            for u in df[COL_UNIDAD].dropna().unique()},
    }
    (RAIZ / "logs" / f"f02_perfil_{ficha['slug_ejercicio']}.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    pe = res["perfil_ejercicio"]
    bitacora(f"Fase 2: mapeo en config/mapeo_columnas.yaml; equivalencia 'UC para la Vida'->T5, vacíos->"
             f"sin_frente_declarado (por defecto del prompt, pendiente de confirmar). Ejercicio: "
             f"{pe['N_filas']} filas, {pe['N_con_comentario']} con comentario; "
             f"{pe['filas_identicas_salvo_id_y_hora']} filas idénticas salvo ID/hora; "
             f"{pe['respuestas_menos_30s']} respuestas <30 s. Columnas personales (Nombre, Correo) se descartan en la Fase 3.")
    print(json.dumps({k: v for k, v in res.items() if k != "estructura"}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
