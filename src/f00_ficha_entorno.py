"""Fase 0 · Ficha, entorno y verificación de la API."""
import json
import re
import sys
import unicodedata
from datetime import date
from importlib.metadata import version
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jev_cliente import NOMBRE_CLAVE, RAIZ, cargar_clave  # noqa: E402

LOG = RAIZ / "logs" / "decisiones.md"
SALIDA = RAIZ / "logs" / "f00_resultado.json"


def bitacora(texto: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    nuevo = not LOG.exists()
    with LOG.open("a", encoding="utf-8") as f:
        if nuevo:
            f.write("# Bitácora de decisiones\n\n")
        f.write(f"- **{date.today().isoformat()}** · {texto}\n")


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", "_", t.strip())


OBLIGATORIOS = ["fechas_desarrollo", "lugar_desarrollo", "archivo_datos",
                "columna_transformacion", "documento_marco"]


def cargar_ficha() -> dict:
    """Lee la ficha, valida los campos obligatorios, normaliza fechas y calcula slug_ejercicio."""
    ficha = yaml.safe_load((RAIZ / "config" / "ficha_ejercicio.yaml").read_text(encoding="utf-8"))
    faltan = [k for k in OBLIGATORIOS if not ficha.get(k)]
    if faltan:
        raise SystemExit(f"Faltan campos en la ficha: {faltan}")
    fechas = sorted(pd.to_datetime(ficha["fechas_desarrollo"]).strftime("%Y-%m-%d"))
    parte_fecha = fechas[0] if len(fechas) == 1 else f"{fechas[0]}_a_{fechas[-1]}"
    ficha["fechas_desarrollo"] = fechas
    ficha["slug_ejercicio"] = f"{parte_fecha}_{slug(ficha['lugar_desarrollo'])}"
    return ficha


def main():
    res = {}

    # 1. .env y clave (sin mostrar su valor)
    clave, nombre_var = cargar_clave()
    res["env"] = {"cargada": True, "variable_usada": nombre_var, "longitud": len(clave)}
    if nombre_var != NOMBRE_CLAVE:
        bitacora(f"DISCREPANCIA: `.env` no contiene `{NOMBRE_CLAVE}`; la clave se cargó desde la variable "
                 f"`{nombre_var}` (valor no mostrado). Recomendado renombrarla a `{NOMBRE_CLAVE}`.")
    else:
        bitacora(f"`{NOMBRE_CLAVE}` cargada desde `.env` (valor no mostrado).")

    # 2. Ficha
    ficha = cargar_ficha()
    fechas = ficha["fechas_desarrollo"]
    res["ficha"] = ficha

    ruta_xlsx = RAIZ / ficha["archivo_datos"]
    if not ruta_xlsx.exists():
        raise SystemExit(f"No existe {ruta_xlsx}")
    df = pd.read_excel(ruta_xlsx)
    col_t = ficha["columna_transformacion"]
    if col_t not in df.columns:
        raise SystemExit(f"La columna '{col_t}' no está en el Excel")
    marco_md = RAIZ / ficha["documento_marco"]
    if not marco_md.exists() or not marco_md.read_text(encoding="utf-8").strip():
        raise SystemExit(f"Documento marco ausente o vacío: {marco_md}")

    # Conteo de control del subconjunto del ejercicio (perfil completo en la Fase 2)
    dia = df["Hora de inicio"].dt.strftime("%Y-%m-%d")
    es_lugar = df["Unidad Regional"].fillna("").map(slug).str.contains(slug(ficha["lugar_desarrollo"]))
    sub = df[es_lugar & dia.isin(fechas)]
    col_com = "¿Qué ajustaría en esta transformación?"
    res["control_subconjunto"] = {
        "filas_excel": len(df),
        "filas_ejercicio": len(sub),
        "filas_lugar_otras_fechas": int((es_lugar & ~dia.isin(fechas)).sum()),
        "filas_fechas_otro_lugar": int((~es_lugar & dia.isin(fechas)).sum()),
        "comentarios_no_vacios": int(sub[col_com].notna().sum()),
        "transformacion_declarada": sub[col_t].fillna("(vacío)").value_counts().to_dict(),
    }

    # 3. Versiones del entorno
    paquetes = ["typesafe-sdk", "pandas", "numpy", "scipy", "scikit-learn", "statsmodels",
                "openpyxl", "matplotlib", "python-dotenv", "PyYAML", "pyarrow", "pytest"]
    res["entorno"] = {"python": sys.version.split()[0], **{p: version(p) for p in paquetes}}

    # 5. Prueba de humo (texto ficticio, sin datos reales)
    from typesafe_sdk import Choice, Noul, TypeSafeClient

    humo_state = {"comentario": "los baños del bloque B no tienen agua hace 2 semanas"}
    humo_preguntas = {
        "infraestructura": Noul(
            instructions="¿El `comentario` se refiere al estado o mantenimiento de espacios físicos de la universidad?"),
        "tipo": Choice(
            instructions="¿Qué tipo de aporte hace el `comentario`?",
            criteria={"oportunidad_de_mejora": "Contiene una queja, problema o sugerencia.",
                      "reconocimiento": "Solo felicita o valora positivamente.",
                      "neutro_observacion": "Describe sin queja, sugerencia ni felicitación."}),
    }
    with TypeSafeClient() as client:
        modelos = client.models.list()
        res["modelos"] = [{"name": m.name, "release_date": m.release_date,
                           "description": m.description[:120]} for m in modelos.models]
        versionados = [m.name for m in modelos.models if re.fullmatch(r"jev-\d+\.\d+\.\d+", m.name)]
        if versionados:
            modelo = sorted(versionados, key=lambda s: tuple(map(int, s[4:].split("."))))[-1]
        else:
            # /v1/models solo lista alias: se resuelve el versionado con la respuesta de jev-latest
            r0 = client.system_one(state=humo_state, questions=humo_preguntas, model="jev-latest")
            modelo = r0.model
            res["resolucion_modelo"] = f"/v1/models solo lista alias; jev-latest respondió como `{modelo}`"
            bitacora(f"DISCREPANCIA: GET /v1/models no lista ids versionados (solo {[m.name for m in modelos.models]}); "
                     f"el id versionado `{modelo}` se tomó del campo `model` de la respuesta de jev-latest.")
            if not re.fullmatch(r"jev-\d+\.\d+\.\d+", modelo):
                raise SystemExit(f"No se pudo resolver un modelo versionado (respuesta: {modelo})")

        # Prueba de humo pidiendo explícitamente el id versionado
        r = client.system_one(state=humo_state, questions=humo_preguntas, model=modelo)
    noul = r.nouls["infraestructura"].noul
    ch = r.choices["tipo"]
    suma = sum(ch.probabilities.values())
    res["humo"] = {
        "modelo_respondio": r.model,
        "claves_respuesta": sorted(r.answers),
        "noul_infraestructura": noul,
        "choice_tipo": ch.choice,
        "probabilidades_tipo": dict(ch.probabilities),
        "suma_probabilidades": suma,
        "confidence_tipo": ch.confidence,
        "usage": {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens},
        "checks": {
            "una_respuesta_por_clave": sorted(r.answers) == ["infraestructura", "tipo"],
            "noul_en_0_1": 0 <= noul <= 1,
            "choice_valida": ch.choice in ch.probabilities,
            "probs_suman_1": abs(suma - 1) <= 0.01,
            "confidence_en_0_1": 0 <= ch.confidence <= 1,
            "usage_reportado": r.usage.input_tokens is not None,
        },
    }

    # 6. Fijar modelo versionado en params.yaml
    params_path = RAIZ / "config" / "params.yaml"
    txt = params_path.read_text(encoding="utf-8")
    txt = re.sub(r"^modelo_jev:.*$", f"modelo_jev: {modelo}                 # fijado en la Fase 0 ({date.today()})",
                 txt, flags=re.M)
    params_path.write_text(txt, encoding="utf-8")
    res["modelo_fijado"] = modelo
    bitacora(f"Modelo Jev fijado: `{modelo}` (de GET /v1/models; respondió `{r.model}` en la prueba de humo).")
    bitacora(f"slug_ejercicio = `{ficha['slug_ejercicio']}`; fechas {fechas}; lugar {ficha['lugar_desarrollo']}.")

    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
