"""Criterios 10, 11, 15, 16, 18, 19, 20 y 21 a través de la interfaz real de Streamlit (AppTest)."""
import json
import os
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import CATEGORIES, PARAM_SPECS, REQUIRED_PARAMS

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import theme  # noqa: E402  (vive en app/, que se acaba de añadir al path)

MASA = 90.0


@pytest.fixture(scope="module", autouse=True)
def perfiles_aislados(tmp_path_factory):
    """La app no debe tocar el JSON de perfiles del usuario durante los tests."""
    destino = tmp_path_factory.mktemp("perfiles") / "perfiles_bici.json"
    previo = os.environ.get("SIMCICLISMO_PERFILES")
    os.environ["SIMCICLISMO_PERFILES"] = str(destino)
    yield destino
    if previo is None:
        os.environ.pop("SIMCICLISMO_PERFILES", None)
    else:
        os.environ["SIMCICLISMO_PERFILES"] = previo


def _arrancada(timeout=90):
    """App recién abierta, con la masa puesta pero SIN simular todavía."""
    at = AppTest.from_file(APP, default_timeout=timeout).run()
    at.number_input(key="p_masa_total").set_value(MASA)
    return at.run()


def _simulada(timeout=90):
    """App con la masa puesta y la simulación ya ejecutada."""
    at = _arrancada(timeout)
    at.button(key="btn_simular").click()
    return at.run()


@pytest.fixture(scope="module")
def at():
    return _simulada()


def _en_estimador(timeout=180):
    """App en el módulo del estimador, con la masa puesta (criterio 31)."""
    at = AppTest.from_file(APP, default_timeout=timeout).run()
    at.segmented_control(key="modulo").set_value("estimador")
    at = at.run()
    at.number_input(key="p_masa_total").set_value(MASA)
    return at.run()


def _graficos(at):
    """Los `plotly_chart` de la página, cada uno como (figura, tema pedido a Streamlit).

    `AppTest` no entiende los gráficos de Plotly (`value` es `None`), pero su proto trae la figura
    en JSON y el tema con el que se pidió pintarla, que es justo lo que hace falta para comprobar
    **qué** se dibuja y **con qué tema**, en vez de confiar en el diccionario que se le pasó.
    """
    import json

    salida = []
    for g in at.get("plotly_chart"):
        salida.append((json.loads(g.proto.spec), g.proto.theme))
    return salida


def _serie(valores):
    """Una serie del JSON de Plotly como lista de floats.

    Plotly 6 serializa los arrays de numpy como `{"dtype": "f8", "bdata": "<base64>"}`, así que
    hay que deshacerlo para poder mirar los números y no solo los rótulos."""
    import base64

    import numpy as _np

    if isinstance(valores, dict) and "bdata" in valores:
        return _np.frombuffer(base64.b64decode(valores["bdata"]),
                              dtype=_np.dtype(valores.get("dtype", "f8"))).tolist()
    return [v for v in (valores or []) if v is not None]


def _trazas(at):
    """Las trazas con nombre de todos los gráficos, por nombre."""
    trazas = {}
    for spec, _ in _graficos(at):
        for tr in spec.get("data", []):
            if tr.get("name"):
                trazas[tr["name"]] = tr
    return trazas


def _texto(at):
    """Todo el markdown de la página, que es donde viven ahora las lecturas (criterio 32)."""
    return " ".join(m.value for m in at.markdown)


def _tiempo(at):
    """La cifra grande del bloque de lectura (el tiempo, en h:mm:ss)."""
    return re.search(r'class="cifra">([^<]+)<', _lectura(at)).group(1)


def _lectura(at, contiene: str = ""):
    """El bloque de lectura numérica: cifra, margen y las cifras que lo sostienen.

    `contiene` elige cuál cuando hay varios en la página (el del tiempo y el del CdA).
    """
    return next(m.value for m in at.markdown
                if 'class="lectura' in m.value and contiene in m.value)


def _widget_labels(at):
    return ({w.label for w in at.number_input} | {w.label for w in at.selectbox}
            | {w.label for w in at.checkbox} | {w.label for w in at.toggle})


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_arranca_sin_errores(at):
    assert not at.exception
    assert not at.error


# --------------------------------------------------------------------------- criterios 10 y 19
def test_c10_todos_los_parametros_editables_con_su_valor_por_defecto(at):
    labels = _widget_labels(at)
    for s in PARAM_SPECS:
        etiqueta = f"{s.label} ({s.unit})" if s.unit else s.label
        assert etiqueta in labels, s.key
    for s in PARAM_SPECS:
        if s.kind == "float" and s.key not in REQUIRED_PARAMS:
            w = at.number_input(key=f"p_{s.key}")
            assert w.value == pytest.approx(s.default)
            assert w.min == pytest.approx(s.minimum) and w.max == pytest.approx(s.maximum)


def test_c10_las_categorias_y_los_avanzados(at):
    nombres = [t.label for t in at.sidebar.tabs]
    assert nombres == list(CATEGORIES)
    assert any(e.label == "Avanzados" for e in at.sidebar.expander)


def test_c19_todos_los_widgets_llevan_su_tooltip(at):
    """El texto de ayuda de `PARAM_SPECS` tiene que llegar al widget, no quedarse en el núcleo."""
    for s in PARAM_SPECS:
        w = (at.number_input(key=f"p_{s.key}") if s.kind in ("float", "optional_float")
             else at.selectbox(key=f"p_{s.key}") if s.kind == "choice"
             else at.checkbox(key=f"p_{s.key}"))
        # la ayuda del parámetro tiene que llegar íntegra; un widget desactivado puede añadir
        # una nota detrás, pero nunca sustituirla
        assert w.help and s.help.strip() in w.help, s.key


# --------------------------------------------------------------------------- criterio 18
def test_c18_la_masa_es_un_solo_campo_obligatorio():
    at = AppTest.from_file(APP, default_timeout=90).run()
    assert not at.exception
    assert at.number_input(key="p_masa_total").value is None
    for viejo in ("p_masa_ciclista", "p_masa_equipo"):
        with pytest.raises(KeyError):
            at.number_input(key=viejo)
    # el estado de «falta un obligatorio» es ahora un bloque de vacío que dice qué hacer
    vacios = [m.value for m in at.markdown if 'class="vacio"' in m.value]
    assert len(vacios) == 1 and "masa total" in vacios[0].lower()
    assert "barra lateral" in vacios[0].lower()
    assert not any('class="lectura' in m.value for m in at.markdown)
    at.number_input(key="p_masa_total").set_value(MASA).run()
    assert not any('class="vacio"' in m.value and "masa" in m.value.lower()
                   for m in at.markdown)


# --------------------------------------------------------------------------- criterio 20
def test_c20_sin_pulsar_el_boton_no_hay_resultados():
    at = _arrancada()
    assert not at.exception
    assert not any('class="lectura' in m.value for m in at.markdown)   # no ha simulado nada
    # la pantalla vacía dice qué hacer, en vez de quedarse en blanco
    assert any('class="vacio"' in m.value and "Simular" in m.value for m in at.markdown)
    assert any(b.label.endswith("Simular") for b in at.button)


def test_c20_al_pulsar_simular_aparecen_los_resultados():
    at = _simulada()
    assert not at.exception
    bloque = _lectura(at)
    assert "Tiempo" in bloque and 'class="cifra"' in bloque
    assert bloque.count("<span><b>") >= 5                  # las cifras que sostienen el tiempo


def test_c20_cambiar_un_parametro_no_recalcula_pero_avisa():
    """La simulación no se dispara sola: se marca el resultado como desfasado."""
    at = _simulada()
    t0 = _tiempo(at)
    at.number_input(key="p_cda").set_value(0.40).run()
    assert not at.exception
    assert _tiempo(at) == t0                               # sigue el resultado anterior
    assert any("Simular" in w.value for w in at.warning)
    at.button(key="btn_simular").click().run()
    h = lambda s: sum(int(x) * f for x, f in zip(s.split(":"), (3600, 60, 1)))
    assert h(_tiempo(at)) > h(t0)                          # con más CdA, más tiempo
    assert not at.warning


def test_c20_el_boton_de_borrar_devuelve_la_interfaz_a_su_estado_inicial(perfiles_aislados):
    from core.profiles import load_profiles, profile_from_params, save_profile
    from core import Params

    save_profile(profile_from_params("no me borres", Params(masa_total=MASA)), perfiles_aislados)
    at = _simulada()
    at.number_input(key="p_cda").set_value(0.40).run()
    at.button(key="btn_borrar_todo").click().run()
    assert not at.exception
    assert at.number_input(key="p_masa_total").value is None    # masa olvidada
    assert at.number_input(key="p_cda").value == pytest.approx(0.27)   # y el CdA, a su inicial
    assert not any('class="lectura' in m.value for m in at.markdown)   # resultados olvidados
    # y los perfiles guardados en disco siguen ahí
    assert "no me borres" in load_profiles(perfiles_aislados)


def test_c20_borrar_deja_el_estado_como_la_app_recien_abierta():
    """Compara contra una referencia independiente —la app recién abierta— en vez de contra una
    lista de claves escrita a mano.

    **Lo que este test NO puede ver**, y conviene dejarlo escrito: que el *campo* de la pantalla
    se repinte. `AppTest` lee `session_state`, y al borrar la clave de un widget Streamlit la
    vuelve a escribir con su valor por defecto en la pasada siguiente, así que el estado parece
    correcto tanto si la pantalla se restablece como si se queda con el valor anterior pintado.
    Eso vive en `tests/test_navegador.py`, que lo mide sobre el DOM.
    """
    recien = AppTest.from_file(APP, default_timeout=180).run()    # sin tocar nada, ni la masa
    at = _simulada()
    at.number_input(key="p_cda").set_value(0.40).run()
    at.checkbox(key="p_limite_curvatura").set_value(False).run()
    at.button(key="btn_borrar_todo").click().run()
    for spec in PARAM_SPECS:
        clave = f"p_{spec.key}"
        assert clave in at.session_state, clave
        assert at.session_state[clave] == recien.session_state[clave], (
            f"{clave}: tras borrar vale {at.session_state[clave]!r} y recién abierta "
            f"{recien.session_state[clave]!r}")


def test_c20_borrar_no_cambia_el_idioma_ni_el_modulo_ni_el_tema():
    """Las tres preferencias de interfaz no son datos: un botón de «borrar» que le cambie a uno el
    idioma es un botón hostil. Lo que sí tiene que quedar es la coherencia entre el interruptor y
    el tema aplicado, que es de donde venía el defecto."""
    at = _arrancada(timeout=180)
    at.segmented_control(key="idioma").set_value("en").run()
    at.toggle(key="modo_oscuro").set_value(True).run()
    at.button(key="btn_borrar_todo").click().run()
    assert not at.exception
    assert at.session_state["idioma"] == "en"
    assert at.session_state["modulo"] == "simulador"
    assert at.session_state["modo_oscuro"] is True
    assert at.toggle(key="modo_oscuro").value is True


def test_c20_borrar_tambien_olvida_los_ficheros_subidos():
    """Lo encontró la revisión del 6-oct-2026: `est_fit` se limpiaba por el prefijo `est_` y el
    GPX y los `.fit` de validación se quedaban cargados. Era una asimetría, no una decisión."""
    at = _arrancada(timeout=180)
    at.file_uploader(key="val_fits").set_value(
        [(FIXTURE_FIT.name, FIXTURE_FIT.read_bytes(), "application/octet-stream")])
    at = at.run()
    assert at.session_state["val_fits"]                       # está cargado
    at.button(key="btn_borrar_todo").click().run()
    assert not at.exception
    for clave in ("val_fits", "gpx_file"):
        assert not at.session_state.get(clave), clave


# --------------------------------------------------------------------------- criterio 21
def test_c21_tema_claro_por_defecto_y_oscuro_opcional(at):
    config = Path(APP).resolve().parents[1] / ".streamlit" / "config.toml"
    texto = config.read_text(encoding="utf-8")
    assert 'base = "light"' in texto
    assert at.toggle(key="modo_oscuro").value is False          # arranca en claro

    oscura = _simulada()
    oscura.toggle(key="modo_oscuro").set_value(True).run()
    assert not oscura.exception
    css = " ".join(m.value for m in oscura.markdown)
    # el CSS sale de los tokens de app/theme.py, no de colores escritos en la interfaz
    assert "<style>" in css and theme.OSCURO.papel.lower() in css.lower()
    assert theme.OSCURO.senal.lower() in css.lower()


# --------------------------------------------------------------------------- criterios 11 y 16
def test_c11_metricas_de_salida(at):
    """Criterios 11 y 32: las cifras viven ahora en el bloque de lectura, no en `st.metric`."""
    bloque = _lectura(at)
    assert "Tiempo" in bloque
    for esperado in ("Velocidad media", "Distancia", "Desnivel", "Potencia media",
                     "Potencia normalizada (NP)", "Índice de variabilidad (VI)"):
        assert esperado in bloque, esperado
    # sin FTP no se inventa un factor de intensidad: esa celda no sale
    assert "Factor de intensidad (IF)" not in bloque


def test_c11_if_con_ftp():
    at = _arrancada()
    at.number_input(key="p_ftp").set_value(250.0)
    at.button(key="btn_simular").click().run()
    assert not at.exception
    bloque = _lectura(at)
    assert "Factor de intensidad (IF)" in bloque           # con FTP sí aparece la celda
    valor = re.search(r"<b>([\d.]+)</b> Factor de intensidad", bloque)
    assert valor and 0.1 < float(valor.group(1)) < 3.0


def test_c11_estan_las_graficas_que_el_alcance_enumera(at):
    """No basta con que exista **una** gráfica: el Alcance enumera velocidad, potencia, pendiente
    suavizada y CdA efectivo, y `len(plotly_chart) >= 1` lo pasaba igual dibujando solo la
    elevación. Así faltó la pendiente durante doce rondas.

    Se comprueban los nombres de las trazas y, para una serie, que los datos trazados son los del
    resultado: una gráfica con el título correcto y los datos de otra magnitud también pasaría.
    """
    from core.i18n import t as _t

    assert len(at.dataframe) >= 1
    assert len(at.get("download_button")) == 2
    trazas = _trazas(at)
    for clave in ("g_velocidad", "g_potencia_aplicada", "g_pendiente", "g_cda"):
        assert _t(clave) in trazas, f"falta la gráfica de {clave}: hay {sorted(trazas)}"
    # la pendiente trazada es la del perfil, en %, no otra magnitud con ese rótulo
    y = _serie(trazas[_t("g_pendiente")]["y"])
    assert len(y) > 10 and max(abs(v) for v in y) <= 30.0 and min(y) < 0.0 < max(y)
    v = _serie(trazas[_t("g_velocidad")]["y"])
    assert 5.0 < sum(v) / len(v) < 100.0, "la velocidad debería ir en km/h"


def test_c16_la_interfaz_muestra_las_dos_bandas_y_el_aviso_de_ruta_nueva(at):
    """Criterios 16 y 29: las dos bandas medidas, y que para una ruta nueva no hay banda."""
    bloque = _lectura(at).lower()
    assert "tiempo" in bloque and "banda" in bloque        # la lectura trae su banda dibujada
    notas = " ".join(c.value for c in at.caption).lower()
    assert "precisión del modelo" in notas and "margen del día" in notas
    # el aviso de ruta nueva va como nota permanente, no como st.warning: ahí competiría con
    # los avisos de verdad (ver criterio 20) y saldría en cada simulación
    assert "ruta nueva" in notas and "no hay banda verificada" in notas and "suelo" in notas
    assert "3 salidas coherentes" in notas and "protocolo recomendado" in notas


def test_c16_la_tabla_por_bloques_lleva_la_banda(at):
    """En pantalla las cabeceras van traducidas; el nombre técnico se conserva en el CSV."""
    from core.i18n import cabeceras
    from core.uncertainty import SUFIJOS

    columnas = set(at.dataframe[0].value.columns)
    traducidas = cabeceras(["tiempo_s" + s for s in SUFIJOS], "es")
    assert len(traducidas) == len(SUFIJOS), "alguna columna de banda se quedó sin cabecera"
    for suf in SUFIJOS:
        assert traducidas["tiempo_s" + suf] in columnas, suf
    assert len(at.get("download_button")) == 2      # el contenido de los CSV se prueba en
    #                                                 tests/test_exports.py (AppTest no lo expone)


def test_c12_sensibilidad_desde_la_interfaz():
    at = _simulada(timeout=120)
    next(b for b in at.button if b.label == "Calcular sensibilidad").click().run()
    assert not at.exception
    assert len(at.dataframe) >= 2     # tabla de bloques + tabla de sensibilidad


# --------------------------------------------------------------------------- criterio 24 (pestaña)
def test_c24_la_pestana_del_estimador_existe_y_pide_un_fit(at):
    nombres = [t.label for t in at.tabs]
    assert "Estimar CdA" in nombres
    textos = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    assert "balance de energía" in textos


# --------------------------------------------------------------------------- criterio 15
def test_c15_guardar_y_cargar_un_perfil_desde_la_interfaz(perfiles_aislados):
    from core.profiles import load_profiles

    at = _simulada()
    at.text_input(key="perfil_nombre").set_value("Bici de test")
    at.text_input(key="perfil_origen").set_value("calibrado con 2 salidas de prueba")
    at.checkbox(key="perfil_calibrado").set_value(True)
    at.number_input(key="p_cda").set_value(0.2688).run()
    next(b for b in at.button if b.label == "Guardar perfil").click().run()
    assert not at.exception

    guardado = load_profiles(perfiles_aislados)["Bici de test"]
    assert guardado.cda == pytest.approx(0.2688) and guardado.calibrado
    assert guardado.masa_total == pytest.approx(MASA)

    # en una sesión nueva el perfil se ofrece y al cargarlo fija los valores de la bici
    at2 = AppTest.from_file(APP, default_timeout=90).run()
    assert "Bici de test" in at2.selectbox(key="perfil_sel").options
    next(b for b in at2.button if b.label == "Cargar").click().run()
    assert not at2.exception
    assert at2.number_input(key="p_cda").value == pytest.approx(0.2688)
    assert at2.number_input(key="p_masa_total").value == pytest.approx(MASA)


def test_c15_calibrado_sin_origen_no_se_guarda(perfiles_aislados):
    from core.profiles import load_profiles

    at = _simulada()
    at.text_input(key="perfil_nombre").set_value("Sin origen")
    at.checkbox(key="perfil_calibrado").set_value(True).run()
    next(b for b in at.button if b.label == "Guardar perfil").click().run()
    assert not at.exception
    assert at.error and "origen" in at.error[0].value.lower()
    assert "Sin origen" not in load_profiles(perfiles_aislados)


# --------------------------------------------------------------------------- criterio 24 (extremo a extremo)
FIXTURE_FIT = Path(__file__).resolve().parent / "fixtures" / "recorrido2_30mar2025.fit"


def _con_fit_cargado(timeout=180):
    at = _simulada(timeout)
    at.file_uploader(key="est_fit").set_value(
        (FIXTURE_FIT.name, FIXTURE_FIT.read_bytes(), "application/octet-stream"))
    return at.run()


def test_c24_estimar_cda_en_un_segmento_llano_desde_la_interfaz():
    """Camino completo por la interfaz: subir el .fit, elegir el segmento y estimar."""
    at = _con_fit_cargado()
    assert not at.exception, at.exception
    deslizador = at.slider(key="est_slider")
    assert deslizador.value[1] > 0                       # se ha leído la longitud de la ruta

    at.slider(key="est_slider").set_value((10.0, 20.0)).run()
    at.button(key="btn_estimar").click().run()
    assert not at.exception

    # el camino manual usa el mismo bloque de lectura que el recomendado (criterio 32)
    bloque = _lectura(at, "CdA del segmento")
    valor = float(re.search(r'class="cifra">([\d.]+)<', bloque).group(1))
    assert 0.15 < valor < 0.45, bloque[:200]           # plausible para este tramo
    assert re.search(r'class="margen">± [\d.]+<', bloque)
    assert any("viento" in w.value.lower() for w in at.warning)
    # la tabla de sensibilidades tiene que estar a la vista
    fuentes = " ".join(str(d.value.to_dict()) for d in at.dataframe)
    assert "Altitud" in fuentes and "Viento" in fuentes


def test_c24_un_segmento_en_cuesta_se_marca_como_no_utilizable_en_la_interfaz():
    at = _con_fit_cargado()
    at.slider(key="est_slider").set_value((20.0, 25.0)).run()
    at.button(key="btn_estimar").click().run()
    assert not at.exception
    assert at.error and "no utilizable" in at.error[0].value.lower()


def test_c24_dos_segmentos_se_combinan_y_el_cda_se_puede_aplicar():
    at = _con_fit_cargado()
    for rango in ((10.0, 20.0), (50.0, 60.0)):
        at.slider(key="est_slider").set_value(rango).run()
        at.button(key="btn_estimar").click().run()
    assert not at.exception
    assert any("Combinado de" in i.value for i in at.info)
    next(b for b in at.button if "Aplicar este CdA" in b.label).click().run()
    assert not at.exception
    assert 0.15 < at.number_input(key="p_cda").value < 0.45
    # y queda marcado como calibrado, con su origen
    assert at.checkbox(key="perfil_calibrado").value is True
    assert "balance de energía" in at.text_input(key="perfil_origen").value


def test_c24_vaciar_la_lista_de_segmentos():
    at = _con_fit_cargado()
    at.slider(key="est_slider").set_value((10.0, 20.0)).run()
    at.button(key="btn_estimar").click().run()
    assert any("CdA del segmento" in m.value for m in at.markdown)
    next(b for b in at.button if "Vaciar" in b.label).click().run()
    assert not at.exception
    assert not any("CdA del segmento" in m.value for m in at.markdown)


def test_c24_la_busqueda_automatica_desde_la_interfaz():
    """El camino recomendado: subir el .fit y pulsar «Buscar tramos fiables»."""
    at = _con_fit_cargado()
    next(b for b in at.button if "Buscar tramos" in b.label).click().run()
    assert not at.exception, at.exception

    # el CdA recomendado vive en el bloque de lectura, con su margen al lado (criterio 32)
    bloque = _lectura(at, "CdA de esta bici")
    assert "CdA de esta bici" in bloque
    valor = float(re.search(r'class="cifra">([\d.]+)<', bloque).group(1))
    assert 0.20 < valor < 0.35, bloque[:200]
    margen = re.search(r'class="margen">± ([\d.]+)<', bloque)
    assert margen and 0.0 < float(margen.group(1)) < 0.05
    for celda in ("pares", "descartados", "en los tramos", "en todo el recorrido"):
        assert celda in bloque, celda
    # y la banda dibuja lo medido junto a lo que no se ha medido (el viento)
    assert "medido" in bloque and "sin medir" in bloque

    # la tabla de pares trae la columna que mide el viento (con la cabecera ya traducida)
    from core.i18n import COLUMNAS

    columnas = set()
    for d in at.dataframe:
        columnas |= set(d.value.columns)
    for tecnica in ("CdA_par", "viento_ms", "separacion_m"):
        assert COLUMNAS[tecnica]["es"] in columnas, tecnica
    # y el sesgo de selección se avisa
    assert any("sesgo de selección" in w.value.lower() for w in at.warning)


def test_c24_aplicar_el_cda_de_los_pares_a_la_barra_lateral():
    at = _con_fit_cargado()
    next(b for b in at.button if "Buscar tramos" in b.label).click().run()
    next(b for b in at.button if b.key == "btn_aplicar_pares").click().run()
    assert not at.exception
    assert 0.20 < at.number_input(key="p_cda").value < 0.35
    assert at.checkbox(key="perfil_calibrado").value is True
    assert "pares de ida y vuelta" in at.text_input(key="perfil_origen").value


def test_c24_la_tabla_de_segmentos_seleccionados_sale_con_uno_solo():
    """Lo que pidió el usuario: la tabla por segmento, desde la primera estimación."""
    from core.exports import COLUMNAS_SEGMENTOS_BASICAS
    from core.i18n import COLUMNAS

    esperadas = [COLUMNAS[c]["es"] for c in COLUMNAS_SEGMENTOS_BASICAS]
    at = _con_fit_cargado()
    at.slider(key="est_slider").set_value((10.0, 20.0)).run()
    at.button(key="btn_estimar").click().run()
    assert not at.exception

    tabla = next((d.value for d in at.dataframe
                  if esperadas[0] in getattr(d.value, "columns", [])), None)
    assert tabla is not None, "no hay tabla de segmentos"
    assert len(tabla) == 1
    assert list(tabla.columns) == esperadas
    for exigida in ("cda", "desnivel_m", "v_media_kmh", "potencia_media_w"):
        assert COLUMNAS[exigida]["es"] in tabla.columns, exigida

    # una segunda estimación añade fila, no sustituye
    at.slider(key="est_slider").set_value((50.0, 60.0)).run()
    at.button(key="btn_estimar").click().run()
    tabla = next(d.value for d in at.dataframe if esperadas[0] in getattr(d.value, "columns", []))
    assert len(tabla) == 2
    assert any("Descargar la tabla" in b.label for b in at.get("download_button"))


def test_c24_ver_todas_las_columnas_anade_el_desglose():
    from core.exports import COLUMNAS_SEGMENTOS_DETALLE
    from core.i18n import COLUMNAS

    at = _con_fit_cargado()
    at.slider(key="est_slider").set_value((10.0, 20.0)).run()
    at.button(key="btn_estimar").click().run()
    at.checkbox(key="est_detalle_seleccion").set_value(True).run()
    assert not at.exception
    tabla = next(d.value for d in at.dataframe
                 if COLUMNAS["tramo_km"]["es"] in getattr(d.value, "columns", []))
    for col in COLUMNAS_SEGMENTOS_DETALLE:
        assert COLUMNAS[col]["es"] in tabla.columns, col


def test_c24_la_busqueda_tambien_lista_cada_tramo_por_separado():
    from core.i18n import COLUMNAS

    at = _con_fit_cargado()
    next(b for b in at.button if "Buscar tramos" in b.label).click().run()
    assert not at.exception
    tabla = next((d.value for d in at.dataframe
                  if COLUMNAS["tramo_km"]["es"] in getattr(d.value, "columns", [])), None)
    assert tabla is not None
    assert len(tabla) >= 6                             # ida y vuelta de cada par
    assert COLUMNAS["rumbo"]["es"] in tabla.columns    # el dato que delata el viento
    assert any("Descargar estos tramos" in b.label for b in at.get("download_button"))


# --------------------------------------------------------------------------- rueda manual
def test_el_perimetro_esta_desactivado_salvo_con_la_medida_manual():
    from core import ETRTO_MANUAL

    at = _arrancada()
    assert at.number_input(key="p_perimetro_mm").disabled is True
    at.selectbox(key="p_etrto").set_value(ETRTO_MANUAL).run()
    assert at.number_input(key="p_perimetro_mm").disabled is False
    # con «manual» y sin perímetro la app no simula y explica cómo medirlo
    assert at.warning and "perímetro" in at.warning[0].value.lower()
    assert "vuelta completa" in at.warning[0].value
    at.number_input(key="p_perimetro_mm").set_value(2105.0).run()
    at.button(key="btn_simular").click().run()
    assert not at.exception
    assert 'class="cifra"' in _lectura(at)


def test_la_rueda_por_defecto_es_700x28_y_se_muestra_su_perimetro(at):
    assert at.selectbox(key="p_etrto").value == "28-622"
    pie = " ".join(c.value for c in at.caption)
    assert "28-622" in pie and "2130 mm de perímetro" in pie


# --------------------------------------------------------------------------- criterio 27: idioma
def test_c27_el_selector_de_idioma_existe_y_arranca_en_castellano(at):
    sel = at.segmented_control(key="idioma")
    assert sel.value == "es"
    assert at.button(key="btn_simular").label == "▶ Simular"


def test_c27_cambiar_a_ingles_traduce_etiquetas_tooltips_y_pestanas():
    from core import PARAM_SPECS
    from core.i18n import PARAM_EN

    at = _simulada()
    at.segmented_control(key="idioma").set_value("en")
    at = at.run()
    assert not at.exception

    # pestañas y botones
    assert [tab.label for tab in at.tabs][:2] == ["Results", "Sensitivity"]
    assert at.button(key="btn_simular").label == "▶ Simulate"
    assert at.toggle(key="modo_oscuro").label == "🌙 Dark mode"
    # categorías de la barra lateral
    assert [tb.label for tb in at.sidebar.tabs] == ["Rider", "Equipment", "External variables"]
    # etiquetas y tooltips de TODOS los parámetros
    for s in PARAM_SPECS:
        w = (at.number_input(key=f"p_{s.key}") if s.kind in ("float", "optional_float")
             else at.selectbox(key=f"p_{s.key}") if s.kind == "choice"
             else at.checkbox(key=f"p_{s.key}"))
        etiqueta_en, ayuda_en = PARAM_EN[s.key]
        assert etiqueta_en in w.label, s.key
        assert ayuda_en in w.help, s.key
    # métricas de salida
    assert "Time" in _lectura(at)


def test_c27_en_ingles_los_avisos_y_las_cabeceras_tambien_cambian():
    at = _simulada()
    at.segmented_control(key="idioma").set_value("en")
    at = at.run()
    # cabeceras traducidas en la tabla por bloques, nombres técnicos en el CSV
    columnas = set(at.dataframe[0].value.columns)
    assert "time (s)" in columnas and "tiempo_s" not in columnas
    # el aviso de masa obligatoria, en inglés
    vacia = AppTest.from_file(APP, default_timeout=90).run()
    vacia.segmented_control(key="idioma").set_value("en")
    vacia = vacia.run()
    vacios = [m.value for m in vacia.markdown if 'class="vacio"' in m.value]
    assert vacios and "total mass" in vacios[0].lower()


#: Palabras que solo existen en castellano y que, si aparecen con la interfaz en inglés, delatan
#: un texto sin traducir. Son funcionales a propósito: cualquier frase española las lleva, y
#: ninguna palabra inglesa coincide con ellas.
DELATORAS_ES = (" el ", " la ", " los ", " las ", " del ", " con ", " para ", " que ", " una ",
                " sin ", " más ", " según ", " sobre el ", "ción ", "ían ", " está ")


def _sin_texto_de_usuario(texto: str) -> str:
    """Quita del barrido el texto libre que redacta la persona, no la interfaz.

    La procedencia del CdA y el nombre de un perfil los escribe el usuario cuando mide, en su
    idioma: traducirlos falsearía un registro, así que el criterio 27 no los alcanza. Se quitan
    **por valor**, leyéndolos del almacén aislado, no recortando una región de la pantalla: así el
    barrido sigue siendo total sobre todo lo demás.

    Sin esto, el barrido fallaba o no según el orden de los tests: cualquier prueba anterior del
    módulo que guardase un perfil con procedencia en castellano lo dejaba dentro del texto barrido.
    """
    ruta = os.environ.get("SIMCICLISMO_PERFILES", "")
    if not ruta or not Path(ruta).exists():
        return texto
    try:
        guardados = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return texto
    for perfil in guardados if isinstance(guardados, list) else []:
        if not isinstance(perfil, dict):
            continue
        for campo in ("origen_cda", "nombre", "perfil_origen"):
            valor = str(perfil.get(campo) or "").strip().lower()
            if len(valor) > 3:
                texto = texto.replace(valor, " ")
    return texto


def _texto_visible(at):
    """Todo el texto que la página enseña: markdown, captions, avisos y errores."""
    # la hoja de estilos se inyecta como markdown y sus comentarios están en castellano: no es
    # texto que el usuario lea
    piezas = [m.value for m in at.markdown if "<style" not in str(m.value)]
    piezas += [c.value for c in at.caption]
    piezas += [w.value for w in at.warning] + [e.value for e in at.error]
    piezas += [s.value for s in at.success] + [i.value for i in at.info]
    return " ".join(str(p) for p in piezas)


def test_c27_en_ingles_no_se_cuela_castellano_en_ningun_texto():
    """Barrido, no lista: cualquier texto nuevo sin traducir cae aquí.

    Los tests anteriores comprobaban cadenas concretas, así que los textos que nadie había
    enumerado se traducían o no sin que la suite se enterara: la procedencia de las dos bandas, los
    errores de `validate_params`, los avisos del GPX, el spinner y las opciones del desplegable de
    superficie por tramos salían en castellano con la interfaz en inglés.
    """
    at = _simulada()
    at.segmented_control(key="idioma").set_value("en")
    at = at.run()
    assert not at.exception
    texto = " " + _sin_texto_de_usuario(_texto_visible(at).lower().replace("\n", " ")) + " "
    assert len(texto) > 500, "poco texto que barrer: el barrido no estaría midiendo nada"
    encontradas = sorted({d for d in DELATORAS_ES if d in texto})
    assert not encontradas, (
        f"texto en castellano con la interfaz en inglés (marcas: {encontradas}). "
        f"Fragmento: …{texto[max(0, texto.find(encontradas[0])) - 90:][:260]}…")


def test_c27_el_barrido_de_castellano_detecta_de_verdad():
    """Control positivo del test anterior: en castellano, las mismas marcas **sí** aparecen. Sin
    esto, un barrido que no encuentre nada podría estar midiendo una página vacía."""
    at = _simulada()
    texto = " " + _texto_visible(at).lower().replace("\n", " ") + " "
    assert sum(1 for d in DELATORAS_ES if d in texto) >= 5


def test_c27_el_estimador_en_ingles_avisa_del_viento_en_ingles():
    at = _con_fit_cargado()
    at.segmented_control(key="idioma").set_value("en")
    at = at.run()
    at.slider(key="est_slider").set_value((10.0, 20.0)).run()
    at.button(key="btn_estimar").click().run()
    assert not at.exception
    assert any("Segment CdA" in m.value for m in at.markdown)
    assert any("wind" in w.value.lower() for w in at.warning)
    assert not any("viento" in w.value.lower() for w in at.warning)


# --------------------------------------------------------------------------- criterios 28 y 30
FIXTURE_INCOHERENTE = Path(__file__).resolve().parent / "fixtures" / "recorrido2_08jun2025.fit"
FIXTURE_PARES_MALOS = Path(__file__).resolve().parent / "fixtures" / "recorrido2_04may2025.fit"


def _con_fits_de_validacion(*rutas, timeout=300):
    """Sube uno o varios .fit a la pestaña de validación con FIT."""
    at = _simulada(timeout)
    at.file_uploader(key="val_fits").set_value(
        [(r.name, r.read_bytes(), "application/octet-stream") for r in rutas])
    return at.run()


def test_c30_el_examen_de_coherencia_marca_la_buena_y_la_mala_desde_la_interfaz():
    at = _con_fits_de_validacion(FIXTURE_FIT, FIXTURE_INCOHERENTE)
    assert not at.exception, at.exception
    at.button(key="btn_coherencia").click().run()
    assert not at.exception, at.exception

    from core.i18n import COLUMNAS

    columnas = set()
    for d in at.dataframe:
        columnas |= set(d.value.columns)
    for tecnica in ("cda_calibrado", "coherente", "err_llano_%", "err_bajada_%"):
        assert COLUMNAS[tecnica]["es"] in columnas, tecnica

    # cada veredicto usa el código visual del sistema (criterio 32): `ok` la coherente,
    # `mal` la incoherente, con su nombre dentro
    bloques = [m.value for m in at.markdown if 'class="veredicto' in m.value]
    buena = next(b for b in bloques if FIXTURE_FIT.name in b)
    mala = next(b for b in bloques if FIXTURE_INCOHERENTE.name in b)
    assert 'class="veredicto ok"' in buena and "Actividad coherente" in buena
    assert 'class="veredicto mal"' in mala
    assert "No uses esta actividad para calibrar" in mala
    assert any(b.label.endswith("CSV") for b in at.download_button)


def test_c30_calibrar_con_una_actividad_incoherente_avisa_y_frena_el_guardado():
    at = _con_fits_de_validacion(FIXTURE_INCOHERENTE)
    at.button(key="btn_coherencia").click().run()
    at.multiselect(key="cal_sel").set_value([FIXTURE_INCOHERENTE.name]).run()
    at.button(key="btn_calibrar").click().run()
    assert not at.exception, at.exception

    avisos = " ".join(w.value for w in at.warning)
    assert "marcadas como incoherentes" in avisos
    # y el aviso reaparece en el panel de guardar perfil, antes de fijar ese CdA
    assert "actividad marcada como" in avisos


def test_c30_calibrar_con_una_incoherente_avisa_aunque_no_se_examine_antes():
    """El defecto que encontró la revisión: sin pulsar «Examinar coherencia» se podía calibrar un
    CdA de 0,150 —fuera del rango plausible— y guardarlo sin un solo aviso."""
    at = _con_fits_de_validacion(FIXTURE_PARES_MALOS)
    at.multiselect(key="cal_sel").set_value([FIXTURE_PARES_MALOS.name]).run()
    at.button(key="btn_calibrar").click().run()           # NO se pulsa btn_coherencia
    assert not at.exception, at.exception

    avisos = " ".join(w.value for w in at.warning)
    assert "incoherentes" in avisos or "rango plausible" in avisos, avisos
    # y el aviso llega también al panel de guardar perfil
    assert "actividad marcada como" in avisos


def test_c30_un_cda_fuera_de_rango_se_avisa_siempre():
    """Red de seguridad independiente del examen por bandas."""
    at = _con_fits_de_validacion(FIXTURE_PARES_MALOS)
    at.multiselect(key="cal_sel").set_value([FIXTURE_PARES_MALOS.name]).run()
    at.button(key="btn_calibrar").click().run()
    from core.coherence import CDA_PLAUSIBLE

    assert not (CDA_PLAUSIBLE[0] < float(at.session_state["cda_cal"]) < CDA_PLAUSIBLE[1])
    assert any("rango plausible" in w.value for w in at.warning)


def test_c28_los_pares_imposibles_se_enseñan_en_el_estimador():
    at = _simulada(300)
    at.file_uploader(key="est_fit").set_value(
        (FIXTURE_PARES_MALOS.name, FIXTURE_PARES_MALOS.read_bytes(), "application/octet-stream"))
    at = at.run()
    next(b for b in at.button if "Buscar tramos" in b.label).click().run()
    assert not at.exception, at.exception

    # criterio 32: lo descartado se enseña con el código visual del sistema, no con un caption
    bloques = " ".join(m.value for m in at.markdown if 'class="veredicto' in m.value)
    assert "Par descartado" in bloques
    assert "no pueden diferir tanto" in bloques
    assert 'class="veredicto mal"' in bloques
    # y el CdA recomendado sigue siendo plausible pese a la actividad problemática
    bloque = _lectura(at, "CdA de esta bici")
    assert 0.20 < float(re.search(r'class="cifra">([\d.]+)<', bloque).group(1)) < 0.35, bloque[:160]
