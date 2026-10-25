"""Simulador de ciclismo para triatlón (sin drafting) y contrarreloj — MVP en Streamlit.

Ejecutar desde la raíz del proyecto:  streamlit run app/streamlit_app.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import theme
from core import (CATEGORIES, REQUIRED_PARAMS, ParamError, Params, SURFACES,
                  build_profile, parse_gpx, simulate, specs_by_category, validate_params)
from core.params import MODULOS, PARAM_SPECS, specs_for_module
from core.cda_estimator import (combine_estimates, combine_pairs, estimate_cda,
                                find_paired_segments, ride_distance_km, search_summary)
from core.coherence import CDA_PLAUSIBLE, check_coherence
from core.exports import (csv_bytes, tabla_bloques, tabla_coherencia, tabla_segmentos,
                          tabla_tramos, tabla_validacion)
from core.i18n import (ETIQUETAS_IDIOMA, IDIOMAS, cabeceras, categoria, param_help, param_label,
                       superficie as superficie_label, t)
from core.profiles import (PROFILE_KEYS, delete_profile, load_profiles, profile_from_params,
                           profiles_path, save_profile)
from core.sensitivity import RELEVANCE_THRESHOLD_PCT, sensitivity
from core.synthetic import demo_track
from core.uncertainty import bands
from core.wheels import ETRTO_MANUAL, label_for as etrto_label
from core.validation import calibrate_cda, read_fit, replay

st.set_page_config(page_title="Simulador de ciclismo — triatlón / CRI", layout="wide")


def elegir_idioma() -> str:
    """Selector de idioma. Va primero porque todas las etiquetas dependen de él."""
    return st.sidebar.segmented_control(
        "Idioma / Language", IDIOMAS, default=IDIOMAS[0], key="idioma",
        format_func=lambda c: ETIQUETAS_IDIOMA[c]) or IDIOMAS[0]


def elegir_modulo(idioma: str) -> str:
    """Selector de módulo (criterio 31). Decide qué se pide y qué se enseña.

    El módulo inicial se puede fijar desde fuera de dos maneras, y las dos valen: `?modo=estimador`
    en la URL, o `--modo=estimador` en la línea de órdenes, que es por donde lo pasan
    `run.sh --estimador` y `run.bat --estimador`.
    """
    if "modulo" not in st.session_state:
        pedido = str(st.query_params.get("modo", "")).strip().lower()
        if pedido not in MODULOS:
            pedido = next((a.split("=", 1)[1].strip().lower() for a in sys.argv
                           if a.startswith("--modo=")), "")
        st.session_state["modulo"] = pedido if pedido in MODULOS else "simulador"
    elegido = st.sidebar.segmented_control(
        t("modulo", idioma), MODULOS, key="modulo",
        format_func=lambda m: t(f"modulo_{m}", idioma))
    return elegido or st.session_state.get("modulo") or "simulador"


def aplicar_tema(idioma: str):
    """Interruptor de modo oscuro. Devuelve la plantilla de los gráficos.

    El tema base es claro (`.streamlit/config.toml`). Los dos temas salen de los mismos tokens
    (`app/theme.py`), gráficos incluidos: aquí no se escribe ningún color a mano.
    """
    oscuro = st.sidebar.toggle(t("modo_oscuro", idioma), value=False, key="modo_oscuro",
                               help=t("modo_oscuro_ayuda", idioma))
    st.markdown(theme.css(oscuro), unsafe_allow_html=True)
    return oscuro, theme.paleta(oscuro)


# ----------------------------------------------------------------------------- utilidades
def fmt_time(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def _decimals(step) -> int:
    if not step:
        return 2
    txt = f"{step:.10f}".rstrip("0")
    return len(txt.split(".")[1]) if "." in txt else 0


#: Desplegables cuya clave interna se muestra con una etiqueta legible.
FORMATO_OPCIONES = {"etrto": etrto_label}      # se le pasa el idioma en param_widget


def _desactivado(spec) -> bool:
    """El perímetro medido solo se habilita con la medida de rueda en «manual»."""
    if spec.key == "perimetro_mm":
        return st.session_state.get("p_etrto", Params().etrto) != ETRTO_MANUAL
    return False


def param_widget(spec, container, idioma=IDIOMAS[0]):
    key = f"p_{spec.key}"
    etiqueta = param_label(spec, idioma)
    ayuda = param_help(spec, idioma)
    label = f"{etiqueta} ({spec.unit})" if spec.unit else etiqueta
    help_ = ayuda or None
    if _desactivado(spec):
        container.number_input(label, min_value=0.0, max_value=float(spec.maximum), value=0.0,
                               step=float(spec.step or 1.0), key=key, disabled=True,
                               help=ayuda + t("desactivado_nota", idioma))
        return None
    if spec.kind == "choice":
        formato = FORMATO_OPCIONES.get(spec.key)
        if formato is not None:
            formato = lambda c, f=formato: f(c, idioma)          # noqa: E731
        if spec.key == "superficie":
            formato = lambda c: superficie_label(c, idioma)      # noqa: E731
        return container.selectbox(label, spec.choices, index=spec.choices.index(spec.default),
                                   key=key, help=help_, format_func=formato or str)
    if spec.kind == "bool":
        return container.checkbox(label, value=bool(spec.default), key=key, help=help_)
    step = float(spec.step or 1.0)
    fmt = f"%.{_decimals(step)}f"
    if spec.key in REQUIRED_PARAMS:       # obligatorio: sin valor por defecto
        v = container.number_input(label, min_value=float(spec.minimum), max_value=float(spec.maximum),
                                   value=None, step=step, format=fmt, key=key, help=help_,
                                   placeholder=t("obligatorio", idioma))
        return None if v is None else float(v)
    if spec.kind == "optional_float":
        v = container.number_input(label, min_value=0.0, max_value=float(spec.maximum), value=0.0,
                                   step=step, format=fmt, key=key, help=help_)
        return None if not v else float(v)       # 0 o vacío = «sin especificar»
    return float(container.number_input(label, min_value=float(spec.minimum),
                                         max_value=float(spec.maximum), value=float(spec.default),
                                         step=step, format=fmt, key=key, help=help_))


@st.cache_data(show_spinner=False)
def cached_track(data: bytes, idioma: str = "es"):
    return parse_gpx(data, idioma)


@st.cache_data(show_spinner=False)
def cached_demo():
    return demo_track()


@st.cache_data(show_spinner=False)
def cached_sim(track, params_json: str, idioma: str = "es"):
    d = json.loads(params_json)
    d["tramos_superficie"] = tuple(tuple(t) for t in d["tramos_superficie"])
    p = Params(**d)
    return simulate(build_profile(track, p, idioma), p)


def params_json(p: Params) -> str:
    return json.dumps(p.__dict__, default=list, sort_keys=True)


#: Claves de sesión que borra el botón de borrado (los perfiles del disco NO se tocan).
PREFIJOS_BORRABLES = ("p_", "sens_", "cda_", "est_", "perfil_", "tramos_", "sim_")
# Los ficheros subidos también se borran: `est_fit` ya caía por el prefijo `est_`, y que el GPX
# y los `.fit` de validación se quedaran era una asimetría, no una decisión (revisión 6-oct-2026).
# `fit_sel` estuvo aquí sin corresponder a ningún widget; `km_block` sí existe, pero hasta octubre
# de 2026 el deslizador se creaba sin `key` y se restablecía por accidente, no por esta lista.
CLAVES_BORRABLES = ("cal_sel", "coherencia", "cda_de_estimador", "gpx_file", "val_fits",
                    "km_block", "tramos_editor")

#: Lo que el borrado **no** toca: las tres preferencias de interfaz. Idioma, módulo y modo oscuro
#: no son datos ni parámetros del modelo, son cómo está mirando el usuario la herramienta; que un
#: botón de «borrar» le cambiara el idioma sería hostil. Antes `modo_oscuro` sí se borraba, y el
#: resultado era peor que no tocarlo: el tema volvía a claro y el interruptor seguía encendido.
PREFERENCIAS_DE_INTERFAZ = ("idioma", "modulo", "modo_oscuro")


def valor_inicial_widget(spec):
    """Lo que el widget de este parámetro enseña cuando nadie lo ha tocado.

    Tiene que coincidir con lo que `param_widget` pinta sin estado: `None` en el obligatorio (sale
    el marcador de «obligatorio») y 0 en los opcionales vacíos.
    """
    if spec.key in REQUIRED_PARAMS:
        return None
    if spec.kind == "optional_float" or _desactivado(spec):
        return 0.0
    if spec.kind == "bool":
        return bool(spec.default)
    if spec.kind == "choice":
        return spec.default
    return float(spec.default)


def borrar_todo():
    """Devuelve la interfaz a su estado inicial. No borra los perfiles guardados en disco.

    Los widgets se **reasignan** a su valor inicial en vez de borrarles la clave. Borrarla deja
    el estado interno limpio pero la pantalla con el valor anterior pintado, y entonces la página
    dice «Falta la masa total» mientras el campo sigue enseñando 90,0, o el interruptor de modo
    oscuro sigue encendido con el tema ya en claro. Los tests con `AppTest` no lo veían porque
    leen `session_state`, que sí quedaba limpio.
    """
    for k in list(st.session_state.keys()):
        if (k.startswith(PREFIJOS_BORRABLES) or k in CLAVES_BORRABLES) \
                and k not in PREFERENCIAS_DE_INTERFAZ:
            del st.session_state[k]
    for spec in PARAM_SPECS:
        st.session_state[f"p_{spec.key}"] = valor_inicial_widget(spec)


# ----------------------------------------------------------------------------- barra lateral
IDIOMA = elegir_idioma()
st.sidebar.title(t("titulo", IDIOMA))
st.sidebar.caption(t("subtitulo", IDIOMA))

MODULO = elegir_modulo(IDIOMA)
ES_ESTIMADOR = MODULO == "estimador"
OSCURO, COLOR = aplicar_tema(IDIOMA)

# El estimador no pide GPX: su entrada es un .fit y nada más (criterio 31).
gpx_file = (None if ES_ESTIMADOR else
            st.sidebar.file_uploader(t("subir_gpx", IDIOMA), type=["gpx"], key="gpx_file"))

# --- perfiles de bici: se cargan ANTES de crear los widgets para poder fijar sus valores
def _cargar_perfil(nombre: str):
    prof = load_profiles().get(nombre)
    if prof is None:
        return
    for k in PROFILE_KEYS:
        valor = getattr(prof, k)
        if valor is None:                        # un opcional vacío se escribe como 0 en la UI
            valor = 0.0
        st.session_state[f"p_{k}"] = valor
    st.session_state["perfil_activo"] = nombre


with st.sidebar.expander(t("perfil_bici", IDIOMA), expanded=True):
    perfiles = load_profiles()
    if perfiles:
        elegido = st.selectbox(t("perfil_guardado", IDIOMA), list(perfiles), key="perfil_sel")
        prof = perfiles[elegido]
        st.caption(t("perfil_resumen", IDIOMA, cda=prof.cda, masa=prof.masa_total,
                     fecha=prof.actualizado))
        st.caption(t("perfil_calibrado" if prof.calibrado else "perfil_sin_calibrar", IDIOMA)
                   + prof.origen_cda)
        b1, b2 = st.columns(2)
        b1.button(t("perfil_cargar", IDIOMA), key="btn_cargar_perfil", on_click=_cargar_perfil,
                  args=(elegido,),
                  use_container_width=True)
        if b2.button(t("perfil_borrar", IDIOMA), key="btn_borrar_perfil", use_container_width=True):
            delete_profile(elegido)
            st.rerun()
    else:
        st.caption(t("perfil_sin_perfiles", IDIOMA))
    if st.session_state.get("perfil_activo"):
        st.caption(t("perfil_cargado", IDIOMA, nombre=st.session_state["perfil_activo"]))

values = {}
# Cada módulo pide solo los parámetros que usa: 22 de 39 en el estimador (criterio 31).
CATEGORIAS_MODULO = [c for c in CATEGORIES if specs_by_category(c, modulo=MODULO)]
tabs = st.sidebar.tabs([categoria(c, IDIOMA) for c in CATEGORIAS_MODULO])
for tab, cat in zip(tabs, CATEGORIAS_MODULO):
    with tab:
        for spec in specs_by_category(cat, advanced=False, modulo=MODULO):
            values[spec.key] = param_widget(spec, st, IDIOMA)
        adv = specs_by_category(cat, advanced=True, modulo=MODULO)
        if adv:
            with st.expander(t("avanzados", IDIOMA)):
                for spec in adv:
                    values[spec.key] = param_widget(spec, st, IDIOMA)
        # la superficie por tramos de km es del recorrido: en el estimador no hay recorrido
        if cat == "Variables externas" and not ES_ESTIMADOR:
            st.markdown(t("superficie_tramos", IDIOMA))
            st.caption(t("superficie_tramos_nota", IDIOMA))
            tramos_df = st.data_editor(
                pd.DataFrame({"km_inicio": pd.Series(dtype=float), "km_fin": pd.Series(dtype=float),
                              "superficie": pd.Series(dtype=str)}),
                num_rows="dynamic", key="tramos_editor",
                column_config={
                    "superficie": st.column_config.SelectboxColumn(
                        cabeceras(["superficie"], IDIOMA)["superficie"], options=list(SURFACES),
                        # las opciones también se traducen: salían «liso/normal/rugoso» en inglés
                        format_func=lambda c: superficie_label(c, IDIOMA)),
                    "km_inicio": st.column_config.NumberColumn(
                        cabeceras(["km_inicio"], IDIOMA)["km_inicio"], min_value=0.0),
                    "km_fin": st.column_config.NumberColumn(
                        cabeceras(["km_fin"], IDIOMA)["km_fin"], min_value=0.0)})
            tramos = []
            for _, r in tramos_df.dropna().iterrows():
                tramos.append((float(r["km_inicio"]), float(r["km_fin"]), str(r["superficie"])))
            values["tramos_superficie"] = tuple(tramos)

# --- botones de acción: la simulación NO se lanza en cada cambio de parámetro
st.sidebar.divider()
if ES_ESTIMADOR:
    pulsado_simular = False
    st.sidebar.button(t("boton_borrar", IDIOMA), key="btn_borrar_todo", on_click=borrar_todo,
                      use_container_width=True, help=t("boton_borrar_ayuda", IDIOMA))
else:
    c_sim, c_borrar = st.sidebar.columns([3, 2])
    pulsado_simular = c_sim.button(t("boton_simular", IDIOMA), key="btn_simular", type="primary",
                                   use_container_width=True,
                                   help=t("boton_simular_ayuda", IDIOMA))
    c_borrar.button(t("boton_borrar", IDIOMA), key="btn_borrar_todo", on_click=borrar_todo,
                    use_container_width=True, help=t("boton_borrar_ayuda", IDIOMA))

st.markdown(theme.cabecera_modulo(t(f"cab_{MODULO}", IDIOMA), t(f"cab_{MODULO}_sub", IDIOMA)),
            unsafe_allow_html=True)

if not ES_ESTIMADOR and st.session_state.get("cda_de_estimador"):
    st.sidebar.caption(t("cda_viene_del_estimador", IDIOMA,
                         origen=st.session_state["cda_de_estimador"]))

if values.get("etrto") == ETRTO_MANUAL and not values.get("perimetro_mm"):
    st.warning(t("falta_perimetro", IDIOMA))
    st.stop()

faltan = [param_label(sp, IDIOMA) for sp in specs_for_module(MODULO)
          if sp.key in REQUIRED_PARAMS and values.get(sp.key) is None]
if faltan:
    st.markdown(theme.vacio(t("falta_masa_titulo", IDIOMA),
                            t("falta_masa", IDIOMA, faltan=", ".join(faltan))),
                unsafe_allow_html=True)
    st.stop()

try:
    params = validate_params(Params(**values), IDIOMA)
except ParamError as e:
    st.error(t("params_invalidos", IDIOMA, error=e))
    st.stop()

st.sidebar.caption(
    t("pie_resumen_estimador" if ES_ESTIMADOR else "pie_resumen", IDIOMA,
      masa=params.masa_total, cda=params.cda, etrto=params.etrto,
      per=params.perimetro_efectivo_mm))

with st.sidebar.expander(t("guardar_perfil_titulo", IDIOMA)):
    nombre_nuevo = st.text_input(t("guardar_nombre", IDIOMA), key="perfil_nombre",
                                 placeholder=t("guardar_nombre_ph", IDIOMA))
    origen = st.text_input(t("guardar_origen", IDIOMA), key="perfil_origen",
                           placeholder=t("guardar_origen_ph", IDIOMA))
    calibrado = st.checkbox(t("guardar_calibrado", IDIOMA), key="perfil_calibrado")
    # Criterio 30: no se guarda a ciegas un CdA que viene de una actividad marcada como incoherente.
    if st.session_state.get("cda_cal_incoherente"):
        st.warning(t("coh_guardar_incoherente", IDIOMA))
    if st.button(t("guardar_boton", IDIOMA), key="btn_guardar_perfil"):
        try:
            prof = profile_from_params(nombre_nuevo, params, origen_cda=origen.strip(),
                                       calibrado=calibrado)
        except ParamError as e:
            st.error(str(e))       # incluye nombre vacío y CdA calibrado sin origen (regla del núcleo)
        else:
            save_profile(prof)
            st.session_state["perfil_activo"] = prof.nombre
            st.success(t("guardar_ok", IDIOMA, nombre=prof.nombre))
            st.rerun()
    st.caption(t("guardar_nota", IDIOMA, fichero=profiles_path().name))

# ----------------------------------------------------------------------------- ruta
if ES_ESTIMADOR:
    track, using_demo = None, False
elif gpx_file is not None:
    try:
        track = cached_track(gpx_file.getvalue(), IDIOMA)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    using_demo = False
else:
    track = cached_demo()
    using_demo = True

# --- la simulación solo se ejecuta al pulsar el botón (criterio 20)
clave_actual = (params_json(params), using_demo, getattr(gpx_file, "name", ""))
if pulsado_simular:
    try:
        with st.spinner(t("simulando", IDIOMA)):
            st.session_state["sim_result"] = cached_sim(track, params_json(params), IDIOMA)
        st.session_state["sim_clave"] = clave_actual
    except ValueError as e:
        st.error(str(e))
        st.session_state.pop("sim_result", None)

result = st.session_state.get("sim_result")
desfasado = result is not None and st.session_state.get("sim_clave") != clave_actual

# ----------------------------------------------------------------------------- principal
if ES_ESTIMADOR:
    # El estimador es su propio módulo: ni resultados de simulación, ni sensibilidad, ni
    # validación con FIT. La pestaña de validación se dibujaba aquí y **dependía de nueve
    # parámetros que este módulo no muestra**, el `cda` entre ellos, clavado en silencio en su
    # valor por defecto: medido, cambiarlo movía el error de tiempo que esa pestaña presenta de
    # −0,53 % a +9,62 %. Un módulo que presume de funcionar solo con sus parámetros no puede
    # enseñar números gobernados por los que esconde (criterio 31). La calibración por tiempo
    # total vive en el simulador, donde todos sus parámetros están a la vista.
    #
    # El examen de coherencia sí se queda: `coherence.params_del_examen` fija la configuración a
    # los parámetros del estimador y deja el resto en su valor por defecto, así que su veredicto
    # no depende de nada oculto.
    tab_est, tab_model = st.tabs([t(k, IDIOMA) for k in ("tab_estimador", "tab_modelo")])
    tab_res = tab_sens = tab_val = None
else:
    tab_res, tab_sens, tab_val, tab_est, tab_model = st.tabs(
        [t(k, IDIOMA) for k in ("tab_resultados", "tab_sensibilidad", "tab_validacion",
                                "tab_estimador", "tab_modelo")])

# Estos dos bloques son solo del simulador (criterio 31).
if not ES_ESTIMADOR:
    with tab_res:
        if result is None:
            st.markdown(theme.vacio(t("sim_vacio_titulo", IDIOMA),
                                    t("sim_vacio_demo" if using_demo else "sim_vacio_texto",
                                      IDIOMA)), unsafe_allow_html=True)
        else:
            if desfasado:
                st.warning(t("desfasado", IDIOMA))
            if using_demo:
                st.info(t("usando_demo", IDIOMA))
            for w in result.warnings:
                st.warning(w)
            pr = result.profile
            # El tiempo, con sus dos márgenes dibujados: la banda estrecha y sólida es la del
            # modelo y la ancha y rayada la del día (criterios 29 y 32).
            b_modelo, b_dia = bands(result.tiempo_s, IDIOMA)
            st.markdown(
                theme.lectura(
                    t("m_tiempo", IDIOMA), fmt_time(result.tiempo_s),
                    margen=t("banda_margen", IDIOMA, min=fmt_time(b_modelo.margen_s),
                             pct=b_modelo.pct),
                    pie=[(f"{result.velocidad_media_kmh:.1f} km/h", t("m_velocidad", IDIOMA)),
                         (f"{result.distancia_km:.1f} km", t("m_distancia", IDIOMA)),
                         (f"{pr.total_ascent:.0f} m", t("m_desnivel", IDIOMA)),
                         (f"{result.potencia_media_w:.0f} W", t("m_potencia", IDIOMA)),
                         (f"{result.np_w:.0f} W", t("m_np", IDIOMA)),
                         (f"{result.vi:.2f}" if result.vi else "—", t("m_vi", IDIOMA))]
                        + ([(f"{result.if_:.2f}", t("m_if", IDIOMA))] if result.if_ else []),
                    banda=theme.banda_svg(
                        result.tiempo_s,
                        [theme.Tramo(b_modelo.margen_s, COLOR.senal,
                                     t("banda_leyenda_modelo", IDIOMA, pct=b_modelo.pct)),
                         theme.Tramo(b_dia.margen_s, COLOR.ocre,
                                     t("banda_leyenda_dia", IDIOMA, pct=b_dia.pct),
                                     rayada=True)],
                        formato=fmt_time, ident="t")),
                unsafe_allow_html=True)
            # la lectura de arriba ya enseña el valor y las bandas: aquí solo los dos rangos
            st.caption(t("banda_rangos", IDIOMA,
                         a=fmt_time(b_modelo.low_s), b=fmt_time(b_modelo.high_s),
                         p1=b_modelo.pct, c=fmt_time(b_dia.low_s), d=fmt_time(b_dia.high_s),
                         p2=b_dia.pct)
                       + f"  \n±{b_modelo.pct:.1f} % — {b_modelo.origen}."
                       + f"  \n±{b_dia.pct:.0f} % — {b_dia.origen}."
                       + "  \n" + t("banda_ruta_nueva_corto", IDIOMA))
            lim = int((result.limit_seg > 0).sum())
            if lim:
                st.caption(t("limites_activos", IDIOMA, n=lim, total=len(result.dt),
                             pct=lim / len(result.dt) * 100))

            km = np.concatenate([[0.0], pr.s[1:]]) / 1000.0
            kmm = result.s_mid_km
            # Las cuatro magnitudes que enumera el Alcance de la spec —velocidad, potencia,
            # **pendiente suavizada** y CdA efectivo— más la elevación, que es la que orienta.
            # La pendiente faltaba: se dibujaba la elevación en su lugar y solo aparecía en la
            # tabla, y el test del criterio 11 contaba gráficas en vez de mirar cuáles eran.
            fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.035,
                                row_heights=[0.18, 0.18, 0.23, 0.23, 0.18],
                                subplot_titles=tuple(t(k, IDIOMA) for k in (
                                    "g_elevacion", "g_pendiente", "g_velocidad", "g_potencia",
                                    "g_cda")))
            fig.add_trace(go.Scatter(x=km, y=pr.ele, name=t("g_elevacion", IDIOMA), fill="tozeroy",
                                     line=dict(width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=kmm, y=pr.grade * 100.0, name=t("g_pendiente", IDIOMA),
                                     line=dict(width=1)), row=2, col=1)
            fig.add_trace(go.Scatter(x=kmm, y=result.v_seg * 3.6, name=t("g_velocidad", IDIOMA)),
                          row=3, col=1)
            fig.add_trace(go.Scatter(x=kmm, y=result.power_nominal, name=t("g_potencia_perfil", IDIOMA),
                                     line=dict(width=1, dash="dot")), row=4, col=1)
            fig.add_trace(go.Scatter(x=kmm, y=result.power_effective,
                                     name=t("g_potencia_aplicada", IDIOMA)), row=4, col=1)
            fig.add_trace(go.Scatter(x=kmm, y=result.cda_seg, name=t("g_cda", IDIOMA)), row=5, col=1)
            fig.update_yaxes(title_text="%", row=2, col=1)
            fig.update_xaxes(title_text="km", row=5, col=1)
            fig.update_layout(height=900, margin=dict(l=10, r=10, t=40, b=10),
                              legend=dict(orientation="h"))
            theme.aplicar_a_figura(fig, OSCURO)
            # `theme=None` es obligatorio: el valor por defecto (`theme="streamlit"`) sustituye
            # la plantilla del sistema de diseño por una derivada de `.streamlit/config.toml`, que
            # es siempre clara, así que el modo oscuro no llegaba a ningún gráfico (medido:
            # lienzo #F2F5F7 sobre página oscura, y el texto de los ejes a 3,39:1).
            st.plotly_chart(fig, theme=None)

            km_block = st.select_slider(t("tabla_bloques", IDIOMA), options=[0.5, 1.0, 2.0, 5.0],
                                        value=1.0, key="km_block")
            tabla = tabla_bloques(result, km_block)
            st.dataframe(tabla.round(2).rename(columns=cabeceras(tabla.columns, IDIOMA)),
                         hide_index=True)
            st.caption(t("tabla_bloques_nota", IDIOMA, p1=b_modelo.pct, p2=b_dia.pct))
            st.caption(t("csv_nota", IDIOMA))
            d1, d2 = st.columns(2)
            d1.download_button(t("descargar_bloques", IDIOMA), csv_bytes(tabla),
                               "simulacion_bloques.csv", "text/csv")
            d2.download_button(t("descargar_tramos", IDIOMA), csv_bytes(tabla_tramos(result)),
                               "simulacion_tramos.csv", "text/csv")

# Estos dos bloques son solo del simulador (criterio 31).
if not ES_ESTIMADOR:
    with tab_sens:
        st.markdown(t("sens_intro", IDIOMA))
        if st.button(t("sens_boton", IDIOMA), key="btn_sensibilidad"):
            with st.spinner(t("sens_calculando", IDIOMA)):
                st.session_state["sens_rows"] = sensitivity(track, params, idioma=IDIOMA)
                st.session_state["sens_key"] = (params_json(params), using_demo, getattr(gpx_file, "name", ""))
        rows = st.session_state.get("sens_rows")
        if rows and st.session_state.get("sens_key") != (params_json(params), using_demo, getattr(gpx_file, "name", "")):
            st.caption(t("sens_desfasado", IDIOMA))
        if rows:
            df = pd.DataFrame(rows)
            show = df[["etiqueta", "categoria", "unidad", "valor_base", "valor_menos", "valor_mas",
                       "dt_menos_%", "dt_mas_%", "efecto_max_%", "relevante", "interfaz", "sugerencia", "nota"]]
            cabs = dict(cabeceras(show.columns, IDIOMA))
            cabs.update({"dt_menos_%": t("sens_col_menos", IDIOMA),
                         "dt_mas_%": t("sens_col_mas", IDIOMA)})
            st.dataframe(show.rename(columns=cabs), hide_index=True)
            top = df[df["efecto_max_%"] > 0].head(15).iloc[::-1]
            bar = go.Figure()
            bar.add_trace(go.Bar(y=top["etiqueta"], x=top["dt_menos_%"], orientation="h", name="−10 %"))
            bar.add_trace(go.Bar(y=top["etiqueta"], x=top["dt_mas_%"], orientation="h", name="+10 %"))
            bar.add_vline(x=RELEVANCE_THRESHOLD_PCT, line_dash="dot")
            bar.add_vline(x=-RELEVANCE_THRESHOLD_PCT, line_dash="dot")
            bar.update_layout(barmode="relative", height=520, xaxis_title=t("sens_eje", IDIOMA),
                              margin=dict(l=10, r=10, t=10, b=10))
            theme.aplicar_a_figura(bar, OSCURO)
            st.plotly_chart(bar, theme=None)
            st.caption(t("sens_nota", IDIOMA, umbral=RELEVANCE_THRESHOLD_PCT))

# Solo del simulador (criterio 31): la validación con FIT y la calibración por tiempo
# total dependen de parámetros que el módulo del estimador no muestra.
if not ES_ESTIMADOR:
  with tab_val:
    st.markdown(t("val_intro", IDIOMA))
    fits = st.file_uploader(t("val_subir", IDIOMA), type=["fit"],
                            accept_multiple_files=True, key="val_fits")
    rides = {}
    for f in fits or []:
        try:
            rides[f.name] = read_fit(f.getvalue(), f.name)
        except Exception as e:
            st.error(f"{f.name}: {e}")
    if rides:
        names = list(rides)

        # Criterio 30: antes de calibrar con una actividad, conviene saber si sirve.
        with st.expander(t("coh_titulo", IDIOMA), expanded=False):
            st.caption(t("coh_intro", IDIOMA))
            if st.button(t("coh_examinar", IDIOMA), key="btn_coherencia"):
                informes = []
                for n in names:
                    with st.spinner(t("coh_examinando", IDIOMA, nombre=n)):
                        informes.append(check_coherence(rides[n], params, idioma=IDIOMA))
                st.session_state["coherencia"] = [r.as_dict() for r in informes]
            informes = st.session_state.get("coherencia") or []
            if informes:
                malas = [r for r in informes if not r["coherente"]]
                dfc = tabla_coherencia(informes, IDIOMA)
                vista = dfc.drop(columns=["motivo"]).round(3)
                st.dataframe(vista.rename(columns=cabeceras(vista.columns, IDIOMA)),
                             hide_index=True)
                for r in informes:
                    st.markdown(
                        theme.veredicto(f"<b>{r['nombre']}</b> — " + " ".join(r["avisos"]),
                                        "ok" if r["coherente"] else "mal"),
                        unsafe_allow_html=True)
                st.download_button(t("coh_csv", IDIOMA), csv_bytes(dfc),
                                   file_name="coherencia.csv", mime="text/csv",
                                   key="dl_coherencia")
                if malas:
                    st.caption(t("coh_resumen", IDIOMA, n=len(malas), total=len(informes)))

        # la clave ya estaba en CLAVES_BORRABLES pero el widget no la tenía: sin ella, «Borrar»
        # no limpiaba la selección de actividades de calibración
        cal = st.multiselect(t("val_elegir_cal", IDIOMA), names, key="cal_sel")
        if len(cal) == 1:
            st.caption(t("val_una_sola", IDIOMA))
        if cal and st.button(t("val_calibrar", IDIOMA), key="btn_calibrar"):
            with st.spinner(t("val_calibrando", IDIOMA)):
                st.session_state["cda_cal"] = calibrate_cda([rides[n] for n in cal], params)
                st.session_state["cda_cal_origen"] = t("val_origen_texto", IDIOMA, n=len(cal),
                                                       lista=", ".join(cal))
                # Criterio 30: el examen NO puede depender de que el usuario haya pulsado el
                # botón de coherencia. Si alguna de las actividades elegidas no tiene informe,
                # se examina aquí mismo. Antes, sin pulsarlo, se podía calibrar un CdA de 0,150
                # —fuera del rango plausible— y guardarlo sin un solo aviso.
                informes = {r["nombre"]: r for r in (st.session_state.get("coherencia") or [])}
                for nombre in cal:
                    if nombre not in informes:
                        informes[nombre] = check_coherence(
                            rides[nombre], params, idioma=IDIOMA).as_dict()
                st.session_state["coherencia"] = list(informes.values())
                malas = [n for n in cal if not informes[n]["coherente"]]
                st.session_state["cda_cal_incoherente"] = malas
            if malas:
                # la barra lateral ya se dibujó en esta pasada: sin el rerun, el aviso de
                # «no guardes este CdA» no aparecería hasta la siguiente interacción
                st.rerun()
        if st.session_state.get("cda_cal"):
            v = float(st.session_state["cda_cal"])
            origen_cal = st.session_state.get("cda_cal_origen", "")
            st.success(t("val_cda_ok", IDIOMA, cda=v))
            st.caption(t("val_origen", IDIOMA, origen=origen_cal))
            malas = st.session_state.get("cda_cal_incoherente") or []
            if malas:
                st.warning(t("coh_cal_con_malas", IDIOMA, lista=", ".join(malas)))
            # Red de seguridad independiente del examen: un CdA fuera del rango plausible se
            # avisa siempre, venga de donde venga.
            if not (CDA_PLAUSIBLE[0] < v < CDA_PLAUSIBLE[1]):
                st.warning(t("coh_cda_fuera", IDIOMA, cda=v,
                             bajo=CDA_PLAUSIBLE[0], alto=CDA_PLAUSIBLE[1]))
            # `cda_cal_incoherente` se **reescribe** al aplicar, no se deja como estaba: si el
            # usuario recalibra solo con actividades coherentes, la bandera de una calibración
            # anterior tiene que desaparecer, y al revés.
            st.button(t("val_aplicar", IDIOMA), key="btn_aplicar_cal",
                      on_click=lambda m=list(malas): st.session_state.update(
                          p_cda=round(v, 3), perfil_origen=origen_cal, perfil_calibrado=True,
                          cda_de_estimador="", cda_cal_incoherente=m))
        if st.button(t("val_validar", IDIOMA), key="btn_validar"):
            out = []
            for n in names:
                if n in cal:
                    continue
                with st.spinner(t("val_reproduciendo", IDIOMA, nombre=n)):
                    out.append(replay(rides[n], params).as_dict())
            if not out:
                st.warning(t("val_todas_cal", IDIOMA))
            else:
                dfv = tabla_validacion(out)
                vista = dfv.drop(columns=["notas"]).round(2)
                st.dataframe(vista.rename(columns=cabeceras(vista.columns, IDIOMA)), hide_index=True)
                if (dfv["error_tiempo_pct"].abs() > 3.0).any():
                    st.warning(t("val_no_cumple", IDIOMA))
    else:
        st.markdown(theme.vacio(t("val_vacio_titulo", IDIOMA), t("val_vacio_texto", IDIOMA)),
                    unsafe_allow_html=True)

with tab_est:
    st.markdown(t("est_intro", IDIOMA))
    fit_est = st.file_uploader(t("est_subir", IDIOMA), type=["fit"], key="est_fit")
    if fit_est is None:
        st.markdown(theme.vacio(t("est_vacio_titulo", IDIOMA), t("est_vacio_texto", IDIOMA)),
                    unsafe_allow_html=True)
    else:
        try:
            ride = read_fit(fit_est.getvalue(), fit_est.name)
            km = ride_distance_km(ride)
        except Exception as e:
            st.error(f"{fit_est.name}: {e}")
            st.stop()
        km_max = float(km[-1])
        st.caption(t("est_resumen_fit", IDIOMA, nombre=fit_est.name, km=km_max, n=len(km)))

        def veredicto_coherencia():
            """Examen de coherencia de esta actividad (criterio 30), calculado una sola vez.

            Lo necesitan **los dos** caminos del estimador, no solo el automático: hasta octubre
            de 2026 solo se lanzaba al pulsar «Buscar tramos», así que un CdA obtenido a mano
            sobre una actividad incoherente llegaba al panel de guardar perfil marcado como
            calibrado y sin un solo aviso. Se cachea por (parámetros, fichero) para no repetir el
            cálculo en cada interacción.
            """
            clave = (params_json(params), fit_est.name)
            if st.session_state.get("est_coh_clave") != clave:
                with st.spinner(t("coh_examinando", IDIOMA, nombre=fit_est.name)):
                    st.session_state["est_coherencia"] = check_coherence(
                        ride, params, idioma=IDIOMA).as_dict()
                st.session_state["est_coh_clave"] = clave
            return st.session_state["est_coherencia"]

        def actividades_incoherentes():
            """La lista que viaja con el CdA hasta el panel de guardar perfil. Vacía si la
            actividad es coherente, de modo que aplicar un CdA bueno **limpia** una bandera
            anterior en vez de dejarla puesta."""
            coh = veredicto_coherencia()
            return [] if coh["coherente"] else [fit_est.name]

        # --- búsqueda automática: es el camino recomendado
        st.markdown(t("est_seccion_auto", IDIOMA))
        st.caption(t("est_auto_nota", IDIOMA))
        if st.button(t("est_buscar", IDIOMA), key="btn_buscar", type="primary"):
            with st.spinner(t("est_buscando", IDIOMA)):
                rechazados: list = []
                st.session_state["est_pares"] = find_paired_segments(
                    ride, params, rechazados=rechazados, idioma=IDIOMA)
                st.session_state["est_rechazados"] = [r.motivo for r in rechazados]
                # Ida **y** vuelta: con solo las idas, el resumen comparaba media ruta contra la
                # ruta entera y la misma pantalla enseñaba dos velocidades distintas para los
                # mismos tramos (35,0 km/h en el pie y 38,3 km/h en el aviso de sesgo).
                st.session_state["est_resumen"] = search_summary(
                    ride, params,
                    [e for par in st.session_state["est_pares"] for e in (par.ida, par.vuelta)],
                    idioma=IDIOMA)
            # Criterio 30: la actividad pasa por el examen de coherencia, aquí y en el camino
            # manual (ver `veredicto_coherencia`).
            veredicto_coherencia()
            st.session_state["est_clave"] = (params_json(params), fit_est.name)

        # Igual que el simulador (criterio 20): el resultado en pantalla se marca como
        # desfasado si cambian los parámetros con los que se calculó. Subir la masa de 90 a 130 kg
        # dejaba el CdA anterior ahí, sin un solo aviso.
        clave_est = (params_json(params), fit_est.name)
        if st.session_state.get("est_pares") is not None and \
                st.session_state.get("est_clave") != clave_est:
            st.warning(t("est_desfasado", IDIOMA))

        pares = st.session_state.get("est_pares")
        resumen = st.session_state.get("est_resumen")
        # el veredicto va ANTES del número: si la actividad no sirve, el CdA tampoco
        coh = st.session_state.get("est_coherencia")
        if coh is not None:
            (st.success if coh["coherente"] else st.warning)(" ".join(coh["avisos"]))
        # Criterio 28: lo que se ha descartado se enseña, no se esconde.
        motivos = st.session_state.get("est_rechazados") or []
        if motivos:
            with st.expander(t("est_pares_rechazados_titulo", IDIOMA, n=len(motivos))):
                for m in motivos:
                    st.markdown(theme.veredicto(m, "mal"), unsafe_allow_html=True)
        if pares is not None and resumen is not None:
            if not pares:
                st.warning(t("est_sin_pares", IDIOMA))
            else:
                cda_pares, inc_pares = combine_pairs(pares)
                # El sesgo por viento NO está en la incertidumbre (es sesgo, no ruido), así que se
                # dibuja como banda rayada por fuera: el código visual de «esto no está medido».
                sens_viento = float(np.mean([e.sens_viento for par in pares
                                             for e in (par.ida, par.vuelta)]))
                v_media = float(np.mean([e.velocidad_media_kmh for par in pares
                                         for e in (par.ida, par.vuelta)]))
                st.markdown(
                    theme.lectura(
                        t("est_lectura_cab", IDIOMA), f"{cda_pares:.3f}",
                        margen=f"{inc_pares:.3f}", unidad="m²",
                        pie=[(f"{len(pares)}", t("est_m_n_pares", IDIOMA)),
                             (f"{len(motivos)}", t("est_pie_descartados", IDIOMA)),
                             (f"{v_media:.1f} km/h", t("est_pie_velocidad", IDIOMA)),
                             (f"{resumen.cda_ruta_completa:.3f}", t("est_m_completo", IDIOMA))],
                        banda=theme.banda_svg(
                            cda_pares,
                            [theme.Tramo(inc_pares, COLOR.senal,
                                         t("est_banda_medida", IDIOMA, inc=inc_pares)),
                             theme.Tramo(max(sens_viento, inc_pares * 1.2), COLOR.ocre,
                                         t("est_banda_viento", IDIOMA, sens=sens_viento),
                                         rayada=True)],
                            formato="{:.3f}", ident="c")),
                    unsafe_allow_html=True)
                tabla_pares = pd.DataFrame([
                    {"ida_km": par.ida.km_inicio, "rumbo_ida": par.ida.rumbo_grados,
                     "cda_ida": par.ida.cda, "vuelta_km": par.vuelta.km_inicio,
                     "rumbo_vuelta": par.vuelta.rumbo_grados, "cda_vuelta": par.vuelta.cda,
                     "CdA_par": par.cda, "±": par.discrepancia,
                     "viento_ms": par.viento_estimado_ms,
                     "separacion_m": par.separacion_m,
                     "largo_km": par.ida.distancia_m / 1000.0,
                     "v_kmh": (par.ida.velocidad_media_kmh + par.vuelta.velocidad_media_kmh) / 2}
                    for par in pares]).round(
                    {"ida_km": 1, "rumbo_ida": 0, "cda_ida": 3, "vuelta_km": 1,
                     "rumbo_vuelta": 0, "cda_vuelta": 3, "CdA_par": 3, "±": 3,
                     "viento_ms": 1, "separacion_m": 0, "largo_km": 2, "v_kmh": 1})
                st.dataframe(tabla_pares.rename(columns=cabeceras(tabla_pares.columns, IDIOMA)),
                             hide_index=True)
                st.caption(t("est_pares_nota", IDIOMA))

                st.markdown(t("est_sueltos_titulo", IDIOMA))
                sueltos = [par.ida for par in pares] + [par.vuelta for par in pares]
                sueltos.sort(key=lambda e: e.km_inicio)
                detalle_busqueda = st.checkbox(t("est_ver_todas", IDIOMA),
                                               key="est_detalle_busqueda")
                tabla_b = tabla_segmentos(sueltos, detalle=detalle_busqueda, idioma=IDIOMA)
                st.dataframe(tabla_b.round(3).rename(columns=cabeceras(tabla_b.columns, IDIOMA)),
                             hide_index=True)
                st.download_button(t("est_descargar_busqueda", IDIOMA),
                                   csv_bytes(tabla_segmentos(sueltos, detalle=True)),
                                   "cda_tramos_busqueda.csv", "text/csv",
                                   key="btn_csv_busqueda")
                # El sesgo de selección es una propiedad del método de búsqueda, no de la
                # actividad: se **declara siempre** con su cifra medida, y el tono de aviso se
                # reserva para cuando además es grande. Hasta octubre de 2026 solo aparecía si
                # superaba los 2 km/h, así que en las actividades donde era pequeño el usuario no
                # se enteraba de que existía.
                texto_sesgo = t("est_sesgo" if resumen.hay_sesgo else "est_sesgo_medido", IDIOMA,
                                v_tramos=resumen.velocidad_tramos_kmh,
                                v_ruta=resumen.velocidad_ruta_kmh,
                                sesgo=resumen.sesgo_velocidad_kmh,
                                pend=resumen.pendiente_tramos_pct)
                if resumen.hay_sesgo:
                    st.warning(texto_sesgo)
                else:
                    st.caption(texto_sesgo)
                # el veredicto viaja con el CdA: si la actividad era incoherente, el panel de
                # guardar perfil avisa antes de fijarlo en una bici (criterio 30)
                malas = actividades_incoherentes()
                st.button(t("est_aplicar_pares", IDIOMA), key="btn_aplicar_pares",
                          on_click=lambda v=cda_pares, n=len(pares), m=malas:
                              st.session_state.update(
                                  p_cda=round(float(v), 3),
                                  cda_de_estimador=t("est_origen_pares", IDIOMA, n=n,
                                                     fichero=fit_est.name),
                                  perfil_origen=t("est_origen_pares", IDIOMA, n=n,
                                                  fichero=fit_est.name),
                                  perfil_calibrado=True,
                                  cda_cal_incoherente=m),
                          help=t("est_aplicar_ayuda", IDIOMA))

        st.divider()
        st.markdown(t("est_seccion_manual", IDIOMA))
        alt = np.asarray(ride.alt, dtype=float)
        ok = np.isfinite(ride.lat) & np.isfinite(ride.lon)
        alt, vel = alt[ok], np.asarray(ride.speed, dtype=float)[ok] * 3.6
        perfil = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                               row_heights=[0.55, 0.45],
                               subplot_titles=(t("est_g_altitud", IDIOMA),
                                               t("est_g_velocidad", IDIOMA)))
        perfil.add_trace(go.Scatter(x=km, y=alt, name=t("est_g_altitud", IDIOMA), fill="tozeroy",
                                    line=dict(width=1)), row=1, col=1)
        perfil.add_trace(go.Scatter(x=km, y=vel, name=t("est_g_velocidad", IDIOMA),
                                    line=dict(width=1)), row=2, col=1)
        perfil.update_xaxes(title_text="km", row=2, col=1)
        perfil.update_layout(height=430, margin=dict(l=10, r=10, t=40, b=10), dragmode="select",
                             selectdirection="h", legend=dict(orientation="h"))
        theme.aplicar_a_figura(perfil, OSCURO)
        seleccion = st.plotly_chart(perfil, theme=None, key="est_grafico", on_select="rerun",
                                    selection_mode=("box", "lasso"))

        # la selección sobre el gráfico manda; si no hay, valen los deslizadores
        puntos = (seleccion or {}).get("selection", {}).get("points", []) if seleccion else []
        if puntos:
            xs = [p["x"] for p in puntos if p.get("x") is not None]
            if xs:
                st.session_state["est_rango"] = (float(min(xs)), float(max(xs)))
        rango_previo = st.session_state.get("est_rango", (0.0, min(km_max, 10.0)))
        st.caption(t("est_arrastra", IDIOMA))
        a, b = st.slider(t("est_slider", IDIOMA), 0.0, km_max,
                         value=(float(np.clip(rango_previo[0], 0.0, km_max)),
                                float(np.clip(rango_previo[1], 0.0, km_max))),
                         step=0.1, key="est_slider")
        if st.button(t("est_estimar", IDIOMA), key="btn_estimar"):
            try:
                est = estimate_cda(ride, params, a, b, idioma=IDIOMA)
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state.setdefault("est_lista", []).append(est)
                veredicto_coherencia()      # criterio 30, también por aquí

        # El veredicto de la actividad, si ya se ha calculado, se enseña **antes** del número
        # también en el camino manual.
        coh_manual = st.session_state.get("est_coherencia")
        if coh_manual is not None and st.session_state.get("est_lista"):
            (st.success if coh_manual["coherente"] else st.warning)(
                " ".join(coh_manual["avisos"]))

        lista = st.session_state.get("est_lista", [])
        if lista:
            est = lista[-1]
            # el mismo bloque de lectura que el camino recomendado: un CdA es un CdA, venga de
            # donde venga, y su margen se dibuja igual (criterio 32)
            st.markdown(
                theme.lectura(
                    t("est_m_cda", IDIOMA), f"{est.cda:.3f}",
                    margen=f"{est.cda_incertidumbre:.3f}", unidad="m²",
                    pie=[(f"{est.velocidad_media_kmh:.1f} km/h", t("m_velocidad", IDIOMA)),
                         (f"{est.distancia_m / 1000:.2f} km", t("m_distancia", IDIOMA)),
                         (f"{est.desnivel_m:+.0f} m", t("m_desnivel", IDIOMA)),
                         (f"{est.fraccion_aero * 100:.0f} %", t("est_pie_aero", IDIOMA))],
                    banda=theme.banda_svg(
                        est.cda,
                        [theme.Tramo(est.cda_incertidumbre, COLOR.senal,
                                     t("est_banda_medida", IDIOMA, inc=est.cda_incertidumbre)),
                         theme.Tramo(max(est.sens_viento, est.cda_incertidumbre * 1.2), COLOR.ocre,
                                     t("est_banda_viento", IDIOMA, sens=est.sens_viento),
                                     rayada=True)],
                        formato="{:.3f}", ident="m"),
                    estado="" if est.utilizable else "mal"),
                unsafe_allow_html=True)
            if est.utilizable:
                st.success(t("est_utilizable", IDIOMA, a=est.cda_min, b=est.cda_max))
            else:
                st.error(t("est_no_utilizable", IDIOMA))
            st.markdown(t("est_incert_titulo", IDIOMA))
            fuente = t("est_col_fuente", IDIOMA)
            st.dataframe(pd.DataFrame([
                {fuente: t("est_f_altitud", IDIOMA), "ΔCdA": est.sens_altitud},
                {fuente: t("est_f_crr", IDIOMA), "ΔCdA": est.sens_crr},
                {fuente: t("est_f_potencia", IDIOMA), "ΔCdA": est.sens_potencia},
                {fuente: t("est_f_total", IDIOMA), "ΔCdA": est.cda_incertidumbre},
                {fuente: t("est_f_viento", IDIOMA), "ΔCdA": est.sens_viento},
            ]).round(4), hide_index=True)
            st.caption(t("est_condiciones", IDIOMA, aero=est.fraccion_aero * 100,
                         sin_ped=est.fraccion_sin_pedalear * 100, rho=est.densidad_aire))
            for aviso in est.avisos:
                st.warning(aviso)

            st.divider()
            st.markdown(t("est_lista_titulo", IDIOMA, n=len(lista)))
            detalle_sel = st.checkbox(t("est_ver_todas", IDIOMA), key="est_detalle_seleccion")
            tabla_sel = tabla_segmentos(lista, detalle=detalle_sel, idioma=IDIOMA)
            st.dataframe(tabla_sel.round(3).rename(columns=cabeceras(tabla_sel.columns, IDIOMA)),
                         hide_index=True)
            st.caption(t("est_lista_nota", IDIOMA))
            st.download_button(t("est_descargar_lista", IDIOMA),
                               csv_bytes(tabla_segmentos(lista, detalle=True)),
                               "cda_segmentos.csv", "text/csv", key="btn_csv_seleccion")

            if len(lista) > 1:
                utiles = [e for e in lista if e.utilizable]
                if utiles:
                    cda_c, inc_c = combine_estimates(utiles)
                    st.info(t("est_combinado", IDIOMA, n=len(utiles), cda=cda_c, inc=inc_c))
                    # Mismas garantías que el camino automático: el origen del CdA y el veredicto
                    # de coherencia viajan con el valor hasta el panel de guardar perfil.
                    st.button(t("est_aplicar_combinado", IDIOMA), key="btn_aplicar_est",
                              on_click=lambda v=cda_c, n=len(utiles),
                              m=actividades_incoherentes(): st.session_state.update(
                                  p_cda=round(float(v), 3),
                                  cda_de_estimador=t("est_origen_combinado", IDIOMA, n=n),
                                  perfil_origen=t("est_origen_combinado", IDIOMA, n=n),
                                  perfil_calibrado=True,
                                  cda_cal_incoherente=m))
            st.button(t("est_vaciar", IDIOMA), key="btn_vaciar_est",
                      on_click=lambda: st.session_state.pop("est_lista", None))

with tab_model:
    st.markdown(t("modelo_texto", IDIOMA))
