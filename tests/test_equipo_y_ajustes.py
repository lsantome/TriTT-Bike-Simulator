"""Criterios 18 (masa única), 19 (tooltips), 22 (ETRTO) y 23 (presión y prendas)."""
import math

import pytest

from core import CATEGORIES, PARAM_SPECS, REQUIRED_PARAMS, Params, simulate_track
from core.atmosphere import PRESION_MAX, PRESION_MIN, pressure_factor
from core.params import ParamError, validate_params
from core.synthetic import demo_track, straight_track
from core.wheels import (DEFAULT_ETRTO, ETRTO_MANUAL, circumference_mm, etrto_codes,
                         label_for, parse_etrto, radius_m)

P = Params(masa_total=90.0)


# --------------------------------------------------------------------------- criterio 18
def test_c18_no_existen_campos_separados_de_masa():
    claves = {s.key for s in PARAM_SPECS}
    assert "masa_total" in claves
    assert "masa_ciclista" not in claves and "masa_equipo" not in claves
    assert REQUIRED_PARAMS == ("masa_total",)
    assert not hasattr(Params(), "masa_ciclista")


def test_c18_el_modelo_solo_depende_de_la_suma():
    """La razón de colapsar los dos campos: solo la suma entra en la física.

    **La versión anterior de este test no demostraba nada**: comparaba `masa_total=70.0+20.0`
    con `masa_total=90.0`, y Python suma esos literales *antes* de la llamada, así que afirmaba
    `f(90) == f(90)`. Lo detectó la revisión del 6-oct-2026.

    Con una sola masa en el modelo, la propiedad «no depende del reparto» no se puede comprobar
    ejecutando: no hay reparto que variar. Lo que sí se puede garantizar es que **no exista otra
    magnitud de masa**, que es la forma estructural de la misma propiedad, y que la suma sí
    importe. Un futuro `masa_ciclista` rompería la suite por el primero de los dos bloques.
    """
    import re
    from pathlib import Path

    # (a) en el modelo no hay más masa que la total
    campos = [c for c in Params().__dataclass_fields__ if "masa" in c or "peso" in c]
    assert campos == ["masa_total"], campos

    # (b) ni el núcleo usa ninguna otra: un `.masa_algo` o un `.peso` haría fallar esto
    raiz = Path(__file__).resolve().parents[1] / "core"
    patron = re.compile(r"\.masa_(?!total\b)\w+|\.peso\b")
    culpables = [f"{f.name}:{n}" for f in sorted(raiz.glob("*.py"))
                 for n, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
                 if patron.search(linea)]
    assert not culpables, f"el núcleo usa otra magnitud de masa: {culpables}"

    # (c) y la suma sí cambia el resultado, incluso por medio kilo
    tr = demo_track()
    t = simulate_track(tr, P).tiempo_s
    assert simulate_track(tr, P.con(masa_total=100.0)).tiempo_s > t
    assert simulate_track(tr, P.con(masa_total=89.5)).tiempo_s != pytest.approx(t)


# --------------------------------------------------------------------------- criterio 19
def test_c19_todos_los_parametros_tienen_ayuda():
    """Un parámetro nuevo sin tooltip hace fallar la suite: eso es lo que pide el criterio."""
    sin_ayuda = [s.key for s in PARAM_SPECS if not (s.help or "").strip()]
    assert not sin_ayuda, f"parámetros sin texto de ayuda: {sin_ayuda}"


def test_c19_la_ayuda_explica_algo_no_repite_la_etiqueta():
    for s in PARAM_SPECS:
        ayuda = s.help.strip()
        assert len(ayuda) >= 40, f"{s.key}: ayuda demasiado corta ({ayuda!r})"
        assert ayuda.lower() != s.label.lower(), f"{s.key}: la ayuda repite la etiqueta"
        assert ayuda[0] == ayuda[0].upper() and ayuda.endswith((".", ")")), f"{s.key}: {ayuda!r}"


# --------------------------------------------------------------------------- criterio 22
def test_c22_el_perimetro_sale_de_la_geometria_nominal_del_etrto():
    """perímetro = π·(llanta + 2·ancho). Para 25-622: π·672 mm."""
    assert circumference_mm("25-622") == pytest.approx(math.pi * 672.0, abs=0.01)
    assert radius_m("25-622") == pytest.approx(0.336, abs=0.0005)
    # una MTB 29x2.1 es claramente mayor; una 20" claramente menor
    assert circumference_mm("54-622") > circumference_mm("25-622") > circumference_mm("28-406")


def test_c22_todas_las_medidas_de_la_lista_son_validas_y_estan_ordenadas_por_tamano():
    for code in etrto_codes():
        ancho, llanta = parse_etrto(code)
        assert 15 <= ancho <= 110 and 200 <= llanta <= 700
        assert 1.0 < circumference_mm(code) / 1000.0 < 2.6      # entre 1 m y 2,6 m
        assert " · " in label_for(code)                          # etiqueta legible en la UI
    assert DEFAULT_ETRTO in etrto_codes()


@pytest.mark.parametrize("malo", ["", "25", "25-", "ancho-llanta", "25/9999", "5-622", "25-100"])
def test_c22_una_medida_mal_escrita_se_rechaza(malo):
    with pytest.raises(ValueError):
        parse_etrto(malo)
    with pytest.raises(ParamError):
        validate_params(P.con(etrto=malo))


def test_c22_la_medida_por_defecto_es_700x28():
    assert DEFAULT_ETRTO == "28-622"
    assert P.etrto == "28-622"
    assert P.perimetro_efectivo_mm == pytest.approx(math.pi * 678.0, abs=0.01)


def test_c22_la_opcion_manual_usa_el_perimetro_medido_y_no_el_etrto():
    """Se pide el perímetro, no el radio: es lo que se puede medir con una cinta."""
    assert ETRTO_MANUAL in [s.choices for s in PARAM_SPECS if s.key == "etrto"][0]
    manual = P.con(etrto=ETRTO_MANUAL, perimetro_mm=2105.0)
    assert manual.perimetro_efectivo_mm == pytest.approx(2105.0)
    assert manual.radio_efectivo == pytest.approx(2.105 / (2 * math.pi))
    validate_params(manual)


def test_c22_el_radio_ya_no_es_un_parametro_del_modelo():
    claves = {s.key for s in PARAM_SPECS}
    assert "radio_rueda" not in claves and not hasattr(Params(), "radio_rueda")
    assert "perimetro_mm" in claves


def test_c22_manual_sin_perimetro_y_perimetro_sin_manual_se_rechazan():
    with pytest.raises(ParamError):
        validate_params(P.con(etrto=ETRTO_MANUAL))              # falta el perímetro
    with pytest.raises(ParamError):
        validate_params(P.con(perimetro_mm=2100.0))             # perímetro sin elegir «manual»
    with pytest.raises(ParamError):
        P.con(etrto=ETRTO_MANUAL).perimetro_efectivo_mm         # la propiedad también protesta


def test_c22_el_tamano_de_rueda_apenas_mueve_el_tiempo():
    """Lo que se le dijo al usuario: solo entra en la inercia de rotación. Si algún día esto
    falla, es que el radio ha empezado a afectar a algo más y hay que revisarlo."""
    tr = demo_track()
    t_pequena = simulate_track(tr, P.con(etrto="25-451")).tiempo_s
    t_grande = simulate_track(tr, P.con(etrto="57-622")).tiempo_s
    assert abs(t_grande - t_pequena) / t_pequena < 0.001        # < 0,1 %


# --------------------------------------------------------------------------- criterio 23
def test_c23_los_valores_por_defecto_no_cambian_el_resultado():
    """Presión = referencia: el modelo se comporta como en la versión anterior."""
    assert P.presion_neumaticos == P.presion_referencia
    assert P.crr_ref_por_superficie() == pytest.approx((P.crr_liso, P.crr_normal, P.crr_rugoso))


def test_c23_mas_presion_baja_el_crr_y_menos_lo_sube():
    baja = P.con(presion_neumaticos=5.0).crr_ref_por_superficie()
    alta = P.con(presion_neumaticos=9.0).crr_ref_por_superficie()
    base = P.crr_ref_por_superficie()
    for b, n, a in zip(baja, base, alta):
        assert b > n > a
    # el efecto es mayor en liso que en rugoso (exponente más alto)
    assert baja[0] / base[0] > baja[2] / base[2]


def test_c23_la_presion_mueve_el_tiempo_en_el_sentido_esperado():
    tr = straight_track(20000, 10)
    t_baja = simulate_track(tr, P.con(presion_neumaticos=4.0)).tiempo_s
    t_alta = simulate_track(tr, P.con(presion_neumaticos=9.0)).tiempo_s
    assert t_baja > t_alta


def test_c23_exponente_cero_desactiva_el_efecto_de_la_presion():
    p = P.con(crr_exp_liso=0.0, crr_exp_normal=0.0, crr_exp_rugoso=0.0, presion_neumaticos=4.0)
    assert p.crr_ref_por_superficie() == pytest.approx((P.crr_liso, P.crr_normal, P.crr_rugoso))


def test_c23_pressure_factor_es_coherente_y_valida_su_entrada():
    assert pressure_factor(7.0, 7.0, 0.45) == pytest.approx(1.0)
    assert pressure_factor(3.5, 7.0, 1.0) == pytest.approx(2.0)
    for fuera in (PRESION_MIN - 0.1, PRESION_MAX + 0.1, 0.0, -1.0):
        with pytest.raises(ValueError):
            pressure_factor(fuera, 7.0, 0.45)


def test_c23_las_prendas_ya_no_son_un_parametro_del_modelo():
    """Decisión del usuario: lo que lleve puesto ya va dentro del CdA que introduce."""
    claves = {s.key for s in PARAM_SPECS}
    assert "prendas" not in claves and not hasattr(Params(), "prendas")
    for ido in ("delta_cda_prendas", "cda_con_prendas"):
        assert not hasattr(Params(), ido)
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("core.clothing")


def test_c23_los_valores_por_defecto_de_presion_no_cambian_el_resultado():
    assert P.presion_neumaticos == P.presion_referencia
    assert P.crr_ref_por_superficie() == pytest.approx((P.crr_liso, P.crr_normal, P.crr_rugoso))


# --------------------------------------------------------------------------- categorías
def test_las_tres_categorias_y_meteorologia_con_terreno_juntas():
    """Decisión del usuario: meteorología y terreno en un solo menú «Variables externas»."""
    assert CATEGORIES == ("Ciclista", "Equipamiento", "Variables externas")
    externas = [s.key for s in PARAM_SPECS if s.category == "Variables externas"]
    for esperada in ("temperatura", "humedad", "superficie", "presion_neumaticos",
                     "velocidad_maxima", "ventana_elevacion"):
        assert esperada in externas, esperada
    assert {s.category for s in PARAM_SPECS} == set(CATEGORIES)
