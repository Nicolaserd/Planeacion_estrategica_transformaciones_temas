"""Pruebas del flujo combinado BERTopic → Jev (flujo_bert_jev/flujo.py). No llaman a BERT ni a Jev."""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "flujo_bert_jev"))
import flujo  # noqa: E402


def _tema(numero, componente="Inteligencia artificial", **cambios):
    t = dict(id=f"t{numero}", nombre=f"Tema {numero}", componente=componente, justificacion="j", instruccion="¿…?",
             criterio_true="Sí…", criterio_false="No…", ejemplos_si=["x"], tema_bert=numero, firma=f"a{numero}, b{numero}")
    t.update(cambios)
    return t


BASE = {"temas": [{"tema": 0, "palabras": ["a0", "b0"]}, {"tema": 1, "palabras": ["a1", "b1"]}]}


def test_temas_validos():
    temas = {"transformacion": "UC Digital", "temas": [_tema(0), _tema(1, "Automatización de procesos")]}
    assert flujo.errores_temas(temas, BASE) == []


def test_componente_que_no_es_de_la_transformacion():
    temas = {"transformacion": "UC Digital", "temas": [_tema(0, "Convivencia"), _tema(1)]}
    assert any("Convivencia" in e for e in flujo.errores_temas(temas, BASE))


def test_los_temas_deben_ser_los_de_bert():
    faltante = {"transformacion": "UC Digital", "temas": [_tema(0)]}
    assert any("no son los de BERT" in e for e in flujo.errores_temas(faltante, BASE))
    otra_firma = {"transformacion": "UC Digital", "temas": [_tema(0), _tema(1, firma="otra")]}
    assert any("firma" in e for e in flujo.errores_temas(otra_firma, BASE))


def test_campos_vacios():
    temas = {"transformacion": "UC Digital", "temas": [_tema(0, instruccion=""), _tema(1)]}
    assert any("instruccion" in e for e in flujo.errores_temas(temas, BASE))


def test_acuerdo_bert_jev():
    bert = pd.Series({"c1": 0, "c2": 1, "c3": 1, "c4": 0})
    asignados = {"c1": {"t0"}, "c2": {"t0", "t1"}, "c3": set(), "c4": {"t1"}}
    assert flujo.acuerdo_bert_jev(bert, asignados, {0: "t0", 1: "t1"}) == 0.5


def test_nombres_e_ids():
    assert flujo.nombre_salida("Temas", "Sede Fusagasugá", "UC para la Vida") == "Temas_Sede_Fusagasuga_UC_para_la_Vida.xlsx"
    assert flujo.id_tema(2, "Inteligencia artificial: capacitación y uso responsable") == "t2_inteligencia_artificial_capacitacion_uso"
