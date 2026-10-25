"""Validación con actividades reales (.fit): reproducción de la potencia medida.

Flujo: se toma el trazado GPS del FIT, se simula la ruta con la potencia REAL registrada
(mapeada a cada tramo, ignorando las paradas) y se compara el tiempo en movimiento y la
velocidad predichos con los reales. Así el error aísla el modelo físico del perfil de potencia.

Limitación conocida: el modelo no incluye viento; el viento real de la salida queda absorbido
en el CdA calibrado.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np

from .params import Params
from .route import TrackData, _haversine_cumulative, build_profile, track_from_arrays
from .simulate import simulate

SEMICIRCLE = 180.0 / 2 ** 31
MOVING_SPEED = 1.0   # m/s: por debajo se considera parado


@dataclass
class RideData:
    name: str
    t: np.ndarray          # s
    lat: np.ndarray
    lon: np.ndarray
    alt: np.ndarray
    power: np.ndarray      # W
    speed: np.ndarray      # m/s (del FIT o derivada del GPS)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    name: str
    distancia_km: float
    tiempo_real_movimiento_s: float
    tiempo_predicho_s: float
    error_tiempo_pct: float
    error_velocidad_medio_kmh: float     # predicho − real (con signo)
    mae_velocidad_kmh: float
    rmse_velocidad_kmh: float
    potencia_media_real_w: float
    cda_usado: float
    notas: List[str] = field(default_factory=list)

    def as_dict(self):
        return dict(self.__dict__)


def read_fit(source, name: str = "") -> RideData:
    """Lee un FIT (ruta, bytes o archivo abierto) y devuelve los registros por segundo."""
    import fitdecode
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(bytes(source))
    rows = []
    with fitdecode.FitReader(source) as fr:
        for frame in fr:
            if isinstance(frame, fitdecode.FitDataMessage) and frame.name == "record":
                def g(*names):
                    for nme in names:
                        if frame.has_field(nme):
                            v = frame.get_value(nme, fallback=None)
                            if v is not None:
                                return v
                    return None
                ts = g("timestamp")
                if ts is None:
                    continue
                rows.append((ts, g("position_lat"), g("position_long"),
                             g("enhanced_altitude", "altitude"), g("power"),
                             g("enhanced_speed", "speed")))
    if len(rows) < 20:
        raise ValueError("El FIT tiene muy pocos registros.")
    t0 = rows[0][0]
    t = np.array([(r[0] - t0).total_seconds() for r in rows], dtype=float)

    def col(i, scale=1.0):
        return np.array([np.nan if r[i] is None else float(r[i]) * scale for r in rows])
    lat, lon = col(1, SEMICIRCLE), col(2, SEMICIRCLE)
    alt, power, speed = col(3), col(4), col(5)
    warns = []
    if np.isnan(lat).all():
        raise ValueError("El FIT no contiene posición GPS (¿rodillo?): no se puede simular la ruta.")
    if np.isnan(power).all():
        raise ValueError("El FIT no contiene potencia.")
    return RideData(name or "actividad", t, lat, lon, alt, power, speed, warns)


def ride_to_track(ride: RideData) -> TrackData:
    ok = np.isfinite(ride.lat) & np.isfinite(ride.lon)
    return track_from_arrays(ride.lat[ok], ride.lon[ok], ride.alt[ok], name=ride.name)


def _align(ride: RideData):
    """Distancia horizontal acumulada (GPS) por registro válido, con potencia y velocidad."""
    ok = np.isfinite(ride.lat) & np.isfinite(ride.lon)
    lat, lon, t = ride.lat[ok], ride.lon[ok], ride.t[ok]
    power = np.nan_to_num(ride.power[ok], nan=0.0)
    s = _haversine_cumulative(lat, lon)
    speed = ride.speed[ok].copy()
    if np.isnan(speed).all():
        dt = np.maximum(np.diff(t, prepend=t[0] - 1.0), 1e-3)
        speed = np.diff(s, prepend=0.0) / dt
    speed = np.where(np.isfinite(speed), speed, 0.0)
    return t, s, power, speed


def power_by_segment(ride: RideData, profile) -> np.ndarray:
    """Potencia media real por tramo del perfil, usando solo muestras en movimiento."""
    t, s, power, speed = _align(ride)
    moving = speed >= MOVING_SPEED
    n = len(profile.ds)
    sums = np.zeros(n)
    cnt = np.zeros(n)
    idx = np.clip(np.searchsorted(profile.s, s[moving], side="right") - 1, 0, n - 1)
    np.add.at(sums, idx, power[moving])
    np.add.at(cnt, idx, 1.0)
    mid = 0.5 * (profile.s[:-1] + profile.s[1:])
    have = cnt > 0
    out = np.empty(n)
    out[have] = sums[have] / cnt[have]
    if (~have).any():
        out[~have] = np.interp(mid[~have], mid[have], out[have])
    return out


def replay(ride: RideData, params: Params) -> ValidationReport:
    t, s, power, speed = _align(ride)
    track = ride_to_track(ride)
    moving = speed >= MOVING_SPEED
    notes: List[str] = list(track.warnings)
    if not track.has_elevation:
        notes.append("Sin altitud en el FIT: la predicción asume ruta plana.")
    first = speed[moving][0] if moving.any() else params.velocidad_inicial / 3.6
    p = params.con(velocidad_inicial=float(np.clip(first * 3.6, 5.0, 60.0)))
    profile = build_profile(track, p)
    res = simulate(profile, p, power_override=power_by_segment(ride, profile))

    dts = np.diff(t, prepend=t[0])
    real_move_t = float(np.sum(np.where(moving, np.clip(dts, 0, 30), 0.0)))
    # velocidad real interpolada en los nodos (solo donde hay movimiento)
    real_v_nodes = np.interp(profile.s, s, speed)
    m_nodes = real_v_nodes >= MOVING_SPEED
    err = (res.v_nodes - real_v_nodes)[m_nodes] * 3.6
    mean_err = float(err.mean()) if err.size else float("nan")
    mae = float(np.abs(err).mean()) if err.size else float("nan")
    rmse = float(np.sqrt((err ** 2).mean())) if err.size else float("nan")
    notes.append("Modelo sin viento: el viento de la salida queda absorbido en el CdA ajustado.")
    return ValidationReport(
        name=ride.name, distancia_km=profile.length_m / 1000.0,
        tiempo_real_movimiento_s=real_move_t, tiempo_predicho_s=res.tiempo_s,
        error_tiempo_pct=(res.tiempo_s - real_move_t) / real_move_t * 100.0,
        error_velocidad_medio_kmh=mean_err, mae_velocidad_kmh=mae, rmse_velocidad_kmh=rmse,
        potencia_media_real_w=float(power[moving].mean()) if moving.any() else 0.0,
        cda_usado=params.cda, notas=notes)


def calibrate_cda(rides: Sequence[RideData], params: Params, lo: float = 0.10,
                  hi: float = 0.60, tol: float = 1e-4) -> float:
    """CdA que iguala el tiempo predicho total al real en las rutas de calibración
    (bisección: el tiempo crece de forma monótona con el CdA)."""
    def total_error(cda):
        pp = params.con(cda=cda)
        return sum(r.tiempo_predicho_s - r.tiempo_real_movimiento_s
                   for r in (replay(x, pp) for x in rides))
    if total_error(lo) > 0:
        return lo
    if total_error(hi) < 0:
        return hi
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if total_error(mid) > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)
