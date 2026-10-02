"""Fase 1 · Marco estratégico: las 5 transformaciones.

Extrae literalmente del .md el nombre, la referencia y la definición de cada transformación,
y los combina con la redacción operativa de config/marco_redaccion.yaml.
"""
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from f00_ficha_entorno import bitacora  # noqa: E402

PATRON_ENCABEZADO = re.compile(r"^## (\d+)\. (.+?)\s*$")


def _str_multilinea(dumper, valor):
    estilo = "|" if "\n" in valor else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", valor, style=estilo)


yaml.SafeDumper.add_representer(str, _str_multilinea)


def extraer_secciones(lineas: list[str]) -> list[dict]:
    """Devuelve una sección por encabezado '## N. Nombre', con sus líneas (1-indexadas)."""
    inicios = [(i, m) for i, l in enumerate(lineas) if (m := PATRON_ENCABEZADO.match(l))]
    secciones = []
    for j, (i, m) in enumerate(inicios):
        # termina en el siguiente '## ' (numerado o no) o al final
        fin = next((k for k in range(i + 1, len(lineas)) if lineas[k].startswith("## ")), len(lineas))
        while fin > i + 1 and lineas[fin - 1].strip() in ("", "---"):
            fin -= 1
        ini = i + 1
        while ini < fin and not lineas[ini].strip():
            ini += 1
        secciones.append({"numero": int(m.group(1)), "nombre": m.group(2),
                          "linea_ini": i + 1, "linea_fin": fin, "cuerpo": lineas[ini:fin]})
    return secciones


def bloque(cuerpo: list[str], titulo: str) -> list[str]:
    """Líneas bajo un subtítulo en negrita ('**Titulo**') hasta el siguiente subtítulo."""
    i = next(k for k, l in enumerate(cuerpo) if l.strip().startswith(f"**{titulo}**"))
    resto = cuerpo[i + 1:]
    fin = next((k for k, l in enumerate(resto) if l.strip().startswith("**") and l.strip().endswith("**")), len(resto))
    return [l.rstrip() for l in resto[:fin] if l.strip()]


def main():
    ficha = yaml.safe_load((RAIZ / "config" / "ficha_ejercicio.yaml").read_text(encoding="utf-8"))
    ruta_md = RAIZ / ficha["documento_marco"]
    texto = ruta_md.read_text(encoding="utf-8")
    if not texto.strip():
        raise SystemExit(f"Documento marco vacío: {ruta_md}")
    lineas = texto.splitlines()

    secciones = extraer_secciones(lineas)
    if len(secciones) != 5 or [s["numero"] for s in secciones] != [1, 2, 3, 4, 5]:
        raise SystemExit(f"Se esperaban exactamente 5 transformaciones numeradas 1-5; hay "
                         f"{[(s['numero'], s['nombre']) for s in secciones]}. Detenerse y preguntar.")

    # Coherencia con la tabla resumen del propio documento
    tabla = {int(m.group(1)): m.group(2) for l in lineas
             if (m := re.match(r"^\|\s*(\d)\s*\|\s*\*\*(.+?)\*\*\s*\|", l))}

    red = yaml.safe_load((RAIZ / "config" / "marco_redaccion.yaml").read_text(encoding="utf-8"))
    marco = []
    for s in secciones:
        tid = f"T{s['numero']}"
        if tabla.get(s["numero"]) != s["nombre"]:
            raise SystemExit(f"{tid}: el encabezado '{s['nombre']}' no coincide con la tabla resumen "
                             f"'{tabla.get(s['numero'])}'")
        enunciado = " ".join(bloque(s["cuerpo"], "Enunciado estratégico"))
        que_busca = " ".join(bloque(s["cuerpo"], "Qué busca"))
        componentes = [l.lstrip("- ").strip() for l in bloque(s["cuerpo"], "Componentes preliminares")]
        r = red["transformaciones"][tid]
        marco.append({
            "id": tid,
            "nombre_oficial": s["nombre"],
            "referencia": f"{ruta_md.name} · '## {s['numero']}. {s['nombre']}' · líneas {s['linea_ini']}-{s['linea_fin']}",
            "definicion_textual": "\n".join(s["cuerpo"]),
            "enunciado_estrategico": enunciado,
            "que_busca": que_busca,
            "sintesis_documento": " ".join(r["sintesis_documento"].split()),
            "conceptos_clave": componentes,
            "instruccion": " ".join(r["instruccion"].split()),
            "criterio_true": " ".join(r["criterio_true"].split()),
            "criterio_false": " ".join(r["criterio_false"].split()),
        })

    # Verificación de literalidad: cada definición textual debe estar en el .md tal cual
    for t in marco:
        assert t["definicion_textual"] in texto, f"{t['id']}: la definición no es literal"
        assert t["enunciado_estrategico"] in texto.replace("\n", " "), f"{t['id']}: enunciado no literal"

    fronteras = {k: " ".join(v.split()) for k, v in red["fronteras"].items()}
    pares = {f"T{a}-T{b}" for a in range(1, 6) for b in range(a + 1, 6)}
    if set(fronteras) != pares:
        raise SystemExit(f"La matriz de fronteras debe tener los 10 pares; faltan {pares - set(fronteras)}")

    salida = RAIZ / "config" / "marco_estrategico.yaml"
    contenido = yaml.safe_dump(marco, allow_unicode=True, sort_keys=False, width=110)
    salida.write_text(contenido, encoding="utf-8")
    (RAIZ / "config" / "fronteras_marco.yaml").write_text(
        yaml.safe_dump(fronteras, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    sha = hashlib.sha256(salida.read_bytes()).hexdigest()

    bitacora(f"Fase 1: marco extraído de `{ruta_md.name}` (5 transformaciones, coinciden con la tabla resumen; "
             f"definiciones verificadas como literales). `marco_estrategico.yaml` borrador sha256={sha[:16]}… "
             f"(se congela al aprobar el PC1).")

    print(json.dumps({"sha256_marco": sha, "transformaciones": [
        {k: t[k] for k in ("id", "nombre_oficial", "referencia")} for t in marco]},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
