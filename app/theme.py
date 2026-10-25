"""Sistema de diseño de la herramienta (criterio 32). Única fuente de los tokens visuales.

## El plan, y por qué es este

**De qué va esto.** No es una app de fitness ni un cuadro de mando: es un **instrumento de
medida**. Todo el proyecto se ha construido alrededor de una idea —ningún número sin su margen—
y el diseño tiene que decir eso antes de que se lea una sola etiqueta. De ahí sale la decisión
central:

> **La incertidumbre tiene lenguaje visual propio.** El margen se dibuja con un peso comparable
> al del valor, y la *forma* de la banda dice cuánto se puede creer: **sólida y estrecha** = medida
> y estrecha; **rayada y ancha** = margen del día o afirmación sin verificar. El rayado es un
> recurso de dibujo técnico, no un adorno: codifica «esto es menos seguro».

Ese es el único sitio donde el diseño levanta la voz. Todo lo demás se mantiene callado: reglas en
lugar de tarjetas, una sola familia de interfaz, ningún degradado, ninguna animación de entrada.

**Color.** Grafito frío con azul de cianotipo. El azul es el término aerodinámico, que es el que
manda en la física de la herramienta y el que se mide; el ocre es el margen del día, lo que no se
sabe. Se descartaron a propósito dos paletas: crema con terracota y negro con verde ácido, que son
los dos acabados que salen por defecto cuando nadie decide nada. El gris no es un negro teñido
haciendo de negro: es grafito azulado, coherente con el resto de la paleta fría.

**Tipografía.** `Instrument Sans` para la interfaz —estrecha, técnica, sin la neutralidad de las
familias que se usan en todo— y `IBM Plex Mono` **solo para las lecturas numéricas**, porque ahí
la anchura fija sirve para algo: alinea las cifras y los ± de una columna. Nunca para etiquetas,
que es el uso decorativo del monoespaciado. Las dos con pila de reserva: sin red, la herramienta
sigue leyéndose.

**Accesibilidad.** Contraste comprobado en los dos temas, con dos umbrales distintos porque la
norma pide dos cosas distintas: el **texto** cumple el 4,5:1 de AA (el caso justo es el texto
apagado, 4,8:1), y los **bordes de los controles** cumplen el 3:1 de la WCAG 1.4.11, que es por lo
que existe el token `borde` aparte de `regla`. La `regla` se queda en su contraste bajo a
propósito: separa, no informa. Foco de teclado visible y `prefers-reduced-motion` respetado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

# --------------------------------------------------------------------------- tokens


@dataclass(frozen=True)
class Paleta:
    """Los colores de un tema. Mismos papeles en claro y en oscuro."""
    papel: str          # fondo de la página
    superficie: str     # fondo de los bloques que se levantan del papel
    tinta: str          # texto principal
    apagado: str        # texto secundario
    regla: str          # líneas de separación (decorativas)
    borde: str          # bordes de controles: WCAG 1.4.11 pide 3:1, no vale la regla
    senal: str          # acento: lo aerodinámico, lo medido
    ocre: str           # el margen del día, la precaución
    ladrillo: str       # lo que no sirve: incoherente, descartado
    musgo: str          # lo que sí sirve: coherente


CLARO = Paleta(papel="#F2F5F7", superficie="#FFFFFF", tinta="#1B2733", apagado="#5D6E7E",
               regla="#D3DCE4", borde="#7B8C99", senal="#0F5F78", ocre="#8F6218",
               ladrillo="#9E3A2C", musgo="#2C6A4E")

OSCURO = Paleta(papel="#10161C", superficie="#171F27", tinta="#E3EBF2", apagado="#94A5B4",
                regla="#2A3744", borde="#64788A", senal="#4FB3CC", ocre="#D6A356",
                ladrillo="#E07C6B", musgo="#68BE91")

#: Familias y sus papeles. La monoespaciada es solo para cifras que se comparan.
FUENTE_UI = ('"Instrument Sans", "Helvetica Neue", -apple-system, BlinkMacSystemFont, '
             '"Segoe UI", Roboto, sans-serif')
FUENTE_CIFRA = '"IBM Plex Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace'
IMPORT_FUENTES = ("https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&"
                  "family=IBM+Plex+Mono:wght@400;500;600&display=swap")


def paleta(oscuro: bool) -> Paleta:
    return OSCURO if oscuro else CLARO


# --------------------------------------------------------------------------- CSS
def css(oscuro: bool) -> str:
    """Hoja de estilo completa del tema, derivada de los tokens.

    Todo sale de la paleta: no hay un solo color escrito a mano más abajo. Un test comprueba que
    la interfaz tampoco los escriba.
    """
    c = paleta(oscuro)
    return f"""<style>
@import url('{IMPORT_FUENTES}');

:root {{
  --papel:{c.papel}; --superficie:{c.superficie}; --tinta:{c.tinta}; --apagado:{c.apagado};
  --regla:{c.regla}; --borde:{c.borde}; --senal:{c.senal}; --ocre:{c.ocre}; --ladrillo:{c.ladrillo};
  --musgo:{c.musgo};
  --ui:{FUENTE_UI}; --cifra:{FUENTE_CIFRA};
  /* Escala de espacio: una progresión, no literales repetidos por la hoja. Los componentes de
     abajo la usan; las reglas que ajustan a Streamlit conservan sus valores porque persiguen
     medidas ajenas. */
  --e1:0.25rem; --e2:0.5rem; --e3:0.9rem; --e4:1.4rem; --e5:2.2rem;
  --radio:3px; --ancho-lectura:34rem;
}}

/* --- base ------------------------------------------------------------------ */
/* La tipografía se fija SOLO en las raíces y se hereda. Ponerla en un selector con `*`
   pisaba la fuente de iconos de Streamlit y los ligados salían como texto
   («keyboard_double_arrow_down» en vez de la flecha). El color sí se fuerza, porque
   Streamlit lo escribe en elementos concretos. */
.stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {{
  background:{c.papel}; font-family:var(--ui);
}}
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stSidebar"] *, [data-testid="stMarkdownContainer"] {{ color:{c.tinta}; }}
/* La familia **no se hereda** hasta aquí: Streamlit la escribe en estos mismos elementos, así que
   hay que nombrarlos uno a uno. Medido sobre el DOM antes de esta regla: el h1 del panel, los
   captions y los párrafos renderizaban en «Source Sans», la de fábrica. Se enumeran elementos
   concretos y nunca `*`, que pisaría la fuente de los iconos. */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp li, .stApp label, .stApp td, .stApp th,
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
[data-testid="stHeadingWithActionElements"], [data-baseweb="tab"],
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{ font-family:var(--ui); }}
.stApp {{ font-size:0.9375rem; line-height:1.55; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{
  color:{c.apagado} !important; font-size:0.8125rem; line-height:1.5;
}}
.stApp h1 {{ font-size:1.5rem; font-weight:600; letter-spacing:-0.01em; }}
.stApp h2 {{ font-size:1.1875rem; font-weight:600; }}
.stApp h3 {{ font-size:1.0625rem; font-weight:600; }}
.stApp hr {{ border-color:{c.regla}; }}
.stApp a {{ color:{c.senal}; }}
.block-container {{ padding-top:2.2rem; max-width:1400px; }}

/* --- controles -------------------------------------------------------------- */
.stApp input, .stApp select, .stApp textarea,
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"] {{
  background:{c.superficie} !important; color:{c.tinta} !important;
  border-color:{c.borde} !important; font-family:var(--ui);
}}
.stApp [data-testid="stNumberInputContainer"] input {{ font-family:var(--cifra); }}
.stApp button {{ font-family:var(--ui) !important; font-weight:500; border-radius:3px; }}

.stApp [data-testid="stExpander"] {{
  background:{c.superficie}; border:1px solid {c.regla}; border-radius:3px;
}}
/* La **cabecera** del desplegable, que Streamlit pinta aparte y casi blanca: en modo oscuro el
   texto claro quedaba sobre ese fondo a 1,15:1, ilegible. El contenedor ya estaba cubierto; esto
   faltaba. Medido sobre el DOM renderizado, no sobre los tokens. */
.stApp [data-testid="stExpander"] summary,
.stApp [data-testid="stExpander"] details > summary,
.stApp [data-testid="stExpanderHeader"] {{
  background:{c.superficie} !important; color:{c.tinta} !important;
}}
.stApp [data-testid="stExpander"] summary p,
.stApp [data-testid="stExpanderHeader"] * {{ color:{c.tinta} !important; }}
/* los pasos +/- del campo numérico conservaban fondo blanco en oscuro */
.stApp [data-testid="stNumberInputStepUp"],
.stApp [data-testid="stNumberInputStepDown"],
.stApp [data-testid="stNumberInputContainer"] {{
  background:{c.superficie} !important; color:{c.tinta} !important;
  border-color:{c.borde} !important;
}}
.stApp [data-testid="stDataFrame"] {{ border:1px solid {c.regla}; border-radius:3px; }}
/* La monoespaciada es para cifras. `[role="columnheader"]` son **etiquetas** —los nombres de las
   columnas—, y el criterio 32 dice «nunca para etiquetas»: la regla estaba escrita al revés de lo
   que pide la spec. Hoy la tabla se pinta en canvas y no se nota, pero se activaría en cuanto
   Streamlit cambiara de renderer. */
.stApp [data-testid="stDataFrame"] [role="gridcell"] {{
  font-family:var(--cifra); font-size:0.8125rem;
}}
.stApp [data-testid="stDataFrame"] [role="columnheader"] {{
  font-family:var(--ui); font-size:0.8125rem;
}}
[data-testid="stSidebar"] {{ border-right:1px solid {c.regla}; }}
[data-testid="stSidebar"], section[data-testid="stSidebar"] {{
  width:23rem !important; min-width:23rem !important; max-width:23rem !important;
}}
[data-testid="stSidebar"] label {{ font-size:0.8125rem; line-height:1.35; }}

/* Botones y grupos de botones. Streamlit les pone fondo claro fijo, así que en modo oscuro
   el texto claro quedaba invisible: hay que darles el fondo del tema. */
.stApp [data-testid="stBaseButton-secondary"],
.stApp [data-testid="stButtonGroup"] button {{
  background:{c.superficie} !important; color:{c.tinta} !important;
  border-color:{c.borde} !important;
}}
.stApp [data-testid="stBaseButton-primary"],
.stApp [data-testid="stButtonGroup"] button[aria-checked="true"],
.stApp [data-testid="stButtonGroup"] button[aria-pressed="true"],
.stApp [data-testid="stButtonGroup"] button[kind="primary"] {{
  background:{c.senal} !important; color:{c.papel} !important; border-color:{c.senal} !important;
}}
.stApp [data-testid="stBaseButton-primary"]:hover,
.stApp [data-testid="stBaseButton-secondary"]:hover {{
  border-color:{c.senal} !important;
}}
.stApp [data-testid="stFileUploader"] section,
.stApp [data-testid="stFileUploaderDropzone"],
.stApp [data-testid="stFileUploaderFile"] {{
  background:{c.superficie} !important; border-color:{c.regla} !important;
}}
/* La letra pequeña del subidor («200MB per file • FIT») y el valor del deslizador los pinta
   Streamlit con su propio gris: medidos a 1,10:1 en oscuro y 2,11:1 en claro. El test de
   contraste no los veía porque comparaba pares de tokens, no lo que el navegador calcula. */
.stApp [data-testid="stFileUploaderDropzoneInstructions"],
.stApp [data-testid="stFileUploaderDropzoneInstructions"] *,
.stApp [data-testid="stFileUploaderFileName"] {{ color:{c.apagado} !important; }}
/* El valor del deslizador va **sobre el propio pulgar**, que es del color de señal: ahí la tinta
   da 2,11:1 y lo que corresponde es el papel, igual que en los botones primarios. Los extremos
   de la escala sí van sobre la página. */
/* El pulgar lo pinta Streamlit con el `primaryColor` de `config.toml`, que es el de señal del
   tema claro y no cambia con el modo oscuro: medido, el valor quedaba a 2,54:1 en oscuro. Se le
   da fondo propio al rótulo para que el par color/fondo esté garantizado en los dos temas. */
.stApp [data-testid="stSliderThumbValue"] {{
  background:{c.senal} !important; border-radius:3px; padding:0 .3rem;
}}
.stApp [data-testid="stSliderThumbValue"],
.stApp [data-testid="stSliderThumbValue"] * {{ color:{c.papel} !important; }}
.stApp [data-testid="stSliderTickBarMin"],
.stApp [data-testid="stSliderTickBarMax"],
.stApp [data-testid="stTickBar"] {{ color:{c.apagado} !important; }}

/* los iconos conservan su fuente pase lo que pase */
.stApp [data-testid="stIconMaterial"], .stApp span[class*="material-symbols"],
.stApp .material-icons, [data-testid="stSidebar"] [data-testid="stIconMaterial"] {{
  font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
}}

/* el foco se ve: es suelo, no extra */
.stApp *:focus-visible {{ outline:2px solid {c.senal}; outline-offset:2px; }}

/* pestañas: regla, no cápsulas */
.stApp [data-baseweb="tab-list"] {{ gap:1.5rem; border-bottom:1px solid {c.regla}; }}
.stApp [data-baseweb="tab"] {{ font-weight:500; padding-left:0; padding-right:0; }}

/* --- lectura numérica: el elemento con voz ---------------------------------- */
.lectura {{
  background:{c.superficie}; border:1px solid {c.regla}; border-left:3px solid {c.senal};
  border-radius:3px; padding:1.15rem 1.35rem 1.25rem; margin:0 0 1rem;
}}
.lectura-cab {{
  font-family:var(--ui); font-size:0.8125rem; font-weight:500; color:{c.apagado};
  margin-bottom:0.3rem;
}}
.lectura-cifra {{ display:flex; align-items:baseline; gap:0.6rem; flex-wrap:wrap; }}
.cifra {{
  font-family:var(--cifra); font-size:2.6rem; font-weight:600; line-height:1;
  letter-spacing:-0.02em; color:{c.tinta}; font-variant-numeric:tabular-nums;
}}
/* el margen pesa casi lo mismo que el valor: es la idea del proyecto */
.margen {{
  font-family:var(--cifra); font-size:1.3rem; font-weight:400; color:{c.apagado};
  font-variant-numeric:tabular-nums;
}}
.unidad {{ font-family:var(--ui); font-size:0.9375rem; color:{c.apagado}; }}
.lectura-pie {{ display:flex; flex-wrap:wrap; margin-top:0.9rem; }}
.lectura-pie > span {{
  font-size:0.8125rem; color:{c.apagado}; padding:0 0.85rem; border-left:1px solid {c.regla};
}}
.lectura-pie > span:first-child {{ padding-left:0; border-left:0; }}
.lectura-pie b {{
  font-family:var(--cifra); font-weight:500; color:{c.tinta};
  font-variant-numeric:tabular-nums;
}}
.lectura.ok {{ border-left-color:{c.musgo}; }}
.lectura.aviso {{ border-left-color:{c.ocre}; }}
.lectura.mal {{ border-left-color:{c.ladrillo}; }}

/* --- banda de incertidumbre -------------------------------------------------- */
/* La **única** transición del sistema, la que el criterio 32 admite: la banda aparece con el
   resultado. `prefers-reduced-motion` la anula (más abajo). No existía: el criterio la declaraba
   y los tests no la comprobaban. */
@keyframes banda-aparece {{ from {{ opacity:0; transform:translateY(3px); }}
                            to {{ opacity:1; transform:none; }} }}
.banda {{ display:block; width:100%; max-width:var(--ancho-lectura); height:38px;
          margin-top:var(--e3);
          overflow:visible; animation:banda-aparece .22s ease-out both; }}
.banda-pie {{ display:flex; justify-content:space-between; max-width:var(--ancho-lectura);
              font-family:var(--cifra); font-size:0.6875rem; color:{c.apagado};
              font-variant-numeric:tabular-nums; margin-top:0.1rem; }}
.banda text {{ font-family:var(--cifra); font-size:10.5px; fill:{c.apagado};
               font-variant-numeric:tabular-nums; }}
.banda .eje {{ stroke:{c.regla}; stroke-width:1; }}
.banda .marca {{ stroke:{c.tinta}; stroke-width:2; }}
.banda-leyenda {{ display:flex; gap:1.1rem; margin-top:var(--e1); font-size:0.75rem;
                  color:{c.apagado}; }}
.banda-leyenda span {{ display:flex; align-items:center; gap:0.35rem; }}
.muestra {{ width:15px; height:9px; display:inline-block; border-radius:1px; }}

/* --- veredicto: el mismo código de color que las lecturas, en formato breve ---- */
.veredicto {{
  background:{c.superficie}; border:1px solid {c.regla}; border-left:3px solid {c.senal};
  border-radius:3px; padding:0.7rem 0.95rem; margin:0 0 0.55rem; font-size:0.875rem;
  color:{c.tinta};
}}
.veredicto.ok {{ border-left-color:{c.musgo}; }}
.veredicto.aviso {{ border-left-color:{c.ocre}; }}
.veredicto.mal {{ border-left-color:{c.ladrillo}; }}
.veredicto b {{ font-family:var(--cifra); font-weight:500; font-variant-numeric:tabular-nums; }}
/* lo descartado se raya, igual que la banda que el modelo no controla: es el mismo idioma */
.veredicto.mal {{
  background:
    repeating-linear-gradient(45deg, transparent 0 7px,
      color-mix(in srgb, {c.ladrillo} 7%, transparent) 7px 8px), {c.superficie};
}}

/* --- cinta de módulo -------------------------------------------------------- */
.modulo-cab {{ border-bottom:1px solid {c.regla}; padding-bottom:0.7rem; margin-bottom:1.3rem; }}
.modulo-cab h1 {{ margin:0 0 0.15rem; }}
.modulo-cab p {{ margin:0; color:{c.apagado}; font-size:0.875rem; max-width:68ch; }}

/* --- vacío: una invitación, no un hueco ------------------------------------- */
.vacio {{
  border:1px dashed {c.regla}; border-radius:3px; padding:2.4rem 1.5rem; text-align:center;
  color:{c.apagado}; background:{c.superficie};
}}
.vacio strong {{ display:block; color:{c.tinta}; font-weight:600; margin-bottom:0.3rem;
                 font-size:1rem; }}
.vacio p {{ margin:0 auto; max-width:52ch; font-size:0.875rem; color:{c.apagado} !important; }}

@media (prefers-reduced-motion: reduce) {{
  .stApp *, .banda * {{ animation:none !important; transition:none !important; }}
}}
</style>"""


# --------------------------------------------------------------------------- plantilla de gráficos
def aplicar_a_figura(fig, oscuro: bool):
    """Pone la plantilla **y** los colores de fondo directamente en el `layout` de la figura.

    Hace falta lo segundo. El componente de Plotly de Streamlit escribe su propio
    `paper_bgcolor`/`plot_bgcolor` por encima de la plantilla, incluso con `theme=None`: medido,
    el lienzo salía en `#F2F5F7` —el `secondaryBackgroundColor` de `.streamlit/config.toml`— en
    los dos temas, mientras la plantilla pedía `#FFFFFF` en claro y `#171F27` en oscuro. Las
    propiedades escritas en el `layout` sí ganan, porque no son valores por defecto de plantilla.

    Devuelve la misma figura, para poder encadenar.
    """
    c = paleta(oscuro)
    fig.update_layout(template=plantilla_plotly(oscuro),
                      paper_bgcolor=c.superficie, plot_bgcolor=c.superficie,
                      font=dict(family=FUENTE_UI, size=12, color=c.tinta))
    fig.update_xaxes(gridcolor=c.regla, zerolinecolor=c.regla, linecolor=c.regla,
                     tickfont=dict(family=FUENTE_CIFRA, size=11, color=c.apagado))
    fig.update_yaxes(gridcolor=c.regla, zerolinecolor=c.regla, linecolor=c.regla,
                     tickfont=dict(family=FUENTE_CIFRA, size=11, color=c.apagado))
    for anotacion in (fig.layout.annotations or ()):      # títulos de las subgráficas
        anotacion.font.color = c.tinta
        anotacion.font.family = FUENTE_UI
    return fig


def plantilla_plotly(oscuro: bool) -> dict:
    """Plantilla de plotly derivada de los mismos tokens, para que los gráficos sean del sistema."""
    c = paleta(oscuro)
    eje = dict(gridcolor=c.regla, zerolinecolor=c.regla, linecolor=c.regla,
               tickfont=dict(family=FUENTE_CIFRA, size=11, color=c.apagado),
               title=dict(font=dict(family=FUENTE_UI, size=12, color=c.apagado)))
    return dict(layout=dict(
        paper_bgcolor=c.superficie, plot_bgcolor=c.superficie,
        font=dict(family=FUENTE_UI, size=12, color=c.tinta),
        colorway=[c.senal, c.ocre, c.musgo, c.ladrillo, c.apagado],
        xaxis=eje, yaxis=eje,
        legend=dict(font=dict(family=FUENTE_UI, size=11, color=c.apagado),
                    bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(font=dict(family=FUENTE_CIFRA, size=11), bordercolor=c.regla),
        margin=dict(l=52, r=16, t=16, b=40)))


# --------------------------------------------------------------------------- componentes
def _esc(texto: str) -> str:
    return (str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


@dataclass(frozen=True)
class Tramo:
    """Una banda alrededor del valor central: su semiancho, su color y cómo se dibuja.

    `rayada=True` se dibuja **rayada**. El rayado significa «este margen no lo controla el
    modelo»: lo que cae dentro de él depende de algo que la herramienta no conoce —el viento del
    día, sobre todo—, no de la precisión del cálculo. **No** significa «sin medir»: la banda del
    día está medida, y con el peor caso real de las cinco salidas.

    Hasta octubre de 2026 este campo se llamaba `verificada` y la leyenda de la banda del día
    decía «sin verificar», mientras `band_dia(...).verificada` valía `True` y la propia nota al
    pie de la misma pantalla la llamaba «medida». Lo único que de verdad no está verificado es la
    extrapolación a una **ruta nueva**, y de eso avisa su propia nota.
    """
    margen: float
    color: str
    etiqueta: str
    rayada: bool = False


def banda_svg(valor: float, tramos: Sequence[Tramo], *,
              formato="{:.3f}", ident: str = "b") -> str:
    """Dibuja el valor con sus bandas. El ancho del dibujo lo fija la banda más ancha.

    Las bandas se pintan de la más ancha a la más estrecha, así que una banda estrecha y sólida
    queda **dentro** de la ancha y rayada, que es exactamente lo que significan: la del día
    envuelve a la del modelo. Cada `Tramo` trae su color, así que la función no necesita saber
    en qué tema estamos.

    `formato` puede ser una cadena de formato o una función: un tiempo se rotula con `fmt_time`,
    no con los segundos en crudo.
    """
    fmt = formato if callable(formato) else formato.format
    orden = sorted(tramos, key=lambda tr: -abs(tr.margen))
    if not orden or abs(orden[0].margen) <= 0:
        return ""
    ancho_max = abs(orden[0].margen)
    W, Y, H = 100.0, 16.0, 13.0        # coordenadas en %; el SVG escala al contenedor

    def x(v):                          # valor -> % del ancho
        return 50.0 + 50.0 * (v - valor) / ancho_max * 0.92

    # el lector de pantalla recibe el valor y sus márgenes, que es lo que dice el dibujo
    descripcion = fmt(valor) + "".join(
        f", {tr.etiqueta} ± {fmt(abs(tr.margen))}" for tr in orden)
    piezas: List[str] = [
        f'<svg class="banda" viewBox="0 0 {W:.0f} 46" preserveAspectRatio="none" '
        f'role="img" aria-label="{_esc(descripcion)}">']
    # el rayado va en un patrón por cada banda que el modelo no controla
    defs = []
    for i, tr in enumerate(orden):
        if tr.rayada:
            defs.append(
                f'<pattern id="ray{ident}{i}" width="5" height="5" patternUnits="userSpaceOnUse" '
                f'patternTransform="rotate(45)">'
                f'<rect width="5" height="5" fill="{tr.color}" fill-opacity="0.10"/>'
                f'<line x1="0" y1="0" x2="0" y2="5" stroke="{tr.color}" stroke-width="1.4"/>'
                f'</pattern>')
    if defs:
        piezas.append("<defs>" + "".join(defs) + "</defs>")

    for i, tr in enumerate(orden):
        x0, x1 = x(valor - abs(tr.margen)), x(valor + abs(tr.margen))
        relleno = (f'url(#ray{ident}{i})' if tr.rayada else tr.color)
        opacidad = "1" if tr.rayada else "0.22"
        piezas.append(
            f'<rect x="{x0:.2f}" y="{Y:.0f}" width="{max(x1 - x0, 0.8):.2f}" height="{H:.0f}" '
            f'fill="{relleno}" fill-opacity="{opacidad}" stroke="{tr.color}" '
            f'stroke-width="1" vector-effect="non-scaling-stroke"/>')

    piezas.append(f'<line class="eje" x1="0" y1="{Y + H + 4:.0f}" x2="{W:.0f}" '
                  f'y2="{Y + H + 4:.0f}" vector-effect="non-scaling-stroke"/>')
    piezas.append(f'<line class="marca" x1="50" y1="{Y - 3:.0f}" x2="50" y2="{Y + H + 3:.0f}" '
                  f'vector-effect="non-scaling-stroke"/>')
    piezas.append("</svg>")

    # la leyenda va al revés que el dibujo: primero lo medido, que es lo que se ha hecho
    leyenda = "".join(
        f'<span><i class="muestra" style="background:{tr.color};'
        + (f'background:repeating-linear-gradient(45deg,{tr.color} 0 1.4px,'
           f'transparent 1.4px 5px);' if tr.rayada else "opacity:.25;")
        + f'"></i>{_esc(tr.etiqueta)}</span>'
        for tr in reversed(orden))
    extremos = (f'<div class="banda-pie"><span>{_esc(fmt(valor - ancho_max))}</span>'
                f'<span>{_esc(fmt(valor + ancho_max))}</span></div>')
    return ("".join(piezas) + extremos
            + f'<div class="banda-leyenda">{leyenda}</div>')


def lectura(cabecera: str, valor: str, *, margen: str = "", unidad: str = "",
            pie: Sequence[Tuple[str, str]] = (), banda: str = "",
            estado: str = "") -> str:
    """Bloque de lectura: cifra grande, su margen al lado y las cifras que lo sostienen debajo.

    `pie` son pares (valor, etiqueta) y se separan con reglas, no con puntos medios.
    `estado` es "", "ok", "aviso" o "mal" y solo cambia el color del filo izquierdo.
    """
    trozos = [f'<div class="lectura {_esc(estado)}">',
              f'<div class="lectura-cab">{_esc(cabecera)}</div>',
              '<div class="lectura-cifra">',
              f'<span class="cifra">{_esc(valor)}</span>']
    if margen:
        trozos.append(f'<span class="margen">± {_esc(margen)}</span>')
    if unidad:
        trozos.append(f'<span class="unidad">{_esc(unidad)}</span>')
    trozos.append("</div>")
    if banda:
        trozos.append(banda)
    if pie:
        trozos.append('<div class="lectura-pie">'
                      + "".join(f"<span><b>{_esc(v)}</b> {_esc(etq)}</span>" for v, etq in pie)
                      + "</div>")
    trozos.append("</div>")
    return "".join(trozos)


def veredicto(texto: str, estado: str = "") -> str:
    """Bloque breve con el filo de color del sistema: "", "ok", "aviso" o "mal".

    Es la tercera boca del código visual que pide el criterio 32, junto a las bandas de tiempo y
    al CdA estimado: **lo descartado se raya**, igual que lo no verificado. Antes esto salía con
    los `st.warning`/`st.caption` de fábrica, que son de otro sistema de color.
    """
    return f'<div class="veredicto {_esc(estado)}">{texto}</div>'


def cabecera_modulo(titulo: str, subtitulo: str) -> str:
    return (f'<div class="modulo-cab"><h1>{_esc(titulo)}</h1>'
            f'<p>{_esc(subtitulo)}</p></div>')


def vacio(titulo: str, texto: str) -> str:
    """Pantalla vacía: dice qué hacer, no que no hay nada."""
    return f'<div class="vacio"><strong>{_esc(titulo)}</strong><p>{_esc(texto)}</p></div>'
