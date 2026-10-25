"""Densidad del aire a partir de temperatura, humedad, presión y altitud."""
from __future__ import annotations

import numpy as np

R_DRY = 287.058    # J/(kg·K)
R_VAPOR = 461.495  # J/(kg·K)


def pressure_at_altitude(p0_hpa: float, altitude_m) -> np.ndarray:
    """Presión (hPa) a una altitud según la atmósfera estándar (ISA, troposfera)."""
    h = np.clip(np.asarray(altitude_m, dtype=float), -500.0, 11000.0)
    return p0_hpa * (1.0 - 2.25577e-5 * h) ** 5.25588


def saturation_vapor_pressure_hpa(temp_c: float) -> float:
    """Presión de vapor de saturación (Magnus), hPa."""
    return 6.1078 * 10.0 ** (7.5 * temp_c / (temp_c + 237.3))


def air_density(temp_c: float, rh_pct: float, p0_hpa: float, altitude_m) -> np.ndarray:
    """Densidad del aire húmedo (kg/m³) en cada altitud.

    La temperatura se toma constante en toda la ruta (es la que introduce el usuario);
    la presión sí varía con la altitud (ISA).
    """
    t_k = temp_c + 273.15
    p_hpa = pressure_at_altitude(p0_hpa, altitude_m)
    pv = np.clip(rh_pct / 100.0, 0.0, 1.0) * saturation_vapor_pressure_hpa(temp_c)
    pv = np.minimum(pv, p_hpa)
    pd = p_hpa - pv
    return (pd * 100.0) / (R_DRY * t_k) + (pv * 100.0) / (R_VAPOR * t_k)


#: Límites de presión de neumáticos admitidos (bar).
PRESION_MIN, PRESION_MAX = 2.0, 12.0


def pressure_factor(presion_bar: float, presion_ref_bar: float, exponente: float) -> float:
    """Factor multiplicativo sobre el Crr por la presión de neumáticos: `(p_ref/p)^exp`.

    Más presión baja el Crr en el ensayo de rodillo, y el exponente mide cuánto. Es un modelo
    **grosero**: los exponentes por superficie son estimaciones (0,45 liso / 0,33 normal /
    0,15 rugoso), editables, sin respaldo experimental propio.

    **Limitación conocida que esta fórmula no representa:** en firme real, por encima de cierta
    presión la rueda deja de absorber las irregularidades y el conjunto se vuelve más lento
    (pérdidas por impedancia). Una potencia monótona decreciente no puede reproducir ese óptimo,
    así que el exponente del firme rugoso se deja bajo a propósito. Si subes mucho la presión en
    rugoso, el modelo te dará un resultado optimista.
    """
    p = float(presion_bar)
    if not (PRESION_MIN <= p <= PRESION_MAX):
        raise ValueError(f"Presión de neumáticos fuera de rango: {p} bar")
    ref = float(presion_ref_bar)
    if ref <= 0:
        raise ValueError("La presión de referencia debe ser positiva.")
    return float((ref / p) ** float(exponente))
