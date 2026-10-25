# Simulador de ciclismo para triatlón (sin drafting) y contrarreloj

[![tests](../../actions/workflows/tests.yml/badge.svg)](../../actions/workflows/tests.yml)

> **Qué es este repositorio y qué no.** Es una aplicación **Streamlit (Python)** que se ejecuta en
> tu ordenador con `./run.sh` o `run.bat`; abre el navegador en `localhost`. **No es una PWA
> instalable ni se publica en GitHub Pages**: Streamlit necesita un proceso Python detrás, y una
> PWA es un conjunto de ficheros estáticos. Reescribirla en JavaScript (o correrla en el navegador
> con Pyodide/stlite) es un proyecto aparte que obligaría a revalidar la física contra las cinco
> actividades reales. No hay APK.
>
> **Mapa del repo:** `app/` interfaz · `core/` física, estimador de CdA y límites (sin dependencia de
> Streamlit) · `tests/` 372 tests · `simulador-ciclismo-triatlon.spec.md` la especificación y sus
> 32 criterios de aceptación · `docs/calidad/` registro de defectos y revisiones independientes.
> Estado de la calidad: ver [`docs/calidad/README.md`](docs/calidad/README.md).

Herramienta de uso personal, tipo *Best Bike Split* simplificado: dado un **GPX** y un **perfil de
potencia por pendiente** (subida / llano / descenso), predice tiempo, velocidad y potencia por
tramo con un modelo físico y parámetros editables.

**Versión 1 — alcance:** solo simulador directo. Sin viento, sin drafting, sin optimizador de
pacing, sin modo inverso, sin DEM, sin extracción de superficie desde OSM (ver *Limitaciones*).

**Idiomas:** español e inglés, con selector en la barra lateral. Se traduce todo lo que se ve,
incluidos los tooltips de los 39 parámetros y los avisos del estimador. Los CSV descargables
conservan los nombres técnicos de columna (`tiempo_s`, `cda`, `desnivel_m`) en los dos idiomas,
a propósito, para que no se rompa ninguna hoja de cálculo.

## Puesta en marcha

**Sin línea de comandos** (recomendado): descomprime la carpeta y

- **Windows:** doble clic en `run.bat`
- **macOS / Linux:** `./run.sh` en una terminal (en macOS, si prefieres el doble clic, renombra el
  archivo a `run.command`)

La primera vez crea un entorno virtual en `.venv` e instala las dependencias (un par de minutos);
las siguientes arranca directo. Si falta Python, el script lo dice con el enlace de descarga.

`run.sh` está probado de punta a punta (entorno creado desde cero, app respondiendo). **`run.bat` no
se ha podido ejecutar en Windows**: está validado por inspección y por un lint estático de las
trampas de `cmd`. Si te falla, manda lo que diga la ventana.

| Opción | Qué hace |
|---|---|
| `run.sh` / `run.bat` | abre el simulador en el navegador |
| `run.sh --tests` | instala las dependencias de test y ejecuta los 372 tests |
| `run.sh --reinstalar` | rehace el entorno desde cero (si algo se rompió) |
| `run.sh --reinstalar --tests` | las dos cosas |

A mano, si lo prefieres:

```bash
pip install -r requirements.txt          # app
pip install -r requirements-dev.txt      # app + tests (pytest, scipy)
streamlit run app/streamlit_app.py       # desde la raíz del proyecto
python -m pytest -q                      # 372 tests (ver "Tests")
```

**No hay versión en HTML puro.** El modelo vive en Python y reescribirlo en JavaScript duplicaría
1 463 líneas de física ya validada, con dos fuentes de verdad que se separarían. Streamlit ya se
ve en el navegador; lo que estos scripts quitan es la línea de comandos. Una versión con Pyodide
(el mismo Python corriendo en el navegador) sería la vía para no instalar nada, y queda pendiente.

Sin GPX cargado, la app muestra una **ruta de ejemplo sintética** (~26 km) para probar.

## Estructura

```
core/                 núcleo en Python/numpy, sin dependencias de interfaz
  params.py           parámetros, defaults, rangos, categorías, validación (única fuente de verdad)
  atmosphere.py       densidad del aire (temperatura, humedad, presión, altitud)
  route.py            lectura de GPX, remuestreo, suavizado, pendiente y curvatura
  physics.py          potencia por pendiente, CdA(v), Crr(v) y resolución por tramo
  simulate.py         simulación completa + tabla por bloques de km
  metrics.py          potencia media, NP, VI, IF
  sensitivity.py      sensibilidad ±10 % de cada parámetro
  validation.py       lectura de .fit, reproducción de la potencia real, calibración de CdA
  profiles.py         perfiles de bici (masa, CdA, Crr, η) con el origen del CdA
  wheels.py           medidas ETRTO y perímetro de rueda
  cda_estimator.py    estimación del CdA: por segmento, búsqueda automática de tramos llanos
                      y emparejado de ida y vuelta por la misma carretera
  coherence.py        examen de coherencia de una actividad: ¿sirve para calibrar?
  i18n.py             traducciones al inglés y cadenas de la interfaz
  uncertainty.py      bandas de incertidumbre medidas en la validación real
  exports.py          tablas que la app muestra y descarga, con las bandas ya incorporadas
  synthetic.py        rutas sintéticas (tests y ruta de ejemplo)
app/streamlit_app.py  interfaz en Streamlit, con los dos módulos
app/theme.py          sistema de diseño: tokens de color, tipografías y los componentes
                      de lectura numérica y de banda de incertidumbre
.streamlit/config.toml  tema claro por defecto
tests/                tests automáticos de los criterios de aceptación
  fixtures/           5 actividades reales reducidas y anonimizadas (criterios 13, 28-30); ver su README
```

## Modelo físico

Para cada tramo de longitud `d` sobre el firme, con potencia constante `P` y velocidades `v₀ → v₁`:

```
½·m_ef·(v₁² − v₀²) = d·( η·P / v̄ − ½·ρ·CdA(v̄)·(v₀²+v₁²)/2 − Crr(v̄)·m·g·cosθ ) − m·g·Δh
```

con `v̄ = (v₀+v₁)/2` y `m_ef = m + I/r²` (inercia de las ruedas). Esta forma es exacta para potencia
constante y aceleración uniforme. Se resuelve por tramo con un método de regula falsi (Illinois); si
hay varias soluciones (zona de transición de CdA) se elige la más próxima a `v₀` (histéresis: sigue
la trayectoria real). El tiempo del tramo es `d·2/(v₀+v₁)`.

| Elemento | Modelo |
|---|---|
| **Masa** | un único valor total (ciclista + bici + equipo). El reparto no entra en ninguna ecuación: solo la suma |
| **Potencia por pendiente** | `P(g)` = llano / subida / descenso con transición *smoothstep* continua; umbral (±2 %) y anchura editables |
| **CdA(v)** | `CdA + ΔCdA·σ((v₀ − v)/w)`, logística centrada en 20 km/h (por defecto ΔCdA = +0,25 m², w = 1 km/h). Continuo, sin saltos |
| **Crr(v, p)** | `Crr_ref·(p_ref/p)^exp + crr1·(v − 29 km/h)` por superficie (liso / normal / rugoso); `Crr_ref` se define a 29 km/h y a la presión de referencia. Suelo en 0,5·Crr_ref |
| **Rueda** | el perímetro sale de la medida ETRTO (defecto 28-622) o se introduce medido con la opción «manual»; el radio se deduce de él. Solo entra en la inercia de rotación y mueve el tiempo menos del 0,001 % |
| **ρ** | aire húmedo: temperatura, humedad (Magnus), presión a nivel del mar corregida con la altitud de cada punto (ISA) |
| **Límite por curvatura** | `v ≤ √(a_lat/κ)` (activo por defecto, `a_lat` = 3 m/s²), con frenada máxima (3 m/s²) propagada hacia atrás; κ por derivada del rumbo con dilatación a los extremos del arco. Fiable para R ≥ max(10 m, ventana de trazado/7); por debajo es **optimista** (+4,5 % de velocidad a R = 8 m, +16,3 % a R = 4 m) |
| **Tope de velocidad** | 100 km/h por defecto |
| **Potencia aplicada** | si el límite recorta la velocidad, la potencia aplicada se reduce a la necesaria (≥ 0) y eso se refleja en NP/VI/IF |
| **NP / VI / IF** | NP: media móvil 30 s a 1 Hz y media de 4.ª potencia; VI = NP/media; IF = NP/FTP |

**Suavizado del GPX:** remuestreo a distancia constante (20 m), suavizado gaussiano de la elevación
(ventana 150 m) y del trazado (60 m), pendiente limitada a ±30 %.

### Parámetros (valores por defecto: nivel del mar, A Coruña)

| Categoría | Parámetros principales | Avanzados |
|---|---|---|
| **Ciclista** | masa total (**obligatoria**, sin valor por defecto) · P subida/llano/descenso 220/200/0 W · FTP (opcional) | umbral de pendiente 2 %, anchura de transición 1 %, velocidad inicial 18 km/h |
| **Equipamiento** | CdA 0,27 m² · ΔCdA 0,25 m² · η 0,975 · rueda ETRTO 28-622 (o perímetro medido) | umbral de posición 20 km/h, anchura 1 km/h, inercia 0,14 kg·m² |
| **Variables externas** | temperatura 15 °C · humedad 75 % · superficie (liso/normal/rugoso) · presión 7,0 bar · tramos por km · velocidad máx. 100 km/h · límite por curvatura | presión atmosférica 1013,25 hPa, densidad manual | Crr por superficie, variación de Crr con v, a_lat, frenada, ventanas de suavizado, paso |

La clasificación principal/avanzado es una decisión de diseño. La pestaña **Sensibilidad** la
contrasta con los datos de tu ruta (columna `sugerencia`).

## Perfiles de bici

Cada montura tiene su propio CdA y sus propias masas, así que la app guarda **perfiles con nombre**
(`perfiles_bici.json`, junto al proyecto; se puede cambiar con la variable de entorno
`SIMCICLISMO_PERFILES`). Un perfil fija masas, CdA, ΔCdA, η, Crr, superficie e inercia, y guarda
además el **origen del CdA**: de qué salidas sale y si está calibrado o es un valor por defecto. Un
CdA guardado sin ese origen no es trazable y la app lo marca como *sin calibrar*.

`perfiles_bici.ejemplo.json` contiene el perfil obtenido con el estimador de pares sobre las 3
salidas coherentes del recorrido 2 (CdA 0,261 m², masa total 90 kg). Renómbralo a
`perfiles_bici.json` para usarlo. Es un CdA de **posición de entrenamiento**: para competir, mide
el tuyo con una actividad que lleve el montaje y la posición de carrera.

## Cuánto te puedes fiar del tiempo predicho

La app muestra siempre el tiempo con su margen, con dos bandas distintas:

Las tablas y los CSV traen, por cada columna de tiempo, cuatro columnas más
(`_min_modelo`, `_max_modelo`, `_min_dia`, `_max_dia`), para que ningún tiempo salga de la
herramienta sin su margen.

Las dos bandas **miden cosas distintas**, y por eso se dan las dos y no la media ni la mejor:

| Banda | Valor | Qué mide y de dónde sale |
|---|---|---|
| **Precisión del modelo** | **±1,4 %** | **Medido**: validación cruzada dejando una fuera con las 3 salidas coherentes del recorrido 2 (30-mar-2025, 06-abr-2025 y 19-abr-2026); error medio 0,94 %, máximo 1,39 %. Es lo que vale el modelo físico con la misma bici y ruta cuando el día no se sale de lo normal |
| **Margen del día** | **±15 %** | **Medido con el protocolo recomendado** (criterio 30): calibrando solo con las 3 salidas coherentes y prediciendo cualquier día, incluidos los 2 incoherentes. Peor error **14,27 %**, en la salida del 04-may-2025. Es lo que cuesta no saber qué viento hizo |

**En una ruta nueva no hay banda verificada.** El margen del día es un **suelo**, no una
estimación: ninguna validación ha podido cruzar de ruta, porque no hay salidas de esta bici por
otro recorrido (criterio 14). El ±11 % que esta tabla daba antes para «ruta nueva» quedó retirado
por incoherente: era *menor* que el margen por viento ya medido en la propia ruta de calibración.

## Dos módulos, dos trabajos distintos

La herramienta hace dos cosas que no son la misma, y se eligen con el selector **Qué quieres
hacer** de la barra lateral:

| Módulo | Entra | Sale | Parámetros que pide |
|---|---|---|---|
| **Medir mi CdA** | una actividad `.fit` | el CdA de esa bici en esa posición | 22 |
| **Predecir una carrera** | el GPX del recorrido y un CdA | tiempo, velocidad y potencia por tramo | 39 |

El estimador **no pide un GPX** ni los parámetros que no intervienen en su cálculo. Sobre todo,
no pide el **CdA**: es lo que calcula, y pedirlo como entrada sería circular. Tampoco los perfiles
de potencia, el FTP, los límites de velocidad y curvatura o el remuestreo del recorrido.

Esa partición vive en el núcleo (`core.params.specs_for_module`) y la vigila un test **empírico**:
cambiar un parámetro que el módulo no muestra no mueve la estimación, y cambiar uno de los que
muestra sí. La lista no se mantiene a mano.

**Para arrancar directamente en el estimador**, sin pasar por el simulador:

```bash
./run.sh --estimador          # macOS y Linux
run.bat --estimador           # Windows
```

También vale añadir `?modo=estimador` a la URL.

### El flujo pensado

1. En **Medir mi CdA**, sube una actividad con el montaje y la posición que vas a llevar en
   carrera, y con algún tramo llano recorrido en los dos sentidos.
2. Pulsa **Aplicar este CdA en la barra lateral**. El valor queda puesto en el simulador como un campo **editable**:
   úsalo tal cual, o corrígelo a mano si tu montaje de carrera no es exactamente el que mediste.
3. En **Predecir una carrera**, sube el GPX de la competición y di qué potencia piensas sostener.

## El diseño de la interfaz

Los tokens de color, las dos tipografías y los componentes viven en `app/theme.py`, y nada más los
escribe: un test comprueba que la interfaz no define ni un color a mano.

La idea que sostiene el diseño es la misma que sostiene el proyecto: **ningún número aparece sin su
margen**, y a un peso visual comparable. La *forma* de la banda dice cuánto se puede creer:

- **sólida y estrecha** = medida, y lo que mide está escrito debajo;
- **rayada y ancha** = margen del día, o afirmación sin verificar.

El rayado es un recurso de dibujo técnico, no un adorno: en el estimador, la banda rayada que
envuelve a la medida es lo que movería **1 m/s de viento**, que no entra en la incertidumbre
porque es un sesgo y no ruido. En el simulador, la rayada es el margen del día frente a la sólida
del modelo.

Lo demás se mantiene callado: una familia de interfaz (`Instrument Sans`), una monoespaciada
(`IBM Plex Mono`) **solo para las cifras** que se comparan o se alinean, reglas en lugar de
tarjetas y ninguna animación de entrada. Hay tema claro y oscuro derivados de los mismos tokens,
con el contraste comprobado por test en los dos. Las tablas se quedan claras en modo oscuro
porque Streamlit las dibuja en un lienzo al que no llega el CSS; para un oscuro completo está el
tema del menú «Settings» de Streamlit.

## Estimar tu CdA a partir de una actividad

Pestaña **Estimar CdA**: sube un `.fit` y pulsa **🔍 Buscar tramos fiables**. La herramienta barre
la actividad en ventanas de 1 a 5 km, se queda con los tramos llanos, rápidos y sin solapes, y para
cada uno localiza **la pasada de vuelta por la misma carretera**. También puedes elegir un segmento
a mano, arrastrando sobre el perfil o con el deslizador.

En los dos casos cierra el balance de energía del tramo:

```
∫ η·P dt − Δ(½·m_ef·v²) − m·g·Δh − ∫ Crr(v)·m·g·cosθ·v dt  =  ∫ ½·ρ·CdA·v³ dt
```

**Lee los avisos, no solo el número.** El denominador crece con el cubo de la velocidad, pero el
término del desnivel no: en un segmento corto, lento o con cuesta, el desnivel pesa más que el aire
y un error de un metro de altitud se traga la estimación. La herramienta lo cuantifica y marca el
segmento como no utilizable cuando toca. Mínimos para darlo por bueno: 500 m, 45 s, 25 km/h, que al
menos la mitad de la energía disipada sea aerodinámica e incertidumbre ≤ ±0,030 m².

**El viento es el problema gordo.** No está modelado, así que entra entero dentro del CdA estimado:
1 m/s de viento mueve el resultado unos ±0,04–0,06 m², más que todos los demás errores juntos. Por
eso se muestra aparte de la incertidumbre: no es ruido, es un sesgo. La única forma de quitarlo es
**promediar un tramo de ida con el mismo de vuelta**, y la herramienta combina segmentos ponderando
por su incertidumbre, usando la dispersión entre ellos cuando no concuerdan.

Los resultados salen en **una tabla con una fila por segmento**: dónde está el tramo, su CdA con
el margen, el desnivel, la pendiente, la velocidad y la potencia medias, la parte aerodinámica de la
energía disipada, el rumbo y si el tramo es utilizable. Marcando «ver todas las columnas» aparece el
desglose de la incertidumbre por fuente (altitud, Crr, potenciómetro), la duración, la fracción sin
pedalear, la densidad del aire y el CdA descontando las prendas. Todo se descarga en CSV.

El **rumbo** no es decorativo: es la columna que delata el viento. Si los tramos hacia un lado dan
CdA bajo y los del contrario alto, eso es viento y no tu posición.

### Por qué el valor recomendado es el de ida y vuelta

Medido con las dos actividades reales, con tres métodos:

| Método | 30-mar-2025 | 06-abr-2025 | Qué le pasa |
|---|---|---|---|
| Tramos llanos sueltos (combinados) | 0,226 | 0,217 | **sesgado bajo**: ver abajo |
| **Pares de ida y vuelta (recomendado)** | **0,268 ± 0,007** | **0,262 ± 0,007** | el viento se cancela |
| Recorrido completo | 0,277 | 0,264 | sin sesgo de selección |
| Calibración por tiempo total (independiente) | 0,276 | 0,262 | no usa el balance de energía |

Los tramos sueltos, uno a uno, dan entre 0,18 y 0,39 m² según el tramo. Eso **no es ruido de
medida**: es el viento, y se ve en los rumbos. Ese día los tramos hacia el oeste daban CdA bajo y
los del este alto, lo que delata viento del este. Al emparejar cada tramo con su pasada de vuelta,
la dispersión se desploma y el resultado coincide con la calibración por tiempo, que es un método
completamente independiente.

**El sesgo de selección está medido y la app lo avisa.** Exigir velocidad alta y poco desnivel no da
una muestra neutra: los tramos elegidos van a 36,3 km/h frente a los 31,4 km/h de la ruta, con una
pendiente media de −0,16 %. Son justo los tramos con viento a favor o bajada suave, y por eso un
tramo suelto, por muy «fiable» que parezca su diagnóstico, da un CdA bajo.

**Los pares no se ponderan por su discrepancia**, aunque sea tentador dar más peso a los de menos
viento. La teoría dice que la media de ida y vuelta queda sesgada alto en un factor (1 + (w/v)²); se
midió, y corregirlo mueve la media de 0,268 a 0,264 y la dispersión de 0,018 a 0,015, o sea casi
nada. Ponderar por la discrepancia bajaría el resultado a 0,244, que es leer en los datos más de lo
que hay. Así que se promedia a secas y se da la dispersión entre pares como incertidumbre.

## Validación con tus actividades (.fit)

1. Pestaña **Validación con FIT**, sube varios `.fit` con GPS y potencia.
2. Marca una o varias rutas para **calibrar el CdA** (se iguala el tiempo predicho al real en
   movimiento por bisección).
3. Pulsa **Validar**: reproduce la potencia real en el resto de rutas y muestra error de tiempo (%),
   error medio y MAE/RMSE de velocidad. El objetivo es **≤ 3 % de error de tiempo en una ruta no
   usada para calibrar**; si no se cumple, la tabla lo marca y no se oculta.

### Examen de coherencia: ¿esta actividad sirve para calibrar?

La calibración por tiempo total **siempre** devuelve un número, porque busca el CdA que iguala el
tiempo predicho al real y lo encuentra. Lo que no dice es si ese número significa algo. En el
desplegable **Coherencia de la actividad** la herramienta examina cada `.fit` y avisa si:

- el CdA calibrado cae fuera del rango plausible **0,20-0,35 m²**, o
- aparece el patrón **llano demasiado lento (≥ +5 %) y bajadas demasiado rápidas (≤ −4 %)**.

Ese patrón es la firma de una salida más rápida de lo que permite la potencia registrada (viento
neto a favor, rebufo, grupo): la bisección baja el CdA hasta que el llano encaja y, al hacerlo,
rompe las bajadas. Las dos reglas hacen falta: la salida del 08-jun-2025 tiene el CdA dentro del
rango y solo la caza el patrón.

### Protocolo de calibración (actualizado tras validar con 5 salidas)

1. Usa solo salidas de **la misma bici** y de la misma ruta.
2. **Pasa cada una por el examen de coherencia** y deja fuera las que avisen. Anota el motivo con
   la medida que lo respalda, no con una hipótesis.
3. Obtén el CdA con el **estimador de pares de ida y vuelta**, que es el método reproducible
   (1,9 % de dispersión entre salidas frente al 21,3 % de la calibración por tiempo total). La
   calibración por tiempo total queda como **comprobación independiente**, no como fuente del dato.
4. Calibra con **al menos 2 salidas** coherentes y valida dejando una fuera.
5. Mira la dispersión entre salidas, no solo el mejor ajuste.
6. **No promedies salidas incoherentes** con las buenas: meterían el viento de su día en el
   parámetro.

### Resultados con los datos reales (5 salidas del recorrido 2, mar-2025 a abr-2026)

El modelo físico se validó separando el error **por banda de pendiente**, que es más exigente que
el tiempo total: un ajuste global puede acertar compensando errores opuestos, y esto no.

| Banda de pendiente | 30-mar | 06-abr | 19-abr-26 |
|---|---|---|---|
| bajada > 6 % | −7,7 % | −1,6 % | +0,6 % |
| bajada 3-6 % | +1,0 % | +0,2 % | +1,2 % |
| bajada 1-3 % | +0,5 % | −0,4 % | +1,3 % |
| llano ±1 % | −2,5 % | −0,7 % | −1,3 % |
| subida 1-3 % | +0,9 % | +0,1 % | +1,0 % |
| subida 3-6 % | +1,1 % | +1,0 % | −0,3 % |
| subida > 6 % | +0,4 % | −0,5 % | −1,8 % |

Con un solo CdA el error se queda **dentro de ±2,5 % en las siete bandas**, de −6 % a +6 % de
pendiente. El único punto flojo es la bajada de más del 6 % (4,6 % de la ruta), donde lo que limita
al ciclista es la frenada y la visibilidad, no la física.

Y el CdA por los dos métodos, en las cinco salidas:

| Salida | por tiempo total | por pares de ida y vuelta |
|---|---|---|
| 30-mar-2025 | 0,2758 | 0,2611 ± 0,0049 |
| 06-abr-2025 | 0,2621 | 0,2661 ± 0,0087 |
| 04-may-2025 | **0,1550** | 0,2435 ± 0,0188 |
| 08-jun-2025 | **0,2131** | 0,2542 ± 0,0095 |
| 19-abr-2026 | 0,2583 | 0,2550 ± 0,0090 |
| **dispersión** | **21,3 %** | **3,3 %** (1,9 % con el filtro del criterio 28) |

**El estimador de pares es reproducible y la calibración por tiempo total no**, porque los pares de
ida y vuelta cancelan el viento medio y el tiempo total lo absorbe entero en el CdA. De ahí que el
protocolo use los pares como fuente del dato. La salida del 19-abr-2026 encaja con las de 2025 por
los dos métodos trece meses después: el CdA resulta estable a lo largo de un año.

Lo que **no** está validado: la transferencia a otra ruta (las cinco salidas son la misma vuelta,
con un 94-98 % de solape), la posición de carrera (estas son 4 h a 210-226 W y 31-33 km/h: el ~0,26
que sale de ellas es un CdA de entrenamiento) y el viento, que no es una entrada del modelo. La
velocidad instantánea sigue fallando ±3 km/h de MAE aunque el tiempo total acierte.

El informe completo, con las tablas por banda de cada salida y el diagnóstico de las dos
incoherentes, está en `simulador-ciclismo-triatlon.validacion.md`.

## Umbrales documentados (tests)

| Criterio | Umbral usado |
|---|---|
| 1 | velocidad en llano = solución analítica ±0,3 km/h |
| 2 | velocidad terminal en descenso a 0 W: ±1 % |
| 5 | CdA continuo, en tres formas: (a) sobre la función, salto ≤ 0,001 m² entre muestras separadas 0,01 km/h (máx. teórico 0,000625); (b) **sobre las muestras reales de la simulación**, cambio ≤ ΔCdA/(4·anchura) **por km/h de velocidad** (cota de Lipschitz), y además **ajustado**: la pendiente medida llega al 96 % de la cota, así que el test falla si la transición deja de ser la declarada; (c) un CdA con escalón **incumple** esa cota, que es la prueba de que (b) puede fallar. Ojo con el salto absoluto: con el paso de 20 m la velocidad cambia hasta 5,2 km/h entre tramos y el CdA salta **0,187 m²** sin que haya discontinuidad ninguna — eso mide la resolución del remuestreo, no el modelo |
| 6 | potencia continua: salto ≤ 0,5 W entre pendientes separadas 0,001 % |
| 7 | CdA, Crr, eficiencia, superficie y masa total: más valor nunca reduce el tiempo en rutas sin descenso sin pedaleo (en el resto, solo CdA/Crr/η/superficie) |
| 8 | ruido de elevación i.i.d. de σ = 1 m, ventana 150 m: diferencia de tiempo total < 1 % (medido: ≤ 0,63 %) |
| 9 | circuito cerrado con **elevación asimétrica** y potencia constante: ±0,5 % entre sentidos (medido: 0,15 %). Con elevación simétrica la igualdad es exacta por construcción, así que esos dos tests quedan como regresión de indexado, no como prueba del criterio |
| 13 | actividades reales (5 salidas de la misma bici y ruta, reducidas en `tests/fixtures/`): error de tiempo ≤ 3 % calibrando en una y validando en la otra (medido: +1,26 % / −1,23 %) |
| 16 | ninguna columna de tiempo sale sin sus 4 columnas de banda, ni en pantalla ni en los CSV (`core/exports.py`) |
| 18 | el tiempo no cambia al repartir la misma masa total de otra forma; sí cambia al variar la suma |
| 19 | ningún parámetro sin texto de ayuda, y la ayuda llega al widget (no se queda en el núcleo) |
| 20 | sin pulsar «Simular» no hay resultados; al cambiar un parámetro el resultado anterior se marca como desfasado; «Borrar» no toca los perfiles del disco |
| 21 | `base = "light"` en la configuración y CSS oscuro inyectado al activar el interruptor |
| 22 | perímetro = π·(llanta + 2·ancho), defecto 28-622; la opción «manual» usa el perímetro medido; «manual» sin perímetro o perímetro sin «manual» se rechazan; dos ruedas extremas mueven el tiempo menos del 0,1 % |
| 23 | con los valores por defecto el resultado no cambia; más presión baja el Crr; `core.clothing` ya no existe y `prendas` no es un parámetro |
| 24 | se recupera un CdA conocido de una actividad sintética con ±0,005 m²; un segmento en cuesta se marca no utilizable; sobre datos reales coincide con la calibración por tiempo (±0,02) |
| 27 | cada parámetro y cada cadena tienen los dos idiomas, los placeholders de formato coinciden, un idioma desconocido cae al castellano, y en inglés cambian etiquetas, tooltips, pestañas, cabeceras y los avisos del estimador |
| 26 | la tabla por segmento trae las columnas pedidas, marca cuál es utilizable, y el CSV lleva el desglose completo |
| 25 | los tramos encontrados son llanos, utilizables y sin solapes; la pasada de vuelta está a menos de 1 km y en sentido opuesto; los pares discrepan menos entre sí que los tramos sueltos; el combinado de pares coincide con la calibración por tiempo (±0,02); el resumen mide el sesgo de selección |
| 28 | el par imposible se descarta con su motivo; el filtro no toca las 4 salidas que no lo necesitan; el umbral 1,5 cae entre el par legítimo más desigual (1,42) y el imposible más suave (2,13); descartar baja la dispersión entre salidas; **no** se filtra por discrepancia de CdA (algún par con discrepancia > 0,04 sobrevive) |
| 29 | las dos bandas cubren el peor error **vuelto a medir sobre los fixtures**, no una cifra escrita a mano: el modelo (±1,4 %) cubre las 3 coherentes y el día (±15 %) cubre también las incoherentes, midiendo con el protocolo recomendado (calibrar solo con coherentes). La del modelo **no** basta para las incoherentes, que es lo que justifica tener dos; el peor caso lo pone siempre una salida incoherente |
| 30 | las 3 coherentes pasan y las 2 incoherentes se detectan; hacen falta las dos reglas (la del 08-jun-2025 tiene el CdA en rango y solo la caza el patrón); entre la peor coherente y la mejor incoherente hay un orden de magnitud; los avisos salen en los dos idiomas |
| 31 | el estimador no pide GPX, ni el CdA que calcula, ni ningún parámetro que no use; sí pide todos los que usa; la partición se comprueba **midiendo** (mover un parámetro de fuera no cambia la estimación); el CdA medido llega al simulador editable y con su origen a la vista; los dos lanzadores aceptan `--estimador` |
| 32 | la interfaz no escribe ni un color a mano; los dos temas salen de los mismos tokens y ninguno filtra colores del otro; el contraste de todos los colores de texto llega a 4,5:1 en ambos temas; hay foco de teclado y `prefers-reduced-motion`; la banda dibuja rayado lo no verificado, rotula sus extremos y se describe para lectores de pantalla; los componentes escapan lo que reciben |
| 17 | los scripts de arranque existen y son válidos; todo import del núcleo y de la app está declarado en `requirements.txt`, y este no arrastra `pytest` ni `scipy`. `run.bat` pasa además un lint estático de las trampas de `cmd` (`shift` en bloque, comillas simples en `for /f`, guardia del hash, código de salida), comprobado por mutación |

### Hallazgo: el ruido de elevación manda más de lo esperado

Error del tiempo total (%) frente a la ruta sin ruido, según la ventana de suavizado y el ruido
i.i.d. de elevación (σ), en una ruta ondulada de 30 km con el perfil de potencia por defecto
(máximo de 4 semillas):

| σ ruido | 100 m | 150 m (defecto) | 200 m | 300 m |
|---|---|---|---|---|
| 1 m | 0,36 | 0,63 | 0,53 | 0,33 |
| 2 m | **3,06** | 0,78 | 0,32 | 0,59 |
| 3 m | **8,23** | 2,35 | 0,83 | 0,41 |
| 5 m | **15,06** | 7,17 | 3,16 | 1,15 |

Con ventana de 10 m el error ronda el 20 %. **Si tu GPX tiene elevación GPS ruidosa (σ ≥ 3 m),
sube la ventana de suavizado** (avanzado) o usa un GPX con elevación barométrica o corregida. Parte
del error viene de que `P_descenso = 0 W` convierte el ruido de pendiente en "descensos" ficticios.

## Limitaciones conocidas

- **Sin viento:** el de la salida real queda absorbido en el CdA calibrado (sesgo).
- **CdA único** (el cambio a posición convencional se modela solo por velocidad) y es la mayor
  fuente de incertidumbre: ±0,02 m² mueve el tiempo más que cualquier ajuste fino del terreno.
- **Valores de `crr1`** (variación de Crr con la velocidad): estimaciones sin respaldo experimental
  sólido; calíbralos o déjalos en el defecto.
- **Superficie:** el GPX no la trae; se elige global y se sobrescribe a mano por tramos de km.
- **Masa obligatoria:** la app no simula hasta introducir la masa total.
- **Presión de neumáticos:** el modelo solo baja el Crr al subir la presión. No representa que en
  firme rugoso, por encima de cierta presión, el conjunto se vuelva más lento. En rugoso y a mucha
  presión el resultado es optimista.
- **Lo que lleves puesto** no es un parámetro: va dentro del CdA que introduces. Si cambias de
  equipación, el CdA cambia y hay que volver a estimarlo.
- **La masa mayor puede ser más rápida** en rutas con descensos a 0 W (la gravedad escala con la masa
  y la resistencia aerodinámica no).
- **Precisión medida:** ±1,4 % con la misma bici y ruta en condiciones parecidas a las de la
  calibración, y ±15 % de margen del día cuando no se sabe qué viento hizo. Para una **ruta nueva
  no hay cifra verificada**: la app declara el margen del día como un **suelo**, no como una
  estimación, y no presenta ninguna banda como precisión esperable fuera de la ruta de calibración.
- **Un solo CdA por bici no basta para transferir entre rutas** con estos datos; falta una salida
  de la bici calibrada por otro recorrido para cerrarlo.
- XML del GPX parseado con `xml.etree` (uso personal; no exponer a archivos no confiables).

## Tests

`python -m pytest -q` ejecuta 226 tests: física (analítico y contra una integración RK4 independiente), límites
de velocidad, continuidad de CdA y potencia, monotonía, ruido de elevación, simetría de circuitos,
parámetros y validación, sensibilidad, lector de FIT (con un escritor FIT mínimo propio) y la
interfaz con `streamlit.testing` (incluida la pestaña del estimador de punta a punta, subiendo un
`.fit` de verdad), perfiles de bici, bandas de incertidumbre, ruedas, prendas, presión y **la
validación con las dos actividades reales** (`tests/test_validation_real.py`).

`scipy` solo lo usan los tests (solución de referencia independiente); la app no lo necesita, y por
eso está en `requirements-dev.txt` y no en `requirements.txt`. Un test comprueba que todo lo que
importan el núcleo y la app esté declarado, para que no se repita el despiste de `scipy`.
