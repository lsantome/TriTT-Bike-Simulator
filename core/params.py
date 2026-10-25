"""Parámetros del simulador: valores por defecto, rangos, categorías y validación.

Los valores por defecto son genéricos y realistas (nivel del mar, A Coruña).
`PARAM_SPECS` es la única fuente de verdad: la UI y la validación se generan de ahí.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Optional, Tuple

from .atmosphere import pressure_factor
from .wheels import (DEFAULT_ETRTO, ETRTO_MANUAL, circumference_mm, etrto_codes,
                     parse_etrto)

CATEGORIES = ("Ciclista", "Equipamiento", "Variables externas")
SURFACES = ("liso", "normal", "rugoso")
# Parámetros que el usuario debe introducir expresamente en la app (sin valor por defecto en la UI).
# La dataclass conserva un valor por defecto solo para uso programático/tests.
REQUIRED_PARAMS = ("masa_total",)


class ParamError(ValueError):
    """Parámetro fuera de rango o inconsistente."""


@dataclass(frozen=True)
class Params:
    # --- Ciclista -----------------------------------------------------------
    masa_total: float = 85.0             # kg (ciclista + bici + equipo); el modelo solo usa la suma
    p_subida: float = 220.0              # W
    p_llano: float = 200.0               # W
    p_descenso: float = 0.0              # W
    ftp: Optional[float] = None          # W (solo para IF)
    umbral_pendiente: float = 2.0        # % (± umbral subida/descenso)
    anchura_banda_pendiente: float = 1.0  # % (anchura de la transición suave)
    velocidad_inicial: float = 18.0      # km/h
    # --- Equipamiento -------------------------------------------------------
    cda: float = 0.27                    # m² (posición aero)
    delta_cda: float = 0.25              # m² añadidos a baja velocidad
    umbral_posicion: float = 20.0        # km/h
    anchura_transicion_cda: float = 1.0  # km/h (escala logística)
    eficiencia: float = 0.975            # transmisión
    inercia_ruedas: float = 0.14         # kg·m² (par de ruedas)
    etrto: str = DEFAULT_ETRTO           # medida de rueda (ancho-llanta, mm) o "manual"
    perimetro_mm: Optional[float] = None  # mm medidos; obligatorio si etrto == "manual"
    # --- Meteorología -------------------------------------------------------
    temperatura: float = 15.0            # °C
    humedad: float = 75.0                # %
    presion_nivel_mar: float = 1013.25   # hPa
    densidad_manual: Optional[float] = None  # kg/m³ (anula el cálculo)
    # --- Terreno ------------------------------------------------------------
    superficie: str = "normal"
    crr_liso: float = 0.0035
    crr_normal: float = 0.0045
    crr_rugoso: float = 0.0070
    crr1_liso: float = 0.00002           # 1/(m/s): variación de Crr con la velocidad
    crr1_normal: float = 0.00004
    crr1_rugoso: float = 0.00010
    presion_neumaticos: float = 7.0      # bar
    presion_referencia: float = 7.0      # bar a la que se definen los Crr de arriba
    crr_exp_liso: float = 0.45           # exponente de (p_ref/p) por superficie
    crr_exp_normal: float = 0.33
    crr_exp_rugoso: float = 0.15
    velocidad_maxima: float = 100.0      # km/h (tope)
    limite_curvatura: bool = True
    aceleracion_lateral: float = 3.0     # m/s²
    deceleracion_frenada: float = 3.0    # m/s²
    ventana_elevacion: float = 150.0     # m
    ventana_trazado: float = 60.0        # m
    paso_remuestreo: float = 20.0        # m
    razon_velocidad_par: float = 1.5     # umbral del criterio 28 para el par imposible
    tramos_superficie: Tuple[Tuple[float, float, str], ...] = ()  # (km_ini, km_fin, superficie)

    def con(self, **cambios: Any) -> "Params":
        return replace(self, **cambios)

    @property
    def perimetro_efectivo_mm(self) -> float:
        """Perímetro de rueda en mm: el medido si la medida es «manual», y si no el del ETRTO."""
        if self.etrto == ETRTO_MANUAL:
            if not self.perimetro_mm:
                raise ParamError("Con la medida de rueda en «manual» hay que indicar el perímetro "
                                 "medido en mm.")
            return float(self.perimetro_mm)
        return circumference_mm(self.etrto)

    @property
    def radio_efectivo(self) -> float:
        """Radio de rueda en metros, deducido del perímetro. Solo entra en la inercia."""
        return self.perimetro_efectivo_mm / (2.0 * math.pi) / 1000.0

    def crr_ref_por_superficie(self) -> Tuple[float, float, float]:
        """Crr de referencia (liso, normal, rugoso) corregidos por la presión de neumáticos."""
        return tuple(
            crr * pressure_factor(self.presion_neumaticos, self.presion_referencia, exp)
            for crr, exp in ((self.crr_liso, self.crr_exp_liso),
                             (self.crr_normal, self.crr_exp_normal),
                             (self.crr_rugoso, self.crr_exp_rugoso)))


@dataclass(frozen=True)
class ParamSpec:
    key: str
    label: str
    category: str
    unit: str
    default: Any
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    advanced: bool = False
    help: str = ""
    kind: str = "float"            # float | optional_float | choice | bool
    choices: Tuple[str, ...] = ()
    step: Optional[float] = None
    sensitivity: bool = True       # entra en el análisis ±10 %


_D = Params()


def _s(key, label, cat, unit, lo=None, hi=None, *, adv=False, help="", kind="float",
       choices=(), step=None, sens=True) -> ParamSpec:
    return ParamSpec(key, label, cat, unit, getattr(_D, key), lo, hi, adv, help, kind,
                     tuple(choices), step, sens)


PARAM_SPECS: Tuple[ParamSpec, ...] = (
    # --- Ciclista -------------------------------------------------------------------------------
    _s("masa_total", "Masa total (ciclista + bici + equipo)", "Ciclista", "kg", 45, 180, step=0.5,
       help="Todo lo que se mueve: tú vestido, la bici, bidones, herramientas y dorsal. "
            "El modelo solo usa esta suma, así que no hace falta separar tu peso del de la bici. "
            "1 kg de más cuesta en torno al 0,25 % de tiempo en una ruta ondulada."),
    _s("p_subida", "Potencia en subida", "Ciclista", "W", 0, 1000, step=5,
       help="Potencia media que piensas sostener cuando la pendiente supera el umbral "
            "(por defecto +2 %). Es un objetivo de pacing, no tu máximo."),
    _s("p_llano", "Potencia en llano", "Ciclista", "W", 0, 1000, step=5,
       help="Potencia media en el tramo llano, entre los dos umbrales de pendiente. "
            "Es el parámetro que más manda en el tiempo total de una ruta llana."),
    _s("p_descenso", "Potencia en descenso", "Ciclista", "W", 0, 1000, step=5,
       help="Potencia cuando la pendiente baja del umbral negativo. 0 W significa que te dejas "
            "ir sin pedalear; con 0 W, el ruido de altitud del GPX se convierte en descensos "
            "ficticios, así que vigila la ventana de suavizado."),
    _s("ftp", "FTP (opcional, para IF)", "Ciclista", "W", 50, 600, kind="optional_float",
       step=5, sens=False,
       help="Tu umbral funcional de potencia. 0 = sin FTP. No afecta al tiempo predicho: solo "
            "sirve para calcular el factor de intensidad (IF = NP/FTP)."),
    _s("umbral_pendiente", "Umbral de pendiente subida/descenso", "Ciclista", "%", 0.5, 8,
       adv=True, step=0.1,
       help="Por encima de +este valor se aplica la potencia de subida y por debajo de -este "
            "valor la de descenso. Entre ambos, la de llano."),
    _s("anchura_banda_pendiente", "Anchura de la transición entre bandas", "Ciclista", "%",
       0.2, 6, adv=True, step=0.1,
       help="La potencia pasa de una banda a otra de forma continua dentro de esta anchura, "
            "para que no haya saltos bruscos en el umbral."),
    _s("velocidad_inicial", "Velocidad inicial", "Ciclista", "km/h", 5, 60, adv=True, step=1,
       help="Velocidad con la que empieza la simulación en el primer metro. Influye poco salvo "
            "en rutas muy cortas."),
    # --- Equipamiento ---------------------------------------------------------------------------
    _s("cda", "CdA (posición aero)", "Equipamiento", "m²", 0.10, 0.60, step=0.005,
       help="Área frontal efectiva: el producto del coeficiente de arrastre por el área. Es la "
            "mayor fuente de incertidumbre de todo el modelo: ±0,02 m² mueve el tiempo más que "
            "cualquier ajuste del terreno. Mídelo en la pestaña «Estimar CdA» en vez de adivinarlo. "
            "Referencia: 0,21–0,24 contrarreloj muy afinada, 0,26–0,30 triatlón con cuernos, "
            "0,30–0,36 posición de manetas en carretera."),
    _s("delta_cda", "Aumento de CdA en posición convencional", "Equipamiento", "m²", 0, 0.6,
       step=0.01,
       help="Cuánto empeora el CdA cuando dejas la posición aero y subes a las manetas, lo que "
            "el modelo supone que pasa por debajo del umbral de velocidad. Se suma al CdA con "
            "una transición suave, sin saltos."),
    _s("umbral_posicion", "Velocidad de cambio de posición", "Equipamiento", "km/h", 5, 40,
       adv=True, step=0.5,
       help="Velocidad a la que se supone que abandonas la posición aero (en subida). Por debajo "
            "se aplica el ΔCdA completo y por encima ninguno."),
    _s("anchura_transicion_cda", "Anchura de la transición de CdA", "Equipamiento", "km/h",
       0.2, 10, adv=True, step=0.1,
       help="Lo gradual del cambio de posición. Más anchura, cambio más suave alrededor del "
            "umbral."),
    _s("eficiencia", "Eficiencia de transmisión", "Equipamiento", "", 0.90, 1.0, step=0.001,
       help="Fracción de la potencia del potenciómetro que llega a la rueda. 0,975 es lo típico "
            "con cadena limpia y lubricada; 0,95 con la transmisión sucia o cruzada."),
    _s("etrto", "Medida de rueda (ETRTO)", "Equipamiento", "", kind="choice",
       choices=etrto_codes() + (ETRTO_MANUAL,), sens=False,
       help="Medida grabada en el flanco del neumático: ancho-llanta en mm (28-622 es 700x28C). "
            "De aquí sale el perímetro. Elige «manual» para introducir el perímetro que hayas "
            "medido tú. Ojo: el tamaño de rueda solo entra en la inercia de rotación y mueve el "
            "tiempo menos del 0,001 %."),
    _s("perimetro_mm", "Perímetro medido de la rueda", "Equipamiento", "mm", 800, 2600,
       kind="optional_float", step=1, sens=False,
       help="Solo con la medida de rueda en «manual». Es el perímetro de rodadura real: marca el "
            "suelo, da una vuelta completa sentado en la bici y mide entre las dos marcas. Para "
            "700x28C son unos 2 130 mm."),
    _s("inercia_ruedas", "Inercia del par de ruedas", "Equipamiento", "kg·m²", 0.02, 0.5,
       adv=True, step=0.01,
       help="Inercia de rotación de las dos ruedas. Solo importa en aceleraciones y frenadas; en "
            "una ruta completa su efecto es despreciable."),
    # --- Variables externas: meteorología ---------------------------------------------------------
    _s("temperatura", "Temperatura", "Variables externas", "°C", -20, 50, step=0.5,
       help="Temperatura del aire durante la salida. Entra solo por la densidad del aire: más "
            "calor, aire menos denso y algo menos de resistencia. Se supone constante en toda la "
            "ruta."),
    _s("humedad", "Humedad relativa", "Variables externas", "%", 0, 100, step=1,
       help="Humedad relativa. El aire húmedo es ligeramente menos denso que el seco. Su efecto "
            "en el tiempo es pequeño, de décimas de porcentaje."),
    _s("presion_nivel_mar", "Presión a nivel del mar", "Variables externas", "hPa", 900, 1080,
       adv=True, step=0.5,
       help="Presión reducida a nivel del mar, la que dan los partes meteorológicos. Se corrige "
            "con la altitud de cada punto de la ruta según la atmósfera estándar."),
    _s("densidad_manual", "Densidad del aire manual", "Variables externas", "kg/m³", 0.8, 1.5,
       kind="optional_float", adv=True, step=0.005, sens=False,
       help="0 = calcularla a partir de temperatura, humedad, presión y altitud. Rellénala solo "
            "si tienes un valor medido y quieres saltarte el cálculo."),
    # --- Variables externas: terreno ---------------------------------------------------------------
    _s("superficie", "Superficie (global)", "Variables externas", "", kind="choice", choices=SURFACES,
       sens=False,
       help="Firme de toda la ruta: liso (asfalto nuevo), normal (asfalto en buen uso) o rugoso "
            "(asfalto viejo, grava compacta). Puedes sobrescribirlo por tramos de km más abajo."),
    _s("presion_neumaticos", "Presión de neumáticos", "Variables externas", "bar", 2.0, 12.0, step=0.1,
       help="Más presión baja el Crr en el ensayo de rodillo, y el modelo lo aplica con un "
            "exponente por superficie. Cuidado: en firme real, por encima de cierta presión el "
            "conjunto se vuelve MÁS lento (pérdidas por impedancia) y esta fórmula no lo "
            "representa, así que en rugoso te dará un resultado optimista."),
    _s("presion_referencia", "Presión de referencia de los Crr", "Variables externas", "bar", 2.0, 12.0,
       adv=True, step=0.1,
       help="Presión a la que están definidos los Crr de abajo. Con la presión de neumáticos "
            "igual a esta, el Crr queda tal cual se introduce."),
    _s("crr_liso", "Crr asfalto liso (a 29 km/h)", "Variables externas", "", 0.001, 0.05, adv=True,
       step=0.0005,
       help="Coeficiente de resistencia a la rodadura en asfalto liso, definido a 29 km/h y a la "
            "presión de referencia."),
    _s("crr_normal", "Crr asfalto normal (a 29 km/h)", "Variables externas", "", 0.001, 0.05, adv=True,
       step=0.0005,
       help="Lo mismo para asfalto en buen uso. 0,0045 es un valor razonable para un buen "
            "neumático de carretera con cámara."),
    _s("crr_rugoso", "Crr asfalto rugoso (a 29 km/h)", "Variables externas", "", 0.001, 0.05, adv=True,
       step=0.0005,
       help="Lo mismo para asfalto viejo o grava compacta. Puede llegar a doblar el de asfalto "
            "liso."),
    _s("crr_exp_liso", "Exponente de presión (liso)", "Variables externas", "", 0.0, 1.0, adv=True,
       step=0.01,
       help="Exponente de (presión_ref/presión) con el que la presión modula el Crr en liso. "
            "Estimación sin respaldo experimental propio: 0 lo desactiva."),
    _s("crr_exp_normal", "Exponente de presión (normal)", "Variables externas", "", 0.0, 1.0, adv=True,
       step=0.01,
       help="Lo mismo para asfalto en buen uso. Estimación sin respaldo propio, editable."),
    _s("crr_exp_rugoso", "Exponente de presión (rugoso)", "Variables externas", "", 0.0, 1.0, adv=True,
       step=0.01,
       help="Lo mismo para firme rugoso. Se deja bajo a propósito, porque en firme malo la "
            "ganancia por presión casi desaparece y puede invertirse."),
    _s("crr1_liso", "Crr: variación con la velocidad (liso)", "Variables externas", "s/m", 0, 0.001,
       adv=True, step=0.00001,
       help="Cuánto crece el Crr por cada m/s por encima de 29 km/h. Estimación sin respaldo "
            "experimental sólido."),
    _s("crr1_normal", "Crr: variación con la velocidad (normal)", "Variables externas", "s/m", 0, 0.001,
       adv=True, step=0.00001,
       help="Lo mismo para asfalto en buen uso. Estimación, sin respaldo experimental propio."),
    _s("crr1_rugoso", "Crr: variación con la velocidad (rugoso)", "Variables externas", "s/m", 0, 0.001,
       adv=True, step=0.00001,
       help="Lo mismo para firme rugoso, donde la velocidad penaliza más. Estimación."),
    _s("velocidad_maxima", "Velocidad máxima (tope en descenso)", "Variables externas", "km/h", 20, 120,
       step=1,
       help="Tope de seguridad: la simulación no pasa de aquí en ningún descenso, por mucho que "
            "la física lo permita."),
    _s("limite_curvatura", "Limitar velocidad por curvatura", "Variables externas", "", kind="bool",
       sens=False,
       help="Limita la velocidad en cada curva a la que aguanta la aceleración lateral máxima, "
            "con la frenada propagada hacia atrás. Desactívalo para ver el techo teórico sin "
            "frenar en curva."),
    _s("aceleracion_lateral", "Aceleración lateral máxima en curva", "Variables externas", "m/s²", 0.5, 8,
       adv=True, step=0.1,
       help="Cuánta aceleración lateral aceptas en curva. 3 m/s² es conservador y propio de "
            "circular con prudencia; 5–6 es ya pilotar al límite."),
    _s("deceleracion_frenada", "Deceleración máxima de frenada", "Variables externas", "m/s²", 0.5, 10,
       adv=True, step=0.1,
       help="Frenada máxima que se usa para llegar a la velocidad de cada curva. Evita que el "
            "límite por curvatura implique frenadas instantáneas."),
    _s("ventana_elevacion", "Ventana de suavizado de elevación", "Variables externas", "m", 10, 500,
       adv=True, step=5,
       help="Longitud sobre la que se suaviza la altitud del GPX antes de calcular la pendiente. "
            "150 m es el valor por defecto. Si tu GPX tiene altitud de GPS ruidosa (σ ≥ 3 m), "
            "súbela a 200 m; si la bajas mucho, el ruido se convierte en pendientes falsas."),
    _s("ventana_trazado", "Ventana de suavizado del trazado", "Variables externas", "m", 10, 300,
       adv=True, step=5,
       help="Lo mismo para las coordenadas, antes de calcular la curvatura. Más ventana, curvas "
            "más abiertas y menos frenadas falsas por ruido de GPS."),
    _s("paso_remuestreo", "Paso de remuestreo", "Variables externas", "m", 5, 100, adv=True, step=1,
       help="Longitud de cada tramo en que se divide la ruta. Más corto da más detalle y más "
            "tiempo de cálculo; 20 m es un buen compromiso."),
    _s("razon_velocidad_par", "Umbral del par imposible", "Variables externas", "", 1.05, 3.0,
       adv=True, step=0.05,
       help="Relación de velocidades a partir de la cual un par de ida y vuelta se descarta por "
            "imposible: 1,5 significa que si una pasada va a más de 1,5 veces la velocidad de la "
            "otra no puede ser la misma carretera llana en dos sentidos. Medido en las salidas de "
            "referencia: la relación legítima más alta es 1,42 y las descartadas van de 2,1 a 3,2. "
            "Bájalo para ser más exigente con el emparejamiento."),
)

SPEC_BY_KEY = {s.key: s for s in PARAM_SPECS}

# --------------------------------------------------------------------------- módulos (criterio 31)
#: Los dos trabajos que hace la herramienta, y que no son el mismo.
MODULOS = ("estimador", "simulador")

#: Parámetros que intervienen en la estimación de CdA a partir de un `.fit`.
#:
#: **El criterio para estar en esta lista es físico, no de gusto:** el balance de energía que
#: resuelve el estimador necesita la masa, el rendimiento de la transmisión, la inercia de las
#: ruedas, la densidad del aire y la rodadura, y el suavizado de la altitud con el que calcula la
#: pendiente. Nada más.
#:
#: Lo que queda fuera y por qué:
#:
#: - `cda` y `delta_cda`: son **la salida** del estimador. Pedirlos como entrada sería circular.
#: - `p_subida`, `p_llano`, `p_descenso`, `umbral_pendiente`, `anchura_banda_pendiente`, `ftp`,
#:   `velocidad_inicial`: el estimador usa la potencia **registrada** en el `.fit`, no un perfil de
#:   potencia que haya que planificar.
#: - `velocidad_maxima`, `limite_curvatura`, `aceleracion_lateral`, `deceleracion_frenada`: límites
#:   de la simulación. El estimador no simula nada: mide lo que ya pasó.
#: - `umbral_posicion`, `anchura_transicion_cda`: describen cómo varía el CdA con la velocidad, que
#:   es justo lo que el estimador no supone.
#: - `ventana_trazado`, `paso_remuestreo`: remuestreo del GPX, y aquí no hay GPX.
#:
#: La lista **no se mantiene a mano**: `test_c31_la_particion_de_parametros_es_la_real` comprueba
#: empíricamente que mover un parámetro de fuera no cambia la estimación y que los de dentro sí.
PARAMS_ESTIMADOR: Tuple[str, ...] = (
    "masa_total", "eficiencia", "etrto", "perimetro_mm", "inercia_ruedas",
    "temperatura", "humedad", "presion_nivel_mar", "densidad_manual",
    "superficie", "presion_neumaticos", "presion_referencia",
    "crr_liso", "crr_normal", "crr_rugoso",
    "crr_exp_liso", "crr_exp_normal", "crr_exp_rugoso",
    "crr1_liso", "crr1_normal", "crr1_rugoso",
    "ventana_elevacion", "razon_velocidad_par",
)


def specs_for_module(modulo: str) -> Tuple[ParamSpec, ...]:
    """Los parámetros que pide un módulo. El simulador los pide todos; el estimador, los suyos."""
    if modulo not in MODULOS:
        raise ParamError(f"Módulo desconocido: {modulo!r}. Son {', '.join(MODULOS)}.")
    if modulo == "simulador":
        return PARAM_SPECS
    return tuple(s for s in PARAM_SPECS if s.key in PARAMS_ESTIMADOR)


def specs_by_category(category: str, advanced: Optional[bool] = None,
                      modulo: str = "simulador"):
    return [s for s in specs_for_module(modulo) if s.category == category
            and (advanced is None or s.advanced == advanced)]


def validate_params(p: Params, idioma: str = "es") -> Params:
    """Valida rangos y coherencia. Lanza `ParamError` con un mensaje en el idioma pedido.

    Los mensajes se traducen (criterio 27): la interfaz los muestra tal cual, y con el selector en
    inglés salían en castellano. El criterio 22 exige además que el del perímetro manual explique
    cómo medirlo, así que ese texto vive en `i18n` como el resto.
    """
    from .i18n import param_label, t

    def _err(clave, **fmt):
        return ParamError(t(clave, idioma, **fmt))

    for s in PARAM_SPECS:
        val = getattr(p, s.key)
        etiqueta = param_label(s, idioma)
        if s.kind == "choice":
            if val not in s.choices:
                raise _err("err_opcion", campo=etiqueta, valor=val,
                           opciones=", ".join(s.choices))
        elif s.kind == "bool":
            if not isinstance(val, (bool,)):
                raise _err("err_booleano", campo=etiqueta)
        else:
            if val is None:
                if s.kind == "optional_float":
                    continue
                raise _err("err_obligatorio", campo=etiqueta)
            try:
                fv = float(val)
            except (TypeError, ValueError):
                raise _err("err_no_numerico", campo=etiqueta, valor=repr(val))
            if fv != fv or fv in (float("inf"), float("-inf")):
                raise _err("err_no_finito", campo=etiqueta)
            if s.minimum is not None and fv < s.minimum or s.maximum is not None and fv > s.maximum:
                raise _err("err_fuera_de_rango", campo=etiqueta, valor=f"{fv:g}",
                           unidad=s.unit, lo=f"{s.minimum:g}", hi=f"{s.maximum:g}")
    if p.etrto == ETRTO_MANUAL:
        if not p.perimetro_mm:
            raise _err("err_perimetro_falta")
    else:
        try:
            parse_etrto(p.etrto)
        except ValueError as e:
            raise ParamError(str(e))
        if p.perimetro_mm:
            raise _err("err_perimetro_sobra")
    if p.anchura_banda_pendiente > 2 * p.umbral_pendiente + 1e-12:
        raise _err("err_anchura_banda")
    for tr in p.tramos_superficie:
        if len(tr) != 3:
            raise _err("err_tramo_forma")
        a, b, sup = tr
        if sup not in SURFACES:
            raise _err("err_tramo_superficie", valor=sup)
        if not (a >= 0 and b > a):
            raise _err("err_tramo_rango", a=a, b=b)
    return p
