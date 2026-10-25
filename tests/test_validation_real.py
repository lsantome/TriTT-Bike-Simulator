"""Criterio 13 con las actividades REALES del usuario (no sintéticas).

Las dos salidas válidas del recorrido 2, reducidas a 1 de cada 5 registros
(ver `tests/fixtures/README.md`). Este es el único test que mide precisión frente a la realidad;
el resto de `test_validation.py` mide autoconsistencia del mecanismo.
"""
from pathlib import Path

import pytest

from core import Params
from core.validation import calibrate_cda, read_fit, replay

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SALIDAS = ("recorrido2_30mar2025", "recorrido2_06abr2025")

#: Masa total declarada por el usuario (ciclista + bici + equipo).
PARAMS = Params(masa_total=90.0)
UMBRAL_PCT = 3.0          # el que pide la spec, sin relajar


@pytest.fixture(scope="module")
def salidas():
    out = {}
    for nombre in SALIDAS:
        ruta = FIXTURES / f"{nombre}.fit"
        assert ruta.exists(), f"falta el fixture {ruta}"
        out[nombre] = read_fit(ruta.read_bytes(), nombre)
    return out


def test_las_actividades_reales_se_leen_con_gps_y_potencia(salidas):
    for nombre, a in salidas.items():
        assert len(a.t) > 2000, nombre
        assert a.lat.size == a.t.size and a.power.size == a.t.size
        assert a.power.max() > 300 and a.speed.max() > 10
        assert not a.warnings, (nombre, a.warnings)


@pytest.mark.parametrize("i_cal", [0, 1])
def test_c13_calibrar_en_una_salida_y_validar_en_la_otra(salidas, i_cal):
    """Criterio 13: misma bici y misma ruta, error de tiempo en movimiento ≤ 3 %."""
    cal, val = SALIDAS[i_cal], SALIDAS[1 - i_cal]
    cda = calibrate_cda([salidas[cal]], PARAMS)
    assert 0.20 < cda < 0.35, f"CdA calibrado fuera de lo plausible: {cda:.4f}"

    rep = replay(salidas[val], PARAMS.con(cda=cda))
    assert abs(rep.error_tiempo_pct) <= UMBRAL_PCT, (
        f"calibrando en {cal} (CdA {cda:.4f}) el error en {val} es "
        f"{rep.error_tiempo_pct:+.2f} % (> {UMBRAL_PCT} %)")
    # el informe debe traer además el error de velocidad, no solo el de tiempo
    assert rep.mae_velocidad_kmh > 0 and rep.rmse_velocidad_kmh >= rep.mae_velocidad_kmh
    assert any("viento" in n.lower() for n in rep.notas)


def test_c13_el_cda_calibrado_con_las_dos_queda_entre_los_individuales(salidas):
    rides = [salidas[n] for n in SALIDAS]
    conjunto = calibrate_cda(rides, PARAMS)
    individuales = sorted(calibrate_cda([r], PARAMS) for r in rides)
    assert individuales[0] <= conjunto <= individuales[1]
    assert conjunto == pytest.approx(0.269, abs=0.01)     # valor documentado en el README


def test_c13_sin_calibrar_el_error_es_mayor_que_calibrado(salidas):
    """La calibración tiene que aportar algo: con el CdA por defecto el error es peor."""
    rides = [salidas[n] for n in SALIDAS]
    cda = calibrate_cda(rides, PARAMS)
    peor_defecto = max(abs(replay(r, PARAMS).error_tiempo_pct) for r in rides)
    peor_calibrado = max(abs(replay(r, PARAMS.con(cda=cda)).error_tiempo_pct) for r in rides)
    assert peor_calibrado < peor_defecto
