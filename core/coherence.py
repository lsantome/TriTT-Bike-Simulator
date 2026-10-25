"""Examen de coherencia de una actividad real (criterio 30).

**El problema que resuelve.** La calibración por tiempo total siempre devuelve un número: busca el
CdA que iguala el tiempo predicho al real y lo encuentra. Lo que no dice es si ese número significa
algo. Si un día el ciclista fue más rápido de lo que permite la potencia que registró —viento neto
a favor, rebufo, grupo— la bisección baja el CdA hasta cuadrar el total, y el resultado no es un
dato aerodinámico sino el residuo de un ajuste que no cierra.

**Cómo se detecta.** Ese ajuste imposible deja una firma que se ve al separar el error por banda de
pendiente: el modelo sale **demasiado lento en el llano** (donde manda la aerodinámica, y el CdA
rebajado no basta para alcanzar la velocidad real) y **demasiado rápido en las bajadas** (donde con
poca potencia el CdA rebajado deja correr la bici más de lo que corrió). Las dos cosas a la vez, y
con signos opuestos, no las produce un error de CdA: las produce una salida que el modelo no puede
explicar.

**Umbrales medidos** (validación de 5-oct-2026, cinco salidas del recorrido 2):

| salida | CdA calibrado | error en llano | error en bajadas |
|---|---|---|---|
| 30-mar-2025 | 0,276 | −2,5 % | −0,2 % |
| 06-abr-2025 | 0,262 | −0,8 % | −0,7 % |
| 19-abr-2026 | 0,259 | −0,7 % | +0,8 % |
| 04-may-2025 | **0,150** | **+29,6 %** | **−18,4 %** |
| 08-jun-2025 | 0,216 | **+15,8 %** | **−7,9 %** |

Las tres coherentes no pasan de −0,7 % en llano ni de +0,8 % en bajadas; las dos incoherentes están
un orden de magnitud por encima. Los umbrales (+5 % y −4 %) caen en medio con holgura por los dos
lados. El rango plausible de CdA (0,20-0,35) es el que ya usaba el test del criterio 13.

**Configuración fija, a propósito.** El examen usa del usuario solo los parámetros que de verdad
describen la bici y el aire (`PARAMS_ESTIMADOR`); todo lo demás —el ΔCdA de posición, los límites
de velocidad y curvatura, el remuestreo— lo toma de sus valores por defecto. Dos razones:

1. El veredicto no debe cambiar porque alguien haya tocado el límite de curvatura para predecir
   una carrera. Es un diagnóstico sobre la actividad, no sobre la configuración de ese momento.
2. En el módulo del estimador esos parámetros **no se piden** (criterio 31), así que dejar que
   influyeran sería gobernar en silencio un número que la herramienta enseña. Lo detectó la
   revisión del 6-oct-2026: ocho de ellos movían el CdA mostrado, `umbral_posicion` hasta un 10 %.

**Lo que este examen no hace.** No dice *cuál* de las causas fue (viento, rebufo, grupo, firme
mojado): para eso harían falta datos que el FIT no trae. Tampoco rechaza la actividad por su
cuenta; avisa y deja la decisión al usuario.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from .i18n import IDIOMA_POR_DEFECTO, t
from .params import PARAMS_ESTIMADOR, Params
from .route import build_profile
from .simulate import simulate
from .validation import (MOVING_SPEED, RideData, _align, calibrate_cda, power_by_segment,
                         ride_to_track)

#: Rango de CdA que puede salir de una bici de carretera o triatlón con una persona encima (m²).
CDA_PLAUSIBLE: Tuple[float, float] = (0.20, 0.35)

#: Pendiente, en %, que separa el llano de las subidas y bajadas en este examen.
UMBRAL_LLANO_PCT = 1.0

#: El modelo tarda esto de más en el llano: no alcanza la velocidad real ni con el CdA rebajado.
UMBRAL_ERROR_LLANO_PCT = 5.0
#: Y esto de menos en las bajadas: deja correr la bici más de lo que corrió.
UMBRAL_ERROR_BAJADA_PCT = -4.0


def params_del_examen(params: Params) -> Params:
    """Los parámetros del usuario que el examen usa, con los demás en su valor por defecto.

    Ver «Configuración fija» en el encabezado del módulo: el veredicto no puede depender de
    ajustes de simulación que el módulo del estimador ni siquiera muestra.
    """
    return Params(**{k: getattr(params, k) for k in PARAMS_ESTIMADOR})


@dataclass
class CoherenceReport:
    """Diagnóstico de coherencia de una actividad, con los números que lo respaldan."""
    nombre: str
    cda_calibrado: float
    error_llano_pct: float
    error_bajada_pct: float
    error_subida_pct: float
    km_llano: float
    km_bajada: float
    km_subida: float
    cda_fuera_de_rango: bool
    patron_incoherente: bool
    avisos: List[str] = field(default_factory=list)

    @property
    def coherente(self) -> bool:
        return not (self.cda_fuera_de_rango or self.patron_incoherente)

    @property
    def sirve_para_calibrar(self) -> bool:
        """Alias explícito: lo que de verdad se decide con este informe."""
        return self.coherente

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["coherente"] = self.coherente
        return d


def _errores_por_banda(ride: RideData, params: Params):
    """Error de tiempo (%) y km en llano, bajada y subida, con el CdA que traigan los params.

    El tiempo real por tramo sale de la curva tiempo-en-movimiento frente a distancia construida
    con los registros del FIT, no de interpolar velocidades: así el error no mezcla el artefacto
    de la interpolación con el del modelo.
    """
    t_reg, s, _power, speed = _align(ride)
    movimiento = speed >= MOVING_SPEED
    if not movimiento.any():
        raise ValueError("La actividad no tiene ningún registro en movimiento.")
    dts = np.clip(np.diff(t_reg, prepend=t_reg[0]), 0.0, 30.0)
    t_movimiento = np.cumsum(np.where(movimiento, dts, 0.0))

    p = params.con(velocidad_inicial=float(np.clip(speed[movimiento][0] * 3.6, 5.0, 60.0)))
    profile = build_profile(ride_to_track(ride), p)
    res = simulate(profile, p, power_override=power_by_segment(ride, profile))

    dt_real = np.diff(np.interp(profile.s, s, t_movimiento))
    pendiente_pct = profile.grade * 100.0
    con_movimiento = dt_real > 0.05

    def banda(mascara):
        m = mascara & con_movimiento
        if not m.any() or dt_real[m].sum() <= 0.0:
            return float("nan"), 0.0
        error = (res.dt[m].sum() - dt_real[m].sum()) / dt_real[m].sum() * 100.0
        return float(error), float(profile.ds[m].sum() / 1000.0)

    llano = banda(np.abs(pendiente_pct) <= UMBRAL_LLANO_PCT)
    bajada = banda(pendiente_pct < -UMBRAL_LLANO_PCT)
    subida = banda(pendiente_pct > UMBRAL_LLANO_PCT)
    return llano, bajada, subida


def check_coherence(ride: RideData, params: Params, *, cda: Optional[float] = None,
                    idioma: str = IDIOMA_POR_DEFECTO) -> CoherenceReport:
    """Examina una actividad y avisa si no sirve para calibrar.

    `cda` permite pasar un CdA ya calibrado y ahorrarse la bisección; si no se da, se calibra con
    esta actividad sola, que es el caso que interesa examinar.

    De `params` solo se usan los de `PARAMS_ESTIMADOR`; el resto van a su valor por defecto.
    """
    p = params_del_examen(params)
    cda_cal = float(calibrate_cda([ride], p) if cda is None else cda)
    (e_llano, km_llano), (e_bajada, km_bajada), (e_subida, km_subida) = _errores_por_banda(
        ride, p.con(cda=cda_cal))

    bajo, alto = CDA_PLAUSIBLE
    fuera = not (bajo < cda_cal < alto)
    # `nan` en una banda (ruta sin llano, por ejemplo) no debe disparar el aviso ni silenciarlo:
    # la comparación con nan es falsa, así que el patrón simplemente no se detecta.
    patron = bool(e_llano >= UMBRAL_ERROR_LLANO_PCT and e_bajada <= UMBRAL_ERROR_BAJADA_PCT)

    avisos: List[str] = []
    if fuera:
        avisos.append(t("coh_cda_fuera", idioma, cda=cda_cal, bajo=bajo, alto=alto))
    if patron:
        avisos.append(t("coh_patron", idioma, llano=e_llano, bajada=e_bajada))
    if avisos:
        avisos.append(t("coh_no_calibrar", idioma))
    else:
        avisos.append(t("coh_ok", idioma, cda=cda_cal))

    return CoherenceReport(
        nombre=ride.name, cda_calibrado=cda_cal,
        error_llano_pct=e_llano, error_bajada_pct=e_bajada, error_subida_pct=e_subida,
        km_llano=km_llano, km_bajada=km_bajada, km_subida=km_subida,
        cda_fuera_de_rango=fuera, patron_incoherente=patron, avisos=avisos)
