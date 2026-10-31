# Simulador de ciclismo para triatlón (sin drafting) y contrarreloj

[![tests](../../actions/workflows/tests.yml/badge.svg)](../../actions/workflows/tests.yml)

Herramienta de uso personal que hace dos trabajos distintos:

1. **Estima el coeficiente de resistencia al avance (CdA)** de tu bici y tu posición a partir de
   una actividad real en `.fit`, cerrando el balance de energía sobre tramos llanos recorridos en
   los dos sentidos.
2. **Predice una carrera**: con el **GPX** del recorrido, ese CdA y un **perfil de potencia por
   pendiente** (subida / llano / descenso), calcula tiempo, velocidad y potencia por tramo con un
   modelo físico y parámetros editables.

Todo lo que sale de la herramienta va acompañado de su margen de incertidumbre. Ese es el criterio
de diseño del proyecto: **ningún número se presenta solo**, y lo que no está verificado se dice.

> **Qué es este repositorio y qué no.** Es una aplicación **Streamlit (Python)** que se ejecuta en
> tu ordenador con `./run.sh` o `run.bat` y abre el navegador en `localhost`. **No es una PWA
> instalable, no se publica en GitHub Pages y no hay APK**: Streamlit necesita un proceso Python
> detrás, y una PWA es un conjunto de ficheros estáticos. Reescribir el modelo en JavaScript (o
> correrlo en el navegador con Pyodide/stlite) es un proyecto aparte que obligaría a revalidar la
> física contra las cinco actividades reales.

---

## Características

**Estimación del CdA a partir de tus actividades**

- Lee `.fit` con GPS y potencia y estima el CdA cerrando el balance de energía, integrando
  intervalo a intervalo: no supone velocidad ni pendiente constantes.
- **Búsqueda automática de tramos fiables**: barre la actividad en ventanas de 1 a 5 km, se queda
  con los llanos, rápidos y sin solapes, y para cada uno localiza **la pasada de vuelta por la
  misma carretera**. Promediar ida y vuelta es la única forma de cancelar el viento sin modelarlo.
- **Selección manual** de un segmento, arrastrando sobre el perfil de la ruta o con un deslizador.
- Cada estimación llega con su **incertidumbre** (propagando error de altitud, de Crr y de sesgo
  del potenciómetro) y con un **diagnóstico de validez** del tramo: si no sirve, lo dice y no
  presenta el valor como bueno.
- **Examen de coherencia de la actividad**: antes de dar por bueno un CdA, comprueba si la salida
  es explicable por el modelo o si fue más rápida de lo que permite la potencia registrada
  (viento a favor, rebufo, grupo). Ver [¿sirve esta actividad?](#sirve-esta-actividad-examen-de-coherencia).
- **Pares imposibles descartados y a la vista**: un par de ida y vuelta cuyas velocidades difieran
  demasiado no mide viento, mide pendiente; se rechaza con su motivo escrito.
- Tabla con **una fila por segmento** y descarga en CSV, con el desglose de la incertidumbre por
  fuente.
- El resultado se lleva al simulador **con un botón**, y queda como un valor editable.

**Predicción de carrera**

- Carga de **GPX**, remuestreo a distancia constante, suavizado de elevación y de trazado.
- **Perfil de potencia por pendiente** con transición continua, umbral y anchura editables.
- Resultado con **tiempo total, velocidad media, tabla y gráficas por tramo, NP, VI e IF**.
- **Límite por curvatura** y tope de velocidad en descenso, con frenada máxima propagada hacia
  atrás; si el límite recorta la velocidad, la potencia aplicada se reduce a la necesaria y eso se
  refleja en NP/VI/IF.
- **Dos bandas de incertidumbre** que miden cosas distintas (modelo y día), las dos obtenidas de
  validación cruzada con actividades reales. Ver [cuánto fiarte](#cuánto-te-puedes-fiar-del-tiempo-predicho).
- **Informe de sensibilidad**: efecto en el tiempo total de cada parámetro a ±10 %, contrastado
  con los datos de tu ruta.
- **Perfiles de bici** con nombre, que guardan de dónde sale su CdA.
- Sin GPX cargado, una **ruta de ejemplo sintética** (~26 km) para probar.

**Transversal**

- **Español e inglés**, con selector en la barra lateral: etiquetas, tooltips de los 40 parámetros,
  pestañas, mensajes y avisos del estimador. Los CSV conservan los nombres técnicos de columna
  (`tiempo_s`, `cda`, `desnivel_m`) en los dos idiomas, a propósito, para no romper hojas de
  cálculo.
- **Tema claro por defecto y oscuro completo**, los dos derivados de los mismos tokens, gráficas
  incluidas.
- **Sistema de diseño propio** en un único módulo (`app/theme.py`), con lenguaje visual explícito
  para la incertidumbre: banda sólida y estrecha = estimado a partir de datos; banda rayada y
  ancha = margen del día o afirmación sin verificar.
- **Núcleo sin dependencias de interfaz** (`core/`): la física, el estimador y las tablas se
  pueden usar y verificar sin Streamlit.
- **372 tests automáticos** ligados a los 32 criterios de aceptación de la especificación.

---

## Requisitos

| | |
|---|---|
| **Python** | 3.9 o superior. Los lanzadores lo detectan y, si falta, lo dicen con el enlace de descarga |
| **Sistema** | Windows, macOS o Linux |
| **Dependencias de la app** | `numpy`, `pandas`, `streamlit`, `plotly`, `fitdecode` (`requirements.txt`) |
| **Dependencias de test** | las anteriores más `pytest` y `scipy` (`requirements-dev.txt`) |
| **Espacio** | unos 300 MB con el entorno virtual creado |
| **Navegador** | cualquiera reciente; la app se abre en `localhost` |

`scipy` es solo para los tests, que lo usan como solución de referencia independiente. **Arrancar
la app no instala dependencias de test**, y un test comprueba que todo lo que importan la app y el
núcleo esté declarado en `requirements.txt`.

Para estimar el CdA necesitas, además, una actividad en `.fit` **con GPS y potencia**, y
preferiblemente con algún tramo llano recorrido en los dos sentidos.

---

## Cómo se ejecuta

**Sin línea de comandos** (recomendado):

- **Windows:** doble clic en `run.bat`
- **macOS / Linux:** `./run.sh` en una terminal (en macOS, si prefieres el doble clic, renombra el
  archivo a `run.command`)

La primera vez crea un entorno virtual en `.venv` e instala las dependencias (un par de minutos);
las siguientes arranca directo. Si clonas el repositorio en macOS o Linux y `./run.sh` no arranca,
dale permiso de ejecución con `chmod +x run.sh`.

| Opción | Qué hace |
|---|---|
| `run.sh` / `run.bat` | abre la aplicación en el navegador |
| `run.sh --estimador` / `run.bat --estimador` | arranca directamente en el módulo de estimación de CdA |
| `run.sh --tests` | instala las dependencias de test y ejecuta los 372 tests |
| `run.sh --reinstalar` | rehace el entorno desde cero |
| `run.sh --reinstalar --tests` | las dos cosas |

A mano, si lo prefieres:

```bash
pip install -r requirements.txt          # app
pip install -r requirements-dev.txt      # app + tests
streamlit run app/streamlit_app.py       # desde la raíz del proyecto
python -m pytest -q                      # 372 tests
```

También se puede fijar el módulo inicial añadiendo `?modo=estimador` a la URL.

> `run.sh` está probado de punta a punta (entorno creado desde cero, aplicación respondiendo).
> **`run.bat` no se ha podido ejecutar en Windows**: está validado por inspección y por un lint
> estático de las trampas de `cmd`. Si te falla, manda lo que diga la ventana.

---

## Los dos módulos y el flujo pensado

Se eligen con el selector **Qué quieres hacer** de la barra lateral:

| Módulo | Entra | Sale | Parámetros que pide |
|---|---|---|---|
| **Estimación de CdA** | una actividad `.fit` | el CdA de esa bici en esa posición, con su margen | 23 |
| **Predicción de carrera** | el GPX del recorrido y un CdA | tiempo, velocidad y potencia por tramo | 40 |

El orden importa, porque **el CdA es una entrada de la predicción y es el parámetro que más la
mueve**: una predicción hecha con el CdA por defecto no es una predicción de tu bici.

1. En el módulo de **estimación**, sube una actividad con el montaje y la posición que vas a llevar
   en carrera, y con algún tramo llano recorrido en los dos sentidos. Pulsa
   **🔍 Buscar tramos fiables**.
2. Lee el veredicto de coherencia y los avisos **antes** del número. Si la actividad no sirve, el
   CdA tampoco.
3. Pulsa el botón para **aplicar ese CdA**. Queda puesto en el simulador como un campo editable:
   úsalo tal cual o corrígelo a mano si tu montaje de carrera no es exactamente el de la actividad.
4. En el módulo de **predicción**, sube el GPX de la competición y di qué potencia piensas
   sostener.

El módulo de estimación **no pide un GPX** ni los parámetros que no intervienen en su cálculo.
Sobre todo, **no pide el CdA**: es lo que estima, y pedirlo como entrada sería circular. Tampoco
pide los perfiles de potencia, el FTP, los límites de velocidad y curvatura ni el remuestreo del
recorrido.

Esa partición vive en el núcleo (`core.params.specs_for_module`) y la vigila un test **empírico**:
cambiar un parámetro que el módulo no muestra no mueve la estimación, y cambiar uno de los que
muestra sí la mueve. La lista no se mantiene a mano.

---

## Qué es el CdA que estima esta herramienta (y qué no es)

Esto es lo más importante que hay que entender para usar los números con cabeza.

En el modelo, `CdA` es el **área de arrastre** (m², el producto del coeficiente de forma por el
área frontal) que multiplica al término aerodinámico `½·ρ·CdA·v²`. Pero el valor que la
herramienta **estima** no es un CdA de túnel de viento: sale de cerrar el balance de energía de un
tramo real. Lo que entró por los pedales, menos lo que se fue en subir, en rodadura y en cambiar la
energía cinética, se atribuye entero al término aerodinámico:

```
∫ η·P dt − Σ ½·m_ef·Δ(v²) − m·g·Σ Δh − ∫ Crr(v)·m·g·cosθ·v dt  =  ∫ ½·ρ·CdA·v³ dt
```

Como el CdA es **el residuo que hace cuadrar esa igualdad**, dentro de él acaba *todo* lo que se
opuso al avance y el modelo no nombra por separado:

| Dentro del CdA estimado | Cuánto pesa |
|---|---|
| La aerodinámica real (bici, cuerpo, casco, ropa, posición) | lo que de verdad se quiere conocer |
| **El viento neto del día** | **el término más grande, con diferencia**: 1 m/s mueve el resultado unos ±0,04–0,06 m², más que todos los demás errores juntos |
| Rebufo de otros ciclistas, vehículos o grupo | puede ser enorme y no se distingue del viento |
| Error del altímetro | ±1 m de desnivel en el tramo se propaga al resultado; en tramos cortos, lentos o con cuesta se traga la estimación entera |
| Diferencia entre el Crr elegido y el firme real | ±0,0005 de Crr, propagado |
| Sesgo del potenciómetro | ±1,5 % de la potencia, propagado |
| Cualquier error residual del propio modelo | va al mismo sitio, por construcción |

Así que, estrictamente, **lo que sale es un coeficiente efectivo de resistencia al avance** para
esa bici, esa posición y condiciones parecidas a las de la actividad — no una propiedad física de
la bici. Consecuencias prácticas:

- **El viento se descuenta emparejando, no modelando.** No es una entrada del modelo. Como es un
  **sesgo y no ruido**, no entra en la incertidumbre: se muestra aparte (banda rayada) y se cancela
  en primer orden promediando un tramo de ida con el mismo de vuelta. Por eso el valor recomendado
  es el de los **pares**, no el de un tramo suelto.
- **El rumbo de cada tramo delata el viento.** Si los tramos hacia un lado dan CdA bajo y los del
  contrario alto, eso es viento y no tu posición. La tabla trae esa columna por ese motivo.
- **Si cambias de equipación o de posición, hay que volver a estimarlo.** Lo que lleves puesto no
  es un parámetro del modelo: está dentro del CdA.
- **No lo compares con cifras de fabricante o de túnel de viento.** No miden lo mismo.
- **Un CdA obtenido en entrenamiento no es el de competición.** El perfil de ejemplo que acompaña
  al repositorio sale de salidas de 4 h a 210-226 W y 31-33 km/h: es un CdA de posición de
  entrenamiento.

### ¿Sirve esta actividad? Examen de coherencia

Cualquier método de ajuste **siempre** devuelve un número: busca el CdA que hace cuadrar las
cuentas y lo encuentra. Lo que no dice es si ese número significa algo. Si un día fuiste más rápido
de lo que permite la potencia que registraste, el ajuste baja el CdA hasta cuadrar el total y el
resultado no es un dato aerodinámico, sino el residuo de un ajuste que no cierra.

El examen detecta esa firma separando el error **por banda de pendiente**, y avisa si:

- el CdA que sale cae **fuera del rango plausible 0,20–0,35 m²**, o
- aparece el patrón **llano demasiado lento (error ≥ +5 %) y bajadas demasiado rápidas (≤ −4 %)**,
  que es lo que produce una salida con viento a favor, rebufo o grupo, y que un simple error de CdA
  no puede producir (los dos signos a la vez, no).

Hacen falta las dos reglas: una de las cinco salidas de referencia tiene el CdA dentro del rango y
solo la caza el patrón. Los umbrales están justificados con datos: en las tres salidas coherentes
el error en llano no pasa de −0,7 % y en bajadas de +0,8 %; en las dos incoherentes el llano está
en +15,8 % y +29,6 % y las bajadas en −7,9 % y −18,4 %. Hay un **orden de magnitud** entre la peor
coherente y la mejor incoherente.

El diagnóstico se construye en el núcleo (`core/coherence.py`), no en la interfaz, y usa
configuración fija a propósito: el veredicto no debe cambiar porque alguien haya tocado un
parámetro para predecir una carrera.

### Protocolo recomendado

1. Usa solo salidas de **la misma bici**.
2. **Pasa cada una por el examen de coherencia** y deja fuera las que avisen. Anota el motivo con
   el dato que lo respalda, no con una hipótesis.
3. Obtén el CdA con los **pares de ida y vuelta**, que es el método reproducible (3,3 % de
   dispersión entre salidas, 1,9 % con el filtro de pares imposibles, frente al 21,3 % del ajuste
   por tiempo total). El ajuste por tiempo total queda como **comprobación independiente**, no como
   fuente del dato.
4. Usa **al menos 2 salidas** coherentes y mira la dispersión entre ellas, no solo el mejor ajuste.
5. **No promedies salidas incoherentes** con las buenas: meterían el viento de su día en el
   parámetro.

### Cuándo un tramo no se da por bueno

Mínimos para considerar utilizable un tramo: **1 km**, 45 s, 25 km/h de media, que al menos la
**mitad** de la energía disipada sea aerodinámica e incertidumbre **≤ ±0,030 m²**. Un tramo que no
los cumpla aparece marcado como no utilizable y con el motivo escrito, no escondido.

---

## El modelo físico

Para cada tramo de longitud `d` sobre el firme, con potencia constante `P` y velocidades `v₀ → v₁`:

```
½·m_ef·(v₁² − v₀²) = d·( η·P / v̄ − ½·ρ·CdA(v̄)·(v₀²+v₁²)/2 − Crr(v̄)·m·g·cosθ ) − m·g·Δh
```

con `v̄ = (v₀+v₁)/2` y `m_ef = m + I/r²` (inercia de las ruedas). Esta forma es exacta para potencia
constante y aceleración uniforme. Se resuelve por tramo con regula falsi (Illinois); si hay varias
soluciones (zona de transición de CdA) se elige la más próxima a `v₀`, siguiendo la trayectoria
real. El tiempo del tramo es `d·2/(v₀+v₁)`.

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
| **Potencia aplicada** | si el límite recorta la velocidad, la potencia aplicada se reduce a la necesaria (≥ 0), y eso se refleja en NP/VI/IF |
| **NP / VI / IF** | NP: media móvil 30 s a 1 Hz y media de 4.ª potencia; VI = NP/media; IF = NP/FTP |

**Suavizado del GPX:** remuestreo a distancia constante (20 m), suavizado gaussiano de la elevación
(ventana 150 m) y del trazado (60 m), pendiente limitada a ±30 %.

### Parámetros (valores por defecto: nivel del mar, A Coruña)

| Categoría | Parámetros principales | Avanzados |
|---|---|---|
| **Ciclista** | masa total (**obligatoria**, sin valor por defecto) · P subida/llano/descenso 220/200/0 W · FTP (opcional) | umbral de pendiente 2 %, anchura de transición 1 %, velocidad inicial 18 km/h |
| **Equipamiento** | CdA 0,27 m² · ΔCdA 0,25 m² · η 0,975 · rueda ETRTO 28-622 (o perímetro medido) | umbral de posición 20 km/h, anchura 1 km/h, inercia 0,14 kg·m² |
| **Variables externas** | temperatura 15 °C · humedad 75 % · superficie (liso/normal/rugoso) · presión 7,0 bar · tramos por km · velocidad máx. 100 km/h · límite por curvatura | presión atmosférica 1013,25 hPa, densidad manual, Crr por superficie, variación de Crr con v, a_lat, frenada, ventanas de suavizado, paso, umbral de pares imposibles |

La clasificación principal/avanzado es una decisión de diseño. La pestaña **Sensibilidad** la
contrasta con los datos de tu ruta (columna `sugerencia`).

---

## Perfiles de bici

Cada montura tiene su propio CdA y sus propias masas, así que la aplicación guarda **perfiles con
nombre** (`perfiles_bici.json`, junto al proyecto; se puede cambiar con la variable de entorno
`SIMCICLISMO_PERFILES`). Un perfil fija masas, CdA, ΔCdA, η, Crr, superficie e inercia, y guarda
además **el origen del CdA**: de qué actividades sale y si está calibrado o es un valor por
defecto. Un CdA guardado sin ese origen no es trazable y la aplicación lo marca como *sin
calibrar*.

`perfiles_bici.ejemplo.json` contiene el perfil obtenido con los pares de ida y vuelta sobre las 3
salidas coherentes del recorrido de referencia (CdA 0,261 m², masa total 90 kg). Renómbralo a
`perfiles_bici.json` para usarlo. Es un CdA de **posición de entrenamiento**: para competir,
estima el tuyo con una actividad que lleve el montaje y la posición de carrera.

---

## Cuánto te puedes fiar del tiempo predicho

La aplicación muestra siempre el tiempo con su margen, con **dos bandas que miden cosas
distintas** — por eso se dan las dos y no la media ni la mejor:

| Banda | Valor | Qué mide y de dónde sale |
|---|---|---|
| **Precisión del modelo** | **±1,4 %** | Validación cruzada dejando una fuera con las 3 salidas coherentes del recorrido de referencia; error medio 0,94 %, máximo 1,39 %. Es lo que vale el modelo físico con la misma bici y ruta cuando el día no se sale de lo normal |
| **Margen del día** | **±15 %** | Obtenido con el protocolo que la propia herramienta recomienda: calibrando solo con las 3 salidas coherentes y prediciendo cualquier día, incluidos los 2 incoherentes. Peor error **14,27 %**. Es lo que cuesta no saber qué viento hizo |

Las tablas y los CSV traen, por cada columna de tiempo, cuatro columnas más (`_min_modelo`,
`_max_modelo`, `_min_dia`, `_max_dia`), para que ningún tiempo salga de la herramienta sin su
margen.

**En una ruta nueva no hay banda verificada.** El margen del día es un **suelo**, no una
estimación: ninguna validación ha podido cruzar de ruta, porque no hay salidas de esta bici por
otro recorrido. El ±11 % que esta tabla daba en versiones anteriores quedó retirado por
incoherente: era *menor* que el margen por viento ya observado en la propia ruta de calibración.

### Resultados con los datos reales (5 salidas del mismo recorrido, mar-2025 a abr-2026)

El modelo se validó separando el error **por banda de pendiente**, que es más exigente que el
tiempo total: un ajuste global puede acertar compensando errores opuestos, y esto no.

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

| Salida | por ajuste de tiempo total | por pares de ida y vuelta |
|---|---|---|
| 30-mar-2025 | 0,2758 | 0,2611 ± 0,0049 |
| 06-abr-2025 | 0,2621 | 0,2661 ± 0,0087 |
| 04-may-2025 | **0,1550** | 0,2435 ± 0,0188 |
| 08-jun-2025 | **0,2131** | 0,2542 ± 0,0095 |
| 19-abr-2026 | 0,2583 | 0,2550 ± 0,0090 |
| **dispersión** | **21,3 %** | **3,3 %** (1,9 % con el filtro de pares imposibles) |

**Los pares de ida y vuelta son reproducibles y el ajuste por tiempo total no**, porque los pares
cancelan el viento medio y el tiempo total lo absorbe entero en el CdA. De ahí que el protocolo use
los pares como fuente del dato. La salida del 19-abr-2026 encaja con las de 2025 por los dos
métodos trece meses después: el CdA resulta estable a lo largo de un año.

Los tramos sueltos, uno a uno, dan entre 0,18 y 0,39 m² según el tramo. Eso **no es dispersión de
método**: es el viento, y se ve en los rumbos. Además, **el sesgo de selección está cuantificado y
la aplicación lo declara**: exigir velocidad alta y poco desnivel no da una muestra neutra — los
tramos elegidos van a 36,3 km/h frente a los 31,4 km/h de la ruta, con una pendiente media de
−0,16 %. Son justo los tramos con viento a favor o bajada suave, y por eso un tramo suelto, por muy
fiable que parezca su diagnóstico, da un CdA bajo.

El informe completo, con las tablas por banda de cada salida y el diagnóstico de las dos
incoherentes, está en [`simulador-ciclismo-triatlon.validacion.md`](simulador-ciclismo-triatlon.validacion.md).

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

Con ventana de 10 m el error ronda el 20 %. **Si tu GPX tiene elevación GPS ruidosa (σ ≥ 3 m), sube
la ventana de suavizado** (avanzado) o usa un GPX con elevación barométrica o corregida. Parte del
error viene de que `P_descenso = 0 W` convierte el ruido de pendiente en descensos ficticios.

---

## Limitaciones conocidas

- **El viento no es una entrada del modelo.** El de la actividad real queda absorbido en el CdA
  estimado (sesgo, no ruido). Es la limitación de fondo de toda la herramienta.
- **El CdA estimado es un coeficiente efectivo**, no una propiedad de la bici: incluye viento,
  rebufo, error de altímetro, firme y sesgo del potenciómetro. Ver
  [la sección dedicada](#qué-es-el-cda-que-estima-esta-herramienta-y-qué-no-es).
- **CdA único** por bici (el cambio a posición convencional se modela solo por velocidad), y es la
  mayor fuente de incertidumbre: ±0,02 m² mueven el tiempo más que cualquier ajuste fino del
  terreno.
- **Transferencia entre rutas sin verificar:** las cinco salidas de referencia son el mismo
  recorrido, con un 94-98 % de solape. Falta una salida de la misma bici por otro recorrido para
  cerrarlo.
- **Posición de carrera sin verificar:** los datos disponibles son de entrenamiento.
- **Velocidad instantánea:** sigue fallando ±3 km/h de MAE aunque el tiempo total acierte.
- **Valores de `crr1`** (variación de Crr con la velocidad): estimaciones sin respaldo experimental
  sólido; calíbralos o déjalos en el defecto.
- **Superficie:** el GPX no la trae; se elige global y se sobrescribe a mano por tramos de km.
- **Presión de neumáticos:** el modelo solo baja el Crr al subir la presión. No representa que en
  firme rugoso, por encima de cierta presión, el conjunto se vuelva más lento. En rugoso y a mucha
  presión el resultado es optimista.
- **Masa obligatoria:** la aplicación no simula hasta introducir la masa total.
- **La masa mayor puede ser más rápida** en rutas con descensos a 0 W (la gravedad escala con la
  masa y la resistencia aerodinámica no).
- **Tablas en modo oscuro:** se quedan claras, porque Streamlit las dibuja en un lienzo al que no
  llega el CSS. Es una excepción declarada.
- **Alcance de esta versión:** solo simulación directa. Sin optimizador de pacing, sin modo
  inverso, sin DEM y sin extracción de superficie desde OSM.
- XML del GPX parseado con `xml.etree` (uso personal; no exponer a archivos no confiables).

---

## Estructura del repositorio

```
core/                 núcleo en Python/numpy, sin dependencias de interfaz
  params.py           parámetros, defaults, rangos, categorías, validación (única fuente de verdad)
  atmosphere.py       densidad del aire (temperatura, humedad, presión, altitud)
  route.py            lectura de GPX, remuestreo, suavizado, pendiente y curvatura
  physics.py          potencia por pendiente, CdA(v), Crr(v) y resolución por tramo
  simulate.py         simulación completa + tabla por bloques de km
  metrics.py          potencia media, NP, VI, IF
  sensitivity.py      sensibilidad ±10 % de cada parámetro
  cda_estimator.py    estimación del CdA: por segmento, búsqueda automática de tramos llanos
                      y emparejado de ida y vuelta por la misma carretera
  coherence.py        examen de coherencia de una actividad: ¿sirve para estimar con ella?
  validation.py       lectura de .fit, reproducción de la potencia real y ajuste por tiempo total
  profiles.py         perfiles de bici (masa, CdA, Crr, η) con el origen del CdA
  wheels.py           medidas ETRTO y perímetro de rueda
  uncertainty.py      bandas de incertidumbre obtenidas en la validación real
  exports.py          tablas que la aplicación muestra y descarga, con las bandas incorporadas
  i18n.py             traducciones al inglés y cadenas de la interfaz
  synthetic.py        rutas sintéticas (tests y ruta de ejemplo)
app/streamlit_app.py  interfaz en Streamlit, con los dos módulos
app/theme.py          sistema de diseño: tokens de color, tipografías y los componentes
                      de lectura numérica y de banda de incertidumbre
.streamlit/config.toml  tema claro por defecto y barra superior de Streamlit oculta
tests/                tests automáticos de los criterios de aceptación
  fixtures/           5 actividades reales reducidas y anonimizadas; ver su README
docs/calidad/         registro de defectos y revisiones independientes
simulador-ciclismo-triatlon.spec.md       especificación y sus 32 criterios de aceptación
simulador-ciclismo-triatlon.validacion.md informe de validación con datos reales
```

---

## Tests

```bash
python -m pytest -q        # 372 tests
run.sh --tests            # instala las dependencias de test y los ejecuta
```

Cubren: física (contra solución analítica y contra una integración RK4 independiente), límites de
velocidad y curvatura, continuidad de CdA y de potencia, monotonía, ruido de elevación, simetría de
circuitos, parámetros y validación de rangos, sensibilidad, lector de `.fit` (con un escritor FIT
mínimo propio), estimador de CdA y emparejado de ida y vuelta, examen de coherencia, perfiles de
bici, bandas de incertidumbre, ruedas, presión, exportaciones, los dos idiomas, el sistema de
diseño y la interfaz con `streamlit.testing` (incluida la pestaña del estimador de punta a punta,
subiendo un `.fit` de verdad).

Los umbrales concretos de cada test y el criterio al que responde están en
[`simulador-ciclismo-triatlon.spec.md`](simulador-ciclismo-triatlon.spec.md). El estado de la
calidad, con el registro de defectos y las revisiones independientes, en
[`docs/calidad/README.md`](docs/calidad/README.md).
