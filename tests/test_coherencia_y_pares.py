"""Criterios 28 (pares imposibles), 29 (las dos bandas) y 30 (actividad incoherente).

Todo se mide contra las **cinco** actividades reales del recorrido 2, reducidas a 1 de cada 5
registros (ver `tests/fixtures/README.md`). Tres son coherentes y dos no, y eso es justamente lo
que hace útil el fichero: un cambio que relaje la detección hará pasar por buenas a las dos malas,
y un cambio que la endurezca tumbará a alguna de las tres buenas.
"""
from pathlib import Path

import numpy as np
import pytest

from core import Params
from core.cda_estimator import (MAX_RAZON_VELOCIDAD_PAR, ParRechazado, combine_pairs,
                                find_paired_segments, razon_velocidades)
from core.coherence import (CDA_PLAUSIBLE, UMBRAL_ERROR_BAJADA_PCT, UMBRAL_ERROR_LLANO_PCT,
                            check_coherence)
from core.exports import COLUMNAS_COHERENCIA, csv_bytes, tabla_coherencia
from core.uncertainty import DIA_PCT, MODELO_PCT, PEOR_ERROR_DIA_PCT
from core.validation import calibrate_cda, read_fit, replay

FIXTURES = Path(__file__).resolve().parent / "fixtures"
COHERENTES = ("recorrido2_30mar2025", "recorrido2_06abr2025", "recorrido2_19abr2026")
INCOHERENTES = ("recorrido2_04may2025", "recorrido2_08jun2025")
TODAS = COHERENTES + INCOHERENTES

#: Masa total declarada por el usuario (ciclista + bici + equipo).
PARAMS = Params(masa_total=90.0)


@pytest.fixture(scope="module")
def salidas():
    out = {}
    for nombre in TODAS:
        ruta = FIXTURES / f"{nombre}.fit"
        assert ruta.exists(), f"falta el fixture {ruta}"
        out[nombre] = read_fit(ruta.read_bytes(), nombre)
    return out


@pytest.fixture(scope="module")
def pares(salidas):
    """Pares de ida y vuelta de cada salida, con los rechazos aparte."""
    out = {}
    for nombre, ride in salidas.items():
        rechazados: list = []
        out[nombre] = (find_paired_segments(ride, PARAMS, maximo=8, rechazados=rechazados),
                       rechazados)
    return out


@pytest.fixture(scope="module")
def informes(salidas):
    return {n: check_coherence(r, PARAMS) for n, r in salidas.items()}


# --------------------------------------------------------------------------- criterio 28
def test_c28_la_razon_de_velocidades_es_simetrica_y_mayor_que_uno(pares):
    for _nombre, (lista, _r) in pares.items():
        for par in lista:
            r = razon_velocidades(par.ida, par.vuelta)
            assert r >= 1.0
            assert r == pytest.approx(razon_velocidades(par.vuelta, par.ida))


def test_c28_los_pares_imposibles_de_la_salida_del_4_de_mayo_se_descartan(pares):
    """Esa salida emparejaba una bajada rápida con una subida lenta: no es la misma carretera."""
    _lista, rechazados = pares["recorrido2_04may2025"]
    assert rechazados, "el filtro no ha descartado ningún par en la salida que los tiene"
    for r in rechazados:
        assert isinstance(r, ParRechazado)
        assert r.razon_velocidades >= MAX_RAZON_VELOCIDAD_PAR
        # el motivo trae las dos velocidades y el umbral, para que se pueda juzgar
        assert f"{MAX_RAZON_VELOCIDAD_PAR:.2f}" in r.motivo
        assert f"{r.razon_velocidades:.2f}" in r.motivo
    # el peor caso medido empareja ~56 km/h con ~17 km/h
    assert max(r.razon_velocidades for r in rechazados) > 3.0


def test_c28_el_filtro_no_toca_las_salidas_coherentes(pares):
    """Un filtro que también recortara las salidas buenas estaría tirando datos legítimos."""
    for nombre in COHERENTES + ("recorrido2_08jun2025",):
        lista, rechazados = pares[nombre]
        assert rechazados == [], f"{nombre}: descartes inesperados {[r.motivo for r in rechazados]}"
        assert lista, nombre


def test_c28_el_umbral_tiene_margen_por_los_dos_lados(pares):
    """Entre el par legítimo más desigual y el imposible más suave hay un hueco, y 1,5 cae dentro."""
    legitimos = [razon_velocidades(p.ida, p.vuelta)
                 for nombre, (lista, _r) in pares.items() for p in lista]
    rechazados = [r.razon_velocidades for _n, (_l, rs) in pares.items() for r in rs]
    assert max(legitimos) < MAX_RAZON_VELOCIDAD_PAR < min(rechazados)
    assert max(legitimos) < 1.45          # medido: 1,42 en los datos completos
    assert min(rechazados) > 2.0          # medido: 2,13 el más suave de los imposibles


def _dispersion_pct(valores):
    v = np.array(list(valores), dtype=float)
    return float(v.std(ddof=1) / v.mean() * 100.0)


def test_c28_descartar_los_imposibles_acerca_el_cda_al_de_las_demas(salidas, pares):
    """La prueba de que el filtro mejora el dato y no solo lo cambia: baja la dispersión.

    Se compara contra el comportamiento anterior, desactivando el filtro con un umbral infinito,
    en vez de contra una cifra fija: el valor absoluto depende de la reducción de los fixtures,
    pero el signo de la mejora no.
    """
    con = {n: combine_pairs(lista)[0] for n, (lista, _r) in pares.items()}
    sin = {n: combine_pairs(find_paired_segments(
        r, PARAMS, maximo=8, max_razon_velocidad=float("inf")))[0] for n, r in salidas.items()}

    for n, c in con.items():
        assert CDA_PLAUSIBLE[0] < c < CDA_PLAUSIBLE[1], f"{n}: CdA de pares implausible {c:.4f}"
    assert _dispersion_pct(con.values()) < _dispersion_pct(sin.values())
    # la salida afectada sube hacia el grupo; las demás no se mueven
    assert con["recorrido2_04may2025"] > sin["recorrido2_04may2025"]
    for n in COHERENTES + ("recorrido2_08jun2025",):
        assert con[n] == pytest.approx(sin[n])


def test_c28_no_se_filtra_por_discrepancia_de_cda(pares):
    """Filtrar por discrepancia seleccionaría por viento bajo: la trampa del criterio 25.

    Así que tiene que sobrevivir algún par con mucha diferencia entre ida y vuelta, siempre que
    las dos pasadas vayan a velocidades parecidas.
    """
    peor = max(p.discrepancia for _n, (lista, _r) in pares.items() for p in lista)
    # medido: el par legítimo más discrepante llega a 0,101. Pedir solo >0,04 dejaría pasar
    # inadvertido un filtro a 0,05, que es justo el que no queremos.
    assert peor > 0.09, ("ningún par con discrepancia alta ha sobrevivido: el filtro está "
                         f"seleccionando por viento bajo (máximo {peor:.4f})")


# --------------------------------------------------------------------------- criterio 29
def _validacion_cruzada(salidas, conjunto):
    errores = []
    for fuera in conjunto:
        cda = calibrate_cda([salidas[n] for n in conjunto if n != fuera], PARAMS)
        errores.append(replay(salidas[fuera], PARAMS.con(cda=cda)).error_tiempo_pct)
    return np.abs(np.array(errores))


def test_c29_la_banda_del_modelo_cubre_la_validacion_cruzada_de_las_coherentes(salidas):
    """±1,4 %: lo que vale el modelo cuando el día no se sale de lo normal."""
    e = _validacion_cruzada(salidas, COHERENTES)
    assert e.max() <= MODELO_PCT, f"errores {e.round(2)} por encima de ±{MODELO_PCT} %"
    assert e.mean() <= 1.0


def test_c29_la_banda_del_dia_cubre_el_peor_error_del_protocolo_recomendado(salidas):
    """La medida que de verdad importa: calibrar **solo con las coherentes**, como manda el
    protocolo y el criterio 30, y predecir cualquier día.

    La revisión del 6-oct-2026 encontró que el ±14 % anterior se midió con validación cruzada
    sobre las cinco, lo que mete las incoherentes *dentro* de la calibración y da un error más
    benévolo (12,8 %). Con el protocolo real el peor error sube a 14,2 % y la banda se quedaba
    corta. Este test mide el camino recomendado, no el fácil.
    """
    cda = calibrate_cda([salidas[n] for n in COHERENTES], PARAMS)
    peor = max(abs(replay(salidas[n], PARAMS.con(cda=cda)).error_tiempo_pct) for n in TODAS)
    assert peor <= DIA_PCT, (
        f"peor error {peor:.2f} % por encima de la banda ±{DIA_PCT} %: "
        "una banda que no cubre su propia peor observación no es una banda")
    assert peor >= PEOR_ERROR_DIA_PCT - 0.5          # y la constante documentada no está inflada
    # la banda del modelo NO basta aquí: por eso hacen falta las dos
    assert peor > MODELO_PCT


def test_c29_el_metodo_benevolo_da_un_numero_menor(salidas):
    """Deja constancia de por qué se cambió de método, para que nadie vuelva al anterior."""
    loo = _validacion_cruzada(salidas, TODAS).max()
    cda = calibrate_cda([salidas[n] for n in COHERENTES], PARAMS)
    protocolo = max(abs(replay(salidas[n], PARAMS.con(cda=cda)).error_tiempo_pct) for n in TODAS)
    assert loo < protocolo, (
        "si el LOO sobre las cinco dejara de ser el más benévolo, habría que repensar "
        "con qué método se mide la banda")


def test_c29_meter_las_incoherentes_empeora_la_prediccion(salidas):
    """Justifica la regla del protocolo: no promediar salidas incoherentes con las buenas."""
    buenas = _validacion_cruzada(salidas, COHERENTES)
    todas = _validacion_cruzada(salidas, TODAS)
    assert todas.mean() > 3 * buenas.mean()


# --------------------------------------------------------------------------- criterio 30
def test_c30_las_tres_coherentes_pasan_el_examen(informes):
    for nombre in COHERENTES:
        r = informes[nombre]
        assert r.coherente and r.sirve_para_calibrar, (nombre, r.avisos)
        assert not r.cda_fuera_de_rango and not r.patron_incoherente
        assert CDA_PLAUSIBLE[0] < r.cda_calibrado < CDA_PLAUSIBLE[1]


def test_c30_las_dos_incoherentes_se_detectan(informes):
    for nombre in INCOHERENTES:
        r = informes[nombre]
        assert not r.coherente, (nombre, r.cda_calibrado, r.avisos)
        assert any("No uses esta actividad para calibrar" in a for a in r.avisos)


def test_c30_hacen_falta_las_dos_reglas(informes):
    """La del 8-jun tiene el CdA dentro del rango: solo la caza el patrón por bandas.

    Si se quitara la regla del patrón, esa salida pasaría por buena y su viento acabaría en el
    parámetro. Y si se quitara la del rango, el 0,15 del 4 de mayo se presentaría como un CdA.
    """
    jun = informes["recorrido2_08jun2025"]
    assert jun.patron_incoherente and not jun.cda_fuera_de_rango
    may = informes["recorrido2_04may2025"]
    assert may.patron_incoherente and may.cda_fuera_de_rango


def test_c30_el_patron_es_el_de_llano_lento_y_bajadas_rapidas(informes):
    for nombre in INCOHERENTES:
        r = informes[nombre]
        assert r.error_llano_pct >= UMBRAL_ERROR_LLANO_PCT
        assert r.error_bajada_pct <= UMBRAL_ERROR_BAJADA_PCT
    # y en las coherentes los dos errores son pequeños y del mismo orden
    for nombre in COHERENTES:
        r = informes[nombre]
        assert abs(r.error_llano_pct) < 3.0 and abs(r.error_bajada_pct) < 3.0


def test_c30_los_umbrales_tienen_margen_por_los_dos_lados(informes):
    """Entre la peor coherente y la mejor incoherente hay un orden de magnitud."""
    peor_buena = max(informes[n].error_llano_pct for n in COHERENTES)
    mejor_mala = min(informes[n].error_llano_pct for n in INCOHERENTES)
    assert peor_buena < UMBRAL_ERROR_LLANO_PCT < mejor_mala
    assert mejor_mala > 3 * UMBRAL_ERROR_LLANO_PCT     # medido: +15,8 % frente al umbral de +5 %


def test_c30_el_informe_trae_los_numeros_que_lo_justifican(informes):
    for nombre, r in informes.items():
        assert r.nombre == nombre
        assert r.km_llano > 0 and r.km_bajada > 0 and r.km_subida > 0
        assert np.isfinite([r.error_llano_pct, r.error_bajada_pct, r.error_subida_pct]).all()
        assert r.avisos, nombre
        # el mensaje de «todo bien» sale si y solo si la actividad es coherente
        hay_ok = any("Actividad coherente" in a for a in r.avisos)
        assert hay_ok is r.coherente, (nombre, r.avisos)


def test_c30_pasar_un_cda_ya_calibrado_evita_recalcularlo(salidas, informes):
    """La interfaz puede reutilizar el CdA que ya tiene sin pagar la bisección otra vez."""
    nombre = "recorrido2_30mar2025"
    previo = informes[nombre]
    r = check_coherence(salidas[nombre], PARAMS, cda=previo.cda_calibrado)
    assert r.cda_calibrado == pytest.approx(previo.cda_calibrado)
    assert r.error_llano_pct == pytest.approx(previo.error_llano_pct)
    assert r.coherente is previo.coherente


def test_c30_los_avisos_salen_en_los_dos_idiomas(salidas):
    es = check_coherence(salidas["recorrido2_08jun2025"], PARAMS, cda=0.2162, idioma="es")
    en = check_coherence(salidas["recorrido2_08jun2025"], PARAMS, cda=0.2162, idioma="en")
    assert len(es.avisos) == len(en.avisos)
    assert any("rebufo" in a for a in es.avisos)
    assert any("drafting" in a for a in en.avisos)
    assert not any("rebufo" in a for a in en.avisos)
    assert es.error_llano_pct == pytest.approx(en.error_llano_pct)   # el número no es del idioma


def test_c30_la_tabla_de_coherencia_tiene_las_columnas_y_el_veredicto(informes):
    df = tabla_coherencia(list(informes.values()))
    assert list(df.columns) == list(COLUMNAS_COHERENCIA)
    assert len(df) == len(TODAS)
    veredicto = dict(zip(df["actividad"], df["coherente"]))
    for n in COHERENTES:
        assert veredicto[n] == "sí"
    for n in INCOHERENTES:
        assert veredicto[n] == "NO"
    assert csv_bytes(df).startswith(b"actividad,cda_calibrado,coherente")


def test_c30_la_tabla_acepta_tambien_diccionarios(informes):
    """La app guarda los informes en session_state como dicts: la tabla tiene que tragarlos."""
    df = tabla_coherencia([r.as_dict() for r in informes.values()])
    assert len(df) == len(TODAS) and "coherente" in df.columns


def test_c29_los_peores_errores_declarados_son_los_que_se_miden(salidas):
    """Los números de `core/uncertainty.py` se vuelven a medir aquí, no se creen.

    **Protocolo recomendado** (criterio 30): se calibra SOLO con salidas coherentes y se predice
    cualquier día. Medirlo de otra forma —dejando una fuera sobre las cinco, que mete las
    incoherentes dentro del conjunto de calibración— da un peor error más benévolo (12,8 %) y
    mide un flujo que el propio protocolo prohíbe. Ese fue el error del ±14 % anterior.
    """
    from core.uncertainty import (DIA_PCT, MODELO_PCT, PEOR_ERROR_DIA_PCT, PEOR_ERROR_MODELO_PCT)

    errores = {}
    for fuera in TODAS:
        dentro = [salidas[k] for k in COHERENTES if k != fuera]
        cda = calibrate_cda(dentro, PARAMS)
        errores[fuera] = abs(replay(salidas[fuera], PARAMS.con(cda=cda)).error_tiempo_pct)

    peor_modelo = max(errores[n] for n in COHERENTES)
    peor_dia = max(errores.values())

    # lo declarado tiene que parecerse a lo medido (los fixtures están reducidos: margen de 0,5)
    assert PEOR_ERROR_MODELO_PCT == pytest.approx(peor_modelo, abs=0.5), (
        f"PEOR_ERROR_MODELO_PCT dice {PEOR_ERROR_MODELO_PCT} y se mide {peor_modelo:.2f}")
    assert PEOR_ERROR_DIA_PCT == pytest.approx(peor_dia, abs=0.5), (
        f"PEOR_ERROR_DIA_PCT dice {PEOR_ERROR_DIA_PCT} y se mide {peor_dia:.2f}")
    # y las bandas cubren lo medido
    assert MODELO_PCT >= peor_modelo and DIA_PCT >= peor_dia
    # el peor caso lo pone una salida incoherente, que es justo de lo que avisa la banda del día
    assert max(errores, key=errores.get) in INCOHERENTES


def test_c25_la_banda_cubre_la_distancia_al_metodo_independiente(salidas):
    """La prueba empírica de que la incertidumbre de los pares es la correcta.

    El criterio 25 valida el estimador de pares contra la calibración por tiempo total, que es un
    método independiente. Si la banda del primero no llega a alcanzar al segundo, la banda miente.
    Con el error estándar de la media (σ/√n) no llegaba: ±0,0055 frente a una distancia de 0,0090
    en la salida del 30-mar. Con la dispersión (σ) sí.
    """
    from core.validation import calibrate_cda

    for nombre in COHERENTES:
        pares = find_paired_segments(salidas[nombre], PARAMS, maximo=8)
        cda_pares, banda = combine_pairs(pares)
        cda_tiempo = calibrate_cda([salidas[nombre]], PARAMS)
        distancia = abs(cda_pares - cda_tiempo)
        assert banda >= distancia, (
            f"{nombre}: banda ±{banda:.4f} no cubre la distancia {distancia:.4f} al método "
            f"independiente (pares {cda_pares:.4f} vs tiempo {cda_tiempo:.4f})")


def test_c25_la_banda_es_la_dispersion_y_no_el_error_de_la_media(salidas):
    """Que no vuelva el √n: con 6-8 pares la diferencia es un factor de 2,5 a 3."""
    import numpy as np

    pares = find_paired_segments(salidas["recorrido2_30mar2025"], PARAMS, maximo=8)
    assert len(pares) > 3
    cdas = np.array([par.cda for par in pares])
    _, banda = combine_pairs(pares)
    assert banda == pytest.approx(cdas.std(ddof=1), rel=1e-9)
    assert banda > cdas.std(ddof=1) / np.sqrt(len(cdas)) * 1.5
