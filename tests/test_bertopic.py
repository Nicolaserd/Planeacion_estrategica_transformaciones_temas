"""Pruebas del análisis paralelo con BERTopic (scripts/bertopic_temas.py). No cargan el modelo BERT."""
import sys
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bertopic_temas as bt  # noqa: E402


def _tres_grupos(n=20, dim=20, seed=0):
    rng = np.random.default_rng(seed)
    centros = np.eye(dim)[:3] * 4
    E = np.vstack([c + rng.normal(0, 0.3, (n, dim)) for c in centros])
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    vocab = [["sedes", "integración", "territorio", "región", "municipios"],
             ["tecnología", "plataforma", "internet", "conectividad", "software"],
             ["bienestar", "salud", "deporte", "cultura", "acompañamiento"]]
    docs = [" ".join(rng.choice(vocab[g], 3, replace=False)) for g in range(3) for _ in range(n)]
    return E, docs


def test_elige_tres_temas_con_tres_grupos_separados():
    E, docs = _tres_grupos()
    curva = bt.curva_k(E, docs, minimo=5, k_max=6)
    elegido = [f for f in curva if f["elegido"]]
    assert [f["k"] for f in elegido] == [3]
    assert elegido[0]["nivel"] == "estable"
    # partir uno de los grupos en dos no se sostiene al remuestrear
    assert next(f for f in curva if f["k"] == 4)["estabilidad"] < bt.JACCARD_ESTABLE


def test_sin_estructura_la_estabilidad_es_debil():
    rng = np.random.default_rng(3)
    E = rng.normal(size=(60, 20))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    docs = [" ".join(rng.choice(["sedes", "datos", "salud", "bienestar", "procesos", "internet"], 3)) for _ in range(60)]
    curva = bt.curva_k(E, docs, minimo=5, k_max=5)
    assert all(f["estabilidad"] < bt.JACCARD_ESTABLE for f in curva if f["k"] >= 3)


def test_npmi_mayor_si_las_palabras_van_juntas():
    rng = np.random.default_rng(1)
    juntas = rng.random(200) < 0.3
    D = np.column_stack([juntas, juntas, rng.random(200) < 0.3, rng.random(200) < 0.3])
    assert bt.npmi([[0, 1]], D) > 0.9
    assert bt.npmi([[0, 1]], D) > bt.npmi([[2, 3]], D)


def test_elige_el_mayor_k_estable_que_cumple_el_minimo():
    filas = [dict(k=2, cumple=True, estabilidad=0.95), dict(k=3, cumple=True, estabilidad=0.85),
             dict(k=4, cumple=False, estabilidad=0.90), dict(k=5, cumple=True, estabilidad=0.70)]
    assert bt.elegir_k(filas) == 3
    assert not filas[2]["elegido"] and filas[1]["nivel"] == "estable"


def test_sin_temas_estables_usa_moderada_y_luego_la_mas_estable():
    moderadas = [dict(k=2, cumple=True, estabilidad=0.70), dict(k=3, cumple=True, estabilidad=0.62),
                 dict(k=4, cumple=True, estabilidad=0.50)]
    assert bt.elegir_k(moderadas) == 3
    debiles = [dict(k=2, cumple=True, estabilidad=0.40), dict(k=3, cumple=True, estabilidad=0.55),
               dict(k=4, cumple=True, estabilidad=0.30)]
    assert bt.elegir_k(debiles) == 3 and debiles[1]["nivel"] == "débil"
    assert bt.elegir_k([dict(k=2, cumple=False, estabilidad=0.9)]) is None


def test_tamano_minimo():
    assert bt.tamano_minimo(20) == 5
    assert bt.tamano_minimo(700) == 21


def test_no_lee_nombre_ni_correo():
    mapeo = yaml.safe_load((RAIZ / "config" / "mapeo_columnas.yaml").read_text(encoding="utf-8"))
    cols = ["ID", "Hora de inicio", "Correo electrónico", "Nombre", "Tipo de actor", "Unidad Regional",
            "¿Qué ajustaría en esta transformación?", "Total de puntos"]
    leidas = bt.columnas_a_leer(cols, mapeo)
    assert "Nombre" not in leidas and "Correo electrónico" not in leidas
    assert {"ID", "Unidad Regional", "¿Qué ajustaría en esta transformación?"} <= set(leidas)


def test_formulario_desde_el_nombre_del_archivo():
    assert bt.formulario_de_archivo(Path("Experiencia_\xa0_x_. (UC DIGITAL)(1-753) (1).xlsx")) == "UC Digital"
    assert bt.formulario_de_archivo(Path("Experiencia_ _x_. (UCUNDINAMARCA)(1-169).xlsx")) == "UCundinamarca"
    assert bt.formulario_de_archivo(Path("otro.xlsx")) is None


def test_palabras_vacias_y_marcas_fuera_de_las_palabras_clave():
    analizar = bt.analizador((1, 1))
    toks = analizar(bt.texto_para_palabras("La universidad debería mejorar la conectividad con [PERSONA] en las sedes"))
    assert "conectividad" in toks and "sedes" in toks
    assert not {"universidad", "la", "persona", "deberia", "debería"} & set(toks)
