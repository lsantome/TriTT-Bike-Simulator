# Validación del modelo físico con 5 salidas reales

Fecha del análisis: 5-oct-2026. Masa del conjunto: 90 kg. Modelo sin viento.

Las cinco actividades son salidas de entrenamiento largas, **no** ensayos de calibración. El
análisis se limita por tanto a lo que esos datos pueden sostener: si el modelo físico reproduce
la relación potencia→velocidad a lo largo de todo el rango de pendientes, y si el CdA estimado
es reproducible entre salidas.

---

## 1. Inventario e identidad de la ruta

| Salida | Fichero | Distancia | T. movimiento | v media | Desnivel + | P media |
|---|---|---|---|---|---|---|
| 30-mar-2025 08:00 | `1743325211` | 127,9 km | 245,3 min | 31,27 km/h | 2179 m | 221 W |
| 06-abr-2025 06:45 | `1743925539` | 127,9 km | 242,5 min | 31,64 km/h | 2475 m | 218 W |
| 04-may-2025 06:33 | `250504073330` | 127,3 km | 243,8 min | 31,34 km/h | 2292 m | 222 W |
| 08-jun-2025 06:35 | `1749368125` | 127,3 km | 230,4 min | 33,14 km/h | 2629 m | 224 W |
| 19-abr-2026 07:03 | `260419080352` | 126,8 km | 233,7 min | 32,56 km/h | 2255 m | 226 W |

Potencia presente en el 100 % de los registros en las cinco.

**Identidad de ruta.** Discretizando el trazado en celdas de ~50 m, cada salida cubre entre el
**94 % y el 98 %** de las celdas de cualquier otra. Son la misma vuelta de 128 km. Ninguna
aporta carretera nueva.

**Ruido del altímetro barométrico.** El desnivel positivo de la misma ruta oscila entre 2179 y
2629 m, un 20 % de dispersión, y una salida registra un mínimo de −54 m de altitud donde las
demás dan 25-39 m. El dato relevante para el uso de la herramienta: la calidad del perfil de
elevación del GPX condiciona la predicción tanto como el CdA.

---

## 2. CdA por dos métodos independientes

| Salida | Calibración por tiempo total | Estimador de pares ida/vuelta |
|---|---|---|
| 30-mar-2025 | 0,2758 | 0,2611 ± 0,0049 (8 pares) |
| 06-abr-2025 | 0,2621 | 0,2661 ± 0,0087 (7 pares) |
| 04-may-2025 | **0,1550** | 0,2435 ± 0,0188 (8 pares) |
| 08-jun-2025 | **0,2131** | 0,2542 ± 0,0095 (6 pares) |
| 19-abr-2026 | 0,2583 | 0,2550 ± 0,0090 (8 pares) |
| **media / dispersión** | 0,2328 ± **21,3 %** | 0,2560 ± **3,3 %** |

El resultado central del análisis: **el estimador de pares es reproducible y la calibración por
tiempo total no lo es.** Los pares de ida y vuelta cancelan el viento medio; el tiempo total lo
absorbe entero en el CdA.

Los dos métodos coinciden en las tres salidas coherentes (0,2607 el estimador, 0,2653 la
calibración, un 1,8 % de diferencia) y divergen en las dos anómalas.

**La salida 19-abr-2026 encaja con las de marzo y abril de 2025**, trece meses antes, en los dos
métodos. No hace falta la hipótesis de «otra bici» para explicarla, y el CdA resulta estable a
lo largo de un año.

**La hipótesis de «otra bici» para el 08-jun-2025 tampoco se sostiene.** El estimador de pares
le da 0,2542, en línea con el resto. Lo que la hace distinta es otra cosa (ver §4).

---

## 3. Error por banda de pendiente

Tiempo predicho frente a tiempo real por tramo, con el CdA calibrado de cada salida. Signo
positivo = el modelo tarda más que la realidad.

### Las tres salidas coherentes

| Banda | 30-mar (0,2758) | 06-abr (0,2621) | 19-abr-26 (0,2583) |
|---|---|---|---|
| bajada > 6 % | −7,69 % | −1,58 % | +0,58 % |
| bajada 3-6 % | +1,02 % | +0,21 % | +1,23 % |
| bajada 1-3 % | +0,47 % | −0,41 % | +1,28 % |
| llano ±1 % | −2,46 % | −0,70 % | −1,31 % |
| subida 1-3 % | +0,87 % | +0,08 % | +0,96 % |
| subida 3-6 % | +1,12 % | +1,03 % | −0,31 % |
| subida > 6 % | +0,43 % | −0,50 % | −1,80 % |

**Esto es la validación del modelo físico.** Con un solo CdA, el error se queda dentro de ±2,5 %
en las siete bandas, de −6 % a +6 % de pendiente. No es un ajuste global que compense errores
opuestos: acierta banda por banda, con la potencia real como entrada. El único punto flojo es la
bajada de más del 6 % (4,6 % de la ruta), donde el límite por curvatura actúa sobre apenas el
3 % de la distancia y el comportamiento real del ciclista (frenada, visibilidad) no es física.

### Las dos salidas anómalas

| Banda | 04-may (0,1550) | 08-jun (0,2131) |
|---|---|---|
| bajada > 6 % | −36,59 % | −13,42 % |
| bajada 3-6 % | −20,51 % | −8,47 % |
| bajada 1-3 % | −15,57 % | −5,78 % |
| llano ±1 % | **+27,70 %** | **+17,16 %** |
| subida 1-3 % | −0,14 % | −3,83 % |
| subida 3-6 % | −8,70 % | −1,67 % |
| subida > 6 % | −5,11 % | +1,02 % |

Patrón inequívoco: el modelo va **demasiado lento en el llano** y **demasiado rápido en las
bajadas**. La calibración por tiempo total, obligada a cuadrar el total, baja el CdA hasta que
el llano encaja y rompe las bajadas. El CdA de 0,1550 no es un dato aerodinámico: es el residuo
de un ajuste imposible.

---

## 4. Diagnóstico de las dos salidas anómalas

| | v real en llano ±1 % | P en llano | v real en bajada > 6 % |
|---|---|---|---|
| 30-mar-2025 | 34,67 km/h | 218 W | 55,31 km/h |
| 06-abr-2025 | 35,79 km/h | 214 W | 59,80 km/h |
| 19-abr-2026 | 36,24 km/h | 215 W | 60,53 km/h |
| 04-may-2025 | 36,49 km/h | 204 W | **39,59 km/h** |
| 08-jun-2025 | **40,89 km/h** | 209 W | 54,41 km/h |

- **08-jun-2025**: 40,9 km/h en llano con 209 W, unos 5 km/h más que las demás con la misma
  potencia. Eso no lo da la aerodinámica de una bici: es viento neto a favor en el reparto de
  tiempo de la vuelta, rebufo, o ambos.
- **04-may-2025**: incoherente consigo misma. Llano rápido y bajadas lentísimas (39,6 km/h
  frente a 55-60 de las demás, con 122 W aplicados). Firme mojado, tráfico o grupo en el llano
  explicarían las dos cosas; con los datos disponibles es una hipótesis, no un hecho.

Ninguna de las dos se explica por la bici ni por el modelo. Se explican por condiciones del día
que el modelo no tiene como entrada.

---

## 5. Validación cruzada (dejar una fuera)

| Conjunto | Fuente del CdA | Error medio \|·\| | Error máximo |
|---|---|---|---|
| 5 salidas | calibración por tiempo con las otras 4 | 5,61 % | 12,49 % |
| 5 salidas | estimador de pares de las otras 4 | 4,20 % | 13,52 % |
| **3 salidas coherentes** | calibración por tiempo con las otras 2 | **0,94 %** | **1,38 %** |

Detalle del conjunto de 3: −1,38 % (fuera 30-mar), +0,46 % (fuera 06-abr), +0,98 %
(fuera 19-abr-2026).

Detalle de la cadena completa que se quiere usar en carrera (CdA del estimador de pares de las
otras cuatro → predicción de tiempo): −1,89 % / −0,81 % / +13,52 % / +4,57 % / −0,20 %. Los dos
errores grandes son las dos salidas anómalas.

**Consecuencia para el criterio 16.** La banda de ±1,3 % se obtuvo con dos salidas. Con tres
salidas coherentes aguanta (0,94 % medio, 1,38 % máximo). Contra el conjunto completo de cinco,
no: 4,2 % medio y 13,5 % máximo. La lectura honesta es que **±1,4 % es la precisión del modelo
cuando las condiciones se parecen a las de la calibración, y el viento del día es el término
dominante del error, capaz de añadir del 5 al 14 %.** Esos dos números miden cosas distintas y
la herramienta debería mostrar los dos.

---

## 6. Defecto detectado en el emparejador de tramos

`find_paired_segments` acepta pares físicamente imposibles. En la salida del 04-may empareja un
tramo de 1 km a **61,0 km/h con 101 W** con otro a **18,5 km/h con 256 W**, y otro de 56,5 km/h
con uno de 18,0 km/h. No pueden ser la misma carretera en sentidos opuestos con pendiente llana:
el filtro de llaneza (|pendiente| ≤ 1 %, |Δh| ≤ 10 m) los deja pasar porque el suavizado del
altímetro barométrico aplana la pendiente real.

Efecto medido de dos filtros candidatos sobre el CdA combinado:

| Filtro | media | dispersión | rango |
|---|---|---|---|
| actual | 0,2560 | 3,3 % | 0,2435–0,2661 |
| rechazar par con v_max/v_min ≥ 1,5 | **0,2597** | **1,9 %** | 0,2542–0,2661 |
| rechazar par con discrepancia ≥ 0,08 | 0,2584 | 1,5 % | 0,2542–0,2623 |

El filtro por **relación de velocidades** solo toca la salida del 04-may (le quita los dos pares
imposibles y la deja en 0,2621, en línea con el resto) y no altera ninguna de las otras cuatro.
Es la corrección correcta: elimina datos imposibles, no datos incómodos.

El filtro por discrepancia aprieta más la dispersión, pero descarta pares legítimos de las
salidas buenas y selecciona por viento bajo. Es la trampa de ponderación ya rechazada en el
proyecto. **No se recomienda.**

---

## 7. Sensibilidad a la masa

Error de ±4 kg en la masa del conjunto:

| Masa | CdA pares 30-mar | CdA pares 19-abr-2026 |
|---|---|---|
| 86 kg | 0,2622 | 0,2562 |
| 90 kg | 0,2611 | 0,2550 |
| 94 kg | 0,2601 | 0,2538 |

±0,4 % de CdA por ±4 kg. La masa no es un parámetro crítico para el estimador.

---

## 8. Qué queda sin validar

- **Criterio 14 (transferencia a otra ruta): sigue abierto.** Las cinco salidas son la misma
  vuelta con un 94-98 % de solape, así que **no hay ninguna banda verificada para una ruta
  nueva**: el margen del día es un suelo, no una estimación. El ±11 % que las versiones v9 y
  anteriores daban para ruta nueva quedó retirado por incoherente —era menor que el margen por
  viento ya medido en la propia ruta de calibración— y no se sustituye por otra cifra.
- **Posición y equipamiento de carrera.** Estas salidas son 4 h a 210-226 W y 31-33 km/h con
  2200-2600 m de desnivel. El CdA de ~0,26 que sale de ellas es un CdA de posición de
  entrenamiento, no de carrera. Para la predicción de competición hace falta una actividad con
  el montaje y la posición de carrera, como ya estaba previsto.
- **Viento.** Sin dato de viento no hay forma de separarlo del CdA. Las dos salidas anómalas son
  la medida de cuánto cuesta esa ausencia: hasta un 13 % de error en el tiempo de una vuelta de
  4 h.
- **Bajadas de más del 6 %.** 4,6 % de esta ruta, con error de hasta −7,7 % en la mejor de las
  salidas coherentes. En un recorrido de carrera con más descenso técnico, este término pesaría
  más de lo que pesa aquí.

---

## 9. Recomendaciones

1. **Usar el estimador de pares como fuente del CdA, no la calibración por tiempo total.** Es el
   método reproducible de los dos (1,9 % frente a 21,3 % de dispersión con el filtro aplicado).
2. **Añadir el filtro de relación de velocidades** (v_max/v_min < 1,5) a
   `find_paired_segments`, con test de regresión sobre el fichero del 04-may.
3. **Rehacer las bandas del criterio 16** con los dos números que miden cosas distintas: la
   precisión del modelo en condiciones parecidas (±1,4 %) y el margen por viento desconocido
   (hasta ±13 %).
4. **Marcar las salidas incoherentes en la interfaz.** El patrón «llano demasiado lento + bajadas
   demasiado rápidas» con un CdA calibrado fuera del rango 0,20-0,35 es detectable
   automáticamente y debería avisar antes de que el usuario guarde ese CdA en un perfil.
5. No añadir las cinco salidas a un promedio único de calibración. Las tres coherentes sirven;
   las dos anómalas meterían el viento de su día en el parámetro.
