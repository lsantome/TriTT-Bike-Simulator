"""Criterio 16 en las tablas que la app muestra y descarga (`core.exports`)."""
import pytest

from core import Params, simulate_track
from core.exports import (COLUMNAS_TIEMPO_BLOQUES, COLUMNAS_TIEMPO_TRAMOS,
                          COLUMNAS_TIEMPO_VALIDACION, csv_bytes, tabla_bloques, tabla_tramos,
                          tabla_validacion)
from core.synthetic import demo_track
from core.uncertainty import DIA_PCT, MODELO_PCT, SUFIJOS


@pytest.fixture(scope="module")
def resultado():
    return simulate_track(demo_track(), Params(masa_total=90.0))


def test_c16_la_tabla_por_bloques_lleva_banda_en_su_tiempo(resultado):
    df = tabla_bloques(resultado, 1.0)
    for col in COLUMNAS_TIEMPO_BLOQUES:
        for suf in SUFIJOS:
            assert col + suf in df.columns, col + suf
        assert (df[col + "_min_dia"] < df[col + "_min_modelo"]).all()
        assert (df[col + "_max_dia"] > df[col + "_max_modelo"]).all()


def test_c16_el_detalle_por_tramo_lleva_banda_en_duracion_y_acumulado(resultado):
    df = tabla_tramos(resultado)
    for col in COLUMNAS_TIEMPO_TRAMOS:
        for suf in SUFIJOS:
            assert col + suf in df.columns, col + suf


def test_c16_ninguna_columna_de_tiempo_queda_sin_banda(resultado):
    """Barrido: si mañana se añade otra columna de tiempo, este test la delata."""
    for df, propias in ((tabla_bloques(resultado, 1.0), COLUMNAS_TIEMPO_BLOQUES),
                        (tabla_tramos(resultado), COLUMNAS_TIEMPO_TRAMOS)):
        candidatas = [c for c in df.columns
                      if ("tiempo" in c or "duracion" in c) and not c.endswith(SUFIJOS)]
        assert sorted(candidatas) == sorted(propias), candidatas


def test_c16_los_csv_descargables_incluyen_las_columnas_de_banda(resultado):
    cab_bloques = csv_bytes(tabla_bloques(resultado, 1.0)).decode().splitlines()[0]
    cab_tramos = csv_bytes(tabla_tramos(resultado)).decode().splitlines()[0]
    for suf in SUFIJOS:
        assert "tiempo_s" + suf in cab_bloques, suf
        assert "duracion_s" + suf in cab_tramos, suf
        assert "tiempo_acum_s" + suf in cab_tramos, suf


def test_c16_los_margenes_coinciden_con_los_porcentajes_declarados(resultado):
    df = tabla_bloques(resultado, 2.0)
    base = df["tiempo_s"].iloc[0]
    assert df["tiempo_s_max_modelo"].iloc[0] == pytest.approx(base * (1 + MODELO_PCT / 100))
    assert df["tiempo_s_min_dia"].iloc[0] == pytest.approx(base * (1 - DIA_PCT / 100))


# --------------------------------------------------------------------------- pestaña de validación
def _reporte(error_pct):
    """Informe mínimo con la forma que devuelve `replay`."""
    return dict(name="salida", distancia_km=100.0, tiempo_real_movimiento_s=10000.0,
                tiempo_predicho_s=10000.0 * (1 + error_pct / 100.0), error_tiempo_pct=error_pct,
                error_velocidad_medio_kmh=0.3, mae_velocidad_kmh=2.9, rmse_velocidad_kmh=3.9,
                potencia_media_real_w=220.0, cda_usado=0.269, notas=[])


def test_c16_el_informe_de_validacion_fit_lleva_banda_en_el_tiempo_predicho():
    df = tabla_validacion([_reporte(1.2), _reporte(-1.1)])
    for col in COLUMNAS_TIEMPO_VALIDACION:
        for suf in SUFIJOS:
            assert col + suf in df.columns, col + suf


def test_el_informe_de_validacion_marca_el_criterio_de_3_por_ciento():
    df = tabla_validacion([_reporte(1.2), _reporte(4.5), _reporte(-3.0)])
    assert list(df["criterio_<=3%"]) == ["cumple", "NO cumple", "cumple"]


def test_el_informe_de_validacion_vacio_no_revienta():
    assert tabla_validacion([]).empty


def test_el_informe_de_validacion_acepta_objetos_validationreport():
    from core.validation import ValidationReport

    rep = ValidationReport(**_reporte(0.8))
    df = tabla_validacion([rep])
    assert df["tiempo_predicho_s_max_modelo"].iloc[0] > df["tiempo_predicho_s"].iloc[0]


# --------------------------------------------------------------------------- tabla de segmentos
def _estimaciones_reales():
    from pathlib import Path

    from core.cda_estimator import estimate_cda
    from core.validation import read_fit

    fx = Path(__file__).resolve().parent / "fixtures" / "recorrido2_30mar2025.fit"
    ride = read_fit(fx.read_bytes(), "30mar")
    p = Params(masa_total=90.0)
    return [estimate_cda(ride, p, a, b) for a, b in ((10.0, 20.0), (20.0, 25.0))]


def test_la_tabla_de_segmentos_trae_lo_que_se_pidio_y_en_orden():
    from core.exports import COLUMNAS_SEGMENTOS_BASICAS, tabla_segmentos

    ests = _estimaciones_reales()
    df = tabla_segmentos(ests)
    assert list(df.columns) == list(COLUMNAS_SEGMENTOS_BASICAS)
    # lo que pidió el usuario, explícitamente
    for exigida in ("cda", "desnivel_m", "v_media_kmh", "potencia_media_w"):
        assert exigida in df.columns
    assert len(df) == len(ests)
    assert df["tramo_km"].iloc[0] == "10.0–20.0"


@pytest.mark.parametrize("idioma", ["es", "en"])
def test_la_tabla_de_segmentos_marca_cual_es_utilizable(idioma):
    """En los **dos** idiomas. Este test exigía `{"sí", "NO"}` literalmente, así que la celda sin
    traducir era un defecto que ningún test podía detectar: el test la fijaba."""
    from core.exports import tabla_segmentos
    from core.i18n import t

    df = tabla_segmentos(_estimaciones_reales(), idioma=idioma)
    si, no = t("celda_si", idioma), t("celda_no_enfatico", idioma)
    assert set(df["utilizable"]) <= {si, no}
    assert df["utilizable"].iloc[0] == si            # 10–20 km es llano y rápido
    assert df["utilizable"].iloc[1] == no            # 20–25 km es una cuesta
    # y la fila mala se nota en las columnas de juicio
    assert df["aero_%"].iloc[1] < df["aero_%"].iloc[0]
    if idioma == "en":
        assert si == "yes"                           # la traducción existe de verdad
    assert df["±"].iloc[1] > df["±"].iloc[0]


def test_la_tabla_de_segmentos_con_detalle_anade_el_desglose_del_error():
    from core.exports import COLUMNAS_SEGMENTOS_BASICAS, COLUMNAS_SEGMENTOS_DETALLE, tabla_segmentos

    df = tabla_segmentos(_estimaciones_reales(), detalle=True)
    assert list(df.columns) == list(COLUMNAS_SEGMENTOS_BASICAS) + list(COLUMNAS_SEGMENTOS_DETALLE)
    for col in ("err_altitud", "err_crr", "err_potencia", "viento_1ms_±"):
        assert (df[col] >= 0).all()
    # el margen mostrado es coherente con el CdA
    assert (df["cda_min"] < df["cda"]).all() and (df["cda"] < df["cda_max"]).all()


def test_la_tabla_de_segmentos_acepta_dicts_y_una_lista_vacia():
    from core.exports import COLUMNAS_SEGMENTOS_BASICAS, tabla_segmentos

    ests = _estimaciones_reales()
    como_dicts = tabla_segmentos([e.as_dict() for e in ests])
    assert como_dicts.equals(tabla_segmentos(ests))
    vacia = tabla_segmentos([])
    assert vacia.empty and list(vacia.columns) == list(COLUMNAS_SEGMENTOS_BASICAS)


def test_el_csv_de_segmentos_lleva_todas_las_columnas():
    from core.exports import COLUMNAS_SEGMENTOS_BASICAS, COLUMNAS_SEGMENTOS_DETALLE, csv_bytes, tabla_segmentos

    cabecera = csv_bytes(tabla_segmentos(_estimaciones_reales(), detalle=True)).decode().splitlines()[0]
    for col in list(COLUMNAS_SEGMENTOS_BASICAS) + list(COLUMNAS_SEGMENTOS_DETALLE):
        assert col in cabecera, col
