"""Incertidumbre medida de la predicción de tiempo (criterio 29).

Las cifras vienen de la validación con las actividades reales del usuario y **no son teóricas**.
Cada banda declara su origen y si está verificada, para que la interfaz no pueda presentar una
predicción sin su margen.

Las dos bandas **miden cosas distintas** y por eso se dan las dos, no la media ni la mejor:

- **Banda del modelo, ±1,5 %.** Precisión con la misma bici y la misma ruta, en condiciones
  parecidas a las de la calibración. Medida por validación cruzada dejando una salida fuera con
  las **tres salidas coherentes** del recorrido 2 (30-mar-2025, 06-abr-2025 y 19-abr-2026): error
  medio 0,97 %, máximo 1,43 % (−1,42 %, +0,40 %, +1,08 %) sobre los datos completos, y 1,46 %
  sobre los fixtures reducidos. Es lo que vale el modelo físico cuando nada del día se sale de lo
  normal.
- **Banda del día, ±15 %.** La anterior más el viento y las condiciones que el modelo no conoce.
  Medida **con el protocolo que la herramienta recomienda**: calibrar solo con las salidas
  coherentes (criterio 30) y predecir cualquier día, incluidos los incoherentes. Peor error
  observado: **14,09 %** sobre los datos completos (14,05 % sobre los fixtures), en la salida del
  04-may-2025. La banda cubre ese peor caso en vez de redondearlo a la baja.

**Remedido el 13-oct-2026**, tras corregir el límite por curvatura (criterio 3): el estimador de
curvatura pasó a medirla por circunradio y a propagarla a los extremos de cada curva, lo que frena
algo más en las curvas y alarga las predicciones un 0,4-0,5 %. El peor error del modelo subió de
1,39 % a 1,43 % y la banda de ±1,4 % se quedaba corta por 0,06 puntos. Las cifras anteriores eran
correctas para el código anterior; lo que no sería correcto es dejarlas escritas.

  **Corregido tras la revisión del 6-oct-2026.** El ±14 % anterior se midió con validación cruzada
  dejando una fuera **sobre las cinco**, lo que mete las dos incoherentes *dentro* del conjunto de
  calibración y da un peor error de 12,8 %. Eso mide un flujo que el propio protocolo prohíbe: si
  se calibra como manda el criterio 30, el error llega a 14,27 % y el ±14 % se quedaba corto. Una
  banda tiene que medir el camino que la herramienta recomienda, no el más benévolo.

**Ruta nueva: no hay banda verificada.** La del día es un *suelo*, no una estimación. Ninguna
validación ha podido cruzar de ruta (criterio 14: no hay salidas de esta bici por otro recorrido),
así que la herramienta no puede ofrecer ningún número como precisión esperable en una ruta nueva.

Historial: el ±1,3 % anterior se obtuvo con solo 2 salidas y sigue siendo correcto para lo que
mide, pero se presentaba como la precisión de la herramienta sin más. El ±11 % de «ruta nueva»
queda **retirado por incoherente**: era menor que el margen por viento ya medido en la propia ruta
de calibración.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

#: Precisión del modelo físico: misma bici, misma ruta, condiciones como las de la calibración.
MODELO_PCT = 1.5
#: La anterior más el viento y las condiciones desconocidas del día.
DIA_PCT = 15.0

#: Peores errores observados **con el protocolo recomendado**, que las bandas tienen que cubrir.
#: Los vigilan los tests, que los vuelven a medir sobre los fixtures en vez de creérselos.
PEOR_ERROR_MODELO_PCT = 1.43
PEOR_ERROR_DIA_PCT = 14.09

#: Compatibilidad: el nombre antiguo de la banda estrecha. La ancha ya no es «ruta nueva».
MISMA_RUTA_PCT = MODELO_PCT

#: Procedencia de cada banda, en los dos idiomas: la interfaz las muestra tal cual debajo del
#: tiempo predicho, así que tienen que estar traducidas como el resto de los textos. Hasta octubre
#: de 2026 eran cadenas fijas en castellano y se concatenaban en crudo, de modo que con la interfaz
#: en inglés salían dos párrafos enteros en español.
ORIGEN_MODELO_I18N = {
    "es": ("medido: validación cruzada dejando una fuera con las 3 salidas coherentes del "
           "recorrido 2 (30-mar-2025, 06-abr-2025 y 19-abr-2026); error medio 0,97 %, "
           "máximo 1,43 %. Vale con la misma bici y ruta y condiciones parecidas"),
    "en": ("measured: leave-one-out cross-validation over the 3 coherent rides of route 2 "
           "(30-Mar-2025, 06-Apr-2025 and 19-Apr-2026); mean error 0.97 %, worst 1.43 %. Holds "
           "with the same bike and route and similar conditions"),
}
ORIGEN_DIA_I18N = {
    "es": ("medido con el protocolo recomendado: calibrando solo con las 3 salidas coherentes y "
           "prediciendo cualquier día, incluidos los 2 incoherentes por viento o rebufo; peor "
           "error 14,09 %. Es el margen cuando no se sabe qué viento hizo"),
    "en": ("measured with the recommended protocol: calibrating only on the 3 coherent rides and "
           "predicting any day, including the 2 flagged as incoherent for wind or drafting; worst "
           "error 14.09 %. This is the margin when the day's wind is unknown"),
}
#: Lo que la herramienta puede decir de una ruta que no se usó para calibrar: nada medido.
AVISO_RUTA_NUEVA_I18N = {
    "es": ("sin verificar: no hay ninguna salida de esta bici por otra ruta, así que no existe una "
           "banda medida para una ruta nueva. La banda del día es un suelo, no una estimación: en "
           "una ruta nueva el error puede ser mayor"),
    "en": ("unverified: there is no ride of this bike on another route, so no measured band exists "
           "for a new route. The day band is a floor, not an estimate: on a new route the error "
           "can be larger"),
}

#: Compatibilidad con el código y los tests que leen la versión castellana directamente.
ORIGEN_MODELO = ORIGEN_MODELO_I18N["es"]
ORIGEN_DIA = ORIGEN_DIA_I18N["es"]
AVISO_RUTA_NUEVA = AVISO_RUTA_NUEVA_I18N["es"]


@dataclass(frozen=True)
class Band:
    """Banda de incertidumbre de un tiempo predicho."""
    pct: float
    verificada: bool
    origen: str
    tiempo_s: float
    #: Clave estable para la interfaz y las cabeceras; no se traduce en los CSV.
    clave: str = "modelo"

    @property
    def low_s(self) -> float:
        return self.tiempo_s * (1.0 - self.pct / 100.0)

    @property
    def high_s(self) -> float:
        return self.tiempo_s * (1.0 + self.pct / 100.0)

    @property
    def margen_s(self) -> float:
        return self.tiempo_s * self.pct / 100.0


def _idioma(idioma: str) -> str:
    return "en" if str(idioma).strip().lower().startswith("en") else "es"


def band_modelo(tiempo_s: float, idioma: str = "es") -> Band:
    """Precisión del modelo: misma bici y ruta, condiciones parecidas a las de la calibración."""
    return Band(MODELO_PCT, True, ORIGEN_MODELO_I18N[_idioma(idioma)], float(tiempo_s), "modelo")


def band_dia(tiempo_s: float, idioma: str = "es") -> Band:
    """La del modelo más el viento y las condiciones desconocidas del día."""
    return Band(DIA_PCT, True, ORIGEN_DIA_I18N[_idioma(idioma)], float(tiempo_s), "dia")


def aviso_ruta_nueva(idioma: str = "es") -> str:
    """Lo único que se puede decir de una ruta nueva, en el idioma de la interfaz."""
    return AVISO_RUTA_NUEVA_I18N[_idioma(idioma)]


def bands(tiempo_s: float, idioma: str = "es") -> Tuple[Band, Band]:
    """Las dos bandas, de la más estrecha a la más ancha."""
    return band_modelo(tiempo_s, idioma), band_dia(tiempo_s, idioma)


#: Compatibilidad con el nombre anterior de la banda estrecha.
band_misma_ruta = band_modelo


#: Sufijos de las columnas que acompañan a un tiempo en una tabla o CSV.
SUFIJOS = ("_min_modelo", "_max_modelo", "_min_dia", "_max_dia")


def with_bands(df, columna: str):
    """Añade a un DataFrame las dos bandas de la columna de tiempo indicada.

    Devuelve una copia con cuatro columnas nuevas, para que ningún tiempo salga de la app
    (tabla en pantalla o CSV descargado) sin su margen. Las columnas se insertan justo
    detrás de la de origen.
    """
    if columna not in df.columns:
        raise KeyError(columna)
    out = df.copy()
    base = out[columna].astype(float)
    lo, hi = MODELO_PCT / 100.0, DIA_PCT / 100.0
    pos = list(out.columns).index(columna) + 1
    for i, (nombre, factor) in enumerate((
            (columna + SUFIJOS[0], 1.0 - lo), (columna + SUFIJOS[1], 1.0 + lo),
            (columna + SUFIJOS[2], 1.0 - hi), (columna + SUFIJOS[3], 1.0 + hi))):
        out.insert(pos + i, nombre, base * factor)
    return out
