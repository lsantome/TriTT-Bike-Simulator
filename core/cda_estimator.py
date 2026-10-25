"""Estimación del CdA a partir de una actividad real (.fit).

## El método

Sobre el segmento elegido se cierra el balance de energía. Lo que entra por los pedales, menos lo
que se gasta en subir, en rodadura y en cambiar la energía cinética, es lo que se ha ido en
aerodinámica:

    ∫ η·P dt − Σ ½·m_ef·(v²ᵢ₊₁ − v²ᵢ) − m·g·Σ Δh − ∫ Crr(v)·m·g·cosθ·v dt  =  ∫ ½·ρ·CdA·v³ dt

y de ahí se despeja el CdA medio del segmento. No hace falta suponer velocidad ni pendiente
constantes: se integra intervalo a intervalo. El término cinético se suma por intervalos en vez de
restar los extremos, para que los huecos (paradas, pérdidas de GPS) no metan un salto falso.

## Por qué el número puede salir mal

El denominador (∫½ρv³dt) crece con el cubo de la velocidad, pero el término de la pendiente
(m·g·Δh) crece con el desnivel sin más. En un segmento corto, lento o con cuesta, **el desnivel
pesa mucho más que la aerodinámica**, y entonces un error de un metro en la altitud del GPS se
traga la estimación entera. Esto no es un defecto de la implementación: es la física del problema.

Por eso cada estimación viene con su incertidumbre, calculada propagando tres errores concretos:

- **altitud**: ±1 m de error en el desnivel del segmento (ajustable),
- **Crr**: ±0,0005 de error en el coeficiente de rodadura,
- **potencia**: ±1,5 % de sesgo del potenciómetro.

Y con un diagnóstico que dice si el segmento sirve. **El viento no se modela**: si sopla, su efecto
entra entero dentro del CdA estimado, y es el término más grande de todos. Como es un sesgo y no
ruido, va fuera de la incertidumbre y se cancela de otra manera: promediando un tramo de ida con el
mismo de vuelta. `find_flat_segments` busca los tramos aprovechables y `pair_opposite_segments`
empareja los de sentidos opuestos, que es la forma correcta de quitarse el viento de encima.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .atmosphere import air_density
from .i18n import IDIOMA_POR_DEFECTO, t
from .params import Params, validate_params
from .physics import G, crr_effective
from .route import EARTH_R
from .validation import MOVING_SPEED, RideData, _align

#: Errores que se propagan para dar la incertidumbre del CdA.
ERROR_ALTITUD_M = 1.0
ERROR_CRR = 0.0005
SESGO_POTENCIA_REL = 0.015
#: Viento frontal de referencia para medir cuánto contamina la estimación (m/s).
VIENTO_REFERENCIA_MS = 1.0

#: Mínimos para que un segmento se considere utilizable.
#: La distancia es la del criterio 25, «tramos llanos de al menos 1 km», y se mide sobre el camino
#: **recorrido con datos válidos**, no sobre la anchura de la ventana de búsqueda: hasta octubre de
#: 2026 valía 500 m y la búsqueda devolvía tramos de 944,7 m sobre ventanas de 1 km, porque los
#: huecos de la grabación se descontaban después del filtro.
MIN_DISTANCIA_M = 1000.0
MIN_DURACION_S = 45.0
MIN_VELOCIDAD_KMH = 25.0
#: Fracción mínima de la energía disipada que debe ser aerodinámica.
MIN_FRACCION_AERO = 0.50
#: Incertidumbre por encima de la cual el valor no se puede tomar en serio.
MAX_INCERTIDUMBRE_CDA = 0.030

#: Búsqueda automática de tramos: longitudes que se prueban (m) y paso entre ventanas (m).
LONGITUDES_BUSQUEDA_M = (1000.0, 1500.0, 2000.0, 3000.0, 5000.0)
PASO_BUSQUEDA_M = 250.0
#: Un tramo se considera llano si su pendiente media y su desnivel neto no pasan de esto.
MAX_PENDIENTE_LLANA_PCT = 1.0
MAX_DESNIVEL_LLANO_M = 10.0
#: Tolerancia para considerar que dos tramos van en sentidos opuestos (grados).
TOLERANCIA_OPUESTOS_GRADOS = 40.0

#: Relación máxima de velocidades (la mayor entre la menor) admisible en un par de ida y vuelta.
#:
#: Dos pasadas por la misma carretera llana no pueden diferir tanto en velocidad. Si difieren, el
#: filtro de llaneza ha dejado pasado una bajada o una subida que el suavizado del altímetro
#: barométrico aplanó, y el par no mide viento: mide pendiente.
#:
#: **Umbral medido** (criterio 28, validación de 5-oct-2026 con cinco salidas del recorrido 2): la
#: relación máxima entre pares legítimos de las cuatro salidas coherentes es **1,42**, y los pares
#: imposibles de la salida del 04-may-2025 están en **2,13, 2,56 y 3,24** — uno empareja 56,7 km/h
#: con 22,2 km/h. El 1,5 deja margen por los dos lados.
#:
#: **Por qué no se filtra por discrepancia de CdA.** Rechazar los pares con mucha diferencia entre
#: ida y vuelta aprieta más la dispersión (1,5 % frente a 1,9 %), pero descarta pares legítimos de
#: las salidas buenas y selecciona por viento bajo: es la trampa de ponderación ya rechazada en
#: `combine_pairs`. Este filtro elimina datos *imposibles*, no datos incómodos.
#:
#: Es el **valor por defecto** del parámetro `razon_velocidad_par`, editable en la interfaz
#: (criterio 28: «con el umbral editable»). Hasta octubre de 2026 solo existía como constante y
#: como argumento de estas dos funciones, así que el criterio no se cumplía: desde la aplicación no
#: había forma de tocarlo. Lo que se usa en cada llamada sale de `Params`, no de aquí.
MAX_RAZON_VELOCIDAD_PAR = 1.5
#: Separación máxima entre los centros de dos tramos para considerarlos la MISMA carretera (m).
MAX_SEPARACION_MISMA_VIA_M = 1000.0


@dataclass
class SegmentEstimate:
    """CdA estimado en un segmento, con su incertidumbre y su diagnóstico."""
    nombre: str
    km_inicio: float
    km_fin: float
    distancia_m: float
    duracion_s: float
    velocidad_media_kmh: float
    desnivel_m: float
    pendiente_media_pct: float
    potencia_media_w: float
    densidad_aire: float
    cda: float
    cda_incertidumbre: float
    fraccion_aero: float               # parte aerodinámica de la energía disipada
    fraccion_sin_pedalear: float
    rumbo_grados: float                # rumbo medio del tramo (0 = norte, 90 = este)
    lat_media: float                   # centro geográfico, para reconocer la misma carretera
    lon_media: float
    sens_altitud: float                # ΔCdA por ERROR_ALTITUD_M
    sens_crr: float                    # ΔCdA por ERROR_CRR
    sens_potencia: float               # ΔCdA por SESGO_POTENCIA_REL
    sens_viento: float                 # ΔCdA por VIENTO_REFERENCIA_MS de viento frontal
    utilizable: bool
    avisos: List[str] = field(default_factory=list)

    @property
    def cda_min(self) -> float:
        return self.cda - self.cda_incertidumbre

    @property
    def cda_max(self) -> float:
        return self.cda + self.cda_incertidumbre

    @property
    def llano(self) -> bool:
        return (abs(self.pendiente_media_pct) <= MAX_PENDIENTE_LLANA_PCT
                and abs(self.desnivel_m) <= MAX_DESNIVEL_LLANO_M)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["cda_min"], d["cda_max"], d["llano"] = self.cda_min, self.cda_max, self.llano
        return d


# --------------------------------------------------------------------------- preparación
@dataclass
class _PreparedRide:
    """La actividad convertida una sola vez en magnitudes por intervalo.

    Prepararla aparte es lo que permite barrer cientos de ventanas sin recalcular la actividad
    completa cada vez, y además hace que el suavizado de la altitud sea el mismo para todas las
    ventanas (si se suavizara dentro de cada segmento, el resultado dependería de dónde se corta).
    """
    nombre: str
    s_nodo: np.ndarray                 # distancia acumulada de cada muestra (m)
    lat: np.ndarray
    lon: np.ndarray
    dt: np.ndarray                     # por intervalo
    ds: np.ndarray
    dh: np.ndarray
    camino: np.ndarray
    cos_t: np.ndarray
    v_lo: np.ndarray
    v_hi: np.ndarray
    v_mid: np.ndarray
    pw_mid: np.ndarray
    alt_suave: np.ndarray
    valido: np.ndarray                 # intervalos usables (en movimiento, dt razonable)


def _smooth_altitude(alt: np.ndarray, s: np.ndarray, ventana_m: float) -> np.ndarray:
    """Suavizado gaussiano de la altitud con reflexión impar, como en `core.route`."""
    if not np.isfinite(alt).all() or len(alt) < 4:
        return alt
    paso = max(float(np.median(np.diff(s))), 1e-6)
    n_win = max(3, int(round(ventana_m / paso)) | 1)
    if n_win >= len(alt):
        n_win = max(3, (len(alt) - 1) | 1)
    nucleo = np.exp(-0.5 * (np.arange(n_win) - n_win // 2) ** 2 / (n_win / 3.5) ** 2)
    nucleo /= nucleo.sum()
    pad = n_win // 2
    ext = np.concatenate([2 * alt[0] - alt[1:pad + 1][::-1], alt,
                          2 * alt[-1] - alt[-pad - 1:-1][::-1]])
    return np.convolve(ext, nucleo, mode="same")[pad:pad + len(alt)]


def _prepare(ride: RideData, params: Params,
             ventana_altitud_m: Optional[float] = None) -> _PreparedRide:
    t, s, power, speed = _align(ride)
    ok = np.isfinite(ride.lat) & np.isfinite(ride.lon)
    lat, lon = np.asarray(ride.lat, float)[ok], np.asarray(ride.lon, float)[ok]
    alt = np.asarray(ride.alt, dtype=float)[ok]
    if len(s) < 5:
        raise ValueError("La actividad tiene menos de 5 registros con GPS.")

    ventana = float(ventana_altitud_m if ventana_altitud_m else params.ventana_elevacion)
    alt_suave = _smooth_altitude(alt, s, ventana)
    hay_alt = np.isfinite(alt_suave).all()

    dt = np.diff(t)
    ds = np.diff(s)
    dh = np.diff(alt_suave) if hay_alt else np.zeros_like(ds)
    camino = np.sqrt(ds ** 2 + dh ** 2)
    camino = np.where(camino > 0, camino, np.maximum(ds, 1e-6))
    v_lo, v_hi = speed[:-1], speed[1:]
    v_mid = 0.5 * (v_lo + v_hi)
    valido = (dt > 0) & (dt < 30) & (v_mid >= MOVING_SPEED)
    return _PreparedRide(
        nombre=ride.name, s_nodo=s, lat=lat, lon=lon, dt=dt, ds=ds, dh=dh, camino=camino,
        cos_t=np.clip(ds / camino, 0.0, 1.0), v_lo=v_lo, v_hi=v_hi, v_mid=v_mid,
        pw_mid=0.5 * (power[:-1] + power[1:]), alt_suave=alt_suave, valido=valido)


def _rumbo(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Rumbo (grados, 0 = norte) de la cuerda que une los extremos del tramo.

    Es la dirección que importa para el viento: lo que se recorre en conjunto, no cada curva.
    """
    f1, f2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(f2)
    y = math.cos(f1) * math.sin(f2) - math.sin(f1) * math.cos(f2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def _crr_base(params: Params) -> float:
    """Crr de referencia de la superficie global, ya con la presión aplicada."""
    idx = {"liso": 0, "normal": 1, "rugoso": 2}[params.superficie]
    return params.crr_ref_por_superficie()[idx]


def _crr1(params: Params) -> float:
    return {"liso": params.crr1_liso, "normal": params.crr1_normal,
            "rugoso": params.crr1_rugoso}[params.superficie]


def ride_distance_km(ride: RideData) -> np.ndarray:
    """Distancia acumulada (km) de cada muestra válida, para poder elegir el segmento."""
    _, s, _, _ = _align(ride)
    return s / 1000.0


# --------------------------------------------------------------------------- estimación
def _estimate(prep: _PreparedRide, p: Params, i0: int, i1: int, *,
              error_altitud_m: float, error_crr: float, sesgo_potencia_rel: float,
              viento_referencia_ms: float, con_avisos: bool = True,
              idioma: str = IDIOMA_POR_DEFECTO) -> SegmentEstimate:
    """Estima el CdA en los intervalos [i0, i1) de una actividad ya preparada."""
    sel = prep.valido[i0:i1]
    if sel.sum() < 4:
        raise ValueError("El segmento no tiene suficientes muestras en movimiento.")

    dt = prep.dt[i0:i1][sel]
    v_mid = prep.v_mid[i0:i1][sel]
    v_lo, v_hi = prep.v_lo[i0:i1][sel], prep.v_hi[i0:i1][sel]
    pw_mid = prep.pw_mid[i0:i1][sel]
    dh = prep.dh[i0:i1][sel]
    camino = prep.camino[i0:i1][sel]
    cos_t = prep.cos_t[i0:i1][sel]

    m = p.masa_total
    m_ef = m + p.inercia_ruedas / p.radio_efectivo ** 2
    alt_tramo = prep.alt_suave[i0:i1 + 1]
    alt_media = float(np.nanmean(alt_tramo)) if np.isfinite(alt_tramo).all() else 0.0
    rho = (float(p.densidad_manual) if p.densidad_manual
           else float(air_density(p.temperatura, p.humedad, p.presion_nivel_mar, alt_media)))

    crr = crr_effective(v_mid, _crr_base(p), _crr1(p))
    # cinética por intervalos: así un hueco en los datos no mete un salto de energía falso
    e_cinetica = 0.5 * m_ef * float(np.sum(v_hi ** 2 - v_lo ** 2))
    denominador = float(np.sum(0.5 * rho * v_mid ** 3 * dt))
    if denominador <= 0:
        raise ValueError("El segmento no tiene velocidad suficiente para estimar el CdA.")

    def _cda(pot_factor: float = 1.0, dh_extra: float = 0.0, crr_extra: float = 0.0):
        e_pedales = float(np.sum(p.eficiencia * pot_factor * pw_mid * dt))
        e_altura = m * G * (float(np.sum(dh)) + dh_extra)
        e_rodadura = float(np.sum((crr + crr_extra) * m * G * cos_t * camino))
        e_aero = e_pedales - e_cinetica - e_altura - e_rodadura
        return e_aero / denominador, e_aero, e_rodadura, e_altura

    cda, e_aero, e_rod, e_alt = _cda()
    sens_alt = abs(_cda(dh_extra=error_altitud_m)[0] - cda)
    sens_crr = abs(_cda(crr_extra=error_crr)[0] - cda)
    sens_pot = abs(_cda(pot_factor=1.0 + sesgo_potencia_rel)[0] - cda)
    incert = float(np.sqrt(sens_alt ** 2 + sens_crr ** 2 + sens_pot ** 2))

    # Sensibilidad al viento. NO entra en la incertidumbre: no es un error aleatorio sino un sesgo
    # que solo se cancela promediando ida y vuelta. Con viento w la resistencia real es
    # ½ρ·CdA·(v+w)²·v, así que el CdA que cierra el balance sin viento queda escalado por
    # ⟨v³⟩/⟨(v+w)²·v⟩. Suele ser el término más grande de todos, y con diferencia.
    w = float(viento_referencia_ms)
    num = float(np.sum((v_mid + w) ** 2 * v_mid * dt))
    sens_viento = abs(cda - cda * denominador / (0.5 * rho * num)) if num > 0 else float("nan")

    distancia = float(np.sum(camino))
    duracion = float(np.sum(dt))
    v_media = distancia / duracion * 3.6 if duracion > 0 else 0.0
    desnivel = float(np.sum(dh))
    disipada = abs(e_aero) + abs(e_rod) + max(e_alt, 0.0)
    fraccion_aero = float(abs(e_aero) / disipada) if disipada > 0 else 0.0
    sin_pedalear = float(np.mean(pw_mid <= 1.0))
    pendiente = float(desnivel / distancia * 100.0) if distancia > 0 else 0.0

    km_ini = float(prep.s_nodo[i0] / 1000.0)
    km_fin = float(prep.s_nodo[min(i1, len(prep.s_nodo) - 1)] / 1000.0)
    j1 = min(i1, len(prep.lat) - 1)
    rumbo = _rumbo(prep.lat[i0], prep.lon[i0], prep.lat[j1], prep.lon[j1])
    jm = (i0 + j1) // 2

    utilizable = bool(distancia >= MIN_DISTANCIA_M and duracion >= MIN_DURACION_S
                      and v_media >= MIN_VELOCIDAD_KMH and fraccion_aero >= MIN_FRACCION_AERO
                      and incert <= MAX_INCERTIDUMBRE_CDA and 0.05 < cda <= 0.70)

    avisos: List[str] = []
    if con_avisos:
        if distancia < MIN_DISTANCIA_M:
            avisos.append(t("aviso_corto", idioma, d=distancia, min=MIN_DISTANCIA_M))
        if duracion < MIN_DURACION_S:
            avisos.append(t("aviso_breve", idioma, t=duracion, min=MIN_DURACION_S))
        if v_media < MIN_VELOCIDAD_KMH:
            avisos.append(t("aviso_lento", idioma, v=v_media, min=MIN_VELOCIDAD_KMH))
        if fraccion_aero < MIN_FRACCION_AERO:
            avisos.append(t("aviso_poco_aero", idioma, pct=fraccion_aero * 100))
        if abs(desnivel) > MAX_DESNIVEL_LLANO_M:
            avisos.append(t("aviso_desnivel", idioma, dh=desnivel))
        if incert > MAX_INCERTIDUMBRE_CDA:
            avisos.append(t("aviso_incertidumbre", idioma, inc=incert, max=MAX_INCERTIDUMBRE_CDA))
        if sin_pedalear > 0.5:
            avisos.append(t("aviso_sin_pedalear", idioma, pct=sin_pedalear * 100))
        if cda <= 0.05 or cda > 0.70:
            avisos.append(t("aviso_implausible", idioma, cda=cda))
        avisos.append(t("aviso_viento", idioma, w=w, wkmh=w * 3.6, sens=sens_viento, inc=incert))

    return SegmentEstimate(
        nombre=prep.nombre, km_inicio=km_ini, km_fin=km_fin, distancia_m=distancia,
        duracion_s=duracion, velocidad_media_kmh=v_media, desnivel_m=desnivel,
        pendiente_media_pct=pendiente, potencia_media_w=float(np.average(pw_mid, weights=dt)),
        densidad_aire=rho, cda=float(cda), cda_incertidumbre=incert,
        fraccion_aero=fraccion_aero,
        fraccion_sin_pedalear=sin_pedalear, rumbo_grados=rumbo,
        lat_media=float(prep.lat[jm]), lon_media=float(prep.lon[jm]),
        sens_altitud=float(sens_alt), sens_crr=float(sens_crr), sens_potencia=float(sens_pot),
        sens_viento=float(sens_viento), utilizable=utilizable, avisos=avisos)


def estimate_cda(ride: RideData, params: Params, km_inicio: float, km_fin: float,
                 *, ventana_altitud_m: Optional[float] = None,
                 error_altitud_m: float = ERROR_ALTITUD_M,
                 error_crr: float = ERROR_CRR,
                 sesgo_potencia_rel: float = SESGO_POTENCIA_REL,
                 viento_referencia_ms: float = VIENTO_REFERENCIA_MS,
                 idioma: str = IDIOMA_POR_DEFECTO) -> SegmentEstimate:
    """Estima el CdA medio del segmento [km_inicio, km_fin] de una actividad.

    Lanza `ValueError` si el segmento no tiene muestras suficientes para cerrar el balance.
    Un segmento inservible **no** lanza excepción: devuelve `utilizable=False` con sus avisos.
    """
    p = validate_params(params)
    if km_fin <= km_inicio:
        raise ValueError("El segmento debe terminar después de empezar.")
    prep = _prepare(ride, p, ventana_altitud_m)
    i0 = int(np.searchsorted(prep.s_nodo, km_inicio * 1000.0, side="left"))
    i1 = int(np.searchsorted(prep.s_nodo, km_fin * 1000.0, side="right")) - 1
    if i1 - i0 < 4:
        raise ValueError("El segmento tiene menos de 5 registros: elige uno más largo.")
    return _estimate(prep, p, i0, i1, error_altitud_m=error_altitud_m, error_crr=error_crr,
                     sesgo_potencia_rel=sesgo_potencia_rel,
                     viento_referencia_ms=viento_referencia_ms, idioma=idioma)


# --------------------------------------------------------------------------- búsqueda automática
def find_flat_segments(ride: RideData, params: Params, *,
                       longitudes_m: Sequence[float] = LONGITUDES_BUSQUEDA_M,
                       paso_m: float = PASO_BUSQUEDA_M,
                       max_pendiente_pct: float = MAX_PENDIENTE_LLANA_PCT,
                       max_desnivel_m: float = MAX_DESNIVEL_LLANO_M,
                       maximo: int = 12,
                       ventana_altitud_m: Optional[float] = None,
                       idioma: str = IDIOMA_POR_DEFECTO) -> List[SegmentEstimate]:
    """Busca por la actividad los tramos **llanos y fiables** donde estimar el CdA.

    Barre ventanas de varias longitudes (por defecto de 1 a 5 km, cada 250 m), se queda con las
    que cumplen todos los criterios de validez **y** son llanas, y descarta los solapes quedándose
    con la mejor de cada zona. El orden es por incertidumbre creciente: el primero es el más fiable.

    No garantiza que el CdA de cada tramo sea el correcto: el viento sigue ahí. Para eso están
    `pair_opposite_segments` y `combine_estimates`.
    """
    p = validate_params(params)
    prep = _prepare(ride, p, ventana_altitud_m)
    total_m = float(prep.s_nodo[-1])
    candidatos: List[SegmentEstimate] = []

    for largo in sorted(set(float(x) for x in longitudes_m)):
        if largo > total_m:
            continue
        inicio = 0.0
        while inicio + largo <= total_m + 1e-9:
            i0 = int(np.searchsorted(prep.s_nodo, inicio, side="left"))
            i1 = int(np.searchsorted(prep.s_nodo, inicio + largo, side="right")) - 1
            inicio += paso_m
            if i1 - i0 < 4:
                continue
            try:
                est = _estimate(prep, p, i0, i1, error_altitud_m=ERROR_ALTITUD_M,
                                error_crr=ERROR_CRR, sesgo_potencia_rel=SESGO_POTENCIA_REL,
                                viento_referencia_ms=VIENTO_REFERENCIA_MS, con_avisos=False)
            except ValueError:
                continue
            if (est.utilizable and abs(est.pendiente_media_pct) <= max_pendiente_pct
                    and abs(est.desnivel_m) <= max_desnivel_m):
                candidatos.append(est)

    # quitar solapes: se ordena por fiabilidad y se van descartando los que pisan a uno mejor
    candidatos.sort(key=lambda e: (e.cda_incertidumbre, -e.distancia_m))
    elegidos: List[SegmentEstimate] = []
    for est in candidatos:
        if any(est.km_inicio < otro.km_fin and otro.km_inicio < est.km_fin for otro in elegidos):
            continue
        # se recalcula con avisos para que el que llega al usuario los lleve
        elegidos.append(estimate_cda(ride, p, est.km_inicio, est.km_fin,
                                     ventana_altitud_m=ventana_altitud_m, idioma=idioma))
        if len(elegidos) >= maximo:
            break
    return elegidos


def separacion_m(a: SegmentEstimate, b: SegmentEstimate) -> float:
    """Distancia entre los centros geográficos de dos tramos."""
    lat_m = math.radians((a.lat_media + b.lat_media) / 2.0)
    dx = math.radians(b.lon_media - a.lon_media) * math.cos(lat_m)
    dy = math.radians(b.lat_media - a.lat_media)
    return float(EARTH_R * math.hypot(dx, dy))


def razon_velocidades(a: SegmentEstimate, b: SegmentEstimate) -> float:
    """Relación entre la velocidad media mayor y la menor de dos tramos (≥ 1)."""
    alta = max(a.velocidad_media_kmh, b.velocidad_media_kmh)
    baja = min(a.velocidad_media_kmh, b.velocidad_media_kmh)
    return float(alta / baja) if baja > 0 else float("inf")


@dataclass
class ParRechazado:
    """Par de ida y vuelta descartado por imposible, con el motivo a la vista (criterio 28)."""
    ida: SegmentEstimate
    vuelta: SegmentEstimate
    razon_velocidades: float
    motivo: str


def _par_imposible(a: SegmentEstimate, b: SegmentEstimate, max_razon: float,
                   idioma: str) -> Optional[ParRechazado]:
    """Devuelve el rechazo si el par no puede ser la misma carretera llana, o `None`."""
    razon = razon_velocidades(a, b)
    if razon < max_razon:
        return None
    return ParRechazado(ida=a, vuelta=b, razon_velocidades=razon,
                        motivo=t("est_par_rechazado", idioma, razon=f"{razon:.2f}",
                                 v_alta=f"{max(a.velocidad_media_kmh, b.velocidad_media_kmh):.1f}",
                                 v_baja=f"{min(a.velocidad_media_kmh, b.velocidad_media_kmh):.1f}",
                                 umbral=f"{max_razon:.2f}"))


@dataclass
class OppositePair:
    """Dos pasadas por la misma carretera en sentidos opuestos."""
    ida: SegmentEstimate
    vuelta: SegmentEstimate
    cda: float                 # media de los dos: el viento se cancela en primer orden
    discrepancia: float        # mitad de la diferencia: cuánto viento había
    separacion_m: float

    @property
    def viento_estimado_ms(self) -> float:
        """Viento aproximado que explicaría la diferencia entre ida y vuelta.

        De `CdA_aparente ≈ CdA·(1 ± w/v)²` sale `w ≈ v·(√(CdA_ida/CdA_vuelta) − 1)`, con la
        velocidad media de las dos pasadas. Es una cifra orientativa, no una medición.
        """
        v = (self.ida.velocidad_media_kmh + self.vuelta.velocidad_media_kmh) / 2.0 / 3.6
        alto, bajo = max(self.ida.cda, self.vuelta.cda), min(self.ida.cda, self.vuelta.cda)
        return float(v * (math.sqrt(alto / bajo) - 1.0) / 2.0) if bajo > 0 else float("nan")


def pair_opposite_segments(segmentos: Sequence[SegmentEstimate], *,
                           tolerancia_grados: float = TOLERANCIA_OPUESTOS_GRADOS,
                           max_separacion_m: float = MAX_SEPARACION_MISMA_VIA_M,
                           max_razon_velocidad: float = MAX_RAZON_VELOCIDAD_PAR,
                           rechazados: Optional[List[ParRechazado]] = None,
                           idioma: str = IDIOMA_POR_DEFECTO) -> List[OppositePair]:
    """Empareja tramos que recorren **la misma carretera en sentidos opuestos**.

    Promediar una pasada de ida con una de vuelta es la única forma de cancelar el viento sin
    modelarlo: lo que a la ida infla el CdA, a la vuelta lo desinfla. Pero solo vale si es la misma
    carretera, así que además de los rumbos opuestos se exige que los centros de los dos tramos
    estén cerca: dos tramos llanos en sentidos opuestos a 40 km de distancia no comparten ni el
    viento ni el firme.

    La **discrepancia** (media diferencia entre ambos CdA) es la cota realista del error de ese CdA
    combinado, y a la vez una medida de cuánto viento había.

    Criterio 28: el par cuya relación de velocidades alcanza `max_razon_velocidad` se descarta por
    imposible y, si se pasa una lista en `rechazados`, se anota ahí con su motivo.
    """
    pares: List[OppositePair] = []
    usados: set = set()
    orden = sorted(range(len(segmentos)), key=lambda i: segmentos[i].cda_incertidumbre)
    for i in orden:
        if i in usados:
            continue
        a = segmentos[i]
        mejor, mejor_sep = None, None
        for j in orden:
            if j == i or j in usados:
                continue
            b = segmentos[j]
            dif_rumbo = abs((a.rumbo_grados - b.rumbo_grados + 180.0) % 360.0 - 180.0)
            if abs(dif_rumbo - 180.0) > tolerancia_grados:
                continue
            sep = separacion_m(a, b)
            if sep > max_separacion_m:
                continue
            if mejor_sep is None or sep < mejor_sep:        # la misma carretera manda
                mejor, mejor_sep = j, sep
        if mejor is not None:
            b = segmentos[mejor]
            rechazo = _par_imposible(a, b, max_razon_velocidad, idioma)
            if rechazo is not None:
                if rechazados is not None:
                    rechazados.append(rechazo)
                continue          # no se marca como usado: un par imposible no consume tramos
            # El orden importa, y hasta octubre de 2026 estaba al revés: se marcaban los dos
            # tramos como usados **antes** de comprobar el rechazo, así que un par imposible se
            # llevaba por delante dos segmentos que podrían haber emparejado con otros.
            # `find_paired_segments` ya lo hacía bien; estas dos funciones tienen que coincidir.
            usados.update({i, mejor})
            pares.append(OppositePair(ida=a, vuelta=b, cda=(a.cda + b.cda) / 2.0,
                                      discrepancia=abs(a.cda - b.cda) / 2.0,
                                      separacion_m=mejor_sep))
    pares.sort(key=lambda par: (par.discrepancia, par.separacion_m))
    return pares


#: Radio para dar por buena la coincidencia con la pasada de vuelta (m).
RADIO_PASADA_VUELTA_M = 300.0


def _rumbo_local(prep: _PreparedRide, j: int, nodos: int = 10) -> float:
    a = max(0, j - nodos)
    b = min(len(prep.lat) - 1, j + nodos)
    return _rumbo(prep.lat[a], prep.lon[a], prep.lat[b], prep.lon[b])


def find_return_pass(ride: RideData, params: Params, segmento: SegmentEstimate, *,
                     radio_m: float = RADIO_PASADA_VUELTA_M,
                     tolerancia_grados: float = TOLERANCIA_OPUESTOS_GRADOS,
                     ventana_altitud_m: Optional[float] = None,
                     idioma: str = IDIOMA_POR_DEFECTO) -> Optional[SegmentEstimate]:
    """Busca la pasada por **la misma carretera en sentido contrario** y la estima.

    Es la pieza que hace fiable todo lo demás: el viento que a la ida infla el CdA, a la vuelta lo
    desinfla, y el error de altitud cambia de signo con la pendiente. Devuelve `None` si la
    actividad no vuelve a pasar por ahí en sentido opuesto.
    """
    p = validate_params(params)
    prep = _prepare(ride, p, ventana_altitud_m)
    lat_m = math.radians(segmento.lat_media)
    dx = np.radians(prep.lon - segmento.lon_media) * math.cos(lat_m)
    dy = np.radians(prep.lat - segmento.lat_media)
    dist = EARTH_R * np.hypot(dx, dy)

    s_ini, s_fin = segmento.km_inicio * 1000.0, segmento.km_fin * 1000.0
    largo = s_fin - s_ini
    cerca = np.where((dist <= radio_m) & ((prep.s_nodo < s_ini - largo / 2)
                                         | (prep.s_nodo > s_fin + largo / 2)))[0]
    mejor, mejor_dist = None, None
    for j in cerca:
        dif = abs((_rumbo_local(prep, int(j)) - segmento.rumbo_grados + 180.0) % 360.0 - 180.0)
        if abs(dif - 180.0) > tolerancia_grados:
            continue
        if mejor_dist is None or dist[j] < mejor_dist:
            mejor, mejor_dist = int(j), float(dist[j])
    if mejor is None:
        return None

    centro = float(prep.s_nodo[mejor])
    a = max(0.0, centro - largo / 2.0)
    b = min(float(prep.s_nodo[-1]), a + largo)
    try:
        return estimate_cda(ride, p, a / 1000.0, b / 1000.0, ventana_altitud_m=ventana_altitud_m,
                            idioma=idioma)
    except ValueError:
        return None


def find_paired_segments(ride: RideData, params: Params, *, maximo: int = 6,
                         max_razon_velocidad: Optional[float] = None,
                         rechazados: Optional[List[ParRechazado]] = None,
                         idioma: str = IDIOMA_POR_DEFECTO, **kwargs) -> List[OppositePair]:
    """Busca tramos llanos y, para cada uno, su pasada de vuelta por la misma carretera.

    Esto es lo que hay que mirar: un tramo suelto tiene el viento dentro, un par de ida y vuelta
    no. Devuelve los pares ordenados por discrepancia creciente.

    Criterio 28: descarta el par cuya relación de velocidades alcanza `max_razon_velocidad`, porque
    no puede ser la misma carretera llana en dos sentidos. Pasando una lista en `rechazados` se
    recupera cada descarte con su motivo, para poder enseñarlo en la interfaz.
    """
    p = validate_params(params)
    if max_razon_velocidad is None:            # el umbral lo fija el usuario (criterio 28)
        max_razon_velocidad = p.razon_velocidad_par
    segmentos = find_flat_segments(ride, p, idioma=idioma, **kwargs)
    pares: List[OppositePair] = []
    usados: List[Tuple[float, float]] = []
    for seg in segmentos:
        vuelta = find_return_pass(ride, p, seg, idioma=idioma)
        if vuelta is None:
            continue
        # Los **dos** extremos del par contra lo ya usado. Comprobar solo la vuelta dejaba la
        # puerta abierta a que una ida solapara con la vuelta de un par anterior: no ocurre en
        # ninguna de las cinco salidas de referencia, pero nada lo impedía.
        if any(tramo.km_inicio < f and i < tramo.km_fin
               for tramo in (seg, vuelta) for i, f in usados):
            continue
        rechazo = _par_imposible(seg, vuelta, max_razon_velocidad, idioma)
        if rechazo is not None:
            if rechazados is not None:
                rechazados.append(rechazo)
            continue                                   # ni se marca como usado: no es un par
        usados.append((seg.km_inicio, seg.km_fin))
        usados.append((vuelta.km_inicio, vuelta.km_fin))
        pares.append(OppositePair(ida=seg, vuelta=vuelta, cda=(seg.cda + vuelta.cda) / 2.0,
                                  discrepancia=abs(seg.cda - vuelta.cda) / 2.0,
                                  separacion_m=separacion_m(seg, vuelta)))
        if len(pares) >= maximo:
            break
    pares.sort(key=lambda par: par.discrepancia)
    return pares


def combine_pairs(pares: Sequence[OppositePair]) -> Tuple[float, float]:
    """Combina pares de ida y vuelta: media **sin ponderar** y dispersión entre pares.

    Lanza `ValueError` con la lista vacía.

    **Por qué sin ponderar.** La tentación es dar más peso a los pares con menos discrepancia, por
    ser los de menos viento. La teoría dice que la media de ida y vuelta queda sesgada alto en
    segundo orden, en un factor (1 + (w/v)²), así que los pares con más viento deberían salir algo
    más altos. Se midió con las dos actividades reales: corregir ese factor mueve la media de 0,268
    a 0,264 y la dispersión entre pares de 0,018 a 0,015, es decir **casi nada**. La dispersión que
    queda no la explica el viento, y no sabemos qué la explica (firme distinto, viento cruzado,
    cambios de posición, tráfico). Ponderar por la discrepancia bajaría el resultado a 0,244,
    que es leer en los datos más de lo que hay. Así que se promedia a secas y se da la dispersión
    como incertidumbre, que es la cifra honesta.

    **Dispersión, no error estándar de la media** (corregido tras la revisión del 6-oct-2026). El
    código dividía la desviación típica por √n, que responde a «¿con cuánta precisión conozco la
    media?» suponiendo que los pares son medidas independientes del mismo número. No lo son: cada
    par arrastra su propio viento residual, su firme y su postura, y esa discrepancia entre pares
    es variabilidad real, no ruido de muestreo. Dividir por √n reclamaba una precisión que el
    método no tiene, y se notaba: en la salida del 30-mar la banda salía ±0,0055 cuando la
    distancia al método independiente —la calibración por tiempo total— es de 0,0090. **Una banda
    que no cubre su propio contraste no vale.** Con la dispersión (±0,0155) sí lo cubre, y lo
    vigila `test_c25_la_banda_cubre_la_distancia_al_metodo_independiente`.

    Nota: `combine_estimates`, que combina segmentos sueltos elegidos a mano, conserva el √n porque
    ahí sí es una combinación por inverso de la varianza de medidas de un mismo tramo. Si alguna vez
    se usa para promediar tramos distintos, habrá que revisarlo con el mismo argumento.

    Contraste con un método independiente: la media de los pares da 0,267 y 0,268 en dos de las
    actividades coherentes, frente a 0,276 y 0,262 de la calibración por tiempo total.
    """
    if not pares:
        raise ValueError("No hay pares de ida y vuelta que combinar.")
    cdas = np.array([par.cda for par in pares], dtype=float)
    media = float(np.mean(cdas))
    formal = float(np.mean([max(par.ida.cda_incertidumbre, par.vuelta.cda_incertidumbre)
                            for par in pares]) / math.sqrt(len(pares)))
    dispersion = float(np.std(cdas, ddof=1)) if len(cdas) > 1 else 0.0
    return media, max(formal, dispersion)


@dataclass
class SearchSummary:
    """Resumen honesto de una búsqueda automática, con el sesgo de selección a la vista."""
    n_tramos: int
    velocidad_ruta_kmh: float
    velocidad_tramos_kmh: float
    pendiente_tramos_pct: float
    cda_combinado: float
    cda_combinado_incertidumbre: float
    cda_ruta_completa: float
    cda_ruta_completa_incertidumbre: float
    sesgo_velocidad_kmh: float

    @property
    def hay_sesgo(self) -> bool:
        """Los tramos elegidos son bastante más rápidos que la ruta: el CdA saldrá bajo."""
        return self.sesgo_velocidad_kmh > 2.0


def search_summary(ride: RideData, params: Params, segmentos: Sequence[SegmentEstimate],
                   idioma: str = IDIOMA_POR_DEFECTO) -> SearchSummary:
    """Compara los tramos encontrados con la ruta completa, para enseñar el sesgo de selección.

    La búsqueda exige velocidad alta y poco desnivel, y eso **no es una muestra neutra**: tiende a
    quedarse con los tramos rápidos, que son justamente los de viento a favor o con una bajada
    suave. Medido en una actividad real, los tramos elegidos iban a 36,3 km/h frente a los
    31,4 km/h de la ruta, con una pendiente media de −0,16 %. Por eso conviene comparar siempre su
    CdA con el de la ruta completa, que no sufre esa selección.
    """
    p = validate_params(params)
    prep = _prepare(ride, p)
    v_ruta = float(np.mean(prep.v_mid[prep.valido]) * 3.6) if prep.valido.any() else 0.0
    completa = estimate_cda(ride, p, 0.0, float(prep.s_nodo[-1] / 1000.0),
                            idioma=idioma)
    if segmentos:
        v_tramos = float(np.mean([e.velocidad_media_kmh for e in segmentos]))
        pend = float(np.mean([e.pendiente_media_pct for e in segmentos]))
        cda_c, inc_c = combine_estimates(segmentos)
    else:
        v_tramos, pend, cda_c, inc_c = 0.0, 0.0, float("nan"), float("nan")
    return SearchSummary(
        n_tramos=len(segmentos), velocidad_ruta_kmh=v_ruta, velocidad_tramos_kmh=v_tramos,
        pendiente_tramos_pct=pend, cda_combinado=cda_c, cda_combinado_incertidumbre=inc_c,
        cda_ruta_completa=completa.cda,
        cda_ruta_completa_incertidumbre=completa.cda_incertidumbre,
        sesgo_velocidad_kmh=v_tramos - v_ruta if segmentos else 0.0)


def combine_estimates(estimaciones: Sequence[SegmentEstimate]) -> Tuple[float, float]:
    """Combina varias estimaciones ponderando por el inverso del cuadrado de su incertidumbre.

    Sirve sobre todo para promediar un tramo de ida con el de vuelta y cancelar el viento.
    Devuelve (CdA combinado, incertidumbre). Lanza `ValueError` si la lista está vacía.
    """
    if not estimaciones:
        raise ValueError("No hay estimaciones que combinar.")
    cdas = np.array([e.cda for e in estimaciones], dtype=float)
    incs = np.array([max(e.cda_incertidumbre, 1e-6) for e in estimaciones], dtype=float)
    pesos = 1.0 / incs ** 2
    media = float(np.sum(cdas * pesos) / np.sum(pesos))
    inc_formal = float(np.sqrt(1.0 / np.sum(pesos)))
    # si las estimaciones no concuerdan entre sí, manda la dispersión, no la incertidumbre formal
    dispersion = float(np.std(cdas, ddof=1) / np.sqrt(len(cdas))) if len(cdas) > 1 else 0.0
    return media, max(inc_formal, dispersion)
