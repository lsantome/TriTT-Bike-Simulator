"""Lectura de GPX, remuestreo, suavizado, pendiente y curvatura."""
from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np

from .i18n import t
from .params import Params, SURFACES

EARTH_R = 6371008.8
MAX_GRADE = 0.30       # pendientes mayores se consideran artefacto (|30 %|)

#: 1/m. Radio mínimo con sentido físico (3 m). Es una guarda contra geometría absurda, no un
#: recorte del trazado real: el estimador de curvatura (ver `curvatura`) resuelve radios muy por
#: encima de este valor. Hasta octubre de 2026 valía 0,10 (radio 10 m) y recortaba curvas reales,
#: con lo que el límite por curvatura las dejaba pasar a velocidad insegura.
MAX_CURVATURE = 1.0 / 3.0

#: m. Radio por debajo del cual el límite por curvatura deja de ser fiable con la ventana de
#: trazado por defecto (30 m) y el paso de remuestreo mínimo. No es un recorte: es el alcance
#: medido del estimador (ver `curvatura_por_rumbo`). Por debajo, la predicción es **optimista**:
#: +4,5 % de velocidad sobre `√(a_lat·R)` a radio 8 m y +16,3 % a radio 4 m (arco de 180°).
#: Con una ventana mayor el alcance empeora, ver `radio_resuelto`.
RADIO_RESUELTO_M = 10.0

#: Divisor empírico de `radio_resuelto`: el radio resuelto crece con la ventana de trazado porque
#: una curva más pequeña que la ventana desaparece al suavizar. Medido sobre la rejilla completa
#: (radios 10-200 m × ventanas 30-150 m × arcos de 180° y 540°): con ventana 100 m, R = 10 m
#: excede un 9,6 %; con ventana 150 m, R = 10 m excede un 5,5 % y R = 15 m un 3,5 %.
VENTANA_ENTRE_RADIO = 7.0


def radio_resuelto(ventana_trazado: float) -> float:
    """Radio mínimo (m) hasta el que el límite por curvatura se cumple al 4 % para esa ventana."""
    return max(RADIO_RESUELTO_M, float(ventana_trazado) / VENTANA_ENTRE_RADIO)


#: Factor sobre la ventana de suavizado para la dilatación de la curvatura. El suavizado del
#: trazado reparte la curva sobre ~3σ ≈ la ventana, así que cada nodo hereda la curvatura máxima
#: de su entorno: es lo que impide entrar en la curva a la velocidad de la recta previa, y es lo
#: que cierra la subestimación del rumbo en los extremos del arco.
MARGEN_CURVATURA = 1.2


@dataclass
class TrackData:
    lat: np.ndarray
    lon: np.ndarray
    ele: np.ndarray
    has_elevation: bool = True
    warnings: List[str] = field(default_factory=list)
    name: str = ""

    def reversed(self) -> "TrackData":
        return TrackData(self.lat[::-1].copy(), self.lon[::-1].copy(), self.ele[::-1].copy(),
                         self.has_elevation, list(self.warnings), self.name + " (inversa)")


@dataclass
class Profile:
    s: np.ndarray        # distancia horizontal en nodos (N+1), m
    ds: np.ndarray       # longitud horizontal de cada tramo (N), m
    path: np.ndarray     # longitud real sobre el firme (N), m
    ele: np.ndarray      # elevación suavizada en nodos (N+1), m
    dh: np.ndarray       # desnivel por tramo (N), m
    grade: np.ndarray    # pendiente por tramo (N), m/m
    kappa: np.ndarray    # curvatura en nodos (N+1), 1/m
    x: np.ndarray
    y: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    surf: np.ndarray     # índice de superficie por tramo (0 liso, 1 normal, 2 rugoso)
    warnings: List[str] = field(default_factory=list)

    @property
    def length_m(self) -> float:
        return float(self.s[-1])

    @property
    def total_ascent(self) -> float:
        return float(np.sum(np.clip(self.dh, 0, None)))

    @property
    def total_descent(self) -> float:
        return float(-np.sum(np.clip(self.dh, None, 0)))


# ---------------------------------------------------------------------------
# GPX
# ---------------------------------------------------------------------------

def _read_bytes(source) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if hasattr(source, "read"):
        data = source.read()
        return data.encode("utf-8") if isinstance(data, str) else bytes(data)
    if isinstance(source, (str, Path)):
        if isinstance(source, Path) or (len(str(source)) < 4096 and os.path.exists(str(source))):
            return Path(source).read_bytes()
        if str(source).lstrip().startswith("<"):
            return str(source).encode("utf-8")
    raise ValueError(t("gpx_formato", "es"))


def parse_gpx(source, idioma: str = "es") -> TrackData:
    """Lee un GPX (ruta, bytes, texto o archivo abierto). Usa <trkpt>; si no hay, <rtept>.

    Los errores y los avisos se devuelven traducidos (criterio 27): la interfaz los muestra tal
    cual, y con el selector en inglés salían en castellano.
    """
    try:
        root = ET.fromstring(_read_bytes(source))
    except ET.ParseError as e:
        raise ValueError(t("gpx_no_xml", idioma, detalle=e))
    name = ""
    pts = {"trkpt": [], "rtept": []}
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "name" and not name and el.text:
            name = el.text.strip()
        if tag in pts:
            try:
                lat = float(el.attrib["lat"])
                lon = float(el.attrib["lon"])
            except (KeyError, ValueError):
                continue
            ele = float("nan")
            for ch in el:
                if ch.tag.split("}")[-1] == "ele" and ch.text:
                    try:
                        ele = float(ch.text)
                    except ValueError:
                        pass
            pts[tag].append((lat, lon, ele))
    data = pts["trkpt"] or pts["rtept"]
    if len(data) < 2:
        raise ValueError(t("gpx_sin_puntos", idioma))
    arr = np.array(data, dtype=float)
    return track_from_arrays(arr[:, 0], arr[:, 1], arr[:, 2], name=name, idioma=idioma)


def track_from_arrays(lat, lon, ele=None, name: str = "", idioma: str = "es") -> TrackData:
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    warnings: List[str] = []
    if ele is None:
        ele = np.full_like(lat, np.nan)
    ele = np.asarray(ele, dtype=float)
    ok = np.isfinite(lat) & np.isfinite(lon)
    if not ok.all():
        warnings.append(t("gpx_sin_coordenadas", idioma, n=int((~ok).sum())))
    lat, lon, ele = lat[ok], lon[ok], ele[ok]
    has_ele = bool(np.isfinite(ele).any())
    if not has_ele:
        warnings.append(t("gpx_sin_elevacion", idioma))
        ele = np.zeros_like(lat)
    elif not np.isfinite(ele).all():
        idx = np.arange(len(ele))
        good = np.isfinite(ele)
        warnings.append(t("gpx_elevacion_interpolada", idioma, n=int((~good).sum())))
        ele = np.interp(idx, idx[good], ele[good])
    return TrackData(lat, lon, ele, has_ele, warnings, name)


def _haversine_cumulative(lat, lon) -> np.ndarray:
    la = np.radians(lat)
    lo = np.radians(lon)
    dla = np.diff(la)
    dlo = np.diff(lo)
    a = np.sin(dla / 2) ** 2 + np.cos(la[:-1]) * np.cos(la[1:]) * np.sin(dlo / 2) ** 2
    d = 2 * EARTH_R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    return np.concatenate([[0.0], np.cumsum(d)])


def curvatura_por_rumbo(x, y, s) -> np.ndarray:
    """Curvatura (1/m) en cada nodo como `|dψ/ds|`, con ψ el rumbo del trazado ya suavizado.

    **Por qué esta y no el circunradio.** El circunradio de tres puntos separados una base fija
    devuelve 1/R exactamente para un arco perfecto, sea cual sea la base, y por eso parecía la
    opción obvia. Sobre un trazado real no lo es, y las dos razones se midieron (14-oct-2026,
    arcos de 180° y las tres salidas coherentes del recorrido 2):

    - con base de 30 m, una curva **más corta que la base** se subestima mucho: κ sale un 37 %
      por debajo en una horquilla de radio 8 m y un 67 % en una de radio 4 m, y el límite dejaba
      pasar la curva un 25,6 % y un 74,7 % por encima de `√(a_lat·R)`;
    - bajar la base a 10 m corrige el arco (κ correcta de radio 4 m a 80 m) pero **inventa curvas
      en rutas reales**: el ruido de GPS que sobrevive al suavizado produce radios de 15 m donde
      el trazado crudo gira 0,2°, y la predicción se alarga un 0,49 % sin motivo físico. Tomar la
      mediana o el segundo máximo entre varias bases no lo separa: el ruido aparece en todas.

    La derivada del rumbo no inventa curvas —el giro acumulado es el que es— y su único defecto
    conocido, subestimar en los **extremos** del arco, lo cierra `dilata_maximo`, que lleva a cada
    nodo la curvatura máxima de su entorno. Medido con esa pareja: error de κ entre −2 % y 0 %
    para radios de 10 m en adelante, y −8 % a radio 8 m y −26 % a radio 4 m, que es la limitación
    declarada en el criterio 3 (el paso de remuestreo mínimo, 5 m, no da para más).
    """
    psi = np.unwrap(np.arctan2(np.gradient(y, s), np.gradient(x, s)))
    return np.abs(np.gradient(psi, s))


def dilata_maximo(a, ventana_m: float, step: float) -> np.ndarray:
    """Máximo móvil sobre ±`ventana_m`. No crea valores nuevos: reparte los que ya hay."""
    a = np.asarray(a, dtype=float)
    w = max(1, int(round(ventana_m / step)))
    out = a.copy()
    for d in range(1, w + 1):
        out = np.maximum(out, np.concatenate([a[d:], np.full(d, a[-1])]))
        out = np.maximum(out, np.concatenate([np.full(d, a[0]), a[:-d]]))
    return out


def gaussian_smooth(a, sigma: float) -> np.ndarray:
    """Suavizado gaussiano con reflexión impar en los extremos (conserva tendencias lineales)."""
    a = np.asarray(a, dtype=float)
    if sigma < 0.3 or len(a) < 3:
        return a.copy()
    r = int(min(max(1, math.ceil(3 * sigma)), len(a) - 1))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    left = 2 * a[0] - a[r:0:-1]
    right = 2 * a[-1] - a[-2:-r - 2:-1]
    return np.convolve(np.concatenate([left, a, right]), k, mode="valid")


# ---------------------------------------------------------------------------
# Perfil
# ---------------------------------------------------------------------------

def build_profile(track: TrackData, params: Params, idioma: str = "es") -> Profile:
    lat, lon, ele = track.lat, track.lon, track.ele
    s_raw = _haversine_cumulative(lat, lon)
    keep = np.concatenate([[True], np.diff(s_raw) > 1e-6])
    lat, lon, ele, s_raw = lat[keep], lon[keep], ele[keep], s_raw[keep]
    if len(s_raw) < 2 or s_raw[-1] < 2 * params.paso_remuestreo:
        raise ValueError(t("gpx_ruta_corta", idioma))

    step = params.paso_remuestreo
    n = int(math.floor(s_raw[-1] / step))
    s = np.arange(0, n + 1) * step
    if s_raw[-1] - s[-1] > 1e-6:
        s = np.append(s, s_raw[-1])
    lat0 = float(np.mean(lat))
    x_raw = np.radians(lon - lon.mean()) * EARTH_R * math.cos(math.radians(lat0))
    y_raw = np.radians(lat - lat0) * EARTH_R

    x = np.interp(s, s_raw, x_raw)
    y = np.interp(s, s_raw, y_raw)
    z = np.interp(s, s_raw, ele)
    la = np.interp(s, s_raw, lat)
    lo = np.interp(s, s_raw, lon)

    ds = np.diff(s)
    sig_e = params.ventana_elevacion / 3.5 / step
    z_s = gaussian_smooth(z, sig_e)
    grade = np.clip(np.diff(z_s) / ds, -MAX_GRADE, MAX_GRADE)
    dh = grade * ds
    z_s = z_s[0] + np.concatenate([[0.0], np.cumsum(dh)])
    path = np.sqrt(ds ** 2 + dh ** 2)

    sig_t = params.ventana_trazado / 3.5 / step
    xs = gaussian_smooth(x, sig_t)
    ys = gaussian_smooth(y, sig_t)
    kappa = curvatura_por_rumbo(xs, ys, s)
    kappa = dilata_maximo(kappa, MARGEN_CURVATURA * params.ventana_trazado, step)
    kappa = np.clip(kappa, 0.0, MAX_CURVATURE)

    surf = np.full(len(ds), SURFACES.index(params.superficie), dtype=int)
    s_mid = 0.5 * (s[:-1] + s[1:])
    for a, b, sup in params.tramos_superficie:
        mask = (s_mid >= a * 1000.0) & (s_mid < b * 1000.0)
        surf[mask] = SURFACES.index(sup)

    warns = list(track.warnings)
    return Profile(s, ds, path, z_s, dh, grade, kappa, xs, ys, la, lo, surf, warns)
