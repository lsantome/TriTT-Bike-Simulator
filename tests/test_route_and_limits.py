"""Criterios 3, 8 y 9 + lectura de GPX, suavizado y atmósfera."""
import math

import numpy as np
import pytest

from core import Params, build_profile, parse_gpx, simulate, simulate_track
from core.atmosphere import air_density, saturation_vapor_pressure_hpa
from core.route import gaussian_smooth
from core.synthetic import arc_track, asym_loop_track, loop_track, rolling_track, straight_track


#: Presión de vapor de saturación sobre agua líquida, hPa. Valores **tabulados**, no calculados
#: con la fórmula del proyecto: tabla psicrométrica estándar (Smithsonian Meteorological Tables /
#: WMO). Son la referencia externa que ancla `core.atmosphere`: hasta octubre de 2026 el único
#: test atmosférico comprobaba un punto con una tolerancia del ±0,41 %, y una constante de Magnus
#: equivocada (273,3 en lugar de 237,3) pasaba desapercibida porque a 15 °C solo mueve la densidad
#: un +0,058 %. A 30 °C la mueve un +0,26 % y la presión de vapor un −20,6 %.
TABLA_PRESION_VAPOR_HPA = {0.0: 6.112, 5.0: 8.726, 10.0: 12.281, 15.0: 17.044, 20.0: 23.388,
                           25.0: 31.690, 30.0: 42.455, 35.0: 56.267, 40.0: 73.849}


@pytest.mark.parametrize("temp_c", sorted(TABLA_PRESION_VAPOR_HPA))
def test_presion_de_vapor_contra_la_tabla_psicrometrica(temp_c):
    """La fórmula de Magnus debe reproducir la tabla al 0,4 %, que es su propia exactitud."""
    esperado = TABLA_PRESION_VAPOR_HPA[temp_c]
    assert saturation_vapor_pressure_hpa(temp_c) == pytest.approx(esperado, rel=0.004)


@pytest.mark.parametrize("temp_c,rh_pct", [(0.0, 0.0), (15.0, 75.0), (25.0, 60.0),
                                           (30.0, 80.0), (35.0, 90.0)])
def test_densidad_del_aire_contra_referencia_calculada_a_mano(temp_c, rh_pct):
    """ρ = p_seca/(R_seco·T) + p_vapor/(R_vapor·T), con la presión de vapor de la **tabla** y las
    constantes escritas aquí. No importa nada de `core.atmosphere` salvo la función medida, así
    que un error en cualquiera de sus dos piezas rompe este test."""
    r_seco, r_vapor = 287.058, 461.495          # J/(kg·K)
    p_total_pa = 101325.0
    t_k = temp_c + 273.15
    pv_pa = rh_pct / 100.0 * TABLA_PRESION_VAPOR_HPA[temp_c] * 100.0
    esperado = (p_total_pa - pv_pa) / (r_seco * t_k) + pv_pa / (r_vapor * t_k)
    medido = float(air_density(temp_c, rh_pct, 1013.25, 0.0))
    assert medido == pytest.approx(esperado, rel=5e-4), (
        f"{temp_c} °C / {rh_pct} % HR: {medido:.6f} frente a {esperado:.6f} kg/m³")


def test_la_humedad_baja_la_densidad_y_el_efecto_crece_con_la_temperatura():
    """El vapor es más ligero que el aire seco. Control de signo y de monotonía: fija la dirección
    del efecto, que es lo que invierte un error de constante en la presión de vapor."""
    efectos = []
    for t in (10.0, 25.0, 35.0):
        seco = float(air_density(t, 0.0, 1013.25, 0.0))
        humedo = float(air_density(t, 90.0, 1013.25, 0.0))
        assert humedo < seco
        efectos.append((seco - humedo) / seco)
    assert efectos[0] < efectos[1] < efectos[2]
    assert efectos[2] == pytest.approx(0.0195, rel=0.05)   # medido: 1,95 % a 35 °C / 90 % HR


def test_atmosfera_a_coruna_nivel_del_mar():
    rho = float(air_density(15.0, 75.0, 1013.25, 0.0))
    assert rho == pytest.approx(1.2191, abs=5e-4)


def test_atmosfera_baja_con_la_altitud():
    """La presión sigue la ISA troposférica: referencia escrita a mano, no la del módulo."""
    r0, r1 = air_density(15, 75, 1013.25, np.array([0.0, 1000.0]))
    assert r1 < r0 * 0.92
    p1 = 1013.25 * (1.0 - 2.25577e-5 * 1000.0) ** 5.25588
    assert p1 == pytest.approx(898.75, rel=1e-3)           # ISA a 1000 m
    # la densidad a 1000 m con la misma temperatura escala con la presión salvo el término de vapor
    assert r1 / r0 == pytest.approx(0.8875, rel=2e-3)


def test_gaussiano_conserva_tendencias_lineales():
    a = np.linspace(0, 100, 200)
    assert np.allclose(gaussian_smooth(a, 8.0), a, atol=1e-9)


def test_parse_gpx_roundtrip_con_namespace():
    gpx = """<?xml version="1.0"?>
    <gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1"><trk><name>Prueba</name><trkseg>
    <trkpt lat="43.3600" lon="-8.4100"><ele>10</ele></trkpt>
    <trkpt lat="43.3610" lon="-8.4100"><ele>12</ele></trkpt>
    <trkpt lat="43.3610" lon="-8.4100"><ele>12</ele></trkpt>
    <trkpt lat="43.3620" lon="-8.4100"></trkpt>
    </trkseg></trk></gpx>"""
    tr = parse_gpx(gpx.encode())
    assert len(tr.lat) == 4 and tr.name == "Prueba"
    assert any("interpol" in w for w in tr.warnings)   # el punto sin <ele>
    assert tr.ele[3] == pytest.approx(12.0)


def test_parse_gpx_sin_elevacion_avisa():
    gpx = '<gpx><trk><trkseg><trkpt lat="43.0" lon="-8.0"/><trkpt lat="43.001" lon="-8.0"/></trkseg></trk></gpx>'
    tr = parse_gpx(gpx)
    assert not tr.has_elevation and any("elevación" in w for w in tr.warnings)


def test_parse_gpx_invalido():
    with pytest.raises(ValueError):
        parse_gpx(b"esto no es xml")
    with pytest.raises(ValueError):
        parse_gpx('<gpx><trk><trkseg><trkpt lat="1" lon="1"/></trkseg></trk></gpx>')


def test_longitud_y_pendiente_del_perfil():
    pr = build_profile(straight_track(10000, 10, grade=0.05), Params())
    assert pr.length_m == pytest.approx(10000, rel=1e-3)
    assert np.allclose(pr.grade[5:-5], 0.05, atol=2e-3)
    assert pr.total_ascent == pytest.approx(500, rel=0.02)


def _arco(radio, ventana, angulo=540):
    p = Params(p_subida=450, p_llano=450, p_descenso=450, velocidad_inicial=40,
               limite_curvatura=True, aceleracion_lateral=3.0, ventana_trazado=ventana,
               paso_remuestreo=5.0)
    tr = arc_track(radius=radio, angle_deg=angulo, lead_m=800, step=2)
    pr = build_profile(tr, p)
    res = simulate(pr, p)
    s0, s1 = 800.0, 800.0 + math.radians(angulo) * radio
    return p, pr, res, (pr.s >= s0) & (pr.s <= s1)


def _exceso_en_arco(radio, ventana, angulo, nodos_minimos=4):
    p, _, res, arco = _arco(radio, ventana, angulo)
    assert arco.sum() >= nodos_minimos, f"solo {arco.sum()} nodos dentro del arco"
    return res.v_nodes[arco].max() / math.sqrt(p.aceleracion_lateral * radio) - 1.0


#: Tolerancia declarada del criterio 3 para radios ≥ `RADIO_RESUELTO_M`. No es holgura de
#: conveniencia: es el error de resolución medido del estimador de curvatura sobre la rejilla
#: completa de radios × ventanas × ángulos. El peor caso cae en el radio justo del límite con la
#: ventana más ancha (R = 10 m, ventana 150 m, 180°: +3,6 %); con la ventana por defecto es
#: +1,2 %. De 20 m en adelante el exceso no llega al 1 % con ninguna ventana.
TOLERANCIA_C3 = 0.04
TOLERANCIA_C3_HOLGADO = 0.01
TOLERANCIA_C3_FUERA_DE_ALCANCE = 0.12   # techo de la limitación declarada, medido +9,6 %


@pytest.mark.parametrize("angulo", [180, 540])
@pytest.mark.parametrize("ventana", [30.0, 60.0, 150.0])
@pytest.mark.parametrize("radio", [10.0, 20.0, 35.0, 60.0, 200.0])
def test_c3_limite_por_curvatura_en_todo_el_arco(radio, ventana, angulo):
    """Criterio 3: en un arco de radio R ≥ 10 m la velocidad no supera `√(a_lat·R)` en más del 4 %.

    **El arco entero, extremos incluidos, y también el arco corto.** Hasta octubre de 2026 este
    test se eximía del tramo donde el criterio fallaba: restringía la comprobación al interior del
    arco con un margen de 4σ «para que el suavizado no los contamine». Medido entonces sobre todo
    el arco: +29,6 % a R = 35 m.

    Se barren tres cosas, y cada una tapó un fallo distinto en su día: la **ventana** de suavizado,
    de la que depende la resolución geométrica; el **radio**; y el **ángulo**, porque una curva más
    corta que la base del estimador es el caso que el circunradio de base fija subestimaba (−37 %
    de κ en una horquilla de 180° y radio 8 m) mientras acertaba en el arco largo.
    """
    from core.route import radio_resuelto
    exceso = _exceso_en_arco(radio, ventana, angulo)
    if radio < radio_resuelto(ventana):
        # Fuera del alcance declarado el criterio no se promete, pero la limitación tiene techo:
        # medido +9,6 % como peor caso de la rejilla (R = 10 m, ventana 100 m, 540°). Si el
        # estimador empeorara, esto falla en vez de saltarse en silencio.
        assert exceso <= TOLERANCIA_C3_FUERA_DE_ALCANCE, (
            f"R={radio} m, ventana={ventana} m, arco={angulo}°: fuera de alcance "
            f"({radio_resuelto(ventana):.1f} m) y aun así {exceso:+.2%}")
        return
    assert exceso <= TOLERANCIA_C3, (
        f"R={radio} m, ventana={ventana} m, arco={angulo}°: exceso {exceso:+.2%} sobre el límite")
    # de 20 m en adelante no hay excusa de resolución: el estimador acierta al 1 %
    if radio >= 20.0:
        assert exceso <= TOLERANCIA_C3_HOLGADO, (
            f"R={radio} m, ventana={ventana} m: exceso {exceso:+.2%}, se esperaba ≤ 1 %")
    # Control negativo, para que el test no pase por ir lento por otro motivo. Solo donde cabe:
    # a 450 W la velocidad terminal es ≈ 13,3 m/s, así que por encima de R ≈ 50 m el límite por
    # curvatura ya no es lo que frena y no hay nada que controlar.
    p, pr, _, arco = _arco(radio, ventana, angulo)
    v_lim = math.sqrt(p.aceleracion_lateral * radio)
    if v_lim * 1.2 < 13.0:
        res2 = simulate(pr, p.con(limite_curvatura=False))
        assert res2.v_nodes[arco].max() > v_lim * 1.2


def test_c3_el_limite_se_mide_contra_el_radio_real_no_contra_la_curvatura_recortada():
    """`pr.kappa` viene recortada por `MAX_CURVATURE`: aseverar `v ≤ √(a/κ)` con esa misma κ es
    autorreferencial y no vería un recorte que deja pasar velocidad insegura. La referencia tiene
    que ser el radio con el que se generó el arco."""
    from core.route import MAX_CURVATURE
    radio = 20.0
    p, pr, res, arco = _arco(radio, 30.0)
    # el recorte no interviene en este arco, así que el límite sale de la geometría medida
    assert pr.kappa[arco].max() < MAX_CURVATURE - 1e-9
    assert pr.kappa[arco].min() == pytest.approx(1.0 / radio, rel=0.10)
    assert res.v_nodes[arco].max() <= math.sqrt(p.aceleracion_lateral * radio) * 1.005


@pytest.mark.parametrize("radio, minimo, maximo", [(4.0, 0.08, 0.30), (8.0, 0.02, 0.09)])
def test_c3_por_debajo_de_la_resolucion_del_trazado_el_limite_es_optimista(radio, minimo, maximo):
    """Limitación declarada: por debajo de `RADIO_RESUELTO_M` el trazado remuestreado y suavizado
    no resuelve la curva y el límite se queda corto.

    Se mide en el arco de **180°**, que es la horquilla realista y el caso peor —en 540° hay arco
    de sobra y el estimador se recupera—. Las cotas fijan por escrito cuánto, en los dos sentidos,
    para que un cambio en el estimador tenga que actualizar también la limitación del README y de
    la spec: medido +16,3 % a radio 4 m y +4,5 % a radio 8 m.
    """
    from core.route import RADIO_RESUELTO_M
    assert radio < RADIO_RESUELTO_M
    exceso = _exceso_en_arco(radio, 30.0, 180, nodos_minimos=3)
    assert minimo < exceso < maximo, f"R={radio} m: exceso medido {exceso:+.2%}"


def test_c3_frenada_antes_de_la_curva():
    """La velocidad llega a la curva sin saltos: deceleración <= frenada máxima."""
    p = Params(p_subida=450, p_llano=450, p_descenso=450, velocidad_inicial=40,
               deceleracion_frenada=3.0, ventana_trazado=30.0, paso_remuestreo=5.0)
    res = simulate_track(arc_track(radius=25, angle_deg=180, lead_m=800, step=2), p)
    v = res.v_nodes
    dec = (v[:-1] ** 2 - v[1:] ** 2) / (2 * res.profile.path)
    assert dec.max() <= 3.0 + 0.05


def test_c8_ruido_de_elevacion_poco_efecto():
    """Criterio 8: el mismo GPX con ruido de elevación (σ = 1 m, i.i.d.) difiere < 1 % en tiempo."""
    p = Params()
    limpio = simulate_track(rolling_track(30000, 10, amp=20.0, period_m=5000.0), p).tiempo_s
    difs = []
    for seed in range(5):
        ruidoso = simulate_track(rolling_track(30000, 10, amp=20.0, period_m=5000.0,
                                               noise_m=1.0, seed=seed), p).tiempo_s
        difs.append(abs(ruidoso - limpio) / limpio * 100.0)
    assert max(difs) < 1.0, difs


def test_c8_suavizado_es_lo_que_protege():
    """Sin suavizado (ventana mínima) el ruido distorsiona más que con la ventana por defecto."""
    clean = rolling_track(30000, 10, amp=20.0, period_m=5000.0)
    noisy = rolling_track(30000, 10, amp=20.0, period_m=5000.0, noise_m=1.0, seed=1)
    d = {}
    for w in (10.0, 150.0):
        p = Params(ventana_elevacion=w)
        t0 = simulate_track(clean, p).tiempo_s
        d[w] = abs(simulate_track(noisy, p).tiempo_s - t0) / t0
    assert d[150.0] < d[10.0]


def test_c9_circuito_asimetrico_mismo_tiempo_en_ambos_sentidos():
    """Criterio 9 de verdad: circuito cerrado con **elevación asimétrica** y potencia constante.
    `loop_track` tiene ele(s) = ele(L−s), así que con él la igualdad de tiempos es cierta por
    construcción (sale 0,000000 %) y el test solo detectaría un error de indexado. Aquí la ruta
    invertida es físicamente distinta, y la simetría de tiempos hay que demostrarla."""
    p = Params(masa_total=90.0, p_subida=200, p_llano=200, p_descenso=200,
               velocidad_inicial=30)
    tr = asym_loop_track(radius=4000, amp=30, n=2500)
    # la ruta invertida NO es la misma: si algún día lo fuera, este test dejaría de probar algo
    assert np.abs(tr.ele - tr.ele[::-1]).max() > 10.0
    t_ida = simulate_track(tr, p).tiempo_s
    t_vuelta = simulate_track(tr.reversed(), p).tiempo_s
    assert abs(t_ida - t_vuelta) / t_ida <= 0.005, (t_ida, t_vuelta)


def test_c9_regresion_de_indexado_circuito_simetrico():
    """Regresión de indexado (NO prueba el criterio 9): con ele(s) = ele(L−s) la igualdad es
    exacta por construcción, así que cualquier diferencia delata un error al invertir la ruta."""
    p = Params(p_subida=200, p_llano=200, p_descenso=200, velocidad_inicial=30)
    tr = loop_track(radius=4000, amp=30, lobes=2, n=2500)
    t_ida = simulate_track(tr, p).tiempo_s
    t_vuelta = simulate_track(tr.reversed(), p).tiempo_s
    assert abs(t_ida - t_vuelta) / t_ida <= 0.005


def test_c9_regresion_de_indexado_con_curvas():
    """Igual que el anterior, con curvas (tampoco prueba el criterio 9: ruta simétrica)."""
    p = Params(p_subida=200, p_llano=200, p_descenso=200, velocidad_inicial=30)
    tr = loop_track(radius=1500, amp=30, lobes=2, n=2500, wobble=0.15)
    t_ida = simulate_track(tr, p).tiempo_s
    t_vuelta = simulate_track(tr.reversed(), p).tiempo_s
    assert abs(t_ida - t_vuelta) / t_ida <= 0.005


def test_sin_viento_no_hay_asimetria_en_recta_llana():
    p = Params()
    t1 = simulate_track(straight_track(10000, 10, bearing_deg=0), p).tiempo_s
    t2 = simulate_track(straight_track(10000, 10, bearing_deg=180), p).tiempo_s
    assert t1 == pytest.approx(t2, rel=1e-4)
