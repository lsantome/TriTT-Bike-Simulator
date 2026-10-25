"""Criterio 31: el estimador de CdA como módulo independiente.

El test que de verdad importa es `test_c31_la_particion_de_parametros_es_la_real`: comprueba
**midiendo** que los parámetros que el módulo no muestra no cambian la estimación y que los que
muestra sí. Así la lista de `PARAMS_ESTIMADOR` no se mantiene a mano ni se degrada: si alguien
añade un parámetro al modelo del estimador y se olvida de incluirlo, la suite falla.
"""
from pathlib import Path

import pytest

from core import PARAM_SPECS, Params
from core.cda_estimator import estimate_cda, find_paired_segments
from core.params import (MODULOS, PARAMS_ESTIMADOR, ParamError, specs_by_category,
                         specs_for_module)
from core.validation import read_fit

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PARAMS = Params(masa_total=90.0)

#: Un valor claramente distinto del de por defecto para cada parámetro, con el que probar si mueve
#: la estimación. No vale cualquier valor: tiene que estar dentro del rango válido.
ALTERNATIVOS = {
    "masa_total": 110.0, "eficiencia": 0.94, "etrto": "23-622", "perimetro_mm": None,
    "inercia_ruedas": 0.22, "temperatura": 32.0, "humedad": 20.0,
    "presion_nivel_mar": 980.0, "densidad_manual": 1.05, "superficie": "rugoso",
    "presion_neumaticos": 5.0, "presion_referencia": 6.0,
    "crr_liso": 0.0028, "crr_normal": 0.0060, "crr_rugoso": 0.0090,
    "crr_exp_liso": 0.30, "crr_exp_normal": 0.50, "crr_exp_rugoso": 0.25,
    # ojo: el alternativo tiene que ser DISTINTO del valor por defecto (crr1_liso es 2e-05)
    "crr1_liso": 0.00015, "crr1_normal": 0.00003, "crr1_rugoso": 0.00004,
    "ventana_elevacion": 400.0, "razon_velocidad_par": 1.10,
    # los del simulador
    "p_subida": 320.0, "p_llano": 300.0, "p_descenso": 90.0, "ftp": 290.0,
    "umbral_pendiente": 4.0, "anchura_banda_pendiente": 2.0, "velocidad_inicial": 25.0,
    "cda": 0.40, "delta_cda": 0.10, "umbral_posicion": 28.0,
    "anchura_transicion_cda": 3.0, "velocidad_maxima": 70.0, "limite_curvatura": False,
    "aceleracion_lateral": 5.0, "deceleracion_frenada": 6.0,
    "ventana_trazado": 90.0, "paso_remuestreo": 40.0,
}


@pytest.fixture(scope="module")
def salida():
    return read_fit((FIXTURES / "recorrido2_30mar2025.fit").read_bytes(), "30mar")


# --------------------------------------------------------------------------- la partición
def test_c31_el_catalogo_de_alternativos_cubre_todos_los_parametros():
    """Si se añade un parámetro al modelo y no se le da alternativo, el test siguiente no lo probaría."""
    faltan = [s.key for s in PARAM_SPECS if s.key not in ALTERNATIVOS]
    assert not faltan, f"parámetros sin valor alternativo con el que probarlos: {faltan}"


#: Contexto en el que cada parámetro está **vivo**, cuando el de por defecto no basta.
#:
#: Lo descubrió este test al fallar la primera vez, y vale la pena dejarlo escrito: un Crr de
#: superficie solo actúa si esa superficie es la elegida, y un exponente de presión solo actúa si
#: la presión difiere de la de referencia (con las dos iguales, la razón es 1 y el exponente da
#: igual). No significa que no pertenezcan al estimador: significa que hay que probarlos donde
#: tienen algo que hacer.
CONTEXTOS = {
    sup_clave: dict(superficie=sup, presion_neumaticos=5.0)
    for sup in ("liso", "normal", "rugoso")
    for sup_clave in (f"crr_{sup}", f"crr_exp_{sup}", f"crr1_{sup}")
}
CONTEXTOS["presion_referencia"] = dict(presion_neumaticos=5.0)


def _cda(salida, **cambios):
    return estimate_cda(salida, PARAMS.con(**cambios), 20.0, 25.0).cda


#: Parámetros del estimador que **no** actúan sobre un segmento suelto, sino sobre la búsqueda o
#: el emparejamiento, y por tanto hay que medirlos con la función que gobiernan.
SONDAS_ALTERNATIVAS = {
    "razon_velocidad_par": lambda salida, **cambios: tuple(
        round(par.cda, 9) for par in find_paired_segments(salida, PARAMS.con(**cambios))),
}


def test_c31_la_particion_de_parametros_es_la_real(salida):
    """Medido, no declarado: los de fuera no mueven la estimación y los de dentro sí.

    Cada parámetro se prueba en un contexto donde pueda actuar (ver `CONTEXTOS`) y con la función
    que de verdad gobierna (ver `SONDAS_ALTERNATIVAS`: el umbral del par imposible no cambia el
    CdA de un segmento, cambia qué pares se aceptan). `perimetro_mm` va aparte porque solo cuenta
    con la rueda en «manual».
    """
    dentro = set(PARAMS_ESTIMADOR) - {"perimetro_mm"} - set(SONDAS_ALTERNATIVAS)
    fuera = {s.key for s in PARAM_SPECS} - set(PARAMS_ESTIMADOR)

    sin_efecto = []
    for clave in sorted(dentro):
        ctx = CONTEXTOS.get(clave, {})
        if _cda(salida, **ctx, **{clave: ALTERNATIVOS[clave]}) == pytest.approx(
                _cda(salida, **ctx), rel=1e-9):
            sin_efecto.append(clave)
    for clave, sonda in sorted(SONDAS_ALTERNATIVAS.items()):
        if sonda(salida, **{clave: ALTERNATIVOS[clave]}) == sonda(salida):
            sin_efecto.append(clave)
    assert not sin_efecto, (
        f"estos parámetros se piden en el estimador pero no cambian nada: {sin_efecto}")

    # los de fuera no deben mover nada en ningún contexto de los que usamos arriba
    con_efecto = []
    for clave in sorted(fuera):
        for ctx in ({}, dict(superficie="rugoso", presion_neumaticos=5.0)):
            if _cda(salida, **ctx, **{clave: ALTERNATIVOS[clave]}) != pytest.approx(
                    _cda(salida, **ctx), rel=1e-9):
                con_efecto.append(clave)
                break
    assert not con_efecto, (
        f"estos parámetros cambian la estimación pero el estimador no los pide: {con_efecto}")


def test_c31_el_perimetro_manual_si_mueve_la_estimacion(salida):
    """Aparte porque solo tiene efecto con la rueda en «manual» (criterio 22)."""
    from core.wheels import ETRTO_MANUAL

    base = estimate_cda(salida, PARAMS.con(etrto=ETRTO_MANUAL, perimetro_mm=2100.0),
                        20.0, 25.0).cda
    otro = estimate_cda(salida, PARAMS.con(etrto=ETRTO_MANUAL, perimetro_mm=2400.0),
                        20.0, 25.0).cda
    assert otro != pytest.approx(base, rel=1e-9)


def test_c31_el_cda_no_es_una_entrada_del_estimador():
    """La trampa conceptual que el módulo evita: pedir como entrada lo que va a calcular."""
    claves = {s.key for s in specs_for_module("estimador")}
    assert "cda" not in claves and "delta_cda" not in claves


def test_c31_el_estimador_pide_bastantes_menos_parametros_que_el_simulador():
    est, sim = specs_for_module("estimador"), specs_for_module("simulador")
    assert sim == PARAM_SPECS                      # el simulador los pide todos
    assert len(est) == len(PARAMS_ESTIMADOR)
    assert len(est) < len(sim) / 1.5               # quitar entradas es parte del diseño
    # y ninguno sobra ni falta respecto a la lista declarada
    assert {s.key for s in est} == set(PARAMS_ESTIMADOR)


def test_c31_las_claves_declaradas_existen_de_verdad():
    desconocidas = [k for k in PARAMS_ESTIMADOR if k not in {s.key for s in PARAM_SPECS}]
    assert not desconocidas, desconocidas


def test_c31_specs_by_category_respeta_el_modulo():
    todas = specs_by_category("Ciclista", modulo="simulador")
    pocas = specs_by_category("Ciclista", modulo="estimador")
    assert len(pocas) < len(todas)
    assert [s.key for s in pocas] == ["masa_total"]      # en el estimador solo hace falta la masa
    # el defecto sigue siendo el simulador, para no cambiar el comportamiento de quien no lo pase
    assert specs_by_category("Ciclista") == todas


def test_c31_un_modulo_inventado_se_rechaza():
    with pytest.raises(ParamError):
        specs_for_module("inventado")
    assert MODULOS == ("estimador", "simulador")


# --------------------------------------------------------------------------- el módulo funciona solo
def test_c31_el_estimador_funciona_sin_tocar_ningun_parametro_de_simulacion(salida):
    """Un `.fit` y la masa: con eso el módulo tiene que dar un número utilizable."""
    pares = find_paired_segments(salida, Params(masa_total=90.0), maximo=8)
    assert pares, "el módulo no encuentra pares con solo la masa puesta"
    from core.cda_estimator import combine_pairs

    cda, inc = combine_pairs(pares)
    assert 0.20 < cda < 0.35 and 0.0 < inc < 0.03


def test_c31_los_alternativos_son_distintos_de_los_valores_por_defecto():
    """Un alternativo igual al defecto haría pasar el test de la partición por la razón errónea.

    Pasó al escribirlo: `crr1_liso` llevaba 0,00002, que es justo el valor por defecto, y el
    parámetro parecía no tener efecto.
    """
    base = Params()
    iguales = [s.key for s in PARAM_SPECS
               if ALTERNATIVOS[s.key] == getattr(base, s.key) and s.key != "perimetro_mm"]
    assert not iguales, f"alternativos que coinciden con el valor por defecto: {iguales}"


# --------------------------------------------------------------------------- la laguna del test
#: Las tres cosas que producen un CdA dentro del módulo del estimador. La revisión del
#: 6-oct-2026 encontró que el test de la partición solo recorría la primera, y que la tercera
#: dependía de ocho parámetros que el módulo no muestra (`umbral_posicion` movía el CdA un 10 %).
def _cda_por_pares(salida, p):
    from core.cda_estimator import combine_pairs, find_paired_segments
    return combine_pairs(find_paired_segments(salida, p, maximo=4))[0]


def _cda_por_coherencia(salida, p):
    from core.coherence import check_coherence
    return check_coherence(salida, p).cda_calibrado


def _cda_ruta_completa(salida, p):
    from core.cda_estimator import search_summary
    return search_summary(salida, p, []).cda_ruta_completa


@pytest.mark.parametrize("via", [_cda_por_pares, _cda_por_coherencia, _cda_ruta_completa],
                         ids=["pares", "coherencia", "ruta_completa"])
def test_c31_ningun_camino_del_modulo_depende_de_parametros_ocultos(salida, via):
    """No basta con que `estimate_cda` esté limpio: **todo** lo que el módulo enseña debe estarlo.

    Si no, se gobierna en silencio un número que el usuario ve con parámetros que no puede tocar,
    que es justo la circularidad que el criterio 31 cierra para el `cda`.
    """
    base = via(salida, PARAMS)
    fuera = sorted({s.key for s in PARAM_SPECS} - set(PARAMS_ESTIMADOR))
    culpables = []
    for clave in fuera:
        if via(salida, PARAMS.con(**{clave: ALTERNATIVOS[clave]})) != pytest.approx(base, rel=1e-9):
            culpables.append(clave)
    assert not culpables, (
        f"este camino del módulo depende de parámetros que no se piden: {culpables}")
