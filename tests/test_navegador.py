"""Criterios 20, 21, 27 y 32 **sobre lo que el navegador pinta**, no sobre el CSS que se escribió.

Por qué existe este fichero. Cuatro revisiones independientes coincidieron en que la mayor parte de
los defectos del sistema de diseño sobrevivieron porque sus tests leían el código en vez de mirar
el resultado: comprobaban que una cadena estaba en la hoja de estilos, que el diccionario de la
plantilla de Plotly tenía los colores correctos, o que el fuente contenía `template=`. Los tres
pasaban en verde mientras el navegador ignoraba la plantilla entera y la tipografía de interfaz no
llegaba a ningún título. `AppTest` tampoco sirve para esto: lee `session_state`, de modo que un
campo que sigue enseñando el valor anterior le parece correcto.

Así que estas comprobaciones arrancan la aplicación de verdad y miden sobre el DOM: la familia
tipográfica **efectiva** de cada elemento, el contraste de los colores **calculados**, el fondo del
`<svg>` del gráfico y el valor que el campo tiene pintado.

**Se saltan si no hay Playwright.** No está en `requirements.txt` ni en `requirements-dev.txt`
porque arrastra un navegador de 150 MB y la suite tiene que poder correr con `./run.sh --tests` en
una máquina recién instalada. Para ejecutarlas:

    .venv/bin/python -m pip install playwright
    .venv/bin/python -m playwright install chromium
    .venv/bin/python -m pytest tests/test_navegador.py

El resto de la suite sigue vigilando lo que sí se puede vigilar sin navegador, y cada test de este
fichero dice en su docstring qué defecto concreto no se podía detectar sin él.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

sync_playwright = pytest.importorskip(
    "playwright.sync_api", reason="Playwright no está instalado: ver la cabecera del fichero"
).sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "app" / "streamlit_app.py"
MASA = 90.0

#: Mínimos de contraste del criterio 32 (WCAG AA).
AA_TEXTO = 4.5
AA_GRANDE = 3.0


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def servidor():
    """La aplicación servida de verdad, en un puerto libre, sin abrir navegador."""
    puerto = _puerto_libre()
    entorno = dict(os.environ, SIMCICLISMO_PERFILES=str(RAIZ / ".perfiles_test_navegador.json"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(APP),
         "--server.port", str(puerto), "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=str(RAIZ), env=entorno, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{puerto}"
    for _ in range(120):
        if proc.poll() is not None:
            salida = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
            pytest.fail(f"streamlit no arrancó:\n{salida[-2000:]}")
        try:
            with socket.create_connection(("127.0.0.1", puerto), timeout=0.5):
                break
        except OSError:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.fail("streamlit no respondió en 60 s")
    time.sleep(1.5)
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    Path(RAIZ / ".perfiles_test_navegador.json").unlink(missing_ok=True)


def _chromium_del_sistema():
    """Ruta a un Chromium ya instalado, si el que Playwright espera no está.

    Permite ejecutar estas comprobaciones sin descargar un navegador cuando la máquina ya tiene
    uno (es el caso de los entornos de CI con `PLAYWRIGHT_BROWSERS_PATH`). Devuelve `None` si no
    encuentra ninguno, y entonces se usa el que Playwright gestione.
    """
    candidatos = []
    base = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    if base.is_dir():
        candidatos += sorted(base.glob("chromium-*/chrome-linux/chrome"), reverse=True)
        candidatos += sorted(base.glob("chromium_headless_shell-*/chrome-linux/headless_shell"),
                             reverse=True)
    candidatos += [Path(p) for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser",
                                     "/usr/bin/google-chrome")]
    return next((str(c) for c in candidatos if Path(c).exists()), None)


@pytest.fixture(scope="module")
def pagina(servidor):
    with sync_playwright() as pw:
        try:
            navegador = pw.chromium.launch()
        except Exception:
            ruta = _chromium_del_sistema()
            if ruta is None:
                pytest.skip("no hay Chromium: `python -m playwright install chromium`")
            navegador = pw.chromium.launch(executable_path=ruta)
        pag = navegador.new_page(viewport={"width": 1500, "height": 1100})
        pag.goto(servidor, wait_until="networkidle")
        pag.wait_for_selector("[data-testid='stSidebar']", timeout=60000)
        _esperar_quieto(pag)
        yield pag
        navegador.close()


# --------------------------------------------------------------------------- utilidades
def _esperar_quieto(pag, ms: int = 1200):
    """Streamlit repinta de forma asíncrona: se espera a que no quede nada corriendo."""
    pag.wait_for_timeout(ms)
    try:
        pag.wait_for_function(
            "() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=30000)
    except Exception:
        pass


JS_CONTRASTE = """
(sel) => {
  const lum = (c) => {
    const [r,g,b] = c.map(v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
    return 0.2126*r + 0.7152*g + 0.0722*b;
  };
  const rgb = (s) => { const m = s.match(/[\\d.]+/g); return m ? m.slice(0,3).map(Number) : null; };
  const alfa = (s) => { const m = s.match(/[\\d.]+/g); return m && m.length > 3 ? Number(m[3]) : 1; };
  const fondoDe = (el) => {
    for (let n = el; n; n = n.parentElement) {
      const c = getComputedStyle(n).backgroundColor;
      if (rgb(c) && alfa(c) > 0.3) return rgb(c);
    }
    return [255,255,255];
  };
  const salida = [];
  for (const el of document.querySelectorAll(sel)) {
    const txt = (el.innerText || '').trim();
    if (!txt) continue;
    const cs = getComputedStyle(el);
    const f = rgb(cs.color), b = fondoDe(el);
    if (!f) continue;
    const l1 = lum(f), l2 = lum(b);
    const ratio = (Math.max(l1,l2) + 0.05) / (Math.min(l1,l2) + 0.05);
    salida.push({texto: txt.slice(0, 40), ratio: Math.round(ratio*100)/100,
                 tamano: parseFloat(cs.fontSize), peso: cs.fontWeight,
                 familia: cs.fontFamily});
  }
  return salida;
}
"""


def _contrastes(pag, selector: str):
    return pag.evaluate(JS_CONTRASTE, selector)


def _poner_masa(pag):
    campo = pag.locator("[data-testid='stSidebar'] input[type='number']").first
    campo.fill(str(MASA))
    campo.press("Enter")
    _esperar_quieto(pag)


def _simular(pag):
    _poner_masa(pag)
    pag.get_by_role("button", name="Simular").first.click()
    _esperar_quieto(pag, 3000)


def _tema_oscuro(pag, encender: bool = True):
    """El interruptor de modo oscuro, localizado por su etiqueta y no por su posición."""
    interruptor = pag.get_by_label("Modo oscuro", exact=False).first
    if interruptor.is_checked() != encender:
        interruptor.scroll_into_view_if_needed()
        interruptor.click(force=True)
        _esperar_quieto(pag, 2000)
    assert interruptor.is_checked() == encender


# --------------------------------------------------------------------------- criterio 32
def test_c32_la_tipografia_de_interfaz_llega_al_panel_principal(pagina):
    """Defecto que solo se ve renderizando: la familia se declaraba en `.stApp`, el sidebar y la
    cabecera, y perdía contra los selectores propios de Streamlit. Medido entonces: 44 nodos del
    panel principal en la `Source Sans` de fábrica frente a 5 en `Instrument Sans`. El test que
    debía cazarlo comprobaba `"Instrument Sans" in theme.FUENTE_UI`, es decir, el código consigo
    mismo."""
    _simular(pagina)        # con resultados hay pestañas, párrafos y lecturas que medir
    nodos = pagina.evaluate("""
      () => {
        const sel = '[data-testid="stMain"] h1, [data-testid="stMain"] h2,'
                  + '[data-testid="stMain"] h3, [data-testid="stMain"] p,'
                  + '[data-testid="stMain"] li, [data-testid="stMain"] [data-baseweb="tab"]';
        const out = [];
        for (const el of document.querySelectorAll(sel)) {
          if (!(el.innerText || '').trim()) continue;
          out.push({fam: getComputedStyle(el).fontFamily, txt: el.innerText.slice(0,30)});
        }
        return out;
      }
    """)
    assert len(nodos) >= 10, f"casi no hay texto que medir: {len(nodos)}"
    fuera = [n for n in nodos if "Instrument Sans" not in n["fam"]]
    assert not fuera, (
        f"{len(fuera)} de {len(nodos)} nodos del panel principal no usan la tipografía del "
        f"sistema de diseño; el primero es {fuera[0]}")


def test_c32_la_monoespaciada_solo_va_en_las_cifras(pagina):
    """El criterio dice «nunca para etiquetas»."""
    _esperar_quieto(pagina)
    etiquetas = pagina.evaluate("""
      () => {
        const out = [];
        for (const el of document.querySelectorAll('label, [data-testid="stWidgetLabel"]')) {
          if (!(el.innerText || '').trim()) continue;
          out.push({fam: getComputedStyle(el).fontFamily, txt: el.innerText.slice(0,30)});
        }
        return out;
      }
    """)
    monos = [e for e in etiquetas if "Plex Mono" in e["fam"] or "monospace" in e["fam"].lower()]
    assert not monos, f"etiquetas en monoespaciada: {monos[:3]}"


@pytest.mark.parametrize("oscuro", [False, True])
def test_c32_los_contrastes_del_criterio_se_cumplen_en_pantalla(pagina, oscuro):
    """Cuatro contrastes por debajo del mínimo que el test de tokens no podía ver, porque comparaba
    pares de tokens en abstracto y no lo que el navegador calcula: los dos selectores de la barra
    lateral a 2,11:1 en claro y 2,01:1 en oscuro, la cabecera del desplegable de perfiles a 1,15:1
    en oscuro y el pie del subidor a 1,10:1."""
    _tema_oscuro(pagina, oscuro)
    medidas = _contrastes(pagina,
                          "[data-testid='stSidebar'] button, [data-testid='stSidebar'] summary, "
                          "[data-testid='stMain'] h1, [data-testid='stMain'] p, "
                          "[data-testid='stMain'] button, "
                          "[data-testid='stFileUploaderDropzoneInstructions'] *")
    assert len(medidas) >= 8, f"poco que medir: {len(medidas)}"
    malos = []
    for m in medidas:
        grande = m["tamano"] >= 24 or (m["tamano"] >= 18.66 and int(m["peso"] or 400) >= 700)
        if m["ratio"] < (AA_GRANDE if grande else AA_TEXTO) - 0.01:
            malos.append(m)
    assert not malos, (
        f"{'oscuro' if oscuro else 'claro'}: {len(malos)} textos por debajo del mínimo; "
        f"los peores: {sorted(malos, key=lambda m: m['ratio'])[:3]}")


# --------------------------------------------------------------------------- criterio 21
@pytest.mark.parametrize("oscuro", [False, True])
def test_c21_el_tema_llega_al_grafico(pagina, oscuro):
    """El defecto más repetido de toda la serie: `st.plotly_chart(fig)` usa `theme="streamlit"`
    por defecto, que sustituye la plantilla propia por la derivada de `config.toml`, que es siempre
    clara. Medido entonces por píxel: el lienzo en `#F2F5F7` sobre una página oscura, en los dos
    temas. Los tres tests del criterio pasaban en verde."""
    _simular(pagina)
    _tema_oscuro(pagina, oscuro)
    fondos = pagina.evaluate("""
      () => {
        const opaco = (el) => {
          for (let n = el; n; n = n.parentElement) {
            const c = getComputedStyle(n).backgroundColor;
            const m = c.match(/[\\d.]+/g);
            if (m && (m.length < 4 || Number(m[3]) > 0.3)) return c;
          }
          return getComputedStyle(document.body).backgroundColor;
        };
        const out = [];
        for (const g of document.querySelectorAll('.js-plotly-plot')) {
          // `_fullLayout` es lo que Plotly está usando de verdad, después de que Streamlit haya
          // metido (o no) su tema por encima de la plantilla que se le pasó.
          const fl = g._fullLayout || {};
          out.push({lienzo: fl.paper_bgcolor, trazado: fl.plot_bgcolor,
                    tinta: (fl.font || {}).color, pagina: opaco(g)});
        }
        return out;
      }
    """)
    assert fondos, "no hay ningún gráfico dibujado"
    assert all(f["lienzo"] for f in fondos), f"no he podido leer la plantilla efectiva: {fondos}"

    def claro(c):
        c = (c or "").strip()
        if c.startswith("#"):
            h = c.lstrip("#")
            nums = [int(h[i:i + 2], 16) for i in (0, 2, 4)] if len(h) >= 6 else []
        else:
            nums = [float(x) for x in c.replace(",", " ").replace("(", " ").replace(")", " ")
                    .split() if x.replace(".", "", 1).isdigit()]
        return sum(nums[:3]) / 3.0 > 140 if len(nums) >= 3 else None

    for f in fondos:
        lienzo_claro, pagina_clara = claro(f["lienzo"]), claro(f["pagina"])
        assert lienzo_claro is not None, f"no he podido leer el fondo del gráfico: {f}"
        assert lienzo_claro == pagina_clara, (
            f"{'oscuro' if oscuro else 'claro'}: lienzo {f['lienzo']} sobre página {f['pagina']}")
        # y la tinta del gráfico sigue al tema, no se queda en el gris de Streamlit
        assert claro(f["tinta"]) is not pagina_clara, f"tinta {f['tinta']} sobre {f['lienzo']}"


def test_c32_limitacion_declarada_las_tablas_no_siguen_al_tema(pagina):
    """Limitación **medida**, no supuesta: `st.dataframe` se pinta en un `<canvas>` con el tema de
    Streamlit, que está anclado a claro en `.streamlit/config.toml`, así que en modo oscuro la
    tabla se queda clara. No hay forma de cambiarlo desde CSS —el color del elemento sí sigue al
    tema, los píxeles no— ni de conmutar el tema de Streamlit en caliente.

    El test fija la limitación por escrito: si algún día deja de cumplirse, hay que revisar la
    excepción declarada en el criterio 32 y en el README en vez de descubrirlo por casualidad.
    """
    _simular(pagina)
    js = """() => {
      for (const cv of document.querySelectorAll('[data-testid="stDataFrame"] canvas')) {
        if (!cv.width || !cv.height) continue;
        try {
          const d = cv.getContext('2d')
                      .getImageData(Math.floor(cv.width/2), Math.floor(cv.height/2), 1, 1).data;
          return [d[0], d[1], d[2]];
        } catch (e) { return null; }
      }
      return null;
    }"""
    _tema_oscuro(pagina, False)
    claro = pagina.evaluate(js)
    _tema_oscuro(pagina, True)
    oscuro = pagina.evaluate(js)
    if claro is None or oscuro is None:
        pytest.skip("no he podido leer los píxeles de la tabla")
    assert claro == oscuro, (
        f"las tablas ya siguen al tema (claro {claro} / oscuro {oscuro}): actualiza la excepción "
        f"declarada en el criterio 32 y en el README")
    assert sum(claro) / 3 > 140, f"la tabla no es clara: {claro}"


# --------------------------------------------------------------------------- criterio 20
def test_c20_borrar_deja_el_campo_de_masa_vacio_en_pantalla(pagina):
    """Lo que `AppTest` no puede ver. Tras pulsar «Borrar», el campo seguía enseñando `90.0`
    mientras la página decía «Falta la masa total»: el estado interno estaba limpio y la pantalla
    no. Se arregló reasignando el valor inicial en vez de borrar la clave del widget."""
    _poner_masa(pagina)
    campo = pagina.locator("[data-testid='stSidebar'] input[type='number']").first
    assert campo.input_value().startswith("90")
    pagina.get_by_role("button", name="Borrar").first.click()
    _esperar_quieto(pagina, 2500)
    assert campo.input_value().strip() in ("", "None"), (
        f"el campo sigue enseñando {campo.input_value()!r} después de borrar")
    assert "Falta la masa total" in pagina.inner_text("[data-testid='stMain']")


# --------------------------------------------------------------------------- criterios 27 y 29
def test_c29_la_leyenda_de_la_banda_no_se_contradice_con_el_nucleo(pagina):
    """La leyenda decía «sin verificar» de una banda que el núcleo marca verificada y que el pie de
    la misma pantalla llama «medida». Ningún test miraba ese texto."""
    _simular(pagina)
    texto = pagina.inner_text("[data-testid='stMain']")
    assert "día ±15 %" in texto
    assert "sin verificar" not in texto.split("ruta nueva")[0]
    assert "viento desconocido" in texto


def test_c27_en_ingles_no_queda_castellano_en_la_pantalla(pagina):
    """La procedencia de las dos bandas eran cadenas fijas en castellano concatenadas en crudo, así
    que con la interfaz en inglés salían dos párrafos enteros en español debajo del tiempo."""
    _simular(pagina)
    pagina.get_by_text("EN · English", exact=False).first.click()
    _esperar_quieto(pagina, 2500)
    texto = pagina.inner_text("[data-testid='stMain']")
    delatores = ["validación cruzada", "dejando una fuera", "salidas coherentes",
                 "protocolo recomendado", "no se sabe qué viento", "Simulando"]
    encontrados = [d for d in delatores if d in texto]
    assert not encontrados, f"texto en castellano con la interfaz en inglés: {encontrados}"
