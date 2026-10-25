"""Criterios 10 (parámetros), 11 (salidas) y 12 (sensibilidad)."""
import numpy as np
import pytest

from core import (CATEGORIES, PARAM_SPECS, ParamError, Params, simulate_track,
                  specs_by_category, table_by_km, validate_params)
from core.i18n import t
from core.metrics import normalized_power
from core.sensitivity import sensitivity
from core.synthetic import demo_track, rolling_track, straight_track


# ---------------------------------------------------------------- criterio 10
def test_c10_todos_los_campos_tienen_spec_y_categoria():
    campos = set(Params.__dataclass_fields__) - {"tramos_superficie"}
    assert campos == {s.key for s in PARAM_SPECS}
    assert {s.category for s in PARAM_SPECS} == set(CATEGORIES)
    for cat in CATEGORIES:
        assert specs_by_category(cat), cat


def test_c10_defaults_realistas_a_coruna():
    p = Params()
    assert (p.temperatura, p.humedad, p.presion_nivel_mar) == (15.0, 75.0, 1013.25)
    assert p.velocidad_maxima == 100.0 and p.limite_curvatura is True
    assert (p.p_subida, p.p_llano, p.p_descenso) == (220.0, 200.0, 0.0)
    assert p.delta_cda == 0.25 and p.umbral_posicion == 20.0
    assert p.umbral_pendiente == 2.0 and p.superficie == "normal"
    assert p.crr_liso == 0.0035 and p.crr_normal == 0.0045 and p.crr_rugoso == 0.0070
    assert p.eficiencia == 0.975 and p.aceleracion_lateral == 3.0


def test_c10_cada_spec_tiene_rango_y_default_dentro_del_rango():
    for s in PARAM_SPECS:
        assert s.label and s.category in CATEGORIES
        if s.kind in ("float", "optional_float"):
            assert s.minimum is not None and s.maximum is not None
            if s.default is not None:
                assert s.minimum <= s.default <= s.maximum, s.key
    validate_params(Params())


@pytest.mark.parametrize("campo,valor", [
    ("masa_total", 10.0), ("masa_total", 500.0), ("cda", 0.0), ("eficiencia", 1.2),
    ("temperatura", 90.0), ("humedad", 120.0), ("velocidad_maxima", 5.0),
    ("superficie", "arena"), ("limite_curvatura", "si"), ("p_llano", -10.0),
    ("aceleracion_lateral", 0.0), ("masa_total", float("nan")),
])
def test_c10_rangos_validados(campo, valor):
    with pytest.raises(ParamError):
        validate_params(Params(**{campo: valor}))


def test_c10_validacion_cruzada_bandas_y_tramos():
    with pytest.raises(ParamError):
        validate_params(Params(umbral_pendiente=1.0, anchura_banda_pendiente=3.0))
    with pytest.raises(ParamError):
        validate_params(Params(tramos_superficie=((5.0, 2.0, "rugoso"),)))
    with pytest.raises(ParamError):
        validate_params(Params(tramos_superficie=((0.0, 2.0, "barro"),)))
    validate_params(Params(tramos_superficie=((0.0, 2.0, "rugoso"),)))


def test_tramos_de_superficie_cambian_el_crr_solo_en_su_rango():
    tr = straight_track(10000, 10)
    base = simulate_track(tr, Params())
    mixto = simulate_track(tr, Params(tramos_superficie=((4.0, 6.0, "rugoso"),)))
    mid = base.s_mid_km
    en = (mid >= 4) & (mid < 6)
    assert np.all(mixto.crr_seg[en] > base.crr_seg[en])
    antes = mid < 3.9      # antes del tramo rugoso nada cambia (la causalidad se respeta)
    assert np.allclose(mixto.crr_seg[antes], base.crr_seg[antes])
    assert mixto.tiempo_s > base.tiempo_s


# ---------------------------------------------------------------- criterio 11
def test_c11_salidas_completas():
    p = Params(ftp=250.0)
    res = simulate_track(demo_track(), p)
    assert res.tiempo_s > 0 and 20 < res.velocidad_media_kmh < 50
    assert res.np_w > 0 and res.vi is not None and res.if_ == pytest.approx(res.np_w / 250.0)
    assert res.vi == pytest.approx(res.np_w / res.potencia_media_w)
    df = res.to_frame()
    for col in ("km", "pendiente_%", "velocidad_kmh", "potencia_w", "cda_efectivo"):
        assert col in df.columns
    assert len(df) == len(res.dt)
    tab = table_by_km(res, 1.0)
    assert len(tab) == int(np.ceil(res.distancia_km))
    assert tab["tiempo_s"].sum() == pytest.approx(res.tiempo_s, rel=1e-9)


def test_c11_sin_ftp_if_es_none():
    assert simulate_track(demo_track(), Params()).if_ is None


def test_np_potencia_constante_igual_a_media():
    dt = np.full(500, 2.0)
    assert normalized_power(dt, np.full(500, 200.0)) == pytest.approx(200.0)


def test_np_mayor_que_media_con_variabilidad():
    dt = np.full(600, 2.0)
    p = np.tile(np.array([100.0] * 30 + [300.0] * 30), 10)
    assert normalized_power(dt, p) > np.average(p, weights=dt)


# ---------------------------------------------------------------- criterio 12
def test_c12_informe_de_sensibilidad():
    rows = sensitivity(rolling_track(15000, 10, amp=20.0, period_m=3000.0), Params())
    por = {r["parametro"]: r for r in rows}

    # El criterio pide el efecto de CADA parámetro: ninguno puede faltar. Antes se omitían en
    # silencio los no numéricos, los marcados sin sensibilidad y los Crr de superficies sin usar,
    # y este test construía la lista esperada con los mismos filtros, así que certificaba la
    # omisión en vez de vigilar la cobertura.
    assert {s.key for s in PARAM_SPECS} == set(por), (
        f"parámetros ausentes del informe: {sorted({s.key for s in PARAM_SPECS} - set(por))}")

    # los que no se pueden perturbar salen igual, con el motivo escrito
    assert "crr_normal" in por and por["crr_normal"]["dt_mas_%"] is not None
    assert por["crr_liso"]["dt_mas_%"] is None                 # superficie no usada en esta ruta
    assert "liso" in por["crr_liso"]["nota"]
    # El motivo tiene que ser **el correcto**, no solo no vacío: comprobar `assert por[k]["nota"]`
    # dejaba pasar un motivo equivocado, y de hecho lo hubo hasta octubre de 2026 («No es un
    # número» para `ftp`, `densidad_manual` y `perimetro_mm`, que son numéricos y opcionales).
    # Se compara contra las cadenas de `i18n`, no contra literales escritos aquí.
    assert por["etrto"]["nota"] == t("sens_no_numerico")        # categórico: no se puede ±10 %
    assert por["superficie"]["nota"] == t("sens_no_numerico")
    assert por["limite_curvatura"]["nota"] == t("sens_no_numerico")
    for clave in ("ftp", "densidad_manual", "perimetro_mm"):
        assert por[clave]["nota"] == t("sens_sin_valor"), clave  # opcionales y vacíos en esta ruta
    assert t("sens_no_numerico") != t("sens_sin_valor") != t("sens_efecto_nulo")
    for r in rows:
        if r["valor_base"] not in (0, None) and r["dt_mas_%"] is None:
            assert r["nota"], f"{r['parametro']} excluido sin decir por qué"
        if r["dt_mas_%"] is not None:
            assert r["dt_menos_%"] is not None
        # la sugerencia solo aparece sobre filas medidas
        if r["dt_mas_%"] is None and r["dt_menos_%"] is None:
            assert r["sugerencia"] == "", f"{r['parametro']}: sugerencia sobre una fila sin medir"
    # signos físicos esperables
    assert por["cda"]["dt_mas_%"] > 0 > por["cda"]["dt_menos_%"]
    assert por["p_llano"]["dt_mas_%"] < 0 < por["p_llano"]["dt_menos_%"]
    assert por["masa_total"]["dt_mas_%"] > 0
    # parámetro con valor 0 -> no aplicable, documentado
    assert "no aplicable" in por["p_descenso"]["nota"]
    # ordenado por efecto y con marca de relevancia
    efectos = [r["efecto_max_%"] for r in rows]
    assert efectos == sorted(efectos, reverse=True)
    assert por["cda"]["relevante"] and por["p_llano"]["relevante"]


def test_c12_los_opcionales_con_valor_se_miden_en_vez_de_excusarse():
    """Los tres `optional_float` del modelo salían excluidos con el motivo «No es un número», que
    es falso. Con valor se miden, y lo medido desmiente la excusa: la densidad manual es uno de
    los parámetros con más efecto de todo el informe."""
    p = Params(ftp=250.0, densidad_manual=1.20, etrto="manual", perimetro_mm=2130.0)
    por = {r["parametro"]: r for r in sensitivity(rolling_track(15000, 10, amp=20.0,
                                                                period_m=3000.0), p)}
    assert por["densidad_manual"]["dt_mas_%"] is not None
    assert por["densidad_manual"]["efecto_max_%"] > 2.0        # medido: 2,95 %
    assert por["densidad_manual"]["relevante"]
    assert por["perimetro_mm"]["dt_mas_%"] is not None
    assert por["perimetro_mm"]["efecto_max_%"] < 0.01          # medido: 0,00018 %
    # el FTP sí es cierto que no entra en el tiempo, y ahora eso está **medido**
    assert por["ftp"]["dt_mas_%"] == 0.0 and por["ftp"]["dt_menos_%"] == 0.0
    assert por["ftp"]["nota"] == t("sens_efecto_nulo")


def test_c12_eficiencia_se_recorta_a_su_rango_y_se_informa():
    """η = 0,975: ±10 % se sale del rango válido [0,90; 1,00] por ambos lados; se recorta y se informa."""
    rows = sensitivity(straight_track(8000, 10), Params())
    r = {x["parametro"]: x for x in rows}["eficiencia"]
    assert r["valor_menos"] == pytest.approx(0.90) and r["valor_mas"] == pytest.approx(1.0)
    assert r["variacion_menos_%"] == pytest.approx(-7.69, abs=0.01)
    assert r["variacion_mas_%"] == pytest.approx(2.56, abs=0.01)
    assert r["dt_menos_%"] > 0 > r["dt_mas_%"]


def test_c12_hallazgo_ventana_de_elevacion_vs_ruido():
    """Documenta el hallazgo del criterio 8: con ruido i.i.d. de σ = 2 m una ventana de 100 m
    no basta; la ventana por defecto (150 m) y la de 200 m dejan el error por debajo de 1 %."""
    assert Params().ventana_elevacion == 150.0
    p100, p200 = Params(ventana_elevacion=100.0), Params()
    limpio = rolling_track(30000, 10, amp=20.0, period_m=5000.0)
    ruidoso = rolling_track(30000, 10, amp=20.0, period_m=5000.0, noise_m=2.0, seed=3)
    e = {}
    for nombre, p in (("100", p100), ("150", p200)):
        t0 = simulate_track(limpio, p).tiempo_s
        e[nombre] = abs(simulate_track(ruidoso, p).tiempo_s - t0) / t0 * 100
    assert e["100"] > 1.5 and e["150"] < 1.0, e
