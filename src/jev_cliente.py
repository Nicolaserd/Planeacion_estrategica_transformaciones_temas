"""Cliente Jev (TypeSafe): carga de clave, construcción de preguntas, caché y clasificación.

Verificado contra typesafe-sdk 0.7.2 y docs.typesafe.ai (2026-10-01).
La clave nunca se imprime ni se escribe en logs u outputs.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path

from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parents[1]
ENV_PATH = RAIZ / ".env"
NOMBRE_CLAVE = "TYPESAFE_API_KEY"
# El .env de este proyecto trae la clave bajo otro nombre; se acepta como alternativa
# y la discrepancia queda registrada en logs/decisiones.md.
NOMBRES_ALTERNOS = ("plan_estrategico",)


def cargar_clave() -> tuple[str, str]:
    """Devuelve (clave, nombre_de_variable_usada). Lanza RuntimeError si no hay clave."""
    if not ENV_PATH.exists():
        raise RuntimeError("Archivo .env no encontrado o TYPESAFE_API_KEY vacía. "
                           "Crea el archivo .env con tu clave antes de continuar.")
    valores = dotenv_values(ENV_PATH)
    for nombre in (NOMBRE_CLAVE, *NOMBRES_ALTERNOS):
        valor = (valores.get(nombre) or "").strip()
        if valor:
            os.environ[NOMBRE_CLAVE] = valor
            return valor, nombre
    raise RuntimeError("TYPESAFE_API_KEY not found in .env")


def construir_preguntas(marco: list, tax: dict) -> dict:
    """Una sola petición: 5 Nouls de transformación + Choice principal
    + Nouls de temas + Choice 'tipo' + Noul 'sin_contenido'."""
    from typesafe_sdk import Choice, Noul

    q = {}
    for t in marco:
        q[f"trans_{t['id']}"] = Noul(
            instructions=t["instruccion"],
            criteria={"true": t["criterio_true"], "false": t["criterio_false"]},
        )
    opciones = {t["id"]: t["instruccion"] for t in marco}
    opciones["ninguna"] = "El comentario no se relaciona con ninguna de las cinco transformaciones."
    q["transformacion_principal"] = Choice(
        instructions="¿Con cuál de las cinco transformaciones se relaciona principalmente el `comentario`?",
        criteria=opciones,
    )
    for tema in tax["temas"]:
        q[tema["id"]] = Noul(
            instructions=tema["instruccion"],
            criteria={"true": tema["criterio_true"], "false": tema["criterio_false"]},
        )
    q["tipo"] = Choice(instructions="¿Qué tipo de aporte hace el `comentario`?", criteria=tax["tipo"])
    q["sin_contenido"] = Noul(instructions=tax["sin_contenido"])
    return q


def clave_cache(modelo: str, state: dict, config_serializada: dict) -> str:
    payload = json.dumps({"m": modelo, "s": state, "q": config_serializada},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Cache:
    """Caché append-only en cache/jev_respuestas.jsonl."""

    def __init__(self, ruta: Path = RAIZ / "cache" / "jev_respuestas.jsonl"):
        self.ruta = ruta
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._d = {}
        if self.ruta.exists():
            for linea in self.ruta.read_text(encoding="utf-8").splitlines():
                if linea.strip():
                    fila = json.loads(linea)
                    self._d[fila["clave"]] = fila

    def contiene(self, k: str) -> bool:
        return k in self._d

    def obtener(self, k: str) -> dict:
        return self._d[k]

    def guardar(self, fila: dict) -> None:
        self._d[fila["clave"]] = fila
        with self.ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def construir_preguntas_temas(temas: list, sin_contenido: str) -> dict:
    """Una Noul por tema del ejercicio + la Noul 'sin_contenido' (flujo por ejercicio)."""
    from typesafe_sdk import Noul

    q = {t["id"]: Noul(instructions=t["instruccion"],
                       criteria={"true": t["criterio_true"], "false": t["criterio_false"]}) for t in temas}
    q["sin_contenido"] = Noul(instructions=sin_contenido)
    return q


async def clasificar(items, marco, tax, modelo, cache, concurrencia=8, extra_registro=None):
    """Flujo del prompt maestro: 5 transformaciones + principal + temas + tipo + sin_contenido."""
    preguntas = construir_preguntas(marco, tax)
    ids_noul = ([f"trans_{t['id']}" for t in marco]
                + [tm["id"] for tm in tax["temas"]] + ["sin_contenido"])
    ids_choice = ["transformacion_principal", "tipo"]
    return await clasificar_preguntas(items, preguntas, ids_noul, ids_choice, {"marco": marco, "tax": tax},
                                      modelo, cache, concurrencia, extra_registro)


async def clasificar_preguntas(items, preguntas, ids_noul, ids_choice, config, modelo, cache, concurrencia=8,
                               extra_registro=None):
    """Una petición por texto único. `config` define la clave de caché junto con el modelo y el state.
    Devuelve (filas_ok, errores). Ningún error se descarta en silencio:
    401 y 422 se relanzan (detener todo); el resto se devuelve para reintentar al final."""
    from datetime import datetime, timezone

    from typesafe_sdk import (AsyncTypeSafeClient, RetryPolicy, TypeSafeAuthenticationError,
                              TypeSafeUnprocessableEntityError)

    sem = asyncio.Semaphore(concurrencia)
    reintentos = RetryPolicy(max_retries=4, backoff_max=20.0, timeout=120.0)  # 429 y 5xx (incl. 529), respeta retry-after

    async with AsyncTypeSafeClient(model=modelo, retry=reintentos, timeout=60.0) as client:

        async def uno(item):
            state = {"comentario": item["comentario_anon"]}   # sin fecha, lugar, grupo, sede ni frente declarado
            k = clave_cache(modelo, state, config)
            if cache.contiene(k):
                return cache.obtener(k)
            async with sem:
                r = await client.system_one(state=state, questions=preguntas, model=modelo)
            fila = {
                "clave": k,
                "id_texto_unico": item["id_texto_unico"],
                "modelo": r.model,
                "nouls": {q: r.nouls[q].noul for q in ids_noul},
                "choices": {c: {"eleccion": r.choices[c].choice,
                                "prob": dict(r.choices[c].probabilities),
                                "conf": r.choices[c].confidence} for c in ids_choice},
                "input_tokens": r.usage.input_tokens,
                "marca_tiempo": datetime.now(timezone.utc).isoformat(),
                **(extra_registro or {}),
            }
            cache.guardar(fila)
            return fila

        resultados = await asyncio.gather(*(uno(i) for i in items), return_exceptions=True)

    for r in resultados:
        if isinstance(r, (TypeSafeAuthenticationError, TypeSafeUnprocessableEntityError)):
            raise r
    ok = [r for r in resultados if isinstance(r, dict)]
    errores = [(i["id_texto_unico"], repr(r)) for i, r in zip(items, resultados) if not isinstance(r, dict)]
    return ok, errores
