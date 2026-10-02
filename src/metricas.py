"""Fórmulas del Apéndice A. Toda aritmética del pipeline pasa por aquí."""
import math

import numpy as np
from scipy import stats

Z = 1.959964


# --- Proporciones e intervalos ---------------------------------------------------------------

def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    """IC de Wilson para k éxitos en n."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z**2 / n
    centro = p + z**2 / (2 * n)
    radio = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, (centro - radio) / den), min(1.0, (centro + radio) / den))


def regla_de_tres(n: int) -> float:
    """Cota superior 95 % con 0 eventos en n."""
    return 3 / n


def tamano_muestra(N: int, p: float = 0.5, e: float = 0.05, z: float = Z) -> float:
    n0 = z**2 * p * (1 - p) / e**2
    return n0 / (1 + (n0 - 1) / N)


def protocolo_por_tamano(N_s: int, fraccion_max_muestra: float = 0.5, n_diseno_completo: int = 1200) -> dict:
    """Censo si la muestra necesaria (±5 pp, IC 95 %) supera `fraccion_max_muestra` de N_s
    (equivale a N_s <= 385); diseño completo del prompt si hay comentarios para D + V + gold disjuntos."""
    n = tamano_muestra(N_s)
    fraccion = n / N_s
    if fraccion > fraccion_max_muestra:
        protocolo = "B_censo"
    elif N_s < n_diseno_completo:
        protocolo = "intermedio_muestreo_reducido"
    else:
        protocolo = "A_completo"
    return {"N_s": N_s, "n_muestra_requerida": round(n, 1), "fraccion": round(fraccion, 3), "protocolo": protocolo}


# --- Clasificación binaria --------------------------------------------------------------------

def _div(a, b):
    return a / b if b else float("nan")


def confusion(y, yhat) -> dict:
    y, yhat = np.asarray(y, int), np.asarray(yhat, int)
    return {"VP": int(((y == 1) & (yhat == 1)).sum()), "FP": int(((y == 0) & (yhat == 1)).sum()),
            "FN": int(((y == 1) & (yhat == 0)).sum()), "VN": int(((y == 0) & (yhat == 0)).sum())}


def binarias(y, yhat) -> dict:
    c = confusion(y, yhat)
    P = _div(c["VP"], c["VP"] + c["FP"])
    R = _div(c["VP"], c["VP"] + c["FN"])
    Sp = _div(c["VN"], c["VN"] + c["FP"])
    F1 = _div(2 * P * R, P + R) if not (math.isnan(P) or math.isnan(R)) else float("nan")
    return {**c, "precision": P, "sensibilidad": R, "especificidad": Sp, "F1": F1,
            "kappa": kappa(y, yhat)}


def kappa(a, b) -> float:
    """κ de Cohen para dos vectores de etiquetas (binarias o categóricas)."""
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    if n == 0:
        return float("nan")
    cats = np.union1d(a, b)
    po = float((a == b).mean())
    pe = float(sum((a == c).mean() * (b == c).mean() for c in cats))
    return _div(po - pe, 1 - pe) if pe != 1 else (1.0 if po == 1 else float("nan"))


# --- Multi-etiqueta (matrices n × K de 0/1) ---------------------------------------------------

def micro_f1(Y, Yhat) -> float:
    Y, Yhat = np.asarray(Y, int), np.asarray(Yhat, int)
    vp = ((Y == 1) & (Yhat == 1)).sum()
    fp = ((Y == 0) & (Yhat == 1)).sum()
    fn = ((Y == 1) & (Yhat == 0)).sum()
    return _div(2 * vp, 2 * vp + fp + fn)


def macro_f1(Y, Yhat, columnas=None) -> float:
    Y, Yhat = np.asarray(Y, int), np.asarray(Yhat, int)
    cols = range(Y.shape[1]) if columnas is None else columnas
    f1s = [binarias(Y[:, k], Yhat[:, k])["F1"] for k in cols]
    f1s = [0.0 if math.isnan(f) else f for f in f1s]
    return float(np.mean(f1s)) if f1s else float("nan")


def hamming_loss(Y, Yhat) -> float:
    Y, Yhat = np.asarray(Y, int), np.asarray(Yhat, int)
    return float((Y != Yhat).mean())


def exact_match(Y, Yhat) -> float:
    Y, Yhat = np.asarray(Y, int), np.asarray(Yhat, int)
    return float((Y == Yhat).all(axis=1).mean())


def jaccard_promedio(Y, Yhat) -> float:
    Y, Yhat = np.asarray(Y, bool), np.asarray(Yhat, bool)
    inter = (Y & Yhat).sum(axis=1)
    union = (Y | Yhat).sum(axis=1)
    return float(np.where(union == 0, 1.0, inter / np.where(union == 0, 1, union)).mean())


# --- Coherencia jerárquica --------------------------------------------------------------------

def coherente(temas_asignados: set, padre: dict, trans_asignadas: set,
              principal: str, p_trans: dict, tau_T: float) -> bool:
    padres = {padre[t] for t in temas_asignados if padre[t] != "fuera_del_marco"}
    ok_temas = padres <= trans_asignadas
    ok_principal = principal == "ninguna" or p_trans.get(principal, 0.0) >= tau_T
    return ok_temas and ok_principal


# --- Calibración ------------------------------------------------------------------------------

def brier(p, y) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    return float(((p - y) ** 2).mean())


def ece(p, y, bins: int = 10) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(total)


# --- Prevalencia corregida --------------------------------------------------------------------

def rogan_gladen(p_hat: float, se: float, sp: float) -> float:
    j = se + sp - 1
    if j <= 0:
        return float("nan")
    return float(min(1.0, max(0.0, (p_hat + sp - 1) / j)))


# --- Asociación -------------------------------------------------------------------------------

def chi2_cramer(tabla) -> dict:
    tabla = np.asarray(tabla, float)
    chi2, p, gl, esperado = stats.chi2_contingency(tabla, correction=False)
    n = tabla.sum()
    k = min(tabla.shape) - 1
    v = math.sqrt(chi2 / (n * k)) if n and k else float("nan")
    return {"chi2": float(chi2), "gl": int(gl), "p": float(p), "V_cramer": v,
            "pct_esperado_menor_5": float((esperado < 5).mean())}


def benjamini_hochberg(pvals, q: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve (rechazar, q_ajustado) en el orden original."""
    p = np.asarray(pvals, float)
    m = len(p)
    orden = np.argsort(p)
    ajust = np.empty(m)
    acumulado = 1.0
    for rango in range(m, 0, -1):
        i = orden[rango - 1]
        acumulado = min(acumulado, m * p[i] / rango)
        ajust[i] = min(1.0, acumulado)
    rechazar = ajust <= q
    return rechazar, ajust


# --- Bootstrap --------------------------------------------------------------------------------

def bootstrap_ic(fn, n: int, B: int = 2000, seed: int = 2026) -> tuple[float, float]:
    """fn(indices) -> estadístico. Percentiles 2,5 y 97,5."""
    rng = np.random.default_rng(seed)
    vals = [fn(rng.integers(0, n, n)) for _ in range(B)]
    vals = np.asarray([v for v in vals if not math.isnan(v)])
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))
