"""Simulación completa: perfil + parámetros -> tiempos, velocidades y potencias por tramo."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .atmosphere import air_density
from .metrics import average_power, intensity_factor, normalized_power, variability_index
from .params import Params, validate_params
from .physics import (V_LO, cda_effective, crr_effective, power_by_grade, required_power,
                      solve_segment)
from .route import Profile, TrackData, build_profile

LIMIT_NONE, LIMIT_CURVE, LIMIT_CAP = 0, 1, 2


@dataclass
class SimResult:
    params: Params
    profile: Profile
    v_nodes: np.ndarray        # velocidad en nodos (m/s)
    dt: np.ndarray             # duración por tramo (s)
    t_nodes: np.ndarray        # tiempo acumulado en nodos (s)
    power_nominal: np.ndarray  # potencia según el perfil por pendiente (W)
    power_effective: np.ndarray  # potencia realmente aplicada (W)
    v_seg: np.ndarray          # velocidad media por tramo (m/s)
    cda_seg: np.ndarray
    crr_seg: np.ndarray
    rho_seg: np.ndarray
    limit_seg: np.ndarray      # 0 sin límite, 1 curvatura/frenada, 2 tope de velocidad
    tiempo_s: float
    distancia_km: float
    velocidad_media_kmh: float
    potencia_media_w: float
    np_w: float
    vi: Optional[float]
    if_: Optional[float]
    warnings: List[str] = field(default_factory=list)

    @property
    def s_mid_km(self) -> np.ndarray:
        s = self.profile.s
        return 0.5 * (s[:-1] + s[1:]) / 1000.0

    def to_frame(self):
        import pandas as pd
        pr = self.profile
        return pd.DataFrame({
            "km": self.s_mid_km,
            "elevacion_m": 0.5 * (pr.ele[:-1] + pr.ele[1:]),
            "pendiente_%": pr.grade * 100.0,
            "velocidad_kmh": self.v_seg * 3.6,
            "potencia_nominal_w": self.power_nominal,
            "potencia_w": self.power_effective,
            "cda_efectivo": self.cda_seg,
            "crr_efectivo": self.crr_seg,
            "densidad_aire": self.rho_seg,
            "limite": self.limit_seg,
            "duracion_s": self.dt,
            "tiempo_acum_s": self.t_nodes[1:],
        })


def _speed_limits(profile: Profile, p: Params) -> tuple[np.ndarray, np.ndarray]:
    """Límite de velocidad en cada nodo (tope + curvatura) con frenada máxima hacia atrás."""
    n = len(profile.ds)
    vmax = p.velocidad_maxima / 3.6
    lim = np.full(n + 1, vmax)
    if p.limite_curvatura:
        k = np.maximum(profile.kappa, 1e-9)
        lim = np.minimum(lim, np.sqrt(p.aceleracion_lateral / k))
    lim = np.maximum(lim, 1.0)
    base = lim.copy()
    lim_l = lim.tolist()
    path = profile.path.tolist()
    a_br = p.deceleracion_frenada
    for i in range(n - 1, -1, -1):
        cand = math.sqrt(lim_l[i + 1] ** 2 + 2.0 * a_br * path[i])
        if cand < lim_l[i]:
            lim_l[i] = cand
    return np.array(lim_l), base


def simulate(profile: Profile, params: Params,
             power_override: Optional[np.ndarray] = None) -> SimResult:
    """Simula la ruta. `power_override` (W por tramo) sustituye al perfil por pendiente
    (se usa para reproducir actividades reales)."""
    p = validate_params(params)
    prof = profile
    n = len(prof.ds)
    m = p.masa_total
    m_ef = m + p.inercia_ruedas / p.radio_efectivo ** 2

    alt_seg = 0.5 * (prof.ele[:-1] + prof.ele[1:])
    if p.densidad_manual:
        rho_seg = np.full(n, float(p.densidad_manual))
    else:
        rho_seg = np.asarray(air_density(p.temperatura, p.humedad, p.presion_nivel_mar, alt_seg))

    p_nom = (np.asarray(power_override, dtype=float) if power_override is not None
             else power_by_grade(prof.grade, p))
    if len(p_nom) != n:
        raise ValueError("power_override debe tener un valor por tramo.")

    crr_ref = np.choose(prof.surf, list(p.crr_ref_por_superficie()))   # ya con la presión aplicada
    crr1 = np.choose(prof.surf, [p.crr1_liso, p.crr1_normal, p.crr1_rugoso])
    cos_t = prof.ds / prof.path

    vlim, vbase = _speed_limits(prof, p)
    vmax = p.velocidad_maxima / 3.6
    thr, wid = p.umbral_posicion / 3.6, p.anchura_transicion_cda / 3.6

    d_l, dh_l, cos_l = prof.path.tolist(), prof.dh.tolist(), cos_t.tolist()
    rho_l, cr_l, c1_l = rho_seg.tolist(), crr_ref.tolist(), crr1.tolist()
    pn_l, vl_l, vb_l = p_nom.tolist(), vlim.tolist(), vbase.tolist()

    v = [0.0] * (n + 1)
    p_eff = [0.0] * n
    limit = [LIMIT_NONE] * n
    v0 = min(p.velocidad_inicial / 3.6, vl_l[0])
    v[0] = v0
    eta = p.eficiencia
    for j in range(n):
        pn = pn_l[j]
        v1 = solve_segment(v0, d_l[j], dh_l[j], cos_l[j], rho_l[j], cr_l[j], c1_l[j],
                           eta * pn, m, m_ef, p.cda, p.delta_cda, thr, wid)
        lim = vl_l[j + 1]
        if v1 > lim:
            v1 = lim
            pe = required_power(v0, v1, d_l[j], dh_l[j], cos_l[j], rho_l[j], cr_l[j], c1_l[j],
                                m, m_ef, p.cda, p.delta_cda, thr, wid, eta)
            p_eff[j] = min(pe, pn)
            limit[j] = LIMIT_CAP if vb_l[j + 1] >= vmax - 1e-9 and lim >= vmax - 1e-9 else LIMIT_CURVE
        else:
            p_eff[j] = pn
        if v1 < V_LO:
            v1 = V_LO
        v[j + 1] = v1
        v0 = v1

    v_nodes = np.array(v)
    dt = prof.path * 2.0 / (v_nodes[:-1] + v_nodes[1:])
    t_nodes = np.concatenate([[0.0], np.cumsum(dt)])
    v_seg = prof.path / dt
    pe = np.array(p_eff)
    v_mid = 0.5 * (v_nodes[:-1] + v_nodes[1:])
    cda_seg = cda_effective(v_mid, p.cda, p.delta_cda, p.umbral_posicion,
                            p.anchura_transicion_cda)
    crr_seg = crr_effective(v_mid, crr_ref, crr1)

    total_t = float(t_nodes[-1])
    dist_km = prof.length_m / 1000.0
    avg_p = average_power(dt, pe)
    np_w = normalized_power(dt, pe)
    return SimResult(
        params=p, profile=prof, v_nodes=v_nodes, dt=dt, t_nodes=t_nodes,
        power_nominal=p_nom, power_effective=pe, v_seg=v_seg, cda_seg=cda_seg,
        crr_seg=crr_seg, rho_seg=rho_seg, limit_seg=np.array(limit),
        tiempo_s=total_t, distancia_km=dist_km,
        velocidad_media_kmh=(prof.path.sum() / total_t) * 3.6,
        potencia_media_w=avg_p, np_w=np_w, vi=variability_index(np_w, avg_p),
        if_=intensity_factor(np_w, p.ftp), warnings=list(prof.warnings),
    )


def simulate_track(track: TrackData, params: Params, **kw) -> SimResult:
    return simulate(build_profile(track, params), params, **kw)


def table_by_km(result: SimResult, km: float = 1.0):
    """Resumen por bloques de `km` kilómetros (tiempo, velocidad, potencia, pendiente, CdA)."""
    import pandas as pd
    df = result.to_frame()
    df["bloque"] = np.floor(df["km"] / km).astype(int)
    pr = result.profile
    df["path_m"] = pr.path
    df["ds_m"] = pr.ds
    rows = []
    for b, g in df.groupby("bloque"):
        t = g["duracion_s"].sum()
        rows.append({
            "km_inicio": b * km,
            "km_fin": min((b + 1) * km, result.distancia_km),
            "tiempo_s": t,
            "velocidad_kmh": g["path_m"].sum() / t * 3.6,
            "potencia_w": float(np.sum(g["potencia_w"] * g["duracion_s"]) / t),
            "pendiente_%": float(np.sum(g["pendiente_%"] * g["ds_m"]) / g["ds_m"].sum()),
            "cda_medio": float(np.sum(g["cda_efectivo"] * g["duracion_s"]) / t),
            "elevacion_fin_m": float(g["elevacion_m"].iloc[-1]),
        })
    return pd.DataFrame(rows)
