"""Criterios 1, 2, 4, 5, 6 y 7: motor físico."""
import numpy as np
import pytest
from scipy.optimize import brentq

from core import Params, simulate_track
from core.physics import G, cda_effective, power_by_grade
from core.synthetic import rolling_track, straight_track

M_TOTAL = 83.0


def base(**kw):
    p = Params(masa_total=83.0, cda=0.32, delta_cda=0.0,
               crr_normal=0.004, crr1_normal=0.0, densidad_manual=1.2,
               p_subida=250.0, p_llano=250.0, p_descenso=250.0,
               limite_curvatura=False, velocidad_inicial=37.0)
    return p.con(**kw)


def test_c1_llano_solucion_analitica():
    """Criterio 1: 250 W, CdA 0,32, Crr 0,004, 83 kg, rho 1,2, eta 0,975 -> ≈37 km/h (±0,3)."""
    p = base()
    coef = [0.5 * 1.2 * 0.32, 0.0, 0.004 * M_TOTAL * G, -0.975 * 250.0]
    roots = np.roots(coef)
    v_an = [r.real for r in roots if abs(r.imag) < 1e-9 and r.real > 0][0] * 3.6
    res = simulate_track(straight_track(20000, 10), p)
    v_sim = res.velocidad_media_kmh
    assert abs(v_sim - v_an) <= 0.3
    assert abs(v_an - 37.1) < 0.2   # el valor de referencia de la spec


def test_c1_converge_desde_baja_velocidad():
    p = base(velocidad_inicial=10.0)
    res = simulate_track(straight_track(30000, 10), p)
    v_fin = res.v_nodes[-1] * 3.6
    assert abs(v_fin - 37.1) <= 0.3


@pytest.mark.parametrize("grade", [-0.06, -0.10, -0.14])
def test_c2_velocidad_terminal_descenso(grade):
    """Criterio 2: con 0 W en pendiente descendente, v -> velocidad terminal analítica (±1 %)."""
    p = base(p_subida=0, p_llano=0, p_descenso=0, velocidad_maxima=120, velocidad_inicial=20)
    res = simulate_track(straight_track(12000, 10, grade=grade), p)
    th = np.arctan(grade)
    f = lambda v: 0.5 * 1.2 * 0.32 * v * v + 0.004 * M_TOTAL * G * np.cos(th) - M_TOTAL * G * abs(np.sin(th))
    v_term = brentq(f, 1, 100)
    assert abs(res.v_nodes[-1] - v_term) / v_term <= 0.01


@pytest.mark.parametrize("vmax", [100.0, 60.0])
def test_c4_tope_de_velocidad(vmax):
    """Criterio 4: ninguna velocidad simulada supera el tope."""
    p = base(p_subida=0, p_llano=0, p_descenso=0, velocidad_maxima=vmax, velocidad_inicial=20)
    res = simulate_track(straight_track(8000, 10, grade=-0.20), p)
    assert res.v_nodes.max() * 3.6 <= vmax + 1e-6
    assert res.v_seg.max() * 3.6 <= vmax + 1e-6
    # y el tope realmente actúa (la terminal sin tope sería mayor)
    assert res.v_nodes.max() * 3.6 > vmax - 0.5


def test_c4_tope_100_por_defecto():
    res = simulate_track(straight_track(8000, 10, grade=-0.25), Params(p_descenso=0))
    assert res.v_nodes.max() * 3.6 <= 100.0 + 1e-6


def test_c5_cda_efectivo_continuo():
    """Criterio 5, cota analítica: |ΔCdA| entre muestras a 0,01 km/h <= 0,001 m²
    (pendiente máx. teórica 0,0625/km/h). OJO: esto solo mide la función, no la simulación;
    el criterio sobre muestras consecutivas reales lo verifica
    `test_c5_cda_entre_muestras_consecutivas_de_la_simulacion`."""
    p = Params()
    v = np.arange(0, 45, 0.01) / 3.6
    c = cda_effective(v, p.cda, p.delta_cda, p.umbral_posicion, p.anchura_transicion_cda)
    assert np.max(np.abs(np.diff(c))) <= 0.001
    assert c.min() >= p.cda - 1e-12 and c.max() <= p.cda + p.delta_cda + 1e-12
    # a muy baja velocidad: posición convencional; a alta: aero
    assert c[0] == pytest.approx(p.cda + p.delta_cda, abs=1e-6)
    assert c[-1] == pytest.approx(p.cda, abs=1e-6)


def test_c5_cda_entre_muestras_consecutivas_de_la_simulacion():
    """Criterio 5 sobre las muestras REALES de la simulación, en una ruta que cruza los 20 km/h.

    **Por qué el umbral es una pendiente y no un salto absoluto.** Con el paso de 20 m, entre dos
    tramos consecutivos la velocidad llega a cambiar 5,2 km/h, así que el CdA efectivo salta hasta
    **0,187 m²** aunque la función sea perfectamente continua. Ese salto no mide una discontinuidad
    del modelo: mide la resolución del remuestreo. Lo que sí es una propiedad del modelo, y lo que
    este test exige, es que el cambio por km/h de velocidad no pase de la cota de Lipschitz de la
    logística, `ΔCdA/(4·anchura)`.

    **Y la cota se exige ajustada**, no solo cumplida: si solo se comprobara `≤`, el test lo pasaría
    cualquier función más suave de la cuenta —incluso una constante— y no diría nada. Exigiendo
    además que la pendiente medida llegue al 90 % de la cota, el test falla si la transición deja
    de ser la que el modelo declara. Medido: 0,0602 frente a los 0,0625 analíticos (96 %).
    """
    p = Params(masa_total=90.0)
    res = simulate_track(rolling_track(12000, 10, amp=60.0, period_m=3000.0), p)
    v_kmh = res.v_seg * 3.6
    assert v_kmh.min() < p.umbral_posicion < v_kmh.max(), "la ruta debe cruzar el umbral"

    lipschitz = p.delta_cda / (4.0 * p.anchura_transicion_cda)      # m² por km/h
    salto = np.abs(np.diff(res.cda_seg))
    dv = np.abs(np.diff(v_kmh))
    assert np.all(salto <= lipschitz * dv + 1e-12), float((salto - lipschitz * dv).max())

    # la cota es ajustada: en algún punto la pendiente real casi la alcanza
    pendiente = np.max(salto / np.maximum(dv, 1e-9))
    assert pendiente >= 0.9 * lipschitz, (
        f"pendiente máxima {pendiente:.4f} muy por debajo de la cota {lipschitz:.4f}: "
        "la cota ha dejado de describir la transición")

    # y el CdA nunca sale del rango físico
    assert res.cda_seg.min() >= p.cda - 1e-12
    assert res.cda_seg.max() <= p.cda + p.delta_cda + 1e-12


def test_c5_la_cota_de_lipschitz_detecta_un_cda_discontinuo():
    """Prueba de que el test anterior **puede fallar**: un escalón incumple la cota.

    Sin esto, la cota de Lipschitz es sospechosa de ser el teorema del valor medio aplicado a sí
    mismo. Aquí se construye a mano un CdA discontinuo —el escalón que la transición logística
    viene justamente a evitar— y se comprueba que la misma comprobación lo rechaza.
    """
    p = Params(masa_total=90.0)
    v_kmh = np.array([19.0, 21.0, 25.0])                  # cruza el umbral de 20 km/h
    escalon = np.where(v_kmh < p.umbral_posicion, p.cda + p.delta_cda, p.cda)

    lipschitz = p.delta_cda / (4.0 * p.anchura_transicion_cda)
    salto = np.abs(np.diff(escalon))
    cota = lipschitz * np.abs(np.diff(v_kmh))
    assert not np.all(salto <= cota), "la cota no detecta un CdA discontinuo: no sirve de test"

    # la función de verdad sí la cumple con los mismos puntos
    suave = cda_effective(v_kmh / 3.6, p.cda, p.delta_cda, p.umbral_posicion,
                          p.anchura_transicion_cda)
    assert np.all(np.abs(np.diff(suave)) <= cota + 1e-12)


def test_c5_cda_en_simulacion_cuesta_arriba():
    """En una subida dura la velocidad cae por debajo de 20 km/h y el CdA efectivo sube."""
    p = Params(p_subida=220)
    res = simulate_track(straight_track(6000, 10, grade=0.08), p)
    assert res.v_seg[-100:].mean() * 3.6 < 15
    assert res.cda_seg[-100:].mean() > p.cda + 0.2


def test_c6_potencia_continua_entre_bandas():
    """Criterio 6: la potencia no tiene saltos al cruzar los umbrales (paso máx. 0,5 W por 0,001 %)."""
    p = Params()
    g = np.arange(-0.10, 0.10, 1e-5)
    pw = power_by_grade(g, p)
    assert np.max(np.abs(np.diff(pw))) <= 0.5
    # valores en las bandas planas
    assert power_by_grade(np.array([0.0]), p)[0] == pytest.approx(p.p_llano)
    assert power_by_grade(np.array([0.08]), p)[0] == pytest.approx(p.p_subida)
    assert power_by_grade(np.array([-0.08]), p)[0] == pytest.approx(p.p_descenso)


def test_c6_umbrales_editables():
    p = Params(umbral_pendiente=3.0, anchura_banda_pendiente=0.5)
    assert power_by_grade(np.array([0.025]), p)[0] == pytest.approx(p.p_llano)
    assert power_by_grade(np.array([0.036]), p)[0] == pytest.approx(p.p_subida)


def _tiempo(track, **kw):
    p = Params(**kw)
    return simulate_track(track, p).tiempo_s


@pytest.mark.parametrize("track_fn", [
    lambda: straight_track(15000, 10),
    lambda: straight_track(8000, 10, grade=0.03),
    lambda: rolling_track(20000, 10, amp=20.0, period_m=4000.0),
])
@pytest.mark.parametrize("campo,v1,v2", [
    ("crr_normal", 0.0045, 0.0070),
    ("cda", 0.27, 0.32),
    ("eficiencia", 0.985, 0.95),
])
def test_c7_monotonia(track_fn, campo, v1, v2):
    """Criterio 7: empeorar Crr, CdA (o la eficiencia) nunca reduce el tiempo total."""
    tr = track_fn()
    t1, t2 = _tiempo(tr, **{campo: v1}), _tiempo(tr, **{campo: v2})
    assert t2 >= t1 - 1e-6


@pytest.mark.parametrize("track_fn", [
    lambda: straight_track(15000, 10),
    lambda: straight_track(8000, 10, grade=0.03),
    lambda: rolling_track(20000, 10, amp=20.0, period_m=4000.0),
])
def test_c7_superficie_peor_nunca_mas_rapida(track_fn):
    tr = track_fn()
    ts = [_tiempo(tr, superficie=s) for s in ("liso", "normal", "rugoso")]
    assert ts[0] <= ts[1] <= ts[2]


@pytest.mark.parametrize("track_fn", [
    lambda: straight_track(15000, 10),
    lambda: straight_track(8000, 10, grade=0.03),
])
def test_c7_masa_en_rutas_sin_descenso(track_fn):
    """Criterio 7 (masa), solo en rutas llanas o de subida: más masa nunca reduce el tiempo.
    En rutas con descensos a 0 W la masa mayor puede ser MÁS rápida (la gravedad escala con la
    masa y la resistencia aerodinámica no): ver incidencia en el Build Log."""
    tr = track_fn()
    t_ligero = _tiempo(tr, masa_total=78.0)
    t_pesado = _tiempo(tr, masa_total=93.0)
    assert t_pesado >= t_ligero - 1e-6


def test_incidencia_masa_en_descenso_puro_es_mas_rapida():
    """Documenta por qué la cláusula 'masa' del criterio 7 no puede ser universal."""
    tr = straight_track(10000, 10, grade=-0.05)
    t_ligero = _tiempo(tr, masa_total=68.0, p_descenso=0.0)
    t_pesado = _tiempo(tr, masa_total=98.0, p_descenso=0.0)
    assert t_pesado < t_ligero


def _rk4_referencia(p, grade, length_m, v0, power_w):
    """Integración independiente (RK4, paso 0,25 m) de la EDO en distancia sobre el firme:
    d(½·m_ef·v²)/dℓ = η·P/v − ½·ρ·CdA(v)·v² − Crr(v)·m·g·cosθ − m·g·sinθ."""
    from core.physics import crr_effective
    m = p.masa_total
    m_ef = m + p.inercia_ruedas / p.radio_efectivo ** 2
    th = np.arctan(grade)
    crr_ref = p.crr_ref_por_superficie()[1]      # normal, ya con la presión aplicada
    def dE(E, ):
        v = np.sqrt(2 * E / m_ef)
        vf = max(v, 1.0)
        cda = float(cda_effective(v, p.cda, p.delta_cda, p.umbral_posicion,
                                  p.anchura_transicion_cda))
        crr = float(crr_effective(v, crr_ref, p.crr1_normal))
        return (p.eficiencia * power_w / vf - 0.5 * p.densidad_manual * cda * v * v
                - crr * m * G * np.cos(th) - m * G * np.sin(th))
    h = 0.25
    n = int(length_m / h)
    E = 0.5 * m_ef * v0 ** 2
    t = 0.0
    for _ in range(n):
        v_a = np.sqrt(2 * E / m_ef)
        k1 = dE(E); k2 = dE(E + 0.5 * h * k1); k3 = dE(E + 0.5 * h * k2); k4 = dE(E + h * k3)
        E_new = E + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        v_b = np.sqrt(2 * E_new / m_ef)
        t += h * 2.0 / (v_a + v_b)
        E = E_new
    return np.sqrt(2 * E / m_ef), t


@pytest.mark.parametrize("grade,power,v0,length", [
    (-0.07, 0.0, 5.0, 2000.0),     # descenso a 0 W desde baja velocidad
    (0.05, 220.0, 8.0, 3000.0),    # subida: cruza la zona de transición de CdA
    (0.0, 250.0, 6.0, 4000.0),     # llano acelerando desde baja velocidad
])
def test_solver_coincide_con_integracion_rk4_independiente(grade, power, v0, length):
    """El esquema implícito por tramos reproduce una integración fina e independiente (±0,3 %)."""
    p = Params(p_subida=power, p_llano=power, p_descenso=power, densidad_manual=1.2,
               limite_curvatura=False, velocidad_inicial=v0 * 3.6, velocidad_maxima=120)
    L_h = length * np.cos(np.arctan(grade))          # longitud horizontal
    res = simulate_track(straight_track(L_h, 10, grade=grade), p)
    v_ref, t_ref = _rk4_referencia(p, grade, res.profile.path.sum(), v0, power)
    assert res.v_nodes[-1] == pytest.approx(v_ref, rel=0.003)
    assert res.tiempo_s == pytest.approx(t_ref, rel=0.003)
