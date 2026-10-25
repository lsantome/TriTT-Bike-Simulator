"""Física del ciclista: potencia por pendiente, CdA efectivo, Crr y resolución por tramo.

Balance de energía por tramo (distancia `d` sobre el firme, potencia constante):

    ½·m_ef·(v1² − v0²) = d·( η·P / v̄ − ½·ρ·CdA(v̄)·(v0²+v1²)/2 − Crr(v̄)·m·g·cosθ ) − m·g·Δh

con v̄ = (v0+v1)/2. Es exacto para P constante y aceleración uniforme (⟨1/v⟩ = 1/v̄ y
⟨v²⟩ = (v0²+v1²)/2 cuando v² es lineal en la distancia).
"""
from __future__ import annotations

import math

import numpy as np

G = 9.80665
CRR_V_REF = 29.0 / 3.6   # m/s: velocidad a la que se define el Crr de referencia (ensayos en rodillo)
V_LO = 0.5               # m/s, velocidad mínima admitida
V_HI = 60.0              # m/s, cota superior de búsqueda
V_FORCE_MIN = 1.0        # m/s, mínimo usado en η·P/v para evitar la singularidad


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def power_by_grade(grade, p) -> np.ndarray:
    """Potencia (W) en función de la pendiente (m/m): perfil continuo subida/llano/descenso."""
    g = np.asarray(grade, dtype=float)
    thr = p.umbral_pendiente / 100.0
    w = p.anchura_banda_pendiente / 100.0
    up = smoothstep((g - (thr - w / 2.0)) / w)
    dn = smoothstep(((-g) - (thr - w / 2.0)) / w)
    return p.p_llano + (p.p_subida - p.p_llano) * up + (p.p_descenso - p.p_llano) * dn


def cda_effective(v_ms, cda: float, delta: float, thr_kmh: float, width_kmh: float) -> np.ndarray:
    """CdA efectivo: transición logística entre posición aero y convencional (continua)."""
    v = np.asarray(v_ms, dtype=float)
    x = np.clip((v - thr_kmh / 3.6) / (width_kmh / 3.6), -60.0, 60.0)
    return cda + delta / (1.0 + np.exp(x))


def crr_effective(v_ms, crr_ref, crr1):
    """Crr(v) = Crr_ref + crr1·(v − 29 km/h), con suelo en 0,5·Crr_ref."""
    v = np.asarray(v_ms, dtype=float)
    return np.maximum(crr_ref + crr1 * (v - CRR_V_REF), 0.5 * crr_ref)


def _cda_scalar(vm, cda, dcda, thr, wid):
    x = (vm - thr) / wid
    if x > 50.0:
        return cda
    if x < -50.0:
        return cda + dcda
    return cda + dcda / (1.0 + math.exp(x))


def _resid(v1, v0, d, dh, cos_t, rho, crr_ref, crr1, pw, m, m_ef, cda, dcda, thr, wid):
    vm = 0.5 * (v0 + v1)
    vf = vm if vm > V_FORCE_MIN else V_FORCE_MIN
    c = _cda_scalar(vm, cda, dcda, thr, wid)
    cr = crr_ref + crr1 * (vm - CRR_V_REF)
    if cr < 0.5 * crr_ref:
        cr = 0.5 * crr_ref
    f_res = 0.5 * rho * c * 0.5 * (v0 * v0 + v1 * v1) + cr * m * G * cos_t
    return 0.5 * m_ef * (v1 * v1 - v0 * v0) - d * (pw / vf - f_res) + m * G * dh


def solve_segment(v0, d, dh, cos_t, rho, crr_ref, crr1, pw, m, m_ef, cda, dcda, thr, wid):
    """Velocidad final del tramo. Si hay varias raíces (zona de transición de CdA) elige la
    más próxima a v0, es decir, la que sigue la trayectoria real (histéresis)."""
    args = (d, dh, cos_t, rho, crr_ref, crr1, pw, m, m_ef, cda, dcda, thr, wid)
    f0 = _resid(v0, v0, *args)
    if f0 == 0.0:
        return v0
    if f0 < 0.0:
        a, fa = v0, f0
        step = 0.25
        b = min(v0 + step, V_HI)
        while True:
            fb = _resid(b, v0, *args)
            if fb >= 0.0:
                break
            if b >= V_HI:
                return V_HI
            a, fa = b, fb
            step *= 2.0
            b = min(b + step, V_HI)
    else:
        b, fb = v0, f0
        step = 0.25
        a = max(v0 - step, V_LO)
        while True:
            fa = _resid(a, v0, *args)
            if fa <= 0.0:
                break
            if a <= V_LO:
                return V_LO
            b, fb = a, fa
            step *= 2.0
            a = max(a - step, V_LO)
    # Illinois (regula falsi modificada) en [a, b] con fa < 0 <= fb
    side = 0
    c = 0.5 * (a + b)
    for _ in range(80):
        denom = fb - fa
        c = (a * fb - b * fa) / denom if denom != 0.0 else 0.5 * (a + b)
        fc = _resid(c, v0, *args)
        if abs(fc) < 1e-7 or (b - a) < 1e-10:
            break
        if fc > 0.0:
            b, fb = c, fc
            if side == -1:
                fa *= 0.5
            side = -1
        else:
            a, fa = c, fc
            if side == 1:
                fb *= 0.5
            side = 1
    return c


def required_power(v0, v1, d, dh, cos_t, rho, crr_ref, crr1, m, m_ef, cda, dcda, thr, wid, eta):
    """Potencia de pedaleo (W) necesaria para ir de v0 a v1 en el tramo (>= 0)."""
    vm = 0.5 * (v0 + v1)
    vf = vm if vm > V_FORCE_MIN else V_FORCE_MIN
    c = _cda_scalar(vm, cda, dcda, thr, wid)
    cr = max(crr_ref + crr1 * (vm - CRR_V_REF), 0.5 * crr_ref)
    f_res = 0.5 * rho * c * 0.5 * (v0 * v0 + v1 * v1) + cr * m * G * cos_t
    work = 0.5 * m_ef * (v1 * v1 - v0 * v0) + d * f_res + m * G * dh
    return max(0.0, vf * work / (eta * d))
