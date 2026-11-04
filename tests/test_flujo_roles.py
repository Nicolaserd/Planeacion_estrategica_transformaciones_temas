"""Pruebas de la versión por rol del flujo BERTopic → Jev (flujo_bert_jev/flujo.py)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "flujo_bert_jev"))
import flujo  # noqa: E402


def test_rol_actor_mapea_los_cuatro_actores_y_variantes():
    serie = pd.Series(["Creadores de Oportunidades (estudiantes)", "Creador de Oportunidades (estudiante)",
                       "Gestores del Conocimiento y el Aprendizaje", "Gestor del Conocimiento y el Aprendizaje",
                       "Administrativo", "Graduados", None])
    assert list(flujo.rol_actor(serie)) == ["Estudiantes", "Estudiantes", "Docentes", "Docentes",
                                            "Administrativos", "Graduados", flujo.SIN_ROL]


def test_grupos_roles_son_24_y_unicos():
    grupos = flujo.grupos_roles()
    assert len(grupos) == 6 * 4
    assert len({g["id"] for g in grupos}) == len(grupos)
    assert {g["rol"] for g in grupos} == set(flujo.ROLES)


def test_detectar_ceros_solo_marca_celdas_con_comentarios_y_temas_con_peso():
    cel = pd.DataFrame([
        dict(T="UC Digital", U="A", rol="Docentes", tema="t1", N=12, n=0),   # cero a revisar
        dict(T="UC Digital", U="A", rol="Docentes", tema="t2", N=12, n=0),   # tema con poco peso: no
        dict(T="UC Digital", U="A", rol="Graduados", tema="t1", N=3, n=0),   # pocos comentarios: no
        dict(T="UC Digital", U="B", rol="Docentes", tema="t1", N=12, n=4),   # no es cero
    ])
    z = flujo.detectar_ceros(cel, {"t1": 30.0, "t2": 5.0})
    assert list(zip(z.U, z.rol, z.tema)) == [("A", "Docentes", "t1")]
