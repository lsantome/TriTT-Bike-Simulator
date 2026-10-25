# Actividades reales reducidas (criterios 13, 28, 29 y 30)

Las **cinco** salidas del recorrido 2, una vuelta de ~128 km con 2200-2600 m de desnivel. Tres son
coherentes y dos no, y esa mezcla es justamente lo que hace útil el conjunto: un cambio que relaje
la detección de incoherencias hará pasar por buenas a las dos malas, y uno que la endurezca tumbará
a alguna de las tres buenas.

| Fixture | Actividad original | Registros | Veredicto (criterio 30) |
|---|---|---|---|
| `recorrido2_30mar2025.fit` | 30-mar-2025, 08:00 UTC, ~127,9 km | 2 927 | coherente |
| `recorrido2_06abr2025.fit` | 06-abr-2025, 06:45 UTC, ~127,8 km | 2 901 | coherente |
| `recorrido2_04may2025.fit` | 04-may-2025, 06:33 UTC, ~127,3 km | 2 907 | **incoherente** |
| `recorrido2_08jun2025.fit` | 08-jun-2025, 06:35 UTC, ~127,3 km | 2 756 | **incoherente** |
| `recorrido2_19abr2026.fit` | 19-abr-2026, 07:03 UTC, ~126,8 km | 2 790 | coherente |

Las marcas de tiempo son las del primer registro del original (con un desfase de 1–2 s por el
redondeo a segundo entero del escritor), no las del nombre del archivo, que en algunos casos va 1 h
por delante.

Se generaron a partir de los `.fit` originales del usuario tomando **1 de cada 5 registros**
(de 1 Hz a 0,2 Hz) y reescribiéndolos con `tests/fit_writer.py`, para que el paquete no cargue
con ~2,7 MB de datos personales. Solo conservan lo que usa el modelo: tiempo, lat/lon, altitud,
velocidad y potencia. El resto de campos del original (cadencia, pulso, temperatura) se descarta.

## Por qué cada una está donde está

Las cinco son la misma vuelta: discretizando el trazado en celdas de ~50 m, cada una cubre entre el
94 % y el 98 % de las celdas de cualquier otra. **Ninguna aporta carretera nueva**, así que el
criterio 14 (transferencia a otra ruta) sigue sin poder verificarse con este conjunto.

Las dos incoherentes fueron más rápidas en llano de lo que permite la potencia que registraron
(viento neto a favor, rebufo o grupo), y eso deja la firma que detecta el criterio 30:

| | CdA calibrado | error en llano | error en bajadas |
|---|---|---|---|
| 30-mar-2025 | 0,276 | −2,5 % | −0,2 % |
| 06-abr-2025 | 0,262 | −0,8 % | −0,7 % |
| 19-abr-2026 | 0,259 | −0,7 % | +0,8 % |
| 04-may-2025 | **0,150** | **+29,6 %** | **−18,4 %** |
| 08-jun-2025 | 0,216 | **+15,8 %** | **−7,9 %** |

La del 04-may-2025 sirve además de caso de prueba del criterio 28: es la única que produce pares de
ida y vuelta imposibles (relaciones de velocidad de 2,13, 2,56 y 3,24, una de ellas emparejando
56 km/h con 17 km/h), porque el suavizado del altímetro barométrico le aplanó una bajada.

## La reducción no cambia las conclusiones

Validación cruzada dejando una fuera, con las tres coherentes:

| | error medio | error máximo |
|---|---|---|
| Datos completos (1 Hz) | 0,94 % | 1,38 % |
| Estos fixtures (0,2 Hz) | 0,94 % | 1,39 % |

CdA calibrado, original frente a fixture:

| Salida | por tiempo total | por pares de ida y vuelta |
|---|---|---|
| 30-mar-2025 | 0,2758 → 0,2761 | 0,2611 → 0,2670 |
| 06-abr-2025 | 0,2621 → 0,2623 | 0,2661 → 0,2684 |
| 04-may-2025 | 0,1550 → 0,1502 | 0,2435 → 0,2362 |
| 08-jun-2025 | 0,2131 → 0,2162 | 0,2542 → 0,2664 |
| 19-abr-2026 | 0,2583 → 0,2587 | 0,2550 → 0,2559 |

**Aviso de interpretación.** La reducción apenas mueve las tres salidas coherentes (≤ 2 % en los
dos métodos), pero mueve más a las dos incoherentes (hasta un 4,8 % en 08-jun), porque con menos
puntos la búsqueda de tramos encuentra segmentos distintos. Por eso los tests de los criterios 28
y 29 comprueban **mecanismos y comparaciones** (que el filtro baja la dispersión, que la banda
cubre el peor error medido) en vez de clavar cifras absolutas que dependen del remuestreo. Las
cifras absolutas de referencia son las de los datos completos, documentadas en
`simulador-ciclismo-triatlon.validacion.md`.

Para regenerarlos hace falta acceso a los `.fit` originales, que **no** están en el paquete; el
procedimiento está descrito arriba y es reproducible con `fit_writer.build_fit`.

## Anonimización de la posición

Los cinco `.fit` llevaban la ruta GPS real del usuario. Antes de publicar el repositorio se les
**sumaron 90,000000° a la longitud** de todos los registros (un entero exacto en semicírculos, así
que no hay error de redondeo) y no se tocó nada más. Se comprobó registro a registro que tiempo,
latitud, altitud, potencia y velocidad son idénticos al original. La haversine solo depende de la
diferencia de longitudes y de la latitud, de modo que distancias, rumbos, curvatura, pendientes y
todos los resultados del modelo son los mismos; la ruta, en cambio, ya no cae sobre el mapa de su
origen. Lo que siguen revelando es el **perfil de altitud** y la **fecha de cada salida**.
