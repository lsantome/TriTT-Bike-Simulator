# Registro de defectos pendientes

**Método.** El código **no se toca** entre revisiones, para que los resultados sean comparables.
Huella del árbol revisado (receta en `huella.py`, sha256 de `core/`, `app/` y `tests/`):

```
58847d19c52af1142dba07adfc331a9dc9df934edceaa99640633c0ce018e958   (42 ficheros)
```

303 tests pasan. Las revisiones 1-3 se midieron sobre el mismo árbol con otra receta de huella
(`80999239b5a2c3c14ee40c203cb9f603`, md5) que no quedó anotada y no he podido reproducir.

| Revisión | Fecha | CUMPLE | PARCIAL | NO CUMPLE | Nuevos | Instrumento |
|---|---|---|---|---|---|---|
| 1 | 6-oct | 20 | 11 | 1 | 12 (línea base) | ad hoc: lectura de código + suite |
| 2 | 7-oct | 26 | 6 | 0 | 3 | ad hoc: + Playwright en un criterio |
| 3 | 8-oct | 23 | 9 | 0 | ~40 | ad hoc: + píxeles, `bash run.sh`, remedición |
| **4** | **12-oct** | **21** | **10** | **1** | **29** | **encargo congelado + calibración por siembra** |

**Las revisiones 1-3 no son comparables entre sí**: endurecí el encargo en cada ronda, así que la
curva de hallazgos medía el encargo, no el repositorio. Desde la revisión 4 el encargo se pasa
literal (`encargo-congelado.md`) y la serie empieza a medir el código. **La revisión 4 es la medida
nº 1 de la serie comparable; la primera que puede confirmar saturación es la 5.**

**Regla de recuento.** El número de «nuevos» sale **solo del brazo congelado** (revisores a1, a2,
a3). Los hallazgos del brazo de calibración (b1, b2, b3), que trabajan sobre un árbol con tres
semillas, se registran igual cuando afectan a código idéntico en los dos árboles, pero **no cuentan
en la serie**: si contaran, el número dependería de si ese ciclo llevó siembra o no. Van marcados
`[b]`.

**Lo que no está en duda.** Ningún defecto del registro cambia el resultado del modelo físico en
condiciones normales. Las cuatro revisiones coinciden en que los criterios **1, 2, 4, 5, 7, 8, 11 y
13** cumplen con medidas independientes. La revisión 4 retira de esa lista los criterios **3** y
**9** (ver A20 y `[b]`-9).

---

# A. Funcionales — afectan a lo que la herramienta hace o muestra

## Del registro anterior (revisiones 1-3)

**A1 · C21/C32 — el modo oscuro no llega a los gráficos.** `st.plotly_chart` usa `theme="streamlit"`
por defecto y pisa la plantilla. Medido por píxel: lienzo en `#F2F5F7` sobre página oscura.
*(rev 2, 3 y 4 — a2, b2, b3.)* **Corrección:** `theme=None` en `app/streamlit_app.py:432, 474, 726`
**y** fijar `paper_bgcolor`, `plot_bgcolor` y `font_color` en el propio `update_layout`; la rev 2 y
la rev 4 comprobaron por separado que solo con `theme=None` no basta.

**A2 · C32 — la tipografía propia no se aplica donde más se ve.** La familia se declara solo en
`.stApp`, la barra lateral y la cabecera (`app/theme.py:102-104`) y pierde contra los selectores de
Streamlit. *(rev 3; la rev 4 lo cuantifica: 44 nodos del panel principal en `Source Sans` frente a
5 en `Instrument Sans` — a2, a3, b3.)*

**A3 · C30 — `btn_aplicar_est` no propaga el veredicto de incoherencia.** *(rev 3 y 4.)*

**A4 · C30 — el camino manual no ejecuta el examen de coherencia.** Solo se lanza en la rama de
«Buscar tramos». *(rev 3; la rev 4 lo reproduce: con el fixture del 04-may-2025 aplica 0,269 como
calibrado sin un solo aviso — a3.)*

**A5 · C30 — ni `btn_aplicar_cal` ni `btn_aplicar_est` limpian `cda_cal_incoherente`.** *(rev 3.)*

**A6 · C28 — `pair_opposite_segments` marca los segmentos como usados *antes* de comprobar el
rechazo.** *(rev 3.)*

**A7 · C29 — la leyenda contradice al núcleo y al criterio.** «día ±15 %, sin verificar»
(`core/i18n.py:948`) frente a `band_dia(...).verificada is True`. *(rev 3 y 4 — a1, a3.)*

**A8 · C27 — los 21 nombres de medida de rueda siguen en castellano en inglés.** *(rev 2;
verificado.)*

**A9 · C27 — el docstring de `core/wheels.py:label_for` afirma que sí se traducen.** Es falso.

**A10 · C27 — las celdas `sí`/`NO` de `utilizable` y `coherente` no se traducen.**

**A11 · C11 — falta la gráfica de pendiente suavizada** que el Alcance enumera. *(rev 3 y 4 — a1,
b1.)*

**A12 · C19 — 21 de los 39 tooltips no citan sus unidades.** *(rev 3 y 4 — b2.)*

**A13 · C20 — «Borrar» no reinicia el idioma ni el módulo activo**, y `"km_block"` no corresponde a
ningún widget. *(rev 3; la rev 4 añade `"fit_sel"`, que tampoco existe — a2, b2.)*

**A14 · C28 — el umbral de razón de velocidades (1,5) no es editable**, aunque el criterio dice que
lo es. *(rev 3.)*

**A15 · C32 — no existe la transición de la banda** que el criterio declara como «la única
transición». *(rev 2, 3 y 4 — medido: `transition-duration: 0s`, `animation-name: none`.)*

**A16 · C32 — la monoespaciada se aplica a etiquetas** (`[role="columnheader"]`), que el criterio
prohíbe. *(rev 2 y 4 — a3.)*

**A17 · C22 — el rechazo «perímetro sin elegir manual» no explica cómo medirlo.** *(rev 3.)*

**A18 · C31 — el módulo del estimador menciona el GPX.** *(rev 2 y 3.)*

**A19 · C32 — no hay tokens de espacio**, solo literales repetidos. *(rev 2.)*

## Nuevos en la revisión 4 (brazo congelado)

**A20 · C3 — la velocidad supera `√(a_lat·R)` dentro de las curvas, por dos mecanismos distintos.**
(a) El trazado se suaviza *antes* de derivar la curvatura (`core/route.py:199`), así que en los
extremos del arco `kappa` queda por debajo de la real; (b) `MAX_CURVATURE = 0,10`
(`core/route.py:17`) recorta todo radio menor de 10 m. **Medido por mí** sobre el arco de los tests,
máximo en todo el arco frente a `√(3·R)`:

| R (m) | límite (m/s) | máximo simulado | exceso |
|---|---|---|---|
| 35 | 10,247 | 13,278 | **+29,6 %** |
| 30 | 9,487 | 12,598 | +32,8 % |
| 20 | 7,746 | 10,764 | +39,0 % |
| 8 | 4,899 | 7,352 | +50,1 % |
| 4 | 3,464 | 7,461 | **+115,4 %** |

A 35 m de radio —una curva de carretera corriente— el modelo deja entrar a 47,8 km/h donde el
criterio permite 36,9. Sesga la predicción **a la baja en tiempo** en recorridos con muchas curvas.
*(a1 y b1 por separado, cada uno con un mecanismo; medido y ampliado por mí.)*
**Corrección:** aplicar el límite sobre la curvatura sin suavizar (o propagar hacia los extremos la
curvatura máxima del entorno), y declarar en el criterio 3 y en las limitaciones del README qué pasa
por debajo de `MAX_CURVATURE`. Ver también B30.

**A21 · C16/C27 — la procedencia de las dos bandas sale en castellano con la interfaz en inglés.**
`core/uncertainty.py:53-58` (`ORIGEN_MODELO`, `ORIGEN_DIA`, cadenas fijas sin i18n) concatenadas en
`app/streamlit_app.py:406-407`. *(a1, b1.)*

**A22 · C12 — el motivo de exclusión del informe de sensibilidad es falso para tres parámetros
numéricos.** `core/sensitivity.py:47-52`: `ftp`, `densidad_manual` y `perimetro_mm` salen con «No es
un número: no se puede variar un ±10 %» teniendo valor numérico; la causa real es
`kind == "optional_float"` con `sensitivity=False`. *(a1, b1.)*
**Corrección:** evaluar `not s.sensitivity` antes que `s.kind != "float"` y dar un motivo propio a
los opcionales vacíos.

**A23 · C14/C16 — la cifra grande lleva siempre el margen de la ruta de calibración (±1,4 %), se
simule la ruta que se simule.** `app/streamlit_app.py:380-400`. Para el caso de uso real —el GPX de
la competición— ese `±` es justo el que el criterio 14 prohíbe presentar como precisión esperable.
Mitigado por la banda rayada y por el pie, no resuelto. *(a1.)*

**A24 · C25 — la interfaz enseña dos velocidades distintas para los mismos tramos.**
`app/streamlit_app.py:604-606` llama a `search_summary` con `[par.ida for par in pares]` mientras el
pie (`:643-644`) usa ida y vuelta. Medido sobre `recorrido2_30mar2025.fit`: la misma pantalla dice
«35,0 km/h en los tramos» y «los tramos encontrados van a 38,3 km/h». *(a2.)*

**A25 · C25 — el aviso de sesgo de selección se dispara con un número que no describe lo que dice, y
puede no aparecer.** Consecuencia de A24: en `recorrido2_19abr2026.fit` el sesgo real es +1,71 km/h
(`hay_sesgo = False`) y la app avisa con +3,49 km/h. Y el aviso está condicionado a `hay_sesgo`
(`:691`), cuando el sesgo es una propiedad del método de búsqueda, no de la actividad. *(a2, b2.)*

**A26 · C21 — el texto de los ejes no llega a AA.** `#808495` sobre `#F2F5F7` = **3,39:1** en los
dos temas, porque el `tickfont` de `app/theme.py:68` nunca se aplica. Derivado de A1. *(a2.)*

**A27 · C31 — la pestaña «Validación con FIT» se dibuja dentro del módulo estimador y se gobierna
con nueve parámetros que ese módulo esconde, el `cda` entre ellos.** `app/streamlit_app.py:477` y
`:559-573`. Medido: cambiar `cda` mueve el error de tiempo que la pestaña presenta de **−0,53 % a
+9,62 %**, y el valor usado es el 0,27 por defecto de la dataclass, invisible en ese módulo. *(a3.)*

**A28 · C32 — contraste 2,11:1 (claro) y 2,01:1 (oscuro) en los dos selectores principales y en los
botones primarios.** `app/theme.py:148-153` colorea el `<button>` pero `[data-testid="stSidebar"] *`
(`:106`) gana al nodo de texto. Afecta a «ES · Español», «Medir mi CdA», «▶ Simular» y «🔍 Buscar
tramos fiables». *(a3, b3.)*

**A29 · C32 — contraste 1,15:1 en la cabecera del desplegable «Perfil de bici» en oscuro y 1,10:1 en
el pie del subidor.** Los botones `−`/`+` de los `number_input` conservan fondo blanco.
`app/theme.py:127-129` colorea el contenedor del `stExpander`, no su cabecera. *(a3, b3.)*

**A30 · C27 — mensajes del núcleo sin traducir.** Errores de `validate_params`
(`core/params.py:349-388`), errores y avisos del GPX (`core/route.py:78, 86, 109, 123, 127, 132`) y
el spinner «Simulando…» (`app/streamlit_app.py:150`). Entre ellos está el mensaje que el criterio 22
exige para la rueda manual. *(a3.)*

**A31 · C27 — los valores del desplegable de superficie por tramos de km no se traducen.**
`app/streamlit_app.py:248`: `options=list(SURFACES)` → `liso / normal / rugoso` en inglés, mientras
el mismo parámetro global sí usa `superficie_label`. *(a3.)*

**A32 · C10 — el mensaje de masa ausente interpola la etiqueta capitalizada en mitad de la frase.**
`core/i18n.py:419-423` → «Falta Masa total (ciclista + bici + equipo): …». Cosmético. *(a1.)*

---

# B. Tests que no pueden fallar

## Del registro anterior

**B1 · C21/C32 — los tres tests del tema son incapaces de detectar A1** (cadena en el CSS,
diccionario de `plantilla_plotly`, regex de `template=` sobre el fuente). *(rev 2, 3 y 4.)*
**B2 · C14 — la guarda de la prohibición es una búsqueda de la cadena «11 %»** en tres ficheros; ni
`app/streamlit_app.py` ni `validacion.md` entran en el barrido. *(rev 3; la rev 4 añade el segundo
fichero — a1.)*
**B3 · C29 — `MODELO_PCT <= PEOR_ERROR_MODELO_PCT * 1.5` permitiría inflar la banda del día hasta el
21,4 %.** *(rev 3.)*
**B4 · C28 — `assert max(legitimos) < MAX_RAZON_VELOCIDAD_PAR < min(rechazados)` es tautológico.**
*(rev 3.)*
**B5 · C13 — `rmse >= mae` es una identidad matemática.** *(rev 3.)*
**B6 · C11 — `len(at.dataframe) >= 1` y `len(plotly_chart) >= 1`.** *(rev 3 y 4 — a1, b1: «se podría
borrar la gráfica de velocidad o intercambiar dos trazas y la suite seguiría verde».)*
**B7 · C17 — cuatro tests son búsqueda de cadenas y ni `run.sh` ni `run.bat` se ejecutan en la
suite.** *(rev 3.)*
**B8 · C17 — `tests/test_arranque.py:200` compara posiciones de texto.** *(rev 3.)*
**B9 · C16 — el barrido de columnas de tiempo las detecta por el nombre.** *(rev 3.)*
**B10 · C30 — ningún test recorre el camino manual del estimador.** *(rev 3 y 4: `grep btn_aplicar_est`
en `tests/` → cero.)*
**B11 · C30 — `abs(error_llano) < 3.0` es frágil: el valor real de 30-mar-2025 es 2,51 %.** *(rev 3.)*
**B12 · C29 — ningún test comprueba cómo se etiqueta la banda en pantalla.** *(rev 3 y 4.)*
**B13 · C31 — el test de los lanzadores busca `--estimador` en el fuente.** *(rev 3.)*
**B14 · C31 — ningún test cubre `?modo=estimador`.** *(rev 3.)*
**B15 · C31 — `test_c31_el_estimador_no_pide_recorrido` solo mira las etiquetas de los subidores.**
*(rev 2 y 3.)*
**B16 · C32 — `test_c32_el_contraste…` solo comprueba contra `papel`.** *(rev 3; la rev 4 lo
confirma midiendo cuatro fallos reales con la paleta intacta — A28, A29.)*
**B17 · C32 — sin tests de tipografía renderizada ni del requisito «sin animaciones».** *(rev 3 y 4.)*
**B18 · C12 — ningún test vigila la columna `sugerencia`.** *(rev 2.)*
**B19 · C25 — el test del «al menos 1 km» admite 900 m.** *(rev 3 y 4.)*
**B20 · C27 — las tablas construidas a mano en la interfaz no las vigila ningún test de traducción.**
*(rev 3.)*
**B21 · C27 — `tests/test_exports.py:117` exige el castellano en las celdas `sí`/`NO`.** *(rev 2.)*

## Nuevos en la revisión 4 (brazo congelado)

**B22 · C24 — toda la batería del criterio 24 es ciega a un error en la física compartida.**
`tests/test_cda_estimator.py:22-29` genera las actividades de referencia con `core.simulate` y
contrasta el caso real contra `calibrate_cda`, que pasa por el mismo simulador. **Verificado por
mí:** con `air_density` sesgada un +3 %, los 23 tests de ese fichero **siguen en verde** (el sesgo lo
caza otro fichero, ver B23) mientras el CdA estimado sobre el fixture real cae un 2,9 %. *(a2.)*
**Corrección:** al menos un caso con una actividad construida fuera del modelo —velocidad y potencia
analíticas en llano, con ρ, Crr y η fijados a mano y el CdA despejado a lápiz— de modo que una
desviación de los coeficientes físicos rompa el test.

**B23 · atmósfera — hay un solo test atmosférico, de un punto, con una tolerancia 7 veces mayor que
el error que se quería detectar.** `tests/test_route_and_limits.py:13-15`: `air_density(15, 75,
1013.25, 0) == approx(1.219, abs=0.005)`, es decir **±0,410 %**, en un único punto, y **ningún test
de `saturation_vapor_pressure_hpa` contra una referencia externa**. **Este es el hallazgo del
experimento de siembra** (ver `rev4-informe.md`): una constante de Magnus equivocada produce
+0,058 % de densidad a 15 °C —siete veces por debajo de la tolerancia— y **+0,44 % a 35 °C/90 %**,
que sí la superaría, pero el test nunca evalúa ese punto. Es la región no medida de la suite.
**Corrección:** una referencia escrita a mano para `saturation_vapor_pressure_hpa` (tabla de Magnus
a 0, 10, 20, 30, 40 °C) y densidad en al menos tres puntos de temperatura, con tolerancia al 0,05 %.

**B24 · C25 — el ±0,02 contra el método independiente se comprueba sobre un solo fixture.**
`tests/test_cda_estimator.py:209-223`. Medido en las tres coherentes: 0,0090 / 0,0062 / 0,0027.
*(a2, b2.)*

**B25 · C25 — el test del sesgo de selección prueba el núcleo bien llamado, no la llamada de la
app.** `tests/test_cda_estimator.py:238-248` pasa todos los tramos; la app pasa solo las idas. Por
eso sobrevive A24. *(a2.)*

**B26 · C31 — el test empírico del criterio 31 no cubre `replay`.** `tests/test_modulos.py:192-207`
recorre `combine_pairs`, `check_coherence` y `search_summary`, pese a que su docstring dice «*todo*
lo que el módulo enseña». Por eso sobrevive A27. *(a3.)*

**B27 · C12 — el motivo del criterio 12 solo se comprueba como «no vacío».**
`tests/test_params_outputs.py:122`: `assert por["etrto"]["nota"] and por["ftp"]["nota"]`. Un motivo
equivocado —que es lo que ocurre, A22— pasa el test. *(a1.)*

**B28 · C26 — `assert list(df.columns) == list(COLUMNAS_SEGMENTOS_BASICAS)` compara la constante
consigo misma.** `tests/test_exports.py:109, 133`. *(a3.)*

**B29 · C16 — el test del criterio 16 pasa *gracias* a A21.** `tests/test_app.py:247-257` busca
«protocolo recomendado» y «3 salidas coherentes» como literales españoles; los encuentra porque el
texto está sin traducir. Corregir A21 rompería este test. *(a1.)*

**B30 · C3 — el test de curvatura se exime del tramo donde el criterio falla y compara contra la
curvatura ya recortada.** `tests/test_route_and_limits.py:71-80`: restringe la comprobación al
interior del arco con un margen de 4σ («para que el suavizado no los contamine») y luego asevera
`v <= √(3/κ)` usando la `κ` del perfil, que ya viene recortada por `MAX_CURVATURE`. Los dos
mecanismos de A20 son invisibles por construcción. *(a1, b1; verificado por mí.)*

---

# C. Documentación con cifras o afirmaciones falsas

## Del registro anterior

**C1 · README:382 — «comprobado por mutación» sin ningún test de mutación en el repositorio.**
**C2 · README:365 — «+1,26 %» donde lo medido es +1,2548 %.**
**C3 · README:365 — el renglón del criterio 13 habla de «5 salidas» cuando ese test usa 2.** *(la
rev 4 lo remide con las tres coherentes: −1,56 % a +1,61 % en las seis permutaciones — a1, b1.)*
**C4 · README — «226 tests» en tres sitios cuando la suite es de 303**, y «2 actividades reales»
cuando son cinco. *(rev 2 y 4.)*
**C5 · README:377 — «discrepancia > 0,04 sobrevive»; el test exige > 0,09.**
**C6 · README:209-211 — «las tablas se quedan claras en modo oscuro» está desactualizado.** La rev 4
precisa el matiz: **el texto** sí hereda la tinta oscura (b2) pero **el fondo** del `st.dataframe` se
queda claro porque se pinta en canvas con el tema de Streamlit (a2, a3). Las dos observaciones son
compatibles; la frase del README sigue sin describir lo que pasa.
**C7 · C12 — la columna `sugerencia` emite «candidato a avanzado» para filas cuyo efecto nunca se
midió.**
**C8 · C17 — `--tests` instala las dependencias de la app sin sellar su hash.**
**C9 · C17 — el guardián de imports no escanea `app/theme.py`.**

## Nuevos en la revisión 4 (brazo congelado)

**C10 · `validacion.md:193` sigue dando por viva la banda de ±11 % para ruta nueva**, que la spec
v10/v11 retiró. *(a1.)*
**C11 · README:367 describe para el criterio 18 el test tautológico que se eliminó el 6-oct**
(«el tiempo no cambia al repartir la misma masa total de otra forma»), hoy imposible de escribir.
*(a2, b2.)*
**C12 · el «menos del 0,001 %» del tamaño de rueda es la medida de la ruta más favorable.**
`core/params.py:186`, `core/wheels.py:14`, `README.md:101`: 0,00073 % en `demo_track` pero
**0,0097 %** en una ruta ondulada de 60 km. *(a2.)*
**C13 · README:242 promete en la tabla del estimador «el CdA descontando las prendas»**, columna que
no existe ni puede existir desde la v8. *(a2.)*
**C14 · README:186 nombra un botón que no existe** («Llevar al simulador»; el real es «Aplicar este
CdA en la barra lateral»). *(a3.)*
**C15 · `run.sh:91-92` describe un mecanismo que el script no usa** (dice que el módulo se
selecciona por la URL; lo que hace es pasar `-- --modo=estimador`). *(a3.)*
**C16 · `tests/test_diseno.py:190` afirma que la monoespaciada se usa en las celdas de tabla**, que
se pintan en canvas con la fuente de Streamlit. *(a3.)*
**C17 · matiz en el docstring de `tests/test_physics.py:86-87`:** Δv máx = 5,20 km/h y salto máx =
0,1872 m² son correctos por separado pero no ocurren en el mismo par de muestras. *(a1.)*

---

# D. Spec inconsistente consigo misma

**D1 — el criterio 28 habla de «las cuatro salidas coherentes» y los Insumos declaran tres.** *(rev 3
y 4: la cuarta sin pares imposibles es la del 08-jun-2025, que es incoherente — a3.)*
**D2 — el historial de la v11 dice «19 parámetros» y el código mide 22.** *(rev 3 y 4 — a1, a3.)*

---

# E. Higiene

**E1 — `_en_estimador()` en `tests/test_app.py:51` es código muerto.**
**E2 — `tests/test_equipo_y_ajustes.py:140` y `:188` son el mismo test duplicado.** *(rev 3 y 4.)*
**E3 — el bloque (c) de `tests/test_equipo_y_ajustes.py:52-56` usa `demo_track()`.**
**E4 · C26 — la tabla de pares se construye en la interfaz, no en el núcleo.**
**E5 — dos cadenas de traducción huérfanas:** `est_m_pares` (`core/i18n.py:617`) y `est_recomendado`
(`:620`) no las usa nadie desde que el resultado se presenta con `theme.lectura`. Quedan dos
redacciones del mismo mensaje, una muerta. *(rev 4 — a2.)*

---

# Hallazgos del brazo de calibración `[b]` — fuera del recuento de la serie

Observaciones de b1, b2 y b3 sobre código **idéntico en los dos árboles** (no tocan ninguna semilla).
Son defectos reales; se registran para no perder la información, pero no cuentan como «nuevos» de la
serie porque el brazo `b` solo existe en los ciclos con siembra.

**[b]-9 · C9 — el ±0,5 % del criterio 9 no es una propiedad del modelo, sino del circuito elegido.**
Con el fixture del test (R = 4000, amp = 30) la diferencia es 0,1508 %; con
`asym_loop_track(radius=2500, amp=60)` sube a **2,7612 %**, y **24 de 36** circuitos asimétricos
barridos superan el 0,5 %, con potencia constante y sin viento. Causa aislada: al invertir el
circuito la pendiente cambia de signo y `∮ds/v(g) ≠ ∮ds/v(−g)` salvo distribución simétrica. El
comportamiento es físicamente correcto; **lo que sobra es el enunciado del criterio**. *(b1.)*
→ Con A20, el criterio 9 sale de la lista de «no está en duda».

**[b]-20 · C20 — «Borrar» deja la pantalla contradiciendo al estado interno.** Tras pulsarlo, el
campo de masa sigue mostrando `90.0` mientras la página dice «Falta la masa total», y el interruptor
de modo oscuro sigue encendido con el tema ya en claro. `AppTest` no lo ve porque lee
`session_state`, que sí queda limpio. *(b2.)*

**[b]-25 · C25 — el mínimo de 1 km no está implementado:** `MIN_DISTANCIA_M = 500.0`
(`core/cda_estimator.py:57`); medido, `find_flat_segments` devuelve un tramo de **944,7 m** en
`recorrido2_04may2025.fit`. B19 cubría la tolerancia del test; esto es el código. *(b2.)*

**[b]-21 · C21 — `modo_oscuro_ayuda` afirma que oscurece «la interfaz y los gráficos».** *(b2.)*

**[b]-28 · C28 — solape de pares no garantizado:** `core/cda_estimator.py:610` contrasta la `vuelta`
contra los rangos usados, nunca la `ida` contra una vuelta anterior. No ocurre en las cinco salidas.
*(b2.)*

**[b]-19 · C19 — `tramos_superficie` es un parámetro del modelo editable en la interfaz que no está
en `PARAM_SPECS`**, así que queda fuera de la garantía del criterio. *(b2.)*

**[b]-6 · C6 — el umbral de continuidad es 16 veces más ancho que el salto real** (0,5 W frente a
0,03 W medidos, `tests/test_physics.py:153`). No es tautológico pero no es ajustado; el criterio 5,
en el mismo fichero, enseña cómo se hace. *(b1.)*

**[b]-14 · C14 — `AVISO_RUTA_NUEVA` ya no es lo que la interfaz muestra** (`t("banda_ruta_nueva_corto")`),
pero dos tests garantizan el contenido de esa constante que el usuario nunca lee. *(b1.)*

**[b]-1 · C1/C2 — `test_solver_coincide_con_integracion_rk4_independiente` reutiliza `cda_effective`
y `crr_effective`.** El esquema de integración sí es independiente, así que no es tautológico, pero
valida el **solver**, no el modelo de fuerzas; conviene que el docstring lo diga. *(b1.)*

**[b]-32a · `.streamlit/config.toml:3-4` afirma que el modo oscuro alcanza a los gráficos.** *(b3.)*
**[b]-32b · README:381 afirma 4,5:1 «en ambos temas»**, cierto para los pares de tokens que el test
mide y falso para lo que el navegador dibuja (A28, A29). *(b3.)*
**[b]-32c · errata en `core/i18n.py:927`:** «medisteis» → «mediste». *(b3.)*
**[b]-32d · código muerto en `tests/test_diseno.py:105-110`:** `pestanas()` se define y no se usa.
*(b3.)*
**[b]-32e · 26 `st.warning`/`st.success`/`st.info` de fábrica conviven con el sistema de diseño**,
pese a que el docstring de `theme.veredicto` los da por sustituidos. *(b3.)*

---

# Confirmado corregido

Siete criterios que la revisión 1 marcó y la 2 dio por cumplidos: 5 (el único NO CUMPLE), 10, 14,
16, 25, 29 y 30. Las revisiones 3 y 4 no los revierten: sus hallazgos sobre 25, 29, 30 y 31 son
puertas distintas del mismo criterio, no la vuelta del defecto anterior.

---

# Recuento

| Grupo | Antes de rev 4 | Nuevos (brazo congelado) | Total |
|---|---|---|---|
| A · funcionales | 19 | 13 | **32** |
| B · tests que no verifican | 21 | 9 | **30** |
| C · documentación | 9 | 8 | **17** |
| D · spec | 2 | 0 | **2** |
| E · higiene | 4 | 1 | **5** |
| **Total de la serie** | **55** | **31** | **86** |
| `[b]` fuera de recuento | — | 13 | 13 |

(Los 29 «nuevos» de la tabla de cabecera son hallazgos distintos del brazo congelado; suman 31
entradas de registro porque dos se desdoblaron al clasificarlos: A20 genera además B30, y A24
genera además B25.)

**Estimación de lo que queda.** Captura-recaptura (Chapman) entre el registro anterior (55) y lo que
el brazo congelado reportó (53 ítems, 24 ya conocidos):

```
N̂ = (55+1)(53+1)/(24+1) − 1 ≈ 120
```

es decir, del orden de **120 defectos detectables con este encargo**, de los cuales 86 ya están
registrados y **quedarían unos 34 sin detectar**. La estimación supone que todos los defectos son
igual de fáciles de encontrar, cosa que no se cumple (las revisiones 1-3 usaron instrumentos más
flojos y cada revisor cubre solo un tercio de los criterios), así que vale como orden de magnitud,
no como cifra.

---

# Sobre el criterio de parada

El instrumento ya está fijado y calibrado, así que la regla «parar cuando una revisión no encuentre
nada nuevo» por fin es medible. Dos cosas que la revisión 4 deja claras:

1. **La serie no está cerca de saturar.** Si quedan ~34 de ~120, un brazo congelado de la revisión 5
   traería del orden de 15 hallazgos nuevos. Hacen falta varias rondas más de revisión **sobre
   código congelado** para llegar al conjunto vacío, y cada una cuesta lo mismo que esta.
2. **Revisar más no mejora el código, solo el registro.** Con 32 defectos funcionales abiertos, el
   siguiente movimiento rentable es corregir el grupo A y volver a medir con el mismo encargo: ahí
   «nada nuevo en A» sí sería información sobre la herramienta.

**Recomendación:** cambiar el umbral a «ninguna revisión encuentra nada nuevo **del grupo A**», y
pasar a corregir. La serie comparable (encargo congelado, siembra de calibración) se mantiene para
medir después de cada tanda de correcciones.
