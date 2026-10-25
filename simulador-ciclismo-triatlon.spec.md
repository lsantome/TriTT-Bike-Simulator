# Spec: Simulador de predicción para triatlón (sin drafting y CRI)

**Slug:** simulador-ciclismo-triatlon
**Versión:** v12 (historial de cambios al final del documento)
**Fecha:** 2026-10-06
**Estado:** Confirmada por el usuario

## Objetivo
Herramienta de uso personal que, dado un GPX y un perfil de potencia por pendiente, predice tiempo, velocidad y potencia por tramo en ciclismo de triatlón sin drafting y contrarreloj, con parámetros físicos y meteorológicos editables.

## Alcance
- Carga de GPX; remuestreo a distancia constante, suavizado de elevación (ventana por defecto 150 m) y trazado, cálculo de pendiente y curvatura.
- Motor físico por balance de energía: pendiente, rodadura, aerodinámica, transmisión, inercia de ruedas, densidad del aire (temperatura, humedad, presión, altitud por punto).
- Potencia por perfil de pendiente (subida / llano / descenso) con umbrales editables (defecto ±2 %) y transición suave entre bandas.
- CdA único, con aumento ΔCdA (defecto +0,25) a velocidades inferiores a 20 km/h mediante transición logística suave. Umbral, anchura y ΔCdA son editables. **Lo que el ciclista lleve puesto va dentro de ese CdA**: no hay parámetro de prendas.
- **Masa: un único valor total** (ciclista + bici + equipo). El modelo solo usa la suma; el reparto no entra en ninguna ecuación.
- **Tamaño de rueda por medida ETRTO** (defecto 28-622), con el perímetro calculado a partir de ella, u opción **manual** que habilita el perímetro medido en mm. El radio no es un parámetro: se deduce del perímetro. Solo afecta a la inercia de rotación.
- **Presión de neumáticos** como factor sobre el Crr, con exponente por superficie.
- **Estimador de CdA** a partir de un segmento seleccionado de una actividad `.fit`, por balance de energía, con diagnósticos de validez del segmento.
- Terreno: superficie global (liso / normal / rugoso) y sobrescritura opcional por rangos de km. Crr con término dependiente de la velocidad.
- Límite de velocidad por curvatura **activo por defecto**, con aceleración lateral máxima editable, más tope de descenso de 100 km/h.
- **Dos módulos independientes**: el **estimador de CdA** (entra un `.fit`, sale un CdA) y el **simulador** (entra un GPX y un CdA, sale una predicción). El estimador no pide GPX ni los parámetros que no intervienen en su cálculo.
- **Interfaz en español e inglés**, con selector; el español es el idioma canónico.
- Parámetros agrupados en **tres** categorías: Ciclista, Equipamiento y Variables externas (meteorología y terreno juntos). Avanzados en una sección aparte.
- Defectos: nivel del mar y condiciones de A Coruña.
- Salidas: tiempo total, velocidad media, tabla y gráficas por tramo (velocidad, potencia, pendiente suavizada, CdA efectivo), NP, VI y IF (si hay FTP).
- Análisis de sensibilidad (±10 % por parámetro) que justifica qué parámetros van en la interfaz principal.
- Módulo de validación con archivos FIT: reproducción de la potencia real y comparación de velocidad y tiempo predichos.

## Fuera de alcance (Non-goals)
Viento, drafting, optimizador de pacing, modo inverso, corrección de elevación con DEM, extracción de superficie desde OSM, modulación de Crr por presión o ancho de neumático, despliegue multiusuario.

## Insumos / contexto disponible
Archivos FIT con potencia del usuario. Masa total declarada 90 kg; posición aero por encima de 20 km/h; mismo potenciómetro, calibrado. Ubicación de referencia: A Coruña, nivel del mar.

**Cinco salidas del recorrido 2** (vuelta de ~128 km, 2200-2600 m de desnivel, 4 h), con un 94-98 % de solape de trazado entre sí: 30-mar-2025, 06-abr-2025, 04-may-2025, 08-jun-2025 y 19-abr-2026. Clasificación tras la validación de 5-oct-2026 (informe en `simulador-ciclismo-triatlon.validacion.md`):

- **Tres coherentes** (30-mar-2025, 06-abr-2025, 19-abr-2026): los dos métodos de estimación de CdA coinciden y el error por banda de pendiente se queda dentro de ±2,5 % en las siete bandas. Son las que sirven para calibrar.
- **Dos incoherentes** (04-may-2025, 08-jun-2025): más rápidas en llano de lo que permite la potencia registrada (viento neto a favor, rebufo o grupo), con el patrón «llano demasiado lento + bajadas demasiado rápidas» en la simulación. No sirven para calibrar; sirven para medir cuánto cuesta no tener el viento como entrada.

La **hipótesis de «bici distinta»** que motivaba las exclusiones anteriores **queda refutada** para el 08-jun-2025: el estimador de pares le da 0,2542, en línea con las coherentes. La salida del 19-abr-2026 encaja con las de 2025 por los dos métodos trece meses después, de modo que el CdA resulta estable a lo largo de un año.

Las salidas del **recorrido 1** siguen excluidas por decisión del usuario y no se han vuelto a analizar.

## Restricciones
Núcleo en Python (numpy) sin dependencias de UI, con tests automatizados. UI: MVP en Streamlit. Interfaz en español. Rangos de entrada validados. Arranque sin línea de comandos (un script por sistema); se descarta reimplementar el modelo en JavaScript, para no tener dos fuentes de verdad.

## Formato de entrega esperado
Paquete Python (`core/` con modelo, parser GPX, solver, validación; `app/` Streamlit; `tests/`), README con el modelo y las limitaciones, y `requirements.txt`.

## Supuestos
- Defectos: masa total 85 kg (obligatoria, sin valor por defecto en la interfaz), CdA 0,27, Crr 0,0045 (liso 0,0035 / rugoso 0,0070), η 0,975, 15 °C, 75 % HR, potencias 220/200/0 W, ETRTO 28-622, 7,0 bar.
- Los exponentes de presión son **estimaciones de orden de magnitud**, no medidas del usuario: son editables y la herramienta lo declara.
- Aceleración lateral máxima por defecto: 3,0 m/s².
- El viento real de las salidas FIT se absorberá en el CdA calibrado (sesgo conocido, documentado en el README). **Medido:** es el término dominante del error y puede llegar al 13 % del tiempo de una vuelta de 4 h.
- La masa declarada por el usuario ("90 kg") se interpreta como **masa total ciclista + bici + equipo**. Medido: un error de ±4 kg mueve el CdA estimado solo ±0,4 %, así que no es un parámetro crítico.
- El CdA que sale de estas cinco salidas (~0,26) es un **CdA de posición de entrenamiento**, no de carrera: son 4 h a 210-226 W y 31-33 km/h con 2200-2600 m de desnivel. Para predecir en competición hace falta una actividad con el montaje y la posición de carrera.
- El desnivel positivo de la misma ruta varía entre 2179 y 2629 m según el día por ruido del altímetro barométrico: la calidad del perfil de elevación del GPX condiciona la predicción tanto como el CdA.

## Preguntas abiertas
Ninguna.

## Criterios de aceptación
1. [ ] Caso llano (250 W, CdA 0,32, Crr 0,004, 83 kg totales, ρ 1,2, η 0,975, ΔCdA desactivado): velocidad = solución analítica ±0,3 km/h (≈37 km/h).
2. [ ] Con 0 W en pendiente constante descendente y sin límites activos, la velocidad converge a la terminal analítica ±1 %.
3. [ ] En un arco de radio R con límite de curvatura activo, la velocidad no supera √(a_lat·R) en más del 4 % **en todo el arco, extremos incluidos**, para R ≥ max(10 m, ventana de trazado / 7), con arcos de 180° y de 540° (test unitario sobre la rejilla radios × ventanas × ángulos). Por debajo de ese radio el límite es optimista y está declarado: +4,5 % a R = 8 m y +16,3 % a R = 4 m con la ventana por defecto. En rutas reales el estimador no inventa curvas (medido sobre las tres salidas coherentes: el tiempo predicho sube +0,29 % a +0,33 % respecto a la versión anterior, que dejaba entrar en las curvas por encima del límite).
4. [ ] Ninguna velocidad simulada supera el tope de descenso configurado (100 km/h por defecto).
5. [ ] El CdA efectivo es continuo: no hay saltos mayores que un umbral definido entre muestras consecutivas alrededor de 20 km/h.
6. [ ] La potencia entre bandas de pendiente es continua (sin saltos en los umbrales).
7. [ ] Aumentar Crr o CdA, empeorar la superficie o reducir la eficiencia nunca reduce el tiempo total; aumentar la masa total (ciclista + bici) nunca lo reduce en rutas sin descenso con pedaleo nulo. En rutas con descensos a potencia baja el efecto de la masa es no monótono y se documenta, no se fuerza (test monótono).
8. [ ] Con ventana 150 m, un GPX limpio y el mismo con ruido de elevación artificial añadido difieren en tiempo total menos de un umbral documentado.
9. [ ] Ruta circular, sin viento, a potencia constante: tiempos iguales en ambos sentidos (±0,5 %) cuando el perfil de potencia es simétrico.
10. [ ] **La masa total es obligatoria**: sin ella la app no simula y lo indica; no tiene valor por defecto en la interfaz. La interfaz muestra y permite editar los parámetros **del módulo activo** (criterio 31), agrupados en las **tres** categorías, con valores por defecto y rangos validados. *(Texto corregido en la v12: se había quedado en la v1 hablando de dos masas separadas y de cuatro categorías, que el Alcance y los criterios 18 y 31 contradicen desde la v5.)*
11. [ ] Salida con tiempo total, velocidad media, tabla y gráficas por tramo, NP, VI e IF (con FTP).
12. [ ] El informe de sensibilidad lista el efecto en el tiempo total de cada parámetro a ±10 %.
13. [ ] **Misma bici y misma ruta:** calibrando el CdA con una salida y validando con otra salida no usada para calibrar, el error de tiempo en movimiento es ≤ 3 %, y el módulo reporta además el error medio de velocidad. Si no se cumple, el informe lo indica sin ocultarlo.
14. [ ] **Transferencia entre rutas (sin verificar):** el mismo criterio de ≤ 3 % aplicado a una ruta distinta de la de calibración, con la misma bici. Queda **pendiente de datos**: no hay ninguna salida de la bici válida por otra ruta. Mientras no haya datos, ni el README ni la interfaz pueden presentar el error de la misma ruta como precisión esperable en una ruta nueva.
15. [ ] **Perfiles de bici:** la app guarda y recupera un perfil con nombre (CdA, masas, Crr, η) para no recalibrar en cada sesión, y deja claro de qué salidas proviene el CdA de ese perfil.
16. [ ] **Incertidumbre a la vista:** toda predicción de tiempo se presenta acompañada de su banda de incertidumbre, nunca como un número solo. Las bandas, su número y su procedencia los fija el criterio 29.

17. [ ] **Arranque de un paso:** un script por sistema (`run.sh` en macOS y Linux, `run.bat` en Windows) que crea el entorno virtual la primera vez, instala las dependencias solo si han cambiado y abre la app en el navegador; con `--tests` instala las de test y ejecuta la suite, y con `--reinstalar` rehace el entorno. Si falta Python, lo dice con el enlace de descarga. Arrancar la app no instala dependencias de test, y todo lo que importan la app y el núcleo está declarado en `requirements.txt`.

18. [ ] **Masa única:** la interfaz pide un solo valor de masa total; no existen campos separados de ciclista y equipo. Un test demuestra que el modelo solo depende de la suma.
19. [ ] **Tooltips:** todos los parámetros de entrada tienen texto de ayuda no vacío, con las unidades y lo que significan. Un test lo comprueba sobre `PARAM_SPECS`, de modo que un parámetro nuevo sin ayuda hace fallar la suite.
20. [ ] **Botones:** la simulación se ejecuta al pulsar un botón, no en cada cambio de parámetro, y hay un botón de borrado que devuelve la interfaz a su estado inicial sin tocar los perfiles de bici guardados en disco.
21. [ ] **Tema:** esquema de colores claro por defecto, con modo oscuro opcional que afecta también a los gráficos.
22. [ ] **ETRTO con opción manual:** el tamaño de rueda se elige por su medida ETRTO de una lista (defecto **28-622**) y el perímetro se calcula a partir de ella; la opción **manual** habilita un campo de perímetro medido en mm, que está desactivado en cualquier otro caso. **El radio no existe como parámetro**: se deduce del perímetro. Elegir «manual» sin perímetro, o dar perímetro sin elegir «manual», se rechaza con un mensaje que explica cómo medirlo.
23. [ ] **Presión de neumáticos:** modula el Crr con un exponente por superficie. Con los valores por defecto el resultado no cambia respecto a la versión anterior. Va documentado como estimación y es editable. **El tipo de prendas no es un parámetro del modelo**: lo que se lleve puesto va dentro del CdA introducido.
24. [ ] **Estimador de CdA:** cargando un `.fit` y seleccionando un segmento sobre el perfil de la ruta, la herramienta calcula el CdA de ese segmento por balance de energía, y **acompaña el número de su incertidumbre y de un diagnóstico de validez del segmento** (sensibilidad a errores de altitud, de Crr y de potencia; velocidad media; peso del término aerodinámico). Si el segmento no sirve, lo dice y no presenta el valor como bueno.
25. [ ] **Búsqueda automática de tramos:** la herramienta identifica por sí sola los tramos llanos de al menos 1 km donde la estimación es fiable, sin solapes y ordenados por fiabilidad, y para cada uno localiza **la pasada de vuelta por la misma carretera**, porque promediar ida y vuelta es la única forma de cancelar el viento sin modelarlo. El valor recomendado es la media de los pares, con la dispersión entre pares como incertidumbre. La interfaz **declara el sesgo de selección**: exigir velocidad alta y poco desnivel elige tramos más rápidos que la ruta, así que el CdA de un tramo suelto sale bajo. Se valida contra la calibración por tiempo total, que es un método independiente: deben coincidir en ±0,02 m².

26. [ ] **Tabla por segmento:** el estimador presenta **una fila por segmento** con su CdA y su margen, el desnivel, la pendiente, la velocidad media, la potencia media, la parte aerodinámica de la energía, el rumbo y si es utilizable; con el desglose de la incertidumbre por fuente disponible y descarga en CSV. La tabla se construye en el núcleo (`core/exports.tabla_segmentos`), no en la interfaz, para poder verificarla sin Streamlit.

27. [ ] **Español e inglés:** selector de idioma en la barra lateral, al estilo del de tema. Se traducen las etiquetas y los tooltips de **todos** los parámetros, las categorías, las pestañas, los botones, los mensajes, las métricas, las cabeceras de tabla que se muestran y **los avisos del estimador**. Los nombres de columna de los CSV descargables **no** se traducen, a propósito, para no romper hojas de cálculo. Un test comprueba que cada parámetro y cada cadena tienen los dos idiomas, de modo que añadir un parámetro sin traducir hace fallar la suite.

28. [ ] **Pares imposibles rechazados:** `find_paired_segments` descarta el par de ida y vuelta cuya relación de velocidades (la mayor entre la menor) alcance **1,5**, porque dos pasadas por la misma carretera llana no pueden diferir tanto: si difieren, el filtro de llaneza ha dejado pasar una bajada o una subida que el suavizado barométrico aplanó. El par rechazado se registra con su motivo. El umbral es editable y está justificado con la medida: en las cuatro salidas coherentes la relación máxima entre pares legítimos es 1,42, y los pares imposibles de la salida del 04-may-2025 están en 2,13, 2,56 y 3,24. **No** se filtra por discrepancia de CdA entre ida y vuelta: eso descartaría pares legítimos y seleccionaría por viento bajo, que es la trampa de ponderación ya rechazada en el criterio 25.

29. [ ] **Dos bandas de incertidumbre que miden cosas distintas**, las dos verificadas con validación cruzada dejando una salida fuera, más un suelo declarado para ruta nueva:
    - **Banda del modelo, ±1,4 %:** precisión con la misma bici y ruta y condiciones parecidas a las de la calibración. Medida con las tres salidas coherentes: error medio 0,94 %, máximo 1,39 %.
    - **Banda del día, ±15 %:** la anterior más el viento y las condiciones desconocidas del día. Se mide **con el protocolo que la propia herramienta recomienda** (criterio 30): calibrando solo con las salidas coherentes y prediciendo cualquier día, incluidos los incoherentes. Peor error observado: **14,27 %** sobre los datos completos (14,19 % sobre los fixtures), en la salida del 04-may-2025. El valor de la banda cubre ese peor caso, no lo redondea a la baja. **Corrección de la v11:** el ±14 % anterior se midió dejando una fuera *sobre las cinco*, lo que mete las incoherentes dentro del conjunto de calibración y da un peor error más benévolo (12,8 %); eso mide un flujo que el criterio 30 prohíbe. Una banda tiene que medir el camino que la herramienta recomienda, no el más cómodo. Un test vuelve a medir los peores errores sobre los fixtures en lugar de creerse las cifras escritas en el código.
    - **Ruta nueva: sin banda verificada.** La banda del día es un **suelo**, no una estimación: una ruta distinta no se ha podido validar nunca (criterio 14). La interfaz lo declara como tal y no presenta ningún número como precisión esperable en una ruta nueva. El ±11 % de la versión anterior queda retirado por incoherente: era menor que el margen por viento ya medido en la propia ruta de calibración.

30. [ ] **Aviso de actividad incoherente:** antes de dar por bueno el CdA de una actividad, el núcleo la examina y avisa si (a) el CdA calibrado cae fuera del rango plausible **0,20-0,35**, o (b) aparece el patrón **llano demasiado lento (error ≥ +5 %) y bajadas demasiado rápidas (error ≤ −4 %)**, que es la firma de una salida más rápida de lo que permite la potencia registrada: viento a favor, rebufo o grupo. El diagnóstico se construye en el núcleo, no en la interfaz. Umbrales justificados con la medida: en las tres salidas coherentes el error en llano no pasa de −0,7 % y en bajadas de +0,8 %; en las dos incoherentes el llano está en +15,8 % y +29,6 % y las bajadas en −7,9 % y −18,4 %. La interfaz muestra el aviso en la validación con FIT y **antes de guardar ese CdA en un perfil de bici**.

31. [ ] **El estimador de CdA es un módulo independiente.** Se elige con un selector de módulo y **se puede arrancar directamente** (`run.sh --estimador`, `run.bat --estimador`, o `?modo=estimador` en la URL). En ese módulo:
    - **No se pide un GPX** ni se menciona: la entrada es un `.fit` y nada más.
    - **Solo se piden los parámetros que intervienen en la estimación.** `cda` y `delta_cda` **no** aparecen: son la salida, no la entrada. Tampoco aparecen los perfiles de potencia, el FTP, los límites de velocidad y curvatura ni los parámetros de remuestreo del GPX. La partición vive en el núcleo (`specs_for_module`), no en la interfaz, y la vigila un test **empírico**: cambiar un parámetro que el módulo no muestra no mueve la estimación, y cambiar uno de los que muestra sí la mueve. Así la lista no se mantiene a mano.
    - El resultado se puede **llevar al simulador con un botón**, donde queda como un valor editable: el usuario puede usarlo tal cual o corregirlo a mano.
    - El examen de coherencia (criterio 30) está disponible en el módulo del estimador, no solo en el del simulador.

32. [ ] **Sistema de diseño propio, no el aspecto por defecto de Streamlit.** Los tokens (color, tipografía, espacio) viven en un único módulo (`app/theme.py`) y no repartidos por la interfaz; un test comprueba que la interfaz no define colores a mano. Requisitos concretos:
    - **La incertidumbre tiene lenguaje visual propio**, que es la idea que sostiene el diseño: ningún número aparece solo, siempre con su margen y a un peso visual comparable. Banda **sólida y estrecha** = medida y estrecha; banda **rayada y ancha** = margen del día o afirmación no verificada. El mismo código visual se usa para las bandas de tiempo, para el CdA estimado y para lo descartado.
    - **Dos tipografías con papeles distintos**: una de interfaz y una monoespaciada **solo para las lecturas numéricas** que se comparan o se alinean, nunca para etiquetas. Con pila de reserva, para que la herramienta siga legible sin red.
    - **Tema claro por defecto y oscuro completo** (criterio 21), los dos derivados de los mismos tokens, incluidos los gráficos.
    - **Accesibilidad como suelo, no como extra**: contraste suficiente en los dos temas, foco de teclado visible, y `prefers-reduced-motion` respetado.
    - Sin animaciones de entrada ni efectos decorativos: la única transición es la de la banda al aparecer un resultado.

## Protocolo de calibración (actualizado tras la validación con 5 salidas)
1. Usar solo salidas de **la misma bici** y de la misma ruta.
2. **Pasar cada salida por el examen de coherencia del criterio 30** y excluir las que avisen. Toda exclusión se registra con su motivo y con la medida que la respalda, no con una hipótesis.
3. Obtener el CdA con el **estimador de pares de ida y vuelta** (criterio 25), que es el método reproducible: 1,9 % de dispersión entre salidas frente al 21,3 % de la calibración por tiempo total. La calibración por tiempo total queda como **comprobación independiente**, no como fuente del dato.
4. Calibrar con **al menos 2 salidas** coherentes y validar dejando una fuera.
5. Informar siempre de la dispersión entre salidas, no solo del mejor ajuste.
6. **No promediar salidas incoherentes** con las buenas: meterían el viento de su día en el parámetro.

---
### Historial de versiones
- v1 (2026-10-01): versión inicial, confirmada por el usuario.
- v2 (2026-10-01): criterio 7 reformulado (masa: solo rutas sin descenso con pedaleo nulo); ventana de suavizado de elevación 100 → 150 m; masa ciclista + bici obligatoria en la interfaz.
- v3 (2026-10-01): tras la primera validación con FIT reales. Criterio 13 limitado a misma bici y misma ruta (cumple: +1,25 % y −1,21 %); nuevo criterio 14 para la transferencia entre rutas, declarado **pendiente de datos**; nuevos criterios 15 (perfiles de bici) y 16 (incertidumbre a la vista); protocolo de calibración añadido; insumos actualizados con las 4 salidas excluidas y su motivo.
- v4 (2026-10-02): nuevo criterio 17 (arranque de un paso con `run.sh` / `run.bat`) y dependencias separadas en `requirements.txt` (app) y `requirements-dev.txt` (tests). Se valoró y **descartó** una interfaz HTML con el modelo reescrito en JavaScript (duplicaría 1 463 líneas de física ya validada); una versión con Pyodide queda como opción futura, con su propia spec.
- v5 (2026-10-03): seis cambios tras la primera prueba de uso real. Criterio 18 (masa única: se confirma en el código que el modelo solo usa la suma), 19 (tooltips en todos los parámetros), 20 (botones de simular y borrar), 21 (tema claro por defecto, oscuro opcional), 22 (rueda por medida ETRTO), 23 (presión de neumáticos sobre el Crr y prendas sobre el CdA) y 24 (estimador de CdA sobre un segmento de un `.fit`). Nota medida: el tamaño de rueda mueve el tiempo menos del 0,001 % porque solo entra en la inercia de rotación; se añade por comodidad de la interfaz, no por precisión.
- v6 (2026-10-03): criterio 25, búsqueda automática de tramos llanos fiables y de su pasada de vuelta, a petición del usuario («mejor identifica tú los tramos llanos > 1 km donde la estimación sea fiable»). Dos hallazgos medidos durante la construcción que cambiaron el diseño: (a) la búsqueda tiene **sesgo de selección** —los tramos elegidos van a 36,3 km/h frente a los 31,4 km/h de la ruta, con pendiente media −0,16 %— y por eso el CdA de un tramo suelto sale bajo (0,226 combinado frente a 0,277 de la ruta completa); (b) emparejando ida y vuelta por la misma carretera, el resultado (0,268 y 0,262) coincide con la calibración por tiempo total (0,276 y 0,262), que es independiente. Se decidió **no ponderar** los pares por su discrepancia tras medir que la corrección de segundo orden por viento solo mueve la media de 0,268 a 0,264.
- v7 (2026-10-03): criterio 26, tabla de resultados por segmento en el estimador, a petición del usuario. Se incluyen además el rumbo (delata el viento), la parte aerodinámica de la energía y el desglose de la incertidumbre por fuente.
- v8 (2026-10-04): limpieza de cierre de la v1 pedida por el usuario. Fuera el parámetro de **prendas** (ya va en el CdA) y fuera el **radio de rueda** (se deduce del perímetro); la medida de rueda gana la opción **manual** con perímetro medido en mm y pasa a 28-622 por defecto; meteorología y terreno se agrupan en **Variables externas**, quedando tres categorías.
- v11 (2026-10-06): a petición del usuario, «ahora que la parte funcional está bien definida y funciona, vamos a por la UI». Criterio 31 (el estimador de CdA pasa a ser un **módulo independiente**: sin GPX y solo con los 19 parámetros de los 39 que intervienen en su cálculo, con el resultado transferible al simulador y corregible a mano) y criterio 32 (**sistema de diseño propio**, con el lenguaje visual de la incertidumbre como idea central). El criterio 31 nace de una observación del propio usuario sobre cómo usa la herramienta: primero mide su CdA con una actividad de montaje de carrera, y después predice con ese valor, o con uno ligeramente corregido, sobre el GPX de la competición. Son dos tareas distintas y hasta ahora compartían una interfaz que pedía las dos cosas a la vez.
- v10 (2026-10-05): tras validar el modelo físico con **cinco** salidas reales del recorrido 2 (informe en `simulador-ciclismo-triatlon.validacion.md`), confirmada por el usuario. Criterios 28 (rechazo de pares imposibles), 29 (dos bandas que miden cosas distintas, en sustitución del ±1,3 % / ±11 % anterior) y 30 (aviso de actividad incoherente); criterio 16 reducido a la exigencia general y los números delegados al 29; protocolo de calibración rehecho. Tres hallazgos medidos que motivan los cambios: (a) el modelo físico acierta **dentro de ±2,5 % en las siete bandas de pendiente**, de −6 % a +6 %, lo que es una validación más fuerte que el ajuste global que había; (b) el **estimador de pares es reproducible y la calibración por tiempo total no** (1,9 % frente a 21,3 % de dispersión entre cinco salidas), así que se invierte cuál de los dos es la fuente del CdA; (c) la banda de ±1,3 % se obtuvo con dos salidas y **solo vale cuando las condiciones se parecen a las de la calibración** — el viento del día añade hasta un 13 %. Se refuta además la hipótesis de «bici distinta» para la salida del 08-jun-2025.
- v9 (2026-10-04): criterio 27, interfaz en español e inglés con selector. **El viento queda fuera del alcance por decisión conjunta**, no por falta de precisión del modelo de viento sino porque la v1 es internamente coherente (un CdA que absorbe el viento medio + ninguna entrada de viento) y añadir el viento a medias contaría el efecto dos veces: exigiría rederivar el CdA libre de viento y dar un dato de viento en cada predicción. Se revisará si el usuario necesita predecir en un sitio desconocido o comparar material.
