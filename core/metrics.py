"""Métricas de potencia: potencia media, NP, VI e IF a partir de tramos con duración."""
from __future__ import annotations

from typing import Optional

import numpy as np


def average_power(dt: np.ndarray, power: np.ndarray) -> float:
    total = float(np.sum(dt))
    return float(np.sum(power * dt) / total) if total > 0 else 0.0


def normalized_power(dt: np.ndarray, power: np.ndarray) -> float:
    """Potencia normalizada (media móvil de 30 s a 1 Hz, media 4.ª potencia).

    Si la actividad dura menos de 30 s devuelve la potencia media.
    """
    dt = np.asarray(dt, dtype=float)
    power = np.asarray(power, dtype=float)
    total = float(np.sum(dt))
    if total < 30.0:
        return average_power(dt, power)
    ends = np.cumsum(dt)
    grid = np.arange(0.5, total, 1.0)
    idx = np.minimum(np.searchsorted(ends, grid, side="right"), len(power) - 1)
    p1 = power[idx]
    csum = np.concatenate([[0.0], np.cumsum(p1)])
    roll = (csum[30:] - csum[:-30]) / 30.0
    return float(np.mean(roll ** 4) ** 0.25)


def variability_index(np_w: float, avg_w: float) -> Optional[float]:
    return float(np_w / avg_w) if avg_w > 0 else None


def intensity_factor(np_w: float, ftp: Optional[float]) -> Optional[float]:
    return float(np_w / ftp) if ftp else None
