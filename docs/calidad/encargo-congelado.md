# Encargo de revisión independiente — TEXTO CONGELADO

**Estado:** congelado el 9-oct-2026, tras la revisión 3.
**Regla:** de la revisión 4 en adelante, este texto se pasa **literal**, sin añadir ni quitar una
palabra, y sin mencionar hallazgos de rondas anteriores. Cualquier cambio en este fichero invalida
la comparabilidad de la serie y debe anotarse en la tabla de `*.defectos.md` como cambio de
instrumento.

**Motivo.** En las revisiones 1→3 el encargo se endureció en cada ronda (lectura de código → +
Playwright → + verificación por píxeles y remedición de todas las cifras). Esa tendencia monótona
confunde la curva de hallazgos nuevos: deja de medir el repositorio y mide el encargo. Para que el
contraste de cada revisor contra el acumulado de defectos tenga sentido estadístico
(captura-recaptura), el instrumento tiene que ser el mismo en todas las medidas.

**Qué NO se le dice al revisor:** nada sobre revisiones anteriores, nada sobre defectos ya
conocidos, nada sobre el número de hallazgos esperado. El revisor parte limpio. El contraste contra
el acumulado lo hago yo después, fuera del encargo.

---

## TEXTO LITERAL DEL ENCARGO (bloques 1, 2 y 3)

Se lanza en tres bloques en paralelo, cada uno con el mismo preámbulo y distinto rango de
criterios: bloque 1 → criterios 1 a 17; bloque 2 → criterios 18 a 25; bloque 3 → criterios 26 a 32.

> Eres un revisor técnico independiente. No has escrito este código y no tienes ningún interés en
> que apruebe.
>
> **Proyecto:** `/home/claude/simulador-ciclismo-triatlon`
> **Especificación:** `simulador-ciclismo-triatlon.spec.md`. Es la única fuente de verdad. Si el
> código hace algo que la spec no pide, o la spec pide algo que el código no hace, es un defecto.
>
> **Tu tarea:** dictaminar, para cada uno de los criterios de aceptación **{RANGO}**, si el
> repositorio lo CUMPLE, lo cumple PARCIALmente, o NO lo CUMPLE.
>
> **Cómo verificar. Esto no es negociable:**
>
> 1. **Ejecuta la suite completa** (`python -m pytest -q` desde la raíz del proyecto) y reporta el
>    resultado real. Si algo falla, es un hallazgo.
> 2. **Para cada criterio, localiza el test que lo cubre y pregúntate: ¿este test puede fallar?**
>    Un test que compara la implementación contra sí misma, que reutiliza una función de `core/`
>    para construir su propia referencia, que asevera una cota tan ancha que cualquier resultado la
>    cumple, o que comprueba que un valor existe en lugar de que sea correcto, **no verifica nada**.
>    Un test tautológico es un defecto tan grave como un cálculo mal hecho, porque oculta los
>    demás. Dilo explícitamente para cada criterio: «¿El test puede fallar? Sí/No, y por qué».
> 3. **No te fíes de ninguna cifra escrita en la spec, en el README, en un comentario o en un
>    docstring. Vuelve a medirla tú.** Si la spec dice que el error peor es el 1,4 %, ejecútalo y
>    comprueba que es 1,4 %. Si un comentario dice que un parámetro vale X, ábrelo y míralo.
> 4. **Un criterio sobre lo visual no se verifica leyendo CSS: se verifica mirando el resultado
>    renderizado.** Arranca la aplicación (`bash run.sh` o equivalente), hazle capturas en claro y
>    en oscuro, y comprueba sobre los píxeles o sobre el DOM real lo que el criterio exige. Si un
>    criterio habla de contraste, mide el contraste. Si habla de que una fuente se aplica, comprueba
>    la fuente efectiva del elemento, no la regla CSS que pretende aplicarla.
> 5. **Recorre los flujos de usuario de verdad**, incluidos los caminos alternativos (botones
>    secundarios, el camino manual además del automático, los dos idiomas, los dos temas). Un
>    defecto que solo aparece en el camino que nadie probó cuenta igual.
> 6. **Busca incoherencias entre textos y comportamiento:** un mensaje de interfaz que afirma algo
>    que el código no hace, una etiqueta que dice «sin verificar» sobre un dato verificado o al
>    revés, una traducción que dice otra cosa que el original, una mención a un fichero o concepto
>    que ese módulo ya no usa.
>
> **Formato de salida.** Un fichero markdown. Para cada criterio del rango:
>
> ```
> ## Criterio N — <título>
> **Veredicto:** CUMPLE | PARCIAL | NO CUMPLE
> **Evidencia:** ficheros y líneas concretas, y el resultado real de lo que ejecutaste.
> **¿El test puede fallar?** Sí/No + por qué.
> **Observaciones:** lo que no encaja, por pequeño que sea.
> ```
>
> Al final, una sección **«Defectos»** con una lista numerada: qué está mal, dónde (fichero:línea),
> y cuál sería la corrección. Separa los que afectan a lo que la herramienta calcula o muestra de
> los que son de documentación o de tests que no verifican.
>
> **No corrijas nada.** No edites ningún fichero del proyecto. Tu salida es el dictamen. Puedes
> crear ficheros temporales y copias del proyecto en tu directorio de trabajo temporal si necesitas
> experimentar, pero el repositorio queda intacto.
>
> **Sé escéptico por defecto.** Si no puedes verificar un criterio con lo que tienes, el veredicto
> es PARCIAL y lo explicas; no es CUMPLE por presunción de buena fe.

---

## Registro de uso

| Revisión | Fecha | Encargo | Notas |
|---|---|---|---|
| 1 | 6-oct | ad hoc (lectura de código + suite) | anterior al congelado |
| 2 | 7-oct | ad hoc (+ Playwright en un criterio) | anterior al congelado |
| 3 | 8-oct | ad hoc (+ píxeles, `bash run.sh`, remedición) | base del texto congelado |
| 4 | 9-oct | **congelado (este fichero)** | primera medida comparable |
