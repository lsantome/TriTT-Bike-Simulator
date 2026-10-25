"""Módulo de validación con FIT (criterio 13: mecánica; la verificación con datos reales
requiere los .fit del usuario). Aquí se prueba con actividades sintéticas generadas con el
propio simulador (autoconsistencia), NO sustituye la validación con datos reales."""
import numpy as np
import pytest

from core import Params, build_profile, simulate
from core.synthetic import loop_track
from core.validation import calibrate_cda, read_fit, replay

from .fit_writer import build_fit

T0 = 1_760_000_000  # época unix arbitraria


def sintetica_a_fit(track, params, nombre="sintetica"):
    """Simula la ruta con `params` y la convierte en un FIT a 1 Hz (como un ciclocomputador)."""
    prof = build_profile(track, params)
    res = simulate(prof, params)
    t_grid = np.arange(0.0, res.t_nodes[-1], 1.0)
    s_t = np.interp(t_grid, res.t_nodes, prof.s)
    v_t = np.interp(t_grid, res.t_nodes, res.v_nodes)
    idx = np.clip(np.searchsorted(res.t_nodes, t_grid, side="right") - 1, 0, len(res.dt) - 1)
    recs = [dict(t=T0 + t, lat=np.interp(s, prof.s, prof.lat), lon=np.interp(s, prof.s, prof.lon),
                 alt=np.interp(s, prof.s, prof.ele), speed=v, power=res.power_effective[i],
                 dist=s) for t, s, v, i in zip(t_grid, s_t, v_t, idx)]
    return build_fit(recs), res


@pytest.fixture(scope="module")
def actividad():
    p = Params(cda=0.28, p_subida=240, p_llano=210, p_descenso=0)
    tr = loop_track(radius=3000, amp=40, lobes=3, n=2500, wobble=0.1)
    data, res = sintetica_a_fit(tr, p)
    return p, data, res


def test_lectura_fit(actividad):
    p, data, res = actividad
    ride = read_fit(data, "sintetica")
    assert len(ride.t) == pytest.approx(res.tiempo_s, abs=2)
    assert np.isfinite(ride.lat).all() and np.isfinite(ride.power).all()
    assert 25 < np.nanmax(ride.alt) < 45
    assert ride.lat[0] == pytest.approx(43.36, abs=1e-3)


def test_replay_con_los_mismos_parametros_error_pequeno(actividad):
    p, data, res = actividad
    rep = replay(read_fit(data, "sintetica"), p)
    assert abs(rep.error_tiempo_pct) < 1.5
    assert rep.mae_velocidad_kmh < 1.0
    assert rep.tiempo_real_movimiento_s == pytest.approx(res.tiempo_s, rel=0.01)
    assert any("viento" in n.lower() for n in rep.notas)


def test_replay_detecta_cda_erroneo(actividad):
    p, data, _ = actividad
    rep = replay(read_fit(data, "sintetica"), p.con(cda=0.36))
    assert rep.error_tiempo_pct > 2.0           # CdA mayor -> más lento que la realidad


def test_calibracion_recupera_el_cda(actividad):
    p, data, _ = actividad
    ride = read_fit(data, "sintetica")
    cda = calibrate_cda([ride], p.con(cda=0.34))
    assert cda == pytest.approx(0.28, abs=0.012)


def test_fit_sin_gps_se_rechaza():
    recs = [dict(t=T0 + i, lat=0, lon=0, alt=0, speed=5, power=100, dist=5 * i) for i in range(40)]
    with pytest.raises(ValueError, match="GPS"):
        read_fit(build_fit(recs, with_gps=False), "rodillo")


def test_fit_muy_corto_se_rechaza():
    recs = [dict(t=T0 + i, lat=43, lon=-8, alt=0, speed=5, power=100, dist=5 * i) for i in range(5)]
    with pytest.raises(ValueError):
        read_fit(build_fit(recs), "x")
