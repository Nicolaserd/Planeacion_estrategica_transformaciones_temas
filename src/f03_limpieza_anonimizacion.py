"""Fase 3 · Limpieza, filtro de ruido y anonimización.

Nunca imprime `comentario_original` ni las columnas personales. Para la auditoría imprime
solo `comentario_anon`.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from f00_ficha_entorno import bitacora, cargar_ficha, slug  # noqa: E402

NO_RESPUESTAS = {
    "ninguno", "ninguna", "nada", "no", "na", "n/a", "n a", "no aplica", "no tengo", "sin comentarios",
    "sin comentario", "ningun comentario", "todo bien", "todo esta bien", "bien", "ok", "okay", "gracias",
    "ninguna observacion",
    # variantes con errores obvios
    "nignuno", "niguno", "ningno", "ningnuo", "ningina", "nada.", "nda", "nadaa", "todo bn", "tdo bien",
}
TITULOS = (r"profesor|profesora|profe|docente|ingeniero|ingeniera|ing\.?|doctor|doctora|dr\.?|dra\.?|"
           r"señor|señora|sr\.?|sra\.?|coordinador|coordinadora|decano|decana|rector|rectora")
MAYUS = "A-ZÁÉÍÓÚÑÜ"
MINUS = "a-záéíóúñü"


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def motivo_exclusion(original) -> str | None:
    if original is None or (isinstance(original, float) and pd.isna(original)) or not str(original).strip():
        return "vacio"
    t = str(original)
    if not re.search(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]", t):
        return "solo_signos_o_numeros"
    if len(re.findall(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]", t)) < 3:
        return "menos_de_3_letras"
    n = normalizar(t).strip(" .,;:!¡?¿-_*\"'()")
    if n in NO_RESPUESTAS:
        return "no_respuesta"
    return None


def anonimizar(t: str, conteo: dict) -> str:
    def sub(patron, reemplazo, texto, clave, flags=0):
        nuevo, n = re.subn(patron, reemplazo, texto, flags=flags)
        conteo[clave] = conteo.get(clave, 0) + n
        return nuevo

    t = sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[CORREO]", t, "CORREO")
    t = sub(r"(https?://|www\.)\S+", "[URL]", t, "URL", re.I)
    t = sub(r"(?<!\d)(\+?57[\s.-]?)?3\d{2}[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)", "[TELEFONO]", t, "TELEFONO")
    t = sub(r"(?<!\d)(\(?60\d\)?|\(?[1-8]\)?)[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)", "[TELEFONO]", t, "TELEFONO")

    # Secuencias de 6 a 11 dígitos (con o sin puntos), salvo montos ($, pesos, mil)
    def _id(m):
        contexto = t[max(0, m.start() - 3):m.end() + 8].lower()
        if "$" in contexto or "peso" in contexto or "mil" in contexto:
            return m.group(0)
        conteo["NUMERO_ID"] = conteo.get("NUMERO_ID", 0) + 1
        return "[NUMERO_ID]"
    t = re.sub(r"(?<![\d.])\d{1,3}(?:\.\d{3}){1,3}(?![\d.])|(?<!\d)\d{6,11}(?!\d)",
               lambda m: _id(m) if 6 <= len(re.sub(r"\D", "", m.group(0))) <= 11 else m.group(0), t)

    # Título + palabra(s) con mayúscula inicial -> [PERSONA]
    # solo el título ignora mayúsculas; el nombre exige mayúscula inicial
    t = sub(rf"\b((?i:{TITULOS}))\s+[{MAYUS}][{MINUS}]+(\s+[{MAYUS}][{MINUS}]+)?",
            lambda m: f"{m.group(1)} [PERSONA]", t, "PERSONA")
    return t


def tokens_nombres(df: pd.DataFrame) -> set[str]:
    """Tokens (>= 4 letras) de la columna Nombre, normalizados. No se imprimen nunca."""
    toks = set()
    for nombre in df["Nombre"].dropna().astype(str):
        toks |= {normalizar(x) for x in re.findall(r"[^\W\d_]+", nombre) if len(x) >= 4}
    return toks


def main():
    ficha = cargar_ficha()
    mapeo = yaml.safe_load((RAIZ / "config" / "mapeo_columnas.yaml").read_text(encoding="utf-8"))
    equiv = yaml.safe_load((RAIZ / "config" / "equivalencia_transformaciones.yaml").read_text(encoding="utf-8"))
    df = pd.read_excel(RAIZ / ficha["archivo_datos"])

    dia = df[mapeo["fecha"]].dt.strftime("%Y-%m-%d")
    es_lugar = df[mapeo["unidad_regional"]].fillna("").map(slug).str.contains(slug(ficha["lugar_desarrollo"]))
    incluir = dia.isin(ficha["fechas_desarrollo"]) | df[mapeo["id_resp"]].isin(ficha.get("incluir_ids_fuera_de_fecha", []))
    sub = df[es_lugar & incluir].copy()
    toks = tokens_nombres(df)

    col_com = mapeo["comentarios"][0]["columna"]
    filas, conteo = [], {}
    for _, r in sub.iterrows():
        original = r[col_com]
        motivo = motivo_exclusion(original)
        texto = "" if motivo == "vacio" else str(original)
        anon = anonimizar(texto, conteo) if texto else ""
        palabras = {normalizar(w) for w in re.findall(r"[^\W\d_]+", anon)}
        decl = r[mapeo["transformacion_declarada"]]
        filas.append({
            "id_resp": int(r[mapeo["id_resp"]]),
            "id_com": f"{int(r[mapeo['id_resp']])}-P1",
            "pregunta": "P1",
            "fecha": dia[r.name],
            "en_fechas_ficha": dia[r.name] in ficha["fechas_desarrollo"],
            "grupo": r[mapeo["grupo"]],
            "programa": r[mapeo["programa"]],
            "unidad_regional": r[mapeo["unidad_regional"]],
            "transformacion_declarada": equiv["equivalencia"].get(decl, equiv["vacio"]) if pd.notna(decl) else equiv["vacio"],
            "transformacion_declarada_vacia_en_excel": bool(pd.isna(decl)),
            "valoracion": r[mapeo["valoracion_cerrada"]],
            "comentario_original": texto,
            "texto_norm": normalizar(texto),
            "comentario_anon": anon,
            "excluido": int(motivo is not None),
            "motivo": motivo or "",
            "coincide_token_nombre": int(bool(palabras & toks)),
        })
    out = pd.DataFrame(filas)

    # 3.4 Textos únicos (sobre los no excluidos)
    con = out["excluido"] == 0
    claves = out.loc[con, ["pregunta", "comentario_anon"]].apply(tuple, axis=1)
    mapa = {k: f"U{i + 1:03d}" for i, k in enumerate(dict.fromkeys(claves))}
    out["id_texto_unico"] = ""
    out.loc[con, "id_texto_unico"] = claves.map(mapa)

    destino = RAIZ / "data" / "interim" / "comentarios.parquet"
    out.to_parquet(destino, index=False)

    resumen = {
        "N_filas": len(out),
        "N_s": int(con.sum()),
        "excluidos_por_motivo": out.loc[~con, "motivo"].value_counts().to_dict(),
        "reemplazos": conteo,
        "filas_con_token_de_nombre_tras_anonimizar": int(out["coincide_token_nombre"].sum()),
        "textos_unicos": len(mapa),
        "transformacion_declarada": out["transformacion_declarada"].value_counts().to_dict(),
        "fuera_de_fechas_ficha": int((~out["en_fechas_ficha"]).sum()),
    }
    (RAIZ / "logs" / "f03_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    bitacora(f"Fase 3: N_filas={resumen['N_filas']}, N_s={resumen['N_s']}, excluidos={resumen['excluidos_por_motivo']}, "
             f"reemplazos={conteo}, textos únicos={len(mapa)}. spaCy no instalado (opcional): la auditoría manual "
             f"cubre el 100 % de los comentarios.")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))

    if "--auditoria" in sys.argv:
        print("\n=== AUDITORÍA · excluidos con texto (anonimizado) ===")
        for _, r in out[(out.excluido == 1) & (out.motivo != "vacio")].iterrows():
            print(f"[{r.id_com}] ({r.motivo}) {r.comentario_anon!r}")
        print("\n=== AUDITORÍA · todos los comentarios anonimizados (N_s) ===")
        for _, r in out[con].iterrows():
            marca = " <<token de nombre>>" if r.coincide_token_nombre else ""
            print(f"[{r.id_com}]{marca} {r.comentario_anon}")


if __name__ == "__main__":
    main()
