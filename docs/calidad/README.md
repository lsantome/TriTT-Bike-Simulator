# Calidad: cómo se ha revisado este código y en qué estado está

La especificación (`../../simulador-ciclismo-triatlon.spec.md`) tiene 32 criterios de aceptación. El código se ha
sometido a cuatro revisiones independientes por revisores que no lo escribieron y recibieron el mismo
encargo literal (desde la cuarta).

| Fichero | Qué es |
|---|---|
| [`registro-de-defectos.md`](registro-de-defectos.md) | Los 86 defectos acumulados tras la revisión 4 (12-oct-2026), clasificados en funcionales, tests que no verifican, documentación, spec e higiene |
| [`revision-4.md`](revision-4.md) | Informe de la revisión 4: veredictos por criterio y calibración del instrumento |
| [`encargo-congelado.md`](encargo-congelado.md) | El texto exacto que recibe cada revisor, para que las medidas sean comparables |
| [`siembra.md`](siembra.md) | Diseño de la calibración: tres defectos introducidos a propósito para medir si un revisor los encuentra |
| [`huella.py`](huella.py) | Receta reproducible de la huella del árbol revisado (`python huella.py <raíz>`) |

## Estado, sin adornar

- **Modelo físico:** ningún defecto registrado cambia el resultado en condiciones normales. Los criterios
  1, 2, 4, 5, 7, 8, 11 y 13 se reprodujeron con medidas independientes en las cuatro revisiones.
- **Registro desactualizado:** el registro es una foto del 12-oct-2026. Desde entonces se han aplicado
  muchas correcciones (gráficos en modo oscuro, mínimo de 1 km de los tramos, traducción de la
  procedencia de las bandas, camino manual del estimador, gráfica de pendiente, límite por curvatura…),
  pero **solo se han comprobado a mano unos catorce de los 86**. El resto no está verificado como
  corregido ni como abierto.
- **Límite por curvatura (criterio 3):** corregido y medido el 14-oct-2026. Fiable para radios de al menos
  `max(10 m, ventana de trazado / 7)`; por debajo es optimista (+4,5 % de velocidad a radio 8 m, +16,3 % a 4 m).
  Cambió el tiempo predicho de las tres salidas coherentes en +0,3 %.
- **Sin ejecutar en Windows:** `run.bat` está validado por inspección y lint estático, no ejecutado.
- **Criterio 14 (transferencia a otra ruta):** sin verificar por falta de datos. La banda del día (±15 %)
  es un suelo, no una estimación para una ruta nueva.
- **Siguiente paso previsto:** una quinta revisión con el encargo congelado y una siembra nueva.
