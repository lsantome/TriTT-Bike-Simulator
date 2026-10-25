"""Criterios 31 (el estimador como módulo) y 32 (sistema de diseño) desde la interfaz real.

Lo que estos tests protegen no es «que quede bonito», que no se puede medir, sino las tres
decisiones que sostienen el diseño y que es fácil deshacer sin darse cuenta:

1. El estimador **no pide** lo que no usa (y sobre todo no pide el CdA, que es su salida).
2. Los colores salen de un único sitio, `app/theme.py`, y no se escriben a mano en la interfaz.
3. Ningún número sale sin su margen, y el margen dibujado distingue lo medido de lo que no.
"""
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import PARAM_SPECS
from core.params import PARAMS_ESTIMADOR

RAIZ = Path(__file__).resolve().parents[1]
APP = str(RAIZ / "app" / "streamlit_app.py")
sys.path.insert(0, str(RAIZ / "app"))
import theme  # noqa: E402  (vive en app/, que se acaba de añadir al path)

MASA = 90.0


@pytest.fixture(scope="module")
def estimador():
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.segmented_control(key="modulo").set_value("estimador")
    at = at.run()
    at.number_input(key="p_masa_total").set_value(MASA)
    return at.run()


@pytest.fixture(scope="module")
def simulador():
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.number_input(key="p_masa_total").set_value(MASA)
    return at.run()


# --------------------------------------------------------------------------- criterio 31
def test_c31_el_simulador_es_el_modulo_de_entrada(simulador):
    assert not simulador.exception
    assert simulador.segmented_control(key="modulo").value == "simulador"


def test_c31_el_estimador_no_pide_recorrido(estimador):
    """La entrada del módulo es un `.fit` y nada más: ni GPX ni nada que hable de rutas."""
    assert not estimador.exception
    with pytest.raises(KeyError):
        estimador.file_uploader(key="gpx_file")
    barra = " ".join(w.label for w in estimador.sidebar.file_uploader) if \
        estimador.sidebar.file_uploader else ""
    assert "gpx" not in barra.lower()


def test_c31_el_estimador_no_pide_el_cda_que_va_a_calcular(estimador):
    """La trampa conceptual que este módulo evita."""
    for salida in ("p_cda", "p_delta_cda"):
        with pytest.raises(KeyError):
            estimador.number_input(key=salida)


def test_c31_el_estimador_no_pide_los_parametros_que_no_usa(estimador):
    fuera = [s.key for s in PARAM_SPECS if s.key not in PARAMS_ESTIMADOR]
    presentes = []
    for clave in fuera:
        for accesor in (estimador.number_input, estimador.selectbox, estimador.checkbox):
            try:
                accesor(key=f"p_{clave}")
            except KeyError:
                continue
            presentes.append(clave)
            break
    assert not presentes, f"el estimador pide parámetros que no usa: {presentes}"


def test_c31_el_estimador_si_pide_los_que_usa(estimador):
    """El reverso: quitar de más también es un fallo."""
    faltan = []
    for clave in PARAMS_ESTIMADOR:
        if clave == "perimetro_mm":
            continue                      # existe pero desactivado salvo rueda «manual»
        for accesor in (estimador.number_input, estimador.selectbox, estimador.checkbox):
            try:
                accesor(key=f"p_{clave}")
                break
            except KeyError:
                continue
        else:
            faltan.append(clave)
    assert not faltan, f"el estimador no pide parámetros que sí usa: {faltan}"


def test_c31_el_estimador_no_ofrece_simular(estimador):
    with pytest.raises(KeyError):
        estimador.button(key="btn_simular")
    etiquetas = " ".join(b.label for b in estimador.button)
    assert "Simular" not in etiquetas


def test_c31_las_pestanas_del_estimador_son_las_suyas(estimador, simulador):
    def pestanas(at):
        return {t for t in re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñ ]+", " ".join(
            str(getattr(x, "label", "")) for x in at.tabs))}

    assert len(estimador.tabs) < len(simulador.tabs)


def test_c31_el_estimador_arranca_directamente_desde_la_linea_de_ordenes(monkeypatch):
    """`run.sh --estimador` pasa `--modo=estimador`: la app tiene que entenderlo."""
    monkeypatch.setattr(sys, "argv", ["streamlit", "run", "app", "--modo=estimador"])
    at = AppTest.from_file(APP, default_timeout=180).run()
    assert not at.exception
    assert at.segmented_control(key="modulo").value == "estimador"


def test_c31_los_dos_lanzadores_aceptan_el_arranque_directo():
    sh = (RAIZ / "run.sh").read_text(encoding="utf-8")
    bat = (RAIZ / "run.bat").read_text(encoding="utf-8")
    for texto, nombre in ((sh, "run.sh"), (bat, "run.bat")):
        assert "--estimador" in texto, nombre          # la bandera que escribe el usuario
        assert "--modo=" in texto, nombre              # lo que se le pasa a la app
        assert "estimador" in texto, nombre


# --------------------------------------------------------------------------- criterio 32
#: Un color escrito a mano en la interfaz rompe el sistema: tiene que salir de `theme`.
COLOR_A_MANO = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(")


def test_c32_la_interfaz_no_escribe_colores_a_mano():
    codigo = (RAIZ / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    sueltos = [l.strip() for l in codigo.splitlines()
               if COLOR_A_MANO.search(l) and not l.strip().startswith("#")]
    assert not sueltos, f"colores fuera de app/theme.py: {sueltos}"


def test_c32_los_dos_temas_salen_de_los_mismos_tokens():
    claro, oscuro = theme.css(False), theme.css(True)
    assert claro != oscuro
    for paleta, hoja in ((theme.CLARO, claro), (theme.OSCURO, oscuro)):
        for campo in ("papel", "superficie", "tinta", "apagado", "regla", "senal",
                      "ocre", "ladrillo", "musgo"):
            assert getattr(paleta, campo).lower() in hoja.lower(), (campo, paleta)
    # y ningún color del tema contrario se cuela en el otro
    assert theme.OSCURO.papel.lower() not in claro.lower()


def _luminancia(hexcolor: str) -> float:
    c = hexcolor.lstrip("#")
    canales = [int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in canales]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contraste(a: str, b: str) -> float:
    la, lb = _luminancia(a), _luminancia(b)
    alto, bajo = max(la, lb), min(la, lb)
    return (alto + 0.05) / (bajo + 0.05)


@pytest.mark.parametrize("nombre", ["CLARO", "OSCURO"])
def test_c32_el_contraste_del_texto_llega_al_minimo_de_accesibilidad(nombre):
    """AA pide 4,5:1 para texto normal. El texto apagado es el caso justo."""
    p = getattr(theme, nombre)
    assert _contraste(p.tinta, p.papel) >= 7.0, "texto principal"
    for campo in ("apagado", "senal", "ocre", "ladrillo", "musgo"):
        c = _contraste(getattr(p, campo), p.papel)
        assert c >= 4.5, f"{nombre}.{campo}: contraste {c:.2f} sobre el papel"


def test_c32_el_css_cumple_el_suelo_de_accesibilidad():
    hoja = theme.css(False)
    assert "focus-visible" in hoja, "el foco de teclado tiene que verse"
    assert "prefers-reduced-motion" in hoja
    # la fuente de iconos de Streamlit no se pisa (si no, los ligados salen como texto)
    assert "Material Symbols" in hoja


def test_c32_hay_dos_tipografias_con_papeles_distintos_y_con_reserva():
    assert "Instrument Sans" in theme.FUENTE_UI and "IBM Plex Mono" in theme.FUENTE_CIFRA
    assert theme.FUENTE_UI != theme.FUENTE_CIFRA
    for pila in (theme.FUENTE_UI, theme.FUENTE_CIFRA):
        assert pila.count(",") >= 2, f"sin pila de reserva: {pila}"
    assert "monospace" in theme.FUENTE_CIFRA         # degrada a otra monoespaciada, no a sans
    # la monoespaciada es para cifras: se usa en la cifra, el margen y las celdas de tabla
    hoja = theme.css(False)
    assert ".cifra" in hoja and ".margen" in hoja


# --------------------------------------------------------------------------- la banda
def test_c32_la_banda_distingue_lo_que_el_modelo_controla_de_lo_que_no():
    svg = theme.banda_svg(0.26, [theme.Tramo(0.01, "#111111", "medido"),
                                 theme.Tramo(0.04, "#222222", "viento", rayada=True)])
    assert svg.count("<rect") >= 2
    assert "pattern" in svg and "rotate(45)" in svg      # lo que no controla el modelo va rayado
    assert svg.index("#222222") < svg.index("#111111")  # la ancha se pinta debajo


def test_c32_la_banda_rotula_sus_extremos_y_se_describe_para_quien_no_la_ve():
    svg = theme.banda_svg(0.26, [theme.Tramo(0.04, "#222222", "viento", rayada=True)])
    assert "0.220" in svg and "0.300" in svg
    aria = re.search(r'aria-label="([^"]+)"', svg)
    assert aria and "viento" in aria.group(1) and "0.260" in aria.group(1)


def test_c32_la_banda_acepta_un_formateador_y_no_solo_una_cadena():
    """Un tiempo se rotula en h:mm:ss, no en segundos crudos."""
    svg = theme.banda_svg(3600.0, [theme.Tramo(60.0, "#333333", "modelo")],
                          formato=lambda s: f"{int(s) // 3600}:{(int(s) % 3600) // 60:02d}")
    assert "0:59" in svg and "1:01" in svg
    assert "3540" not in svg


def test_c32_una_banda_sin_margen_no_dibuja_nada():
    assert theme.banda_svg(1.0, []) == ""
    assert theme.banda_svg(1.0, [theme.Tramo(0.0, "#444444", "nada")]) == ""


def test_c32_la_lectura_pone_el_margen_junto_al_valor():
    html = theme.lectura("CdA", "0.261", margen="0.009", unidad="m²",
                         pie=[("8", "pares")], banda="<svg></svg>")
    assert 'class="cifra">0.261<' in html
    assert 'class="margen">± 0.009<' in html
    # el margen va dentro del mismo bloque que la cifra, no en otro sitio de la página
    cifra = html.index('class="cifra"')
    assert cifra < html.index('class="margen"') < html.index('class="lectura-pie"')
    assert "<b>8</b> pares" in html


def test_c32_los_componentes_escapan_lo_que_les_pasan():
    """Los nombres de fichero del usuario acaban en estos bloques."""
    html = theme.lectura("<script>x</script>", "1", pie=[("<b>", "&")])
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "&amp;" in html
    assert "<script>" not in theme.vacio("<script>", "a & b")


# --------------------------------------------------------------------------- el puente
def test_c31_el_cda_medido_pasa_al_simulador_y_se_puede_corregir():
    """Lo que une los dos módulos: medir aquí, predecir allí, con el valor editable.

    Es el flujo que pidió el usuario: «podré usar ese valor estimado o un valor similar
    ligeramente corregido para hacer mi predicción».
    """
    fixture = RAIZ / "tests" / "fixtures" / "recorrido2_30mar2025.fit"
    at = AppTest.from_file(APP, default_timeout=300).run()
    at.segmented_control(key="modulo").set_value("estimador")
    at = at.run()
    at.number_input(key="p_masa_total").set_value(MASA)
    at = at.run()
    at.file_uploader(key="est_fit").set_value(
        (fixture.name, fixture.read_bytes(), "application/octet-stream"))
    at = at.run()
    next(b for b in at.button if "Buscar tramos" in b.label).click().run()
    next(b for b in at.button if b.key == "btn_aplicar_pares").click().run()
    assert not at.exception, at.exception

    # el valor que se traspasa es EL MEDIDO, no un rango que contenga el valor por defecto:
    # pedir solo 0,20 < cda < 0,35 no distinguiría un traspaso roto, porque el defecto es 0,27
    from core import Params
    from core.cda_estimator import combine_pairs, find_paired_segments
    from core.validation import read_fit

    esperado = round(combine_pairs(find_paired_segments(
        read_fit(fixture.read_bytes(), fixture.name), Params(masa_total=MASA), maximo=6))[0], 3)
    assert esperado != round(Params().cda, 3), (
        "el CdA medido coincide con el valor por defecto: este test no probaría nada")

    at.segmented_control(key="modulo").set_value("simulador")
    at = at.run()
    campo = at.number_input(key="p_cda")
    assert campo.value == pytest.approx(esperado, abs=1e-6), (
        f"el simulador muestra {campo.value} y el estimador midió {esperado}")
    assert campo.disabled is False
    notas = " ".join(c.value for c in at.caption)
    assert "estimador" in notas.lower() and "corregirlo a mano" in notas

    medido = campo.value
    campo.set_value(round(medido - 0.012, 3))
    at = at.run()
    assert not at.exception
    assert at.number_input(key="p_cda").value == pytest.approx(medido - 0.012, abs=1e-6)


def test_c30_el_camino_recomendado_tambien_examina_la_coherencia():
    """El hueco que encontró la revisión: se podía fijar en un perfil el CdA de una actividad
    incoherente **por el camino que la propia herramienta recomienda**, sin un solo aviso.

    El aviso existía en la calibración por tiempo total, que es justo el método que el protocolo
    relegó a comprobación. Aquí se recorre el camino bueno con la salida del 04-may-2025, que el
    criterio 30 marca como incoherente.
    """
    fixture = RAIZ / "tests" / "fixtures" / "recorrido2_04may2025.fit"
    at = AppTest.from_file(APP, default_timeout=300).run()
    at.segmented_control(key="modulo").set_value("estimador")
    at = at.run()
    at.number_input(key="p_masa_total").set_value(MASA)
    at = at.run()
    at.file_uploader(key="est_fit").set_value(
        (fixture.name, fixture.read_bytes(), "application/octet-stream"))
    at = at.run()
    next(b for b in at.button if "Buscar tramos" in b.label).click().run()
    assert not at.exception, at.exception

    # el veredicto se enseña junto al número, no escondido en otra pestaña
    avisos = " ".join(w.value for w in at.warning)
    assert "No uses esta actividad para calibrar" in avisos

    # y al llevarlo al simulador, el panel de guardar perfil avisa antes de fijarlo
    next(b for b in at.button if b.key == "btn_aplicar_pares").click().run()
    at.segmented_control(key="modulo").set_value("simulador")
    at = at.run()
    assert not at.exception, at.exception
    avisos = " ".join(w.value for w in at.warning)
    assert "marcada como" in avisos and "incoherente" in avisos


def test_c30_una_actividad_coherente_no_dispara_el_aviso_al_guardar():
    """El reverso: avisar siempre sería tan inútil como no avisar nunca."""
    fixture = RAIZ / "tests" / "fixtures" / "recorrido2_30mar2025.fit"
    at = AppTest.from_file(APP, default_timeout=300).run()
    at.segmented_control(key="modulo").set_value("estimador")
    at = at.run()
    at.number_input(key="p_masa_total").set_value(MASA)
    at = at.run()
    at.file_uploader(key="est_fit").set_value(
        (fixture.name, fixture.read_bytes(), "application/octet-stream"))
    at = at.run()
    next(b for b in at.button if "Buscar tramos" in b.label).click().run()
    next(b for b in at.button if b.key == "btn_aplicar_pares").click().run()
    at.segmented_control(key="modulo").set_value("simulador")
    at = at.run()
    assert not at.exception
    assert not any("incoherente" in w.value for w in at.warning)


def test_c32_la_configuracion_de_streamlit_no_duplica_los_tokens():
    """`.streamlit/config.toml` repite cuatro colores de la paleta para que el cromo propio de
    Streamlit salga en tono. Si se desincronizan, el borde del sistema deja de encajar y nadie
    se entera: esto lo impide.
    """
    import re

    conf = (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    valores = dict(re.findall(r'^\s*(\w+)\s*=\s*"(#[0-9A-Fa-f]{6})"', conf, re.M))
    esperado = {"primaryColor": theme.CLARO.senal, "backgroundColor": theme.CLARO.papel,
                "secondaryBackgroundColor": theme.CLARO.superficie,
                "textColor": theme.CLARO.tinta}
    for clave, color in esperado.items():
        assert clave in valores, f"{clave} no está en config.toml"
        assert valores[clave].lower() == color.lower(), (
            f"{clave}: config.toml dice {valores[clave]} y theme.CLARO dice {color}")
    sobran = set(valores) - set(esperado)
    assert not sobran, f"colores en config.toml que no salen de la paleta: {sobran}"


def test_c21_la_plantilla_de_graficos_sale_de_los_tokens():
    """La mitad del criterio 21 que no tenía test: el modo oscuro afecta también a los gráficos."""
    claro, oscuro = theme.plantilla_plotly(False), theme.plantilla_plotly(True)
    assert claro != oscuro
    for plantilla, paleta in ((claro, theme.CLARO), (oscuro, theme.OSCURO)):
        cap = plantilla["layout"]
        assert cap["paper_bgcolor"] == paleta.superficie
        assert cap["plot_bgcolor"] == paleta.superficie
        assert cap["font"]["color"] == paleta.tinta
        assert cap["colorway"][0] == paleta.senal
        assert cap["xaxis"]["gridcolor"] == paleta.regla
    # y la tipografía de los ejes es la de las cifras, no la de interfaz
    assert "Mono" in claro["layout"]["xaxis"]["tickfont"]["family"]


def test_c21_aplicar_a_figura_escribe_los_colores_en_el_layout_no_solo_en_la_plantilla():
    """La plantilla **no basta**: el componente de Plotly de Streamlit escribe su propio
    `paper_bgcolor` por encima de ella, incluso con `theme=None`, así que el modo oscuro no llegaba
    al gráfico. Lo que gana es lo escrito directamente en el `layout`.

    Esto se comprueba aquí, en la figura, y en `tests/test_navegador.py` sobre lo que el navegador
    pinta de verdad. El test anterior era una expresión regular que buscaba `template=` en el
    fuente: pasaba en verde con la plantilla completamente ignorada.
    """
    import plotly.graph_objects as go

    for oscuro, paleta in ((False, theme.CLARO), (True, theme.OSCURO)):
        fig = theme.aplicar_a_figura(go.Figure(go.Scatter(x=[0, 1], y=[0, 1])), oscuro)
        assert fig.layout.paper_bgcolor == paleta.superficie
        assert fig.layout.plot_bgcolor == paleta.superficie
        assert fig.layout.font.color == paleta.tinta
        assert fig.layout.template is not None


def test_c21_la_app_pide_sus_graficos_sin_el_tema_de_streamlit():
    """`st.plotly_chart(fig)` usa `theme="streamlit"` por defecto, que sustituye la plantilla
    propia por una derivada de `config.toml`, siempre clara. Se comprueba sobre los protos que la
    app emite —`theme` vacío es `theme=None`—, no buscando cadenas en el fuente."""
    import sys

    sys.path.insert(0, str(RAIZ / "app"))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(RAIZ / "app" / "streamlit_app.py"), default_timeout=180).run()
    at.number_input(key="p_masa_total").set_value(90.0)
    at = at.run()
    at.button(key="btn_simular").click()
    at = at.run()
    graficos = at.get("plotly_chart")
    assert graficos, "no hay ningún gráfico que comprobar"
    for g in graficos:
        assert g.proto.theme == "", (
            f"gráfico pedido con theme={g.proto.theme!r}: la plantilla no se aplicará")
