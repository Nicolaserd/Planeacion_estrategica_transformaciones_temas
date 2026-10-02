import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import metricas as m  # noqa: E402


def test_wilson_p09_n300():
    lo, hi = m.wilson(270, 300)
    assert round(lo, 3) == 0.861
    assert round(hi, 3) == 0.929


def test_tamano_muestra_6000():
    assert round(m.tamano_muestra(6000), 1) == 361.1


def test_protocolo_por_tamano():
    assert m.protocolo_por_tamano(44)["protocolo"] == "B_censo"
    assert m.protocolo_por_tamano(385)["protocolo"] == "B_censo"
    assert m.protocolo_por_tamano(386)["protocolo"] == "intermedio_muestreo_reducido"
    assert m.protocolo_por_tamano(1200)["protocolo"] == "A_completo"


def test_regla_de_tres():
    assert m.regla_de_tres(200) == pytest.approx(0.015)


def test_binarias_y_kappa():
    y = [1, 1, 0, 0, 1, 0]
    yhat = [1, 0, 0, 1, 1, 0]
    r = m.binarias(y, yhat)
    assert (r["VP"], r["FP"], r["FN"], r["VN"]) == (2, 1, 1, 2)
    assert r["F1"] == pytest.approx(2 / 3)
    assert r["kappa"] == pytest.approx(1 / 3)


def test_multietiqueta():
    Y = np.array([[1, 0], [0, 0], [1, 1]])
    Yh = np.array([[1, 1], [0, 0], [1, 0]])
    assert m.micro_f1(Y, Yh) == pytest.approx(2 * 2 / (2 * 2 + 1 + 1))
    assert m.hamming_loss(Y, Yh) == pytest.approx(2 / 6)
    assert m.exact_match(Y, Yh) == pytest.approx(1 / 3)
    assert m.jaccard_promedio(Y, Yh) == pytest.approx((0.5 + 1 + 0.5) / 3)


def test_coherencia():
    padre = {"a": "T1", "b": "fuera_del_marco"}
    assert m.coherente({"a", "b"}, padre, {"T1"}, "T1", {"T1": 0.9}, 0.5)
    assert not m.coherente({"a"}, padre, set(), "ninguna", {}, 0.5)
    assert not m.coherente(set(), padre, {"T1"}, "T2", {"T2": 0.2}, 0.5)


def test_calibracion():
    assert m.brier([1, 0], [1, 0]) == 0
    assert m.ece([0.05, 0.95], [0, 1]) == pytest.approx(0.05)


def test_rogan_gladen():
    assert m.rogan_gladen(0.3, 0.9, 0.95) == pytest.approx((0.3 + 0.95 - 1) / 0.85)
    assert m.rogan_gladen(0.01, 0.9, 0.9) == 0.0


def test_benjamini_hochberg():
    rech, q = m.benjamini_hochberg([0.01, 0.04, 0.03, 0.5])
    assert list(rech) == [True, False, False, False]
    assert q[0] == pytest.approx(0.04)
    assert q[1] == pytest.approx(4 * 0.04 / 3)
    assert q[2] == pytest.approx(4 * 0.04 / 3)
    assert q[3] == pytest.approx(0.5)


def test_chi2_cramer():
    r = m.chi2_cramer([[10, 0], [0, 10]])
    assert r["V_cramer"] == pytest.approx(1.0)
