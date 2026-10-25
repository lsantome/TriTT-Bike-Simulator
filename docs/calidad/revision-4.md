# Revisión 4 — encargo congelado y calibración del instrumento

**Fecha:** 12-oct-2026 · **Código:** intacto, huella
`58847d19c52af1142dba07adfc331a9dc9df934edceaa99640633c0ce018e958` (42 ficheros de `core/`, `app/`
y `tests/`) · **Suite:** 303 tests, los 303 verdes en las seis ejecuciones independientes.

Esta revisión cambia dos cosas respecto a las tres anteriores:

1. **El encargo se pasa literal** (`encargo-congelado.md`), el mismo texto para los seis revisores,
   sin mencionar hallazgos previos. En las revisiones 1→3 yo lo endurecí en cada ronda, así que la
   curva de hallazgos medía el encargo y no el repositorio.
2. **Se mide la potencia del instrumento con una siembra ciega.** Seis revisores en dos brazos de
   tres: el brazo `a` sobre el árbol congelado, el brazo `b` sobre una copia con **tres defectos
   introducidos a propósito**, uno por bloque de criterios, los tres elegidos para **pasar la suite
   en verde** (303/303 también en el árbol sembrado). Ningún revisor sabía nada de esto.

El reparto de criterios es el mismo en los dos brazos: bloque 1 → criterios 1-17, bloque 2 → 18-25,
bloque 3 → 26-32.

---

## 1. Calibración: ¿sirve de algo que un revisor diga «no encuentro nada»?

| Semilla | Dónde | Bloque | Detectada por su revisor | Detectada por alguien |
|---|---|---|---|---|
| **S1** · constante de Magnus `237,3 → 273,3` | `core/atmosphere.py:18` | 1 | **No** (b1) | **Sí** — b3, fuera de su bloque |
| **S2** · cota del test de recuperación de CdA `abs=0,005 → 0,25` | `tests/test_cda_estimator.py:38` | 2 | **Sí** (b2) | Sí |
| **S3** · leyenda inglesa `unverified → verified` | `core/i18n.py:949` | 3 | **Sí** (b3) | Sí |

**Falsos positivos: cero.** Ninguno de los tres revisores del árbol congelado denunció las semillas
—que allí no existen— y el contraste de la constante de Magnus no aparece ni una vez en sus
informes. El instrumento no inventa.

**Potencia demostrada por bloque: 2 de 3.** Los bloques 2 y 3 están medidos: un «no encuentro nada»
de a2 o a3 sería información sobre el código. El bloque 1 **no lo está**: su revisor pasó por encima
de una constante física equivocada, así que su silencio no acredita limpieza en esa región.

### Lo que la semilla fallida enseña, y es el hallazgo más valioso de toda la serie

S1 no es un error inventado: `237,3` es la constante de Magnus y `273,3` es la confusión clásica con
los 273,15 del cero absoluto, que aparecen tres líneas más abajo en el mismo fichero. **Remedido por
mí** sobre el efecto en la densidad del aire:

| T (°C) | HR (%) | ρ correcta | ρ sembrada | diferencia | error en p. de vapor |
|---|---|---|---|---|---|
| 10 | 70 | 1,24261 | 1,24295 | +0,027 % | −8,5 % |
| 15 | 75 | 1,21913 | 1,21984 | **+0,058 %** | −12,0 % |
| 25 | 75 | 1,17340 | 1,17529 | +0,161 % | −18,0 % |
| 30 | 80 | 1,14962 | 1,15265 | +0,264 % | −20,6 % |
| 35 | 90 | 1,12385 | 1,12879 | **+0,439 %** | −22,8 % |

El único test atmosférico que existe (`tests/test_route_and_limits.py:13-15`) comprueba **un punto**,
15 °C / 75 % HR, con `abs=0,005` sobre 1,219 — es decir **±0,410 %**. A esa temperatura el error de
la semilla es siete veces menor que la tolerancia. A 35 °C sí la superaría, pero el test nunca
evalúa ese punto, y no hay ningún test de `saturation_vapor_pressure_hpa` contra una referencia
externa.

Y hay una segunda vía a la misma conclusión, hallada de forma **independiente** por el revisor a2
sobre el árbol limpio, sin saber nada de la siembra: toda la batería del criterio 24 genera sus
actividades de referencia con `core.simulate` y contrasta el resultado contra `calibrate_cda`, que
pasa por el mismo simulador. **Lo verifiqué yo:** con `air_density` sesgada un +3 %, los 23 tests de
`tests/test_cda_estimator.py` siguen en verde mientras el CdA estimado sobre el fixture real cae un
2,9 %. (Ese sesgo del 3 % sí lo caza el test atmosférico de un punto; lo que queda sin vigilancia es
cualquier desviación por debajo del 0,4 %, y los errores de coeficiente físico suelen estar ahí.)

**Conclusión técnica:** la capa de coeficientes físicos —densidad del aire, presión de vapor— es la
región no medida de la suite. Dos instrumentos distintos (una semilla ciega y un revisor haciendo
mutación por su cuenta) han llegado al mismo sitio. Es, de todo lo que llevamos encontrado, lo único
que puede sesgar **el número que la herramienta calcula** sin que nada avise, y crece con la
temperatura: justo las condiciones de una competición de verano. Registrado como **B23**, con la
corrección propuesta.

---

## 2. Veredictos del brazo congelado (los que cuentan)

| Criterio | a1/a2/a3 | Criterio | | Criterio | |
|---|---|---|---|---|---|
| 1 Llano analítico | CUMPLE | 12 Sensibilidad | CUMPLE | 23 Presión | CUMPLE |
| 2 Velocidad terminal | CUMPLE | 13 Calibrar/validar | CUMPLE | 24 Estimador CdA | CUMPLE |
| 3 Límite por curvatura | **PARCIAL** | 14 Transferencia | PARCIAL | 25 Búsqueda de tramos | **PARCIAL** |
| 4 Tope de descenso | CUMPLE | 15 Perfiles de bici | CUMPLE | 26 Tabla por segmento | CUMPLE |
| 5 CdA continuo | CUMPLE | 16 Incertidumbre | **PARCIAL** | 27 Español e inglés | **PARCIAL** |
| 6 Potencia continua | CUMPLE | 17 Arranque de un paso | CUMPLE | 28 Pares imposibles | CUMPLE |
| 7 Monotonía | CUMPLE | 18 Masa única | CUMPLE | 29 Dos bandas | **PARCIAL** |
| 8 Ruido de elevación | CUMPLE | 19 Tooltips | CUMPLE | 30 Aviso de incoherencia | **PARCIAL** |
| 9 Circuito en 2 sentidos | CUMPLE | 20 Botones | CUMPLE | 31 Módulo independiente | **PARCIAL** |
| 10 Masa obligatoria | CUMPLE | 21 Tema | **PARCIAL** | 32 Sistema de diseño | **NO CUMPLE** |
| 11 Salidas | **PARCIAL** | 22 ETRTO manual | CUMPLE | | |

**21 CUMPLE · 10 PARCIAL · 1 NO CUMPLE.**

El brazo de calibración, sobre código con tres defectos añadidos, dio 21 CUMPLE · 9 PARCIAL · 2 NO
CUMPLE: una diferencia de un criterio, atribuible a la semilla S2 y a un umbral de juicio distinto
en el criterio 20. Los dos brazos coinciden en el diagnóstico de fondo.

### Discrepancias entre revisores, resueltas

- **Criterio 9.** a1 lo da por CUMPLE (reproduce el fixture: 0,1508 %); b1 lo baja a PARCIAL tras
  barrer 36 circuitos asimétricos y encontrar que **24 superan el ±0,5 %**, hasta 2,76 %. b1 aísla la
  causa: al invertir un circuito la pendiente cambia de signo y `∮ds/v(g) ≠ ∮ds/v(−g)` salvo
  distribución simétrica. **Tiene razón b1**: el comportamiento del modelo es correcto y lo que está
  mal es el enunciado del criterio, que promete una propiedad general midiendo un caso particular.
- **Criterio 21/32, tablas en oscuro.** a2 y a3 dicen que las tablas se quedan claras; b2 dice que
  el texto sí hereda la tinta oscura. **Los dos aciertan**: el fondo del `st.dataframe` se pinta en
  canvas con el tema de Streamlit y se queda claro, el color del texto sí cambia. La frase del
  README (C6) no describe ninguna de las dos cosas.
- **Criterio 3.** a1 mide +19,6 % de exceso por el suavizado del trazado en los extremos del arco;
  b1 mide +58 % por el recorte `MAX_CURVATURE` en radios menores de 10 m. **Son dos mecanismos
  distintos y los dos existen.** Lo medí por mi cuenta sumando los dos efectos sobre todo el arco:
  **+29,6 % a R = 35 m** (una curva de carretera corriente: el modelo entra a 47,8 km/h donde el
  criterio permite 36,9) y **+115 % a R = 4 m**. Es el defecto nuevo más serio de la ronda (A20), y
  el test se exime por construcción del tramo donde falla (B30).

---

## 3. Contraste contra el acumulado

| | Reportado | Ya en el registro | **Nuevo** |
|---|---|---|---|
| a1 (criterios 1-17) | 15 | 6 | 9 |
| a2 (criterios 18-25) | 16 | 6 | 10 |
| a3 (criterios 26-32) | 22 | 12 | 10 |
| **Brazo congelado** | **53** | **24** | **29** |

El registro pasa de 55 a **86** defectos: 32 funcionales, 30 de tests que no verifican, 17 de
documentación, 2 de spec, 5 de higiene. Más 13 entradas del brazo de calibración, fuera del
recuento de la serie.

**Captura-recaptura (Chapman)** entre el registro anterior y lo que reportó el brazo congelado:

```
N̂ = (55+1)(53+1)/(24+1) − 1 ≈ 120 defectos detectables con este encargo
```

86 conocidos → del orden de **34 sin detectar**. La estimación supone catchability uniforme, cosa
que aquí no se cumple (instrumentos distintos en las rondas 1-3, y cada revisor cubre un tercio de
los criterios), así que vale como orden de magnitud.

---

## 4. Qué dice esto del criterio de parada

Tu estrategia —contrastar cada revisor contra el acumulado— ya está funcionando como debe: separa
limpiamente lo nuevo de lo conocido y la discrepancia entre revisores se resuelve con evidencia, no
por antigüedad. Lo que faltaba era que el instrumento fuera el mismo entre medidas, y ahora lo es.
**La revisión 4 es la medida nº 1 de la serie comparable; la 5 sería la primera que puede confirmar
saturación.**

Dos datos para decidir:

1. **No estamos cerca del conjunto vacío.** Si quedan ~34 de ~120, una revisión 5 con este encargo
   traería del orden de 15 hallazgos nuevos. Llegar a «nada nuevo» exige varias rondas más sobre
   código congelado, cada una al coste de esta.
2. **Con el código congelado, revisar solo hace crecer el registro.** Hay 32 defectos funcionales
   abiertos, uno de ellos (A20) sesgando el tiempo en recorridos con curvas y otro (B23) dejando sin
   vigilancia la capa que puede sesgar el CdA con el calor.

**Recomendación:** cambiar el umbral a «ninguna revisión encuentra nada nuevo **del grupo A**» y
pasar a corregir, empezando por A20, B23 y B22 —los tres que afectan a lo que la herramienta
calcula— y luego el bloque de interfaz (A1, A2, A28, A29, que son cuatro defectos con una causa
común: el sistema de diseño se verificó leyendo CSS). Después de cada tanda, una revisión con este
mismo encargo y una siembra nueva. La siembra del bloque 1 hay que rehacerla con una semilla que su
revisor pueda ver: la de ahora demostró que esa región no está medida, que era su trabajo, pero deja
sin calibrar al revisor.
