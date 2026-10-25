"""Criterio 24: estimador de CdA sobre un segmento de una actividad real.

La prueba fuerte no es que el número salga bonito, sino que salga **el correcto**: se genera una
actividad sintética con un CdA conocido y se comprueba que el estimador lo recupera. Y que, cuando
el segmento no sirve, lo diga en vez de dar un número con cara de bueno.
"""
from pathlib import Path

import numpy as np
import pytest

from core import Params, build_profile, simulate
from core.cda_estimator import (MAX_INCERTIDUMBRE_CDA, MIN_DISTANCIA_M, MIN_VELOCIDAD_KMH,
                                combine_estimates, estimate_cda, ride_distance_km)
from core.synthetic import rolling_track, straight_track
from core.validation import RideData, read_fit

FIXTURES = Path(__file__).resolve().parent / "fixtures"
P = Params(masa_total=90.0)


def _actividad_sintetica(track, params, nombre="sintetica") -> RideData:
    """Simula una ruta y devuelve el resultado como si fuera una actividad grabada a 1 Hz."""
    prof = build_profile(track, params)
    res = simulate(prof, params)
    t = np.concatenate([[0.0], np.cumsum(res.dt)])
    return RideData(name=nombre, t=t, lat=prof.lat, lon=prof.lon, alt=prof.ele,
                    power=np.concatenate([[res.power_effective[0]], res.power_effective]),
                    speed=res.v_nodes)


# ------------------------------------------------- referencia construida FUERA del modelo
#: Presión de vapor de saturación a 15 °C, hPa. Valor **tabulado** (tabla psicrométrica
#: estándar), no calculado con `core.atmosphere`.
PRESION_VAPOR_15C_HPA = 17.044


def _actividad_analitica(cda_real: float, params: Params, *, largo_m: float = 6000.0,
                         v_kmh: float = 29.0, nombre: str = "analitica") -> RideData:
    """Actividad llana a velocidad constante cuya potencia se calcula **a mano**.

    El resto de los tests de este fichero generan la actividad de referencia con `core.simulate` y
    contrastan el resultado con `calibrate_cda`, que pasa por el mismo simulador: toda la física
    compartida —densidad del aire, Crr, eficiencia— queda a los dos lados de la comparación y un
    error en ella es invisible. Verificado en octubre de 2026: con `air_density` sesgada un +3 %,
    los 23 tests de este fichero seguían en verde mientras el CdA estimado sobre una actividad
    real caía un 2,9 %.

    Aquí la referencia se escribe desde cero. En llano y a velocidad constante el balance es
    exacto y no hay energía cinética ni potencial:

        P = (CdA·½·ρ·v³ + Crr·m·g·v) / η

    con ρ calculada de la ley de gases y de la presión de vapor **tabulada**, y Crr evaluado a
    29 km/h, que es la velocidad a la que se define (así el término `crr1·(v − 29 km/h)` vale 0) y
    con la presión de neumáticos igual a la de referencia (factor de presión 1). Las constantes
    están escritas en el test, no importadas.
    """
    g = 9.80665
    r_seco, r_vapor = 287.058, 461.495
    t_k = params.temperatura + 273.15
    pv_pa = params.humedad / 100.0 * PRESION_VAPOR_15C_HPA * 100.0
    rho = (params.presion_nivel_mar * 100.0 - pv_pa) / (r_seco * t_k) + pv_pa / (r_vapor * t_k)
    crr = params.crr_normal                      # a 29 km/h y a la presión de referencia
    v = v_kmh / 3.6
    potencia = (cda_real * 0.5 * rho * v ** 3 + crr * params.masa_total * g * v) / params.eficiencia

    n = int(largo_m / v) + 1
    t = np.arange(n, dtype=float)
    s = v * t
    lat = 43.36 + np.degrees(s / 6371008.8)      # rumbo norte: la longitud no cambia
    return RideData(name=nombre, t=t, lat=lat, lon=np.full(n, -8.41), alt=np.full(n, 10.0),
                    power=np.full(n, potencia), speed=np.full(n, v))


@pytest.mark.parametrize("cda_real", [0.22, 0.27, 0.34])
def test_c24_recupera_un_cda_de_una_actividad_construida_a_mano(cda_real):
    """Criterio 24 contra una referencia independiente del modelo: si la densidad del aire, el
    Crr o la eficiencia se desvían, el CdA estimado se va y este test cae."""
    p = P.con(temperatura=15.0, humedad=75.0, presion_nivel_mar=1013.25, superficie="normal",
              presion_neumaticos=7.0, presion_referencia=7.0)
    ride = _actividad_analitica(cda_real, p)
    e = estimate_cda(ride, p, 0.5, 5.5)
    assert e.utilizable, e.avisos
    assert e.cda == pytest.approx(cda_real, abs=0.002), f"estimado {e.cda:.4f} vs real {cda_real}"
    assert e.cda_min <= cda_real <= e.cda_max


def test_c24_la_referencia_a_mano_distingue_cdas_vecinos():
    """Control de resolución: la cota del test anterior (±0,002) tiene que ser más estrecha que la
    distancia entre dos CdA que un ciclista distinguiría. 0,27 y 0,28 son 0,37 W a 29 km/h."""
    p = P.con(superficie="normal")
    e27 = estimate_cda(_actividad_analitica(0.27, p), p, 0.5, 5.5)
    e28 = estimate_cda(_actividad_analitica(0.28, p), p, 0.5, 5.5)
    assert e28.cda - e27.cda == pytest.approx(0.01, abs=0.001)


# --------------------------------------------------------------------------- recuperar un CdA conocido
@pytest.mark.parametrize("cda_real", [0.22, 0.27, 0.34])
def test_c24_recupera_el_cda_con_el_que_se_genero_la_actividad(cda_real):
    p = P.con(cda=cda_real, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(12000, 10), p)
    e = estimate_cda(ride, p, 1.0, 11.0)
    assert e.cda == pytest.approx(cda_real, abs=0.005), f"estimado {e.cda:.4f} vs real {cda_real}"
    assert e.utilizable and e.cda_min <= cda_real <= e.cda_max


def test_c24_recupera_el_cda_tambien_en_ruta_ondulada():
    p = P.con(cda=0.28, p_llano=240.0, p_subida=240.0, p_descenso=240.0)
    ride = _actividad_sintetica(rolling_track(16000, 10, amp=15.0, period_m=4000.0), p)
    e = estimate_cda(ride, p, 1.0, 15.0)
    assert e.cda == pytest.approx(0.28, abs=0.015)


def test_c24_detecta_un_cda_distinto_del_supuesto():
    """Si la actividad se hizo con 0,34 y los parámetros dicen 0,27, el estimador debe decir 0,34."""
    p_real = P.con(cda=0.34, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(12000, 10), p_real)
    e = estimate_cda(ride, p_real.con(cda=0.27), 1.0, 11.0)       # el CdA de los params no se usa
    assert e.cda == pytest.approx(0.34, abs=0.005)


# --------------------------------------------------------------------------- diagnóstico
def test_c24_un_segmento_corto_se_marca_como_no_utilizable():
    p = P.con(cda=0.27, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(12000, 10), p)
    e = estimate_cda(ride, p, 1.0, 1.3)                            # 300 m
    assert not e.utilizable
    assert any("corto" in a.lower() for a in e.avisos)
    assert e.distancia_m < MIN_DISTANCIA_M


def test_c24_un_segmento_lento_y_en_cuesta_se_marca_como_no_utilizable():
    p = P.con(cda=0.27, p_llano=200.0, p_subida=200.0, p_descenso=200.0)
    ride = _actividad_sintetica(straight_track(6000, 10, grade=0.06), p)
    e = estimate_cda(ride, p, 0.5, 5.5)
    assert e.velocidad_media_kmh < MIN_VELOCIDAD_KMH
    assert not e.utilizable
    assert any("aerodinámica" in a or "Velocidad media baja" in a for a in e.avisos)
    # en cuesta el término de la pendiente domina: poca fracción aero y mucha sensibilidad
    assert e.fraccion_aero < 0.5


def test_c24_el_aviso_del_viento_sale_siempre_y_cuantifica_el_sesgo():
    p = P.con(cda=0.27, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(12000, 10), p)
    e = estimate_cda(ride, p, 1.0, 11.0)
    assert any("viento" in a.lower() for a in e.avisos)
    # el viento es el término dominante y por eso va fuera de la incertidumbre
    assert e.sens_viento > e.cda_incertidumbre


def test_c24_las_sensibilidades_son_positivas_y_la_incertidumbre_las_combina():
    p = P.con(cda=0.27, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(12000, 10), p)
    e = estimate_cda(ride, p, 1.0, 11.0)
    for s in (e.sens_altitud, e.sens_crr, e.sens_potencia):
        assert s >= 0
    esperada = np.sqrt(e.sens_altitud ** 2 + e.sens_crr ** 2 + e.sens_potencia ** 2)
    assert e.cda_incertidumbre == pytest.approx(esperada)
    assert e.cda_max - e.cda_min == pytest.approx(2 * e.cda_incertidumbre)


def test_c24_un_segmento_mas_largo_estima_mejor_que_uno_corto():
    p = P.con(cda=0.27, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(20000, 10), p)
    corto = estimate_cda(ride, p, 1.0, 2.0)
    largo = estimate_cda(ride, p, 1.0, 19.0)
    assert largo.cda_incertidumbre < corto.cda_incertidumbre


# --------------------------------------------------------------------------- errores de uso
def test_c24_rangos_invalidos_lanzan_error_claro():
    p = P.con(cda=0.27, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(12000, 10), p)
    with pytest.raises(ValueError):
        estimate_cda(ride, p, 5.0, 5.0)                 # longitud nula
    with pytest.raises(ValueError):
        estimate_cda(ride, p, 8.0, 2.0)                 # al revés
    with pytest.raises(ValueError):
        estimate_cda(ride, p, 50.0, 60.0)               # fuera de la ruta


def test_c24_combinar_estimaciones_usa_la_dispersion_cuando_no_concuerdan():
    p = P.con(cda=0.27, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(20000, 10), p)
    iguales = [estimate_cda(ride, p, a, a + 6.0) for a in (1.0, 7.0)]
    cda, inc = combine_estimates(iguales)
    assert cda == pytest.approx(0.27, abs=0.01)
    # con estimaciones artificialmente discordantes manda la dispersión, no la incertidumbre formal
    discordantes = [iguales[0], iguales[1]]
    discordantes[1].cda += 0.08
    _, inc2 = combine_estimates(discordantes)
    assert inc2 > inc and inc2 > min(e.cda_incertidumbre for e in discordantes)
    with pytest.raises(ValueError):
        combine_estimates([])


# --------------------------------------------------------------------------- con datos reales
def test_c24_con_la_actividad_real_coincide_con_la_calibracion_por_tiempo():
    """Dos métodos independientes sobre los mismos datos: balance de energía en el recorrido
    completo frente a la calibración por tiempo total (CdA 0,269). Deben parecerse."""
    from core.validation import calibrate_cda

    ride = read_fit((FIXTURES / "recorrido2_30mar2025.fit").read_bytes(), "30mar")
    km = ride_distance_km(ride)
    e = estimate_cda(ride, P, 0.0, float(km[-1]))
    por_tiempo = calibrate_cda([ride], P)
    assert e.utilizable
    assert abs(e.cda - por_tiempo) < 0.02, (e.cda, por_tiempo)


def test_c24_con_datos_reales_los_segmentos_en_cuesta_se_descartan_y_los_llanos_no():
    ride = read_fit((FIXTURES / "recorrido2_30mar2025.fit").read_bytes(), "30mar")
    llano = estimate_cda(ride, P, 10.0, 20.0)
    cuesta = estimate_cda(ride, P, 20.0, 25.0)
    assert llano.utilizable and not cuesta.utilizable
    assert cuesta.cda_incertidumbre > MAX_INCERTIDUMBRE_CDA
    assert llano.fraccion_aero > cuesta.fraccion_aero


def test_c24_ride_distance_km_es_creciente_y_cubre_la_ruta():
    ride = read_fit((FIXTURES / "recorrido2_06abr2025.fit").read_bytes(), "06abr")
    km = ride_distance_km(ride)
    assert np.all(np.diff(km) >= -1e-9)
    assert 120.0 < km[-1] < 135.0


# --------------------------------------------------------------------------- búsqueda automática
from core.cda_estimator import (MAX_DESNIVEL_LLANO_M, MAX_PENDIENTE_LLANA_PCT, combine_pairs,
                                find_flat_segments, find_paired_segments, find_return_pass,
                                search_summary, separacion_m)


@pytest.fixture(scope="module")
def actividad_real():
    return read_fit((FIXTURES / "recorrido2_30mar2025.fit").read_bytes(), "30mar")


def test_c24_la_busqueda_solo_devuelve_tramos_llanos_utilizables_y_sin_solapes(actividad_real):
    segs = find_flat_segments(actividad_real, P)
    assert segs, "no ha encontrado ningún tramo en una ruta de 127 km"
    for e in segs:
        assert e.utilizable and e.llano
        assert abs(e.pendiente_media_pct) <= MAX_PENDIENTE_LLANA_PCT
        assert abs(e.desnivel_m) <= MAX_DESNIVEL_LLANO_M
        # El criterio 25 pide 1 km, así que el test exige 1 km: escrito como `>= 1000 - 100`
        # toleraba 900 m, y la implementación tenía el mínimo en 500 m.
        assert e.distancia_m >= MIN_DISTANCIA_M
        assert MIN_DISTANCIA_M >= 1000.0               # el mínimo del núcleo cumple el criterio
        assert e.avisos                                # llegan con sus avisos
    for a, b in zip(segs, segs[1:]):
        assert a.cda_incertidumbre <= b.cda_incertidumbre      # ordenados por fiabilidad
    for i, a in enumerate(segs):
        for b in segs[i + 1:]:
            assert not (a.km_inicio < b.km_fin and b.km_inicio < a.km_fin), "hay solape"


def test_c24_la_busqueda_respeta_los_limites_que_se_le_pasan(actividad_real):
    segs = find_flat_segments(actividad_real, P, longitudes_m=(2000.0,), paso_m=1000.0, maximo=3)
    assert len(segs) <= 3
    for e in segs:
        assert 1.5 < e.distancia_m / 1000.0 < 2.5


def test_c24_encuentra_la_pasada_de_vuelta_por_la_misma_carretera(actividad_real):
    segs = find_flat_segments(actividad_real, P)
    vuelta = find_return_pass(actividad_real, P, segs[0])
    assert vuelta is not None, "la ruta es de ida y vuelta: debería encontrarla"
    # misma carretera (centros cerca) y sentido opuesto
    assert separacion_m(segs[0], vuelta) < 1000.0
    dif = abs((segs[0].rumbo_grados - vuelta.rumbo_grados + 180.0) % 360.0 - 180.0)
    assert abs(dif - 180.0) < 45.0
    # y no se solapa con la ida
    assert not (segs[0].km_inicio < vuelta.km_fin and vuelta.km_inicio < segs[0].km_fin)


#: Las tres salidas coherentes del recorrido 2 (el examen de coherencia descarta 04-may y 08-jun).
SALIDAS_COHERENTES = ("recorrido2_30mar2025", "recorrido2_06abr2025", "recorrido2_19abr2026")


@pytest.mark.parametrize("nombre", SALIDAS_COHERENTES)
def test_c25_los_pares_concuerdan_con_la_calibracion_por_tiempo(nombre):
    """La prueba de fondo: el promedio de ida y vuelta cancela el viento, y entonces el CdA
    coincide con el que da la calibración por tiempo total, que es un método independiente.

    Sobre **las tres** salidas coherentes. Hasta octubre de 2026 esto se comprobaba solo en
    `recorrido2_30mar2025`: las otras dos cumplían (medido entonces: 0,0090 / 0,0062 / 0,0027),
    pero nada lo vigilaba, así que el criterio 25 descansaba en un fixture de tres.
    """
    from core.validation import calibrate_cda

    ride = read_fit((FIXTURES / f"{nombre}.fit").read_bytes(), nombre)
    pares = find_paired_segments(ride, P)
    assert len(pares) >= 3
    cda, inc = combine_pairs(pares)
    por_tiempo = calibrate_cda([ride], P)
    assert abs(cda - por_tiempo) < 0.02, f"{nombre}: pares {cda:.4f} vs tiempo {por_tiempo:.4f}"
    assert inc < 0.03


def test_c24_la_aritmetica_del_par_es_la_declarada(actividad_real):
    pares = find_paired_segments(actividad_real, P)
    assert len(pares) >= 3
    for par in pares:
        assert par.discrepancia == pytest.approx(abs(par.ida.cda - par.vuelta.cda) / 2)
        assert par.cda == pytest.approx((par.ida.cda + par.vuelta.cda) / 2)
        assert par.viento_estimado_ms >= 0


def test_c24_un_tramo_suelto_sale_mas_disperso_que_el_par(actividad_real):
    """Lo que justifica todo el diseño: los tramos sueltos discrepan entre sí mucho más que los
    pares de ida y vuelta, porque cada uno lleva su viento dentro."""
    import numpy as np

    segs = find_flat_segments(actividad_real, P)
    pares = find_paired_segments(actividad_real, P)
    disp_sueltos = np.std([e.cda for e in segs], ddof=1)
    disp_pares = np.std([par.cda for par in pares], ddof=1)
    assert disp_pares < disp_sueltos


def test_c24_el_resumen_destapa_el_sesgo_de_seleccion(actividad_real):
    """La búsqueda exige velocidad alta, así que elige tramos más rápidos que la ruta. Eso no se
    puede esconder: el resumen lo mide."""
    segs = find_flat_segments(actividad_real, P)
    r = search_summary(actividad_real, P, segs)
    assert r.n_tramos == len(segs)
    assert r.velocidad_tramos_kmh > r.velocidad_ruta_kmh
    assert r.sesgo_velocidad_kmh > 2.0 and r.hay_sesgo
    assert 0.1 < r.cda_ruta_completa < 0.5
    # y el combinado de tramos sueltos sale por debajo del de la ruta completa (el sesgo)
    assert r.cda_combinado < r.cda_ruta_completa


def test_c24_combine_pairs_no_pondera_por_discrepancia():
    """Decisión documentada: media sin ponderar. Si alguien la cambia a ponderada, este test lo
    delata, porque el resultado dejaría de ser la media aritmética."""
    import numpy as np
    from core.cda_estimator import OppositePair

    class _Falso:
        cda_incertidumbre = 0.005
    pares = [OppositePair(ida=_Falso(), vuelta=_Falso(), cda=c, discrepancia=d, separacion_m=100.0)
             for c, d in ((0.240, 0.002), (0.300, 0.060))]
    cda, inc = combine_pairs(pares)
    assert cda == pytest.approx(0.270)                 # media aritmética, no 0,24
    # la incertidumbre es la DISPERSIÓN entre pares, sin dividir por √n (ver criterio 25)
    assert inc == pytest.approx(np.std([0.24, 0.30], ddof=1), rel=1e-6)
    with pytest.raises(ValueError):
        combine_pairs([])


def test_c24_sin_pasada_de_vuelta_devuelve_none():
    """Una recta de ida sin vuelta no puede tener par."""
    p = P.con(cda=0.27, p_llano=250.0, p_subida=250.0, p_descenso=250.0)
    ride = _actividad_sintetica(straight_track(20000, 10), p)
    segs = find_flat_segments(ride, p)
    assert segs
    assert find_return_pass(ride, p, segs[0]) is None
    assert find_paired_segments(ride, p) == []
