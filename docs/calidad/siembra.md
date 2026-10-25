# Siembra de calibración — revisión 4

**Para qué.** Medir la potencia del instrumento. Un revisor que no detecta defectos sembrados no
sirve para certificar «no hay nada»: su «limpio» no es información sobre el código. Es la misma
lógica del mutation testing que ya se usó para el lint de `run.bat`.

**Regla de diseño.** Las tres semillas **pasan la suite** (303 verdes en la copia sembrada). Una
semilla que rompiera un test se detectaría leyendo la salida de pytest y no mediría nada.

**Huellas** (receta en `huella.py`):

| Árbol | Huella sha256 | Tests |
|---|---|---|
| congelado (serie: a1, a2, a3) | `58847d19c52af1142dba07adfc331a9dc9df934edceaa99640633c0ce018e958` | 303 ✓ |
| sembrado (calibración: b1, b2, b3) | `044b017395ea314f86d42eb3fb40211cc0bdd48e7823f187bb36c982f3fd68bf` | 303 ✓ |

Diferencia entre los dos árboles: exactamente las tres líneas de abajo. Nada más.

---

## S1 · bloque 1 (criterios 1-17) — constante física equivocada

`core/atmosphere.py:18`, `saturation_vapor_pressure_hpa`

```diff
-    return 6.1078 * 10.0 ** (7.5 * temp_c / (temp_c + 237.3))
+    return 6.1078 * 10.0 ** (7.5 * temp_c / (temp_c + 273.3))
```

237,3 es la constante de Magnus; 273,3 es un error de transcripción plausible (confusión con los
273,15 del cero absoluto que aparecen tres líneas más abajo). Efecto: la presión de vapor baja un
12 % a 15 °C, y la densidad del aire pasa de 1,21913 a 1,21984 kg/m³ (+0,06 %). El test
`test_atmosfera_a_coruna_nivel_del_mar` lo tolera porque su cota es `abs=0.005`.

**Detectable por:** punto 3 del encargo — contrastar la constante contra la referencia de Magnus en
lugar de creerse el docstring que dice «Magnus».

## S2 · bloque 2 (criterios 18-25) — cota tan ancha que no puede fallar

`tests/test_cda_estimator.py:38-39`, `test_c24_recupera_el_cda_con_el_que_se_genero_la_actividad`

```diff
-    assert e.cda == pytest.approx(cda_real, abs=0.005), f"estimado {e.cda:.4f} vs real {cda_real}"
-    assert e.utilizable and e.cda_min <= cda_real <= e.cda_max
+    assert e.cda == pytest.approx(cda_real, abs=0.25), f"estimado {e.cda:.4f} vs real {cda_real}"
+    assert e.utilizable
```

Es el test más fuerte del estimador: genera una actividad sintética con un CdA conocido y exige
recuperarlo. Con `abs=0.25` cualquier valor del rango plausible 0,20-0,35 lo cumple frente a
cualquier CdA real de la parametrización, y además desaparece la comprobación de que el valor real
cae dentro de la banda declarada. El criterio 24 queda sin verificar y la suite sigue verde.

**Detectable por:** punto 2 del encargo — «¿este test puede fallar?».

## S3 · bloque 3 (criterios 26-32) — el texto en inglés afirma lo contrario

`core/i18n.py:949`, clave `banda_leyenda_dia`

```diff
-                          "en": "day ±{pct:.0f} %, unverified"},
+                          "en": "day ±{pct:.0f} %, verified"},
```

La leyenda de la banda del día dice «sin verificar» en español y «verified» en inglés. Contradice el
criterio 27 (la traducción dice otra cosa que el original), el 29 (la banda del día de ruta nueva es
un suelo no verificado) y el lenguaje visual del 32 (rayada y ancha = no verificada). Ningún test
asevera esa cadena: el guardián de i18n solo comprueba que la clave exista en los dos idiomas.

**Detectable por:** puntos 5 y 6 del encargo — recorrer los dos idiomas y buscar incoherencias entre
texto y comportamiento.

---

## Lectura del resultado

Por bloque hay **una** semilla. Para cada bloque *n*:

- el revisor `b`*n* la detecta → el instrumento tiene potencia demostrada en ese bloque, y el
  «no encuentro nada nuevo» del revisor `a`*n* es información sobre el código;
- el revisor `b`*n* no la detecta → ese bloque no está medido, y el veredicto de `a`*n* no se puede
  interpretar como limpieza del código, solo como silencio del revisor.

Con tres bloques la potencia se informa por bloque, no como un número único: detectar la semilla de
texto no acredita potencia sobre la física.

**Limitación honesta:** tres semillas dan una estimación muy gruesa de la potencia (detectar 1 de 1
por bloque no distingue un revisor del 60 % de sensibilidad de uno del 95 %). Sirve para descartar
el caso malo —un revisor ciego— no para cuantificar la tasa de falsos negativos.
