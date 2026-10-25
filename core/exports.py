"""Tablas que la app muestra y descarga, con sus bandas de incertidumbre ya incorporadas.

La app no construye estas tablas por su cuenta: las pide aquí. Así lo que se ve en pantalla y
lo que se descarga en CSV son el mismo objeto, y el criterio 16 ("ningún tiempo sin su margen")
se puede verificar sin pasar por la interfaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .simulate import table_by_km
from .uncertainty import with_bands

#: Columnas de tiempo de cada tabla a las que hay que añadir banda.
COLUMNAS_TIEMPO_BLOQUES = ("tiempo_s",)
COLUMNAS_TIEMPO_TRAMOS = ("duracion_s", "tiempo_acum_s")


def _si_no(valor: bool, idioma: str = "es", *, enfatico: bool = False) -> str:
    """Celda de sí/no, traducida (criterio 27).

    Las celdas de `utilizable` y `coherente` salían siempre en castellano, y el test de
    traducción exigía precisamente el castellano, así que ningún test podía fallar por ello.
    `enfatico` pone el «no» en mayúsculas, que es el aviso de que ese dato no sirve.
    """
    from .i18n import t

    if valor:
        return t("celda_si", idioma)
    return t("celda_no_enfatico" if enfatico else "celda_no", idioma)


def tabla_bloques(result, km_block: float):
    """Tabla por bloques de km, con la banda del tiempo de cada bloque."""
    df = table_by_km(result, km_block)
    for col in COLUMNAS_TIEMPO_BLOQUES:
        df = with_bands(df, col)
    return df


def tabla_tramos(result):
    """Detalle por tramo, con la banda de la duración y del tiempo acumulado."""
    df = result.to_frame()
    for col in COLUMNAS_TIEMPO_TRAMOS:
        df = with_bands(df, col)
    return df


#: Columna de tiempo del informe de validación con FIT.
COLUMNAS_TIEMPO_VALIDACION = ("tiempo_predicho_s",)


def tabla_validacion(reports):
    """Informe de validación con FIT (lista de `ValidationReport` o de dicts), con banda en el
    tiempo predicho y la marca del criterio de ≤ 3 %."""
    filas = [r if isinstance(r, dict) else r.as_dict() for r in reports]
    df = pd.DataFrame(filas)
    if df.empty:
        return df
    for col in COLUMNAS_TIEMPO_VALIDACION:
        df = with_bands(df, col)
    df["criterio_<=3%"] = np.where(df["error_tiempo_pct"].abs() <= 3.0, "cumple", "NO cumple")
    return df


#: Columnas de la tabla de segmentos del estimador de CdA, en el orden en que se muestran.
#: Las "básicas" son las que se ven de entrada; el resto está en el CSV y tras marcar «ver todas».
COLUMNAS_SEGMENTOS_BASICAS = (
    "tramo_km", "largo_km", "cda", "±", "cda_min", "cda_max", "desnivel_m", "pendiente_%",
    "v_media_kmh", "potencia_media_w", "aero_%", "rumbo", "utilizable",
)
COLUMNAS_SEGMENTOS_DETALLE = (
    "duracion_s", "sin_pedalear_%", "viento_1ms_±", "err_altitud", "err_crr", "err_potencia",
    "densidad_aire", "actividad",
)


def tabla_segmentos(estimaciones, *, detalle: bool = False, idioma: str = "es"):
    """Tabla de los segmentos estimados, uno por fila.

    El orden de las columnas va de lo que se pregunta a lo que se necesita para juzgarlo: primero
    dónde está el tramo y cuánto CdA ha dado con su margen, luego lo que explica ese número
    (desnivel, pendiente, velocidad, potencia), y después la parte aerodinámica de la energía y el
    rumbo, que es lo que delata el viento. `aero_%` y `utilizable` son las dos columnas que dicen
    si la fila se puede creer; `viento_1ms_±` recuerda cuánto movería el resultado un viento de
    1 m/s, que es el sesgo que no entra en `±`.

    Con `detalle=True` añade la duración, la fracción sin pedalear, el desglose de la
    incertidumbre por fuente y la densidad del aire.
    """
    filas = []
    for e in estimaciones:
        d = e if isinstance(e, dict) else e.as_dict()
        filas.append({
            "tramo_km": f"{d['km_inicio']:.1f}–{d['km_fin']:.1f}",
            "largo_km": d["distancia_m"] / 1000.0,
            "cda": d["cda"],
            "±": d["cda_incertidumbre"],
            "cda_min": d["cda_min"],
            "cda_max": d["cda_max"],
            "desnivel_m": d["desnivel_m"],
            "pendiente_%": d["pendiente_media_pct"],
            "v_media_kmh": d["velocidad_media_kmh"],
            "potencia_media_w": d["potencia_media_w"],
            "aero_%": d["fraccion_aero"] * 100.0,
            "rumbo": d["rumbo_grados"],
            "utilizable": _si_no(d["utilizable"], idioma, enfatico=True),
            "duracion_s": d["duracion_s"],
            "sin_pedalear_%": d["fraccion_sin_pedalear"] * 100.0,
            "viento_1ms_±": d["sens_viento"],
            "err_altitud": d["sens_altitud"],
            "err_crr": d["sens_crr"],
            "err_potencia": d["sens_potencia"],
            "densidad_aire": d["densidad_aire"],
            "actividad": d["nombre"],
        })
    columnas = list(COLUMNAS_SEGMENTOS_BASICAS)
    if detalle:
        columnas += list(COLUMNAS_SEGMENTOS_DETALLE)
    return pd.DataFrame(filas, columns=columnas)


#: Columnas del examen de coherencia (criterio 30), una fila por actividad.
COLUMNAS_COHERENCIA = (
    "actividad", "cda_calibrado", "coherente", "err_llano_%", "err_bajada_%", "err_subida_%",
    "km_llano", "km_bajada", "km_subida", "cda_fuera_de_rango", "patron_incoherente", "motivo",
)


def tabla_coherencia(informes, idioma: str = "es"):
    """Examen de coherencia de varias actividades, una por fila (criterio 30).

    El orden va del veredicto a la prueba: qué actividad es, qué CdA sale de ella, si sirve, y
    después los tres errores por banda que lo justifican. `motivo` reúne los avisos del núcleo, de
    modo que la tabla se entiende sin volver al informe.
    """
    filas = []
    for r in informes:
        d = r if isinstance(r, dict) else r.as_dict()
        filas.append({
            "actividad": d["nombre"],
            "cda_calibrado": d["cda_calibrado"],
            "coherente": _si_no(d["coherente"], idioma, enfatico=True),
            "err_llano_%": d["error_llano_pct"],
            "err_bajada_%": d["error_bajada_pct"],
            "err_subida_%": d["error_subida_pct"],
            "km_llano": d["km_llano"],
            "km_bajada": d["km_bajada"],
            "km_subida": d["km_subida"],
            "cda_fuera_de_rango": _si_no(d["cda_fuera_de_rango"], idioma),
            "patron_incoherente": _si_no(d["patron_incoherente"], idioma),
            "motivo": " ".join(d["avisos"]),
        })
    return pd.DataFrame(filas, columns=list(COLUMNAS_COHERENCIA))


def csv_bytes(df) -> bytes:
    return df.to_csv(index=False).encode()
