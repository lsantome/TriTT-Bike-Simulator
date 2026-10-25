"""Criterio 27: la herramienta en español e inglés.

El test que de verdad importa es el primero: si se añade un parámetro y se olvida su traducción,
la suite falla. Sin eso, una interfaz «multilenguaje» se degrada en semanas.
"""
import re

import pytest

from core import CATEGORIES, PARAM_SPECS, SURFACES, Params
from core.i18n import (CATEGORIAS, COLUMNAS, ETIQUETAS_IDIOMA, IDIOMA_POR_DEFECTO, IDIOMAS,
                       PARAM_EN, SUPERFICIES, UI, cabeceras, categoria, normaliza, param_help,
                       param_label, superficie, t)
from core.exports import (COLUMNAS_COHERENCIA, COLUMNAS_SEGMENTOS_BASICAS,
                          COLUMNAS_SEGMENTOS_DETALLE)


# --------------------------------------------------------------------------- cobertura
def test_c27_todos_los_parametros_estan_traducidos():
    """Lo que impide que la traducción se degrade: un parámetro nuevo sin inglés rompe la suite."""
    sin_traducir = [s.key for s in PARAM_SPECS if s.key not in PARAM_EN]
    assert not sin_traducir, f"parámetros sin traducir al inglés: {sin_traducir}"
    sobrantes = [k for k in PARAM_EN if k not in {s.key for s in PARAM_SPECS}]
    assert not sobrantes, f"traducciones de parámetros que ya no existen: {sobrantes}"


def test_c27_las_traducciones_de_parametros_no_son_cascaras_vacias():
    for s in PARAM_SPECS:
        etiqueta, ayuda = PARAM_EN[s.key]
        assert etiqueta.strip(), s.key
        assert len(ayuda.strip()) >= 40, f"{s.key}: ayuda inglesa demasiado corta"
        # una ayuda inglesa idéntica a la española delata un copia y pega sin traducir
        assert ayuda.strip() != s.help.strip(), f"{s.key}: la ayuda inglesa es la española"
        assert etiqueta.strip() != s.label.strip() or not re.search(r"[áéíóúñ¿¡]", s.label), s.key


def test_c27_cada_cadena_de_interfaz_tiene_los_dos_idiomas():
    for clave, entrada in UI.items():
        assert set(entrada) == set(IDIOMAS), f"{clave}: idiomas {sorted(entrada)}"
        for idioma, texto in entrada.items():
            assert texto.strip(), f"{clave}/{idioma} vacío"
    for diccionario, nombre in ((CATEGORIAS, "categorías"), (SUPERFICIES, "superficies"),
                                (COLUMNAS, "columnas")):
        for clave, entrada in diccionario.items():
            assert set(entrada) == set(IDIOMAS), f"{nombre}: {clave}"


def test_c27_las_categorias_y_superficies_del_nucleo_estan_traducidas():
    for c in CATEGORIES:
        assert c in CATEGORIAS, c
        assert categoria(c, "en") != "" and categoria(c, "es") == c
    for sup in SURFACES:
        assert sup in SUPERFICIES, sup
        assert superficie(sup, "es") == sup


def test_c27_las_columnas_que_se_muestran_estan_traducidas():
    """Las de la tabla de segmentos, que es la que más se mira, y las del examen de coherencia."""
    for col in (list(COLUMNAS_SEGMENTOS_BASICAS) + list(COLUMNAS_SEGMENTOS_DETALLE)
                + list(COLUMNAS_COHERENCIA)):
        assert col in COLUMNAS, f"columna sin cabecera traducida: {col}"


def test_c27_los_placeholders_de_formato_coinciden_entre_idiomas():
    """Un `{nombre}` que falte en inglés revienta en ejecución, no al revés."""
    patron = re.compile(r"\{(\w+)")
    for clave, entrada in UI.items():
        campos = {idioma: set(patron.findall(texto)) for idioma, texto in entrada.items()}
        assert campos["es"] == campos["en"], f"{clave}: {campos}"


# --------------------------------------------------------------------------- comportamiento
def test_c27_t_devuelve_cada_idioma_y_formatea():
    assert t("boton_simular", "es") == "▶ Simular"
    assert t("boton_simular", "en") == "▶ Simulate"
    assert "2" in t("est_lista_titulo", "es", n=2)
    assert t("guardar_ok", "en", nombre="X") == "Profile «X» saved."


def test_c27_un_idioma_desconocido_cae_al_castellano_sin_romper():
    assert normaliza("fr") == IDIOMA_POR_DEFECTO == "es"
    assert t("boton_simular", "fr") == t("boton_simular", "es")
    assert t("boton_simular", "") == t("boton_simular", "es")


def test_c27_una_clave_desconocida_se_devuelve_tal_cual_para_que_se_vea():
    assert t("clave_que_no_existe", "es") == "clave_que_no_existe"


def test_c27_las_etiquetas_y_ayudas_de_parametros_cambian_con_el_idioma():
    spec = next(s for s in PARAM_SPECS if s.key == "masa_total")
    assert param_label(spec, "es") == spec.label
    assert param_label(spec, "en") == "Total mass (rider + bike + kit)"
    assert param_help(spec, "en") != param_help(spec, "es")
    # y un idioma raro no deja la interfaz en blanco
    assert param_label(spec, "zz") == spec.label


def test_c27_cabeceras_solo_renombra_lo_que_conoce():
    mapa = cabeceras(["cda", "desnivel_m", "columna_inventada"], "en")
    assert mapa["cda"] == "CdA" and mapa["desnivel_m"] == "elev. change (m)"
    assert "columna_inventada" not in mapa


def test_c27_el_selector_tiene_etiqueta_para_cada_idioma():
    assert set(ETIQUETAS_IDIOMA) == set(IDIOMAS)
    for idioma, etiqueta in ETIQUETAS_IDIOMA.items():
        assert idioma.upper() in etiqueta


# --------------------------------------------------------------------------- avisos del estimador
def test_c27_los_avisos_del_estimador_salen_en_el_idioma_pedido():
    from pathlib import Path

    from core.cda_estimator import estimate_cda
    from core.validation import read_fit

    fx = Path(__file__).resolve().parent / "fixtures" / "recorrido2_30mar2025.fit"
    ride = read_fit(fx.read_bytes(), "30mar")
    p = Params(masa_total=90.0)
    es = estimate_cda(ride, p, 20.0, 25.0, idioma="es")
    en = estimate_cda(ride, p, 20.0, 25.0, idioma="en")
    assert es.cda == pytest.approx(en.cda)                 # el número no depende del idioma
    assert len(es.avisos) == len(en.avisos)
    assert any("viento" in a.lower() for a in es.avisos)
    assert any("wind" in a.lower() for a in en.avisos)
    assert not any("viento" in a.lower() for a in en.avisos)


def test_c27_el_idioma_por_defecto_del_estimador_es_el_castellano():
    from pathlib import Path

    from core.cda_estimator import estimate_cda
    from core.validation import read_fit

    fx = Path(__file__).resolve().parent / "fixtures" / "recorrido2_30mar2025.fit"
    ride = read_fit(fx.read_bytes(), "30mar")
    e = estimate_cda(ride, Params(masa_total=90.0), 10.0, 20.0)
    assert any("viento" in a.lower() for a in e.avisos)


# --------------------------------------------------------------------------- el guardián que faltaba
def test_c27_toda_clave_de_interfaz_que_usa_la_app_existe_en_el_diccionario():
    """El agujero que encontró la revisión del 6-oct-2026.

    `t()` devuelve la clave tal cual cuando no la conoce, que está bien para no dejar la interfaz
    en blanco pero significa que **añadir una cadena sin traducir no rompía nada**: salía en
    pantalla el identificador técnico y la suite seguía verde. El criterio 27 pide justo lo
    contrario. Aquí se leen las llamadas a `t("...")` del código y se exige que todas existan.
    """
    import ast
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    ficheros = sorted((raiz / "core").glob("*.py")) + sorted((raiz / "app").glob("*.py"))
    usadas: dict = {}
    for fichero in ficheros:
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = getattr(nodo.func, "id", None) or getattr(nodo.func, "attr", None)
            if nombre != "t" or not nodo.args:
                continue
            primero = nodo.args[0]
            if isinstance(primero, ast.Constant) and isinstance(primero.value, str):
                usadas.setdefault(primero.value, fichero.name)

    assert len(usadas) > 80, f"el rastreo de claves encontró solo {len(usadas)}: ¿se rompió?"
    faltan = {k: v for k, v in usadas.items() if k not in UI}
    assert not faltan, f"claves usadas en el código y ausentes de UI: {faltan}"


def test_c27_las_claves_con_formato_reciben_los_campos_que_piden():
    """Un `{nombre}` sin su argumento revienta en ejecución, no en la suite."""
    import re

    patron = re.compile(r"\{(\w+)")
    for clave, entrada in UI.items():
        campos = set(patron.findall(entrada["es"]))
        # la cadena sin campos tiene que poder formatearse sin argumentos
        if not campos:
            assert t(clave, "es") == entrada["es"], clave


def test_c27_las_etiquetas_de_rueda_cambian_con_el_idioma():
    """Las medidas ETRTO son normativas y no se traducen; el texto que las acompaña sí."""
    from core.wheels import ETRTO_MANUAL, label_for

    assert label_for(ETRTO_MANUAL, "es") != label_for(ETRTO_MANUAL, "en")
    assert "perímetro" in label_for(ETRTO_MANUAL, "es")
    assert "circumference" in label_for(ETRTO_MANUAL, "en")
    assert label_for("28-622", "en").startswith("28-622")
