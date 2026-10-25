"""Rutas sintéticas para tests y para la ruta de ejemplo de la app."""
from __future__ import annotations

import math

import numpy as np

from .route import EARTH_R, TrackData


def _offset(lat0, lon0, x, y):
    lat = lat0 + np.degrees(np.asarray(y) / EARTH_R)
    lon = lon0 + np.degrees(np.asarray(x) / (EARTH_R * math.cos(math.radians(lat0))))
    return lat, lon


def straight_track(length_m: float = 20000.0, step: float = 10.0, grade: float = 0.0,
                   bearing_deg: float = 0.0, lat0: float = 43.36, lon0: float = -8.41,
                   ele0: float = 0.0) -> TrackData:
    s = np.arange(0, length_m + step / 2, step)
    b = math.radians(bearing_deg)
    lat, lon = _offset(lat0, lon0, s * math.sin(b), s * math.cos(b))
    return TrackData(lat, lon, ele0 + grade * s, True, [], "recta")


def arc_track(radius: float = 100.0, angle_deg: float = 270.0, lead_m: float = 600.0,
              step: float = 5.0, lat0: float = 43.36, lon0: float = -8.41) -> TrackData:
    """Recta de entrada, arco de radio R y recta de salida (todo plano)."""
    xs, ys = [], []
    n_lead = int(lead_m / step)
    for i in range(n_lead):
        xs.append(0.0)
        ys.append(-lead_m + i * step)
    n_arc = int(math.radians(angle_deg) * radius / step)
    for i in range(n_arc + 1):
        th = i * step / radius
        xs.append(radius * (1 - math.cos(th)))
        ys.append(radius * math.sin(th))
    th = math.radians(angle_deg)
    x_end, y_end = xs[-1], ys[-1]
    for i in range(1, n_lead + 1):
        xs.append(x_end + i * step * math.sin(th))
        ys.append(y_end + i * step * math.cos(th))
    lat, lon = _offset(lat0, lon0, np.array(xs), np.array(ys))
    return TrackData(lat, lon, np.zeros(len(lat)), True, [], "arco")


def loop_track(radius: float = 4000.0, amp: float = 25.0, lobes: int = 2, n: int = 1500,
               wobble: float = 0.0, noise_m: float = 0.0, seed: int = 0,
               lat0: float = 43.36, lon0: float = -8.41) -> TrackData:
    """Circuito cerrado casi circular con colinas: ele = amp·cos(lobes·θ).

    Con `lobes` entero, ele(s) = ele(L−s): la ruta recorrida al revés es idéntica.
    """
    th = np.linspace(0, 2 * math.pi, n, endpoint=True)
    r = radius * (1 + wobble * np.sin(3 * th))
    lat, lon = _offset(lat0, lon0, r * np.cos(th), r * np.sin(th))
    ele = amp * np.cos(lobes * th)
    if noise_m > 0:
        ele = ele + np.random.default_rng(seed).normal(0, noise_m, size=n)
    return TrackData(lat, lon, ele, True, [], "circuito")


def asym_loop_track(radius: float = 4000.0, amp: float = 25.0, n: int = 1500,
                    wobble: float = 0.0, lat0: float = 43.36, lon0: float = -8.41) -> TrackData:
    """Circuito cerrado con perfil de elevación **asimétrico**: ele = amp·(sin θ + 0,4·sin 2θ).

    Al estar hecho de senos, `ele(s) ≠ ele(L − s)`: recorrerlo al revés NO da la misma ruta, así
    que la simetría de tiempos del criterio 9 deja de ser cierta por construcción y hay que
    demostrarla. Cierra (ele(0) = ele(2π) = 0) y el desnivel neto es nulo, como todo circuito.
    """
    th = np.linspace(0, 2 * math.pi, n, endpoint=True)
    r = radius * (1 + wobble * np.sin(3 * th))
    lat, lon = _offset(lat0, lon0, r * np.cos(th), r * np.sin(th))
    ele = amp * (np.sin(th) + 0.4 * np.sin(2 * th))
    return TrackData(lat, lon, ele, True, [], "circuito asimétrico")


def rolling_track(length_m: float = 20000.0, step: float = 10.0, amp: float = 20.0,
                  period_m: float = 4000.0, noise_m: float = 0.0, seed: int = 0) -> TrackData:
    """Recta con ondulaciones sinusoidales (sube y baja), con ruido de elevación opcional."""
    t = straight_track(length_m, step)
    s = np.arange(len(t.lat)) * step
    ele = amp * np.sin(2 * math.pi * s / period_m)
    if noise_m > 0:
        ele = ele + np.random.default_rng(seed).normal(0, noise_m, size=len(s))
    t.ele = ele
    t.name = "ondulada"
    return t


def demo_track() -> TrackData:
    """Circuito de ejemplo (~25 km, ondulado y con curvas suaves)."""
    t = loop_track(radius=4000.0, amp=35.0, lobes=3, n=3000, wobble=0.12)
    t.name = "Ruta de ejemplo (sintética)"
    return t
