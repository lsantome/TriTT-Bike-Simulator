"""Traducciones: español (canónico) e inglés.

El español vive donde se usa: las etiquetas y las ayudas de los parámetros están en
`PARAM_SPECS` y los avisos del estimador se escriben donde se generan. Este módulo guarda **el
inglés** y las cadenas de la interfaz, para no tener el texto repartido en dos sitios.

Hay tres tests que lo sujetan: que cada parámetro tenga etiqueta y ayuda en inglés, que cada clave
de interfaz tenga los dos idiomas, y que ninguna ayuda inglesa sea un calco corto del español. Si
se añade un parámetro y se olvida su traducción, la suite falla.

**Lo que no se traduce, a propósito:** los nombres de columna de los CSV descargables. Son nombres
técnicos estables (`tiempo_s`, `cda`, `desnivel_m`) y cambiarlos con el idioma rompería cualquier
hoja de cálculo o script que los lea. En pantalla sí se muestran traducidos.
"""
from __future__ import annotations

from typing import Dict, Tuple

#: Idiomas disponibles. El primero es el canónico y el de por defecto.
IDIOMAS: Tuple[str, ...] = ("es", "en")
IDIOMA_POR_DEFECTO = "es"
#: Etiquetas del selector de idioma.
ETIQUETAS_IDIOMA = {"es": "ES · Español", "en": "EN · English"}


def normaliza(idioma: str) -> str:
    """Devuelve un idioma válido; cualquier cosa rara cae al castellano."""
    return idioma if idioma in IDIOMAS else IDIOMA_POR_DEFECTO


# --------------------------------------------------------------------------- categorías y opciones
CATEGORIAS: Dict[str, Dict[str, str]] = {
    "Ciclista": {"es": "Ciclista", "en": "Rider"},
    "Equipamiento": {"es": "Equipamiento", "en": "Equipment"},
    "Variables externas": {"es": "Variables externas", "en": "External variables"},
}

SUPERFICIES: Dict[str, Dict[str, str]] = {
    "liso": {"es": "liso", "en": "smooth"},
    "normal": {"es": "normal", "en": "normal"},
    "rugoso": {"es": "rugoso", "en": "rough"},
}


def categoria(nombre: str, idioma: str) -> str:
    return CATEGORIAS.get(nombre, {}).get(normaliza(idioma), nombre)


def superficie(nombre: str, idioma: str) -> str:
    return SUPERFICIES.get(nombre, {}).get(normaliza(idioma), nombre)


# --------------------------------------------------------------------------- parámetros en inglés
#: clave -> (etiqueta, ayuda) en inglés. El español está en `PARAM_SPECS`.
PARAM_EN: Dict[str, Tuple[str, str]] = {
    "masa_total": (
        "Total mass (rider + bike + kit)",
        "Everything that moves: you fully dressed, the bike, bottles, tools and race number. "
        "The model only uses this total, so there is no need to split your weight from the "
        "bike's. One extra kilo costs roughly 0.25 % of your time on a rolling route."),
    "p_subida": (
        "Climbing power",
        "Average power you plan to hold when the gradient is above the threshold (+2 % by "
        "default). It is a pacing target, not your maximum."),
    "p_llano": (
        "Flat power",
        "Average power on the flat, between the two gradient thresholds. It is the parameter "
        "that matters most for total time on a flat route."),
    "p_descenso": (
        "Descending power",
        "Power when the gradient drops below the negative threshold. 0 W means you freewheel. "
        "With 0 W, noise in the GPX altitude turns into fake descents, so keep an eye on the "
        "smoothing window."),
    "ftp": (
        "FTP (optional, for IF)",
        "Your functional threshold power. 0 = no FTP. It does not affect the predicted time: it "
        "is only used for the intensity factor (IF = NP/FTP)."),
    "umbral_pendiente": (
        "Climb/descent gradient threshold",
        "Above +this value the climbing power applies, and below -this value the descending "
        "power. In between, the flat power."),
    "anchura_banda_pendiente": (
        "Width of the transition between bands",
        "Power moves from one band to the next smoothly within this width, so there is no abrupt "
        "jump at the threshold."),
    "velocidad_inicial": (
        "Starting speed",
        "Speed the simulation begins with in the first metre. It matters little except on very "
        "short routes."),
    "cda": (
        "CdA (aero position)",
        "Effective frontal area: drag coefficient times area. It is the largest source of "
        "uncertainty in the whole model: ±0.02 m² moves the time more than any fine-tuning of "
        "the terrain. Measure it in the «Estimate CdA» tab instead of guessing. For reference: "
        "0.21–0.24 a well honed time trial position, 0.26–0.30 triathlon on aerobars, "
        "0.30–0.36 on the hoods."),
    "delta_cda": (
        "CdA increase in the upright position",
        "How much worse the CdA gets when you leave the aero position and sit up on the hoods, "
        "which the model assumes happens below the speed threshold. It is added to the CdA with "
        "a smooth transition, no jumps."),
    "umbral_posicion": (
        "Position change speed",
        "Speed at which you are assumed to abandon the aero position (on a climb). Below it the "
        "full CdA increase applies, above it none."),
    "anchura_transicion_cda": (
        "Width of the CdA transition",
        "How gradual the position change is. More width means a smoother change around the "
        "threshold."),
    "eficiencia": (
        "Drivetrain efficiency",
        "Fraction of the power meter's reading that reaches the wheel. 0.975 is typical with a "
        "clean, lubricated chain; 0.95 with a dirty or cross-chained drivetrain."),
    "etrto": (
        "Wheel size (ETRTO)",
        "The size printed on the tyre sidewall: width-rim in mm (28-622 is 700x28C). The "
        "circumference comes from it. Choose «manual» to enter a circumference you have measured "
        "yourself. Note: wheel size only enters the rotational inertia and moves the time by "
        "less than 0.001 %."),
    "perimetro_mm": (
        "Measured wheel circumference",
        "Only with the wheel size set to «manual». This is the real rolling circumference: mark "
        "the ground, roll one full turn while sitting on the bike and measure between the two "
        "marks. For 700x28C it is about 2130 mm."),
    "inercia_ruedas": (
        "Inertia of the wheel pair",
        "Rotational inertia of both wheels. It only matters during accelerations and braking; "
        "over a whole route its effect is negligible."),
    "temperatura": (
        "Temperature",
        "Air temperature during the ride. It enters only through air density: warmer air is less "
        "dense and slightly less resistant. It is assumed constant over the whole route."),
    "humedad": (
        "Relative humidity",
        "Relative humidity. Humid air is slightly less dense than dry air. Its effect on time is "
        "small, a few tenths of a percent."),
    "presion_nivel_mar": (
        "Sea level pressure",
        "Pressure reduced to sea level, the one weather forecasts give. It is corrected with the "
        "altitude of each point of the route using the standard atmosphere."),
    "densidad_manual": (
        "Manual air density",
        "0 = compute it from temperature, humidity, pressure and altitude. Only fill it in if you "
        "have a measured value and want to skip the calculation."),
    "superficie": (
        "Surface (global)",
        "Road surface for the whole route: smooth (fresh asphalt), normal (asphalt in good "
        "condition) or rough (old asphalt, packed gravel). You can override it per kilometre "
        "below."),
    "presion_neumaticos": (
        "Tyre pressure",
        "Higher pressure lowers Crr on a drum test, and the model applies that with an exponent "
        "per surface. Careful: on real roads, above a certain pressure the whole thing gets "
        "SLOWER (impedance losses) and this formula does not represent that, so on rough roads it "
        "will give you an optimistic result."),
    "presion_referencia": (
        "Reference pressure for the Crr values",
        "Pressure at which the Crr values below are defined. With the tyre pressure equal to "
        "this, the Crr is used exactly as entered."),
    "crr_liso": (
        "Crr smooth asphalt (at 29 km/h)",
        "Rolling resistance coefficient on smooth asphalt, defined at 29 km/h and at the "
        "reference pressure."),
    "crr_normal": (
        "Crr normal asphalt (at 29 km/h)",
        "The same for asphalt in good condition. 0.0045 is a reasonable value for a good road "
        "tyre with an inner tube."),
    "crr_rugoso": (
        "Crr rough asphalt (at 29 km/h)",
        "The same for old asphalt or packed gravel. It can be double the smooth asphalt value."),
    "crr_exp_liso": (
        "Pressure exponent (smooth)",
        "Exponent of (reference pressure/pressure) with which pressure modulates Crr on smooth "
        "asphalt. An estimate with no experimental backing of our own: 0 disables it."),
    "crr_exp_normal": (
        "Pressure exponent (normal)",
        "The same for asphalt in good condition. An estimate with no backing of our own, "
        "editable."),
    "crr_exp_rugoso": (
        "Pressure exponent (rough)",
        "The same for rough surfaces. Deliberately kept low, because on a bad surface the gain "
        "from pressure almost disappears and can even reverse."),
    "crr1_liso": (
        "Crr: change with speed (smooth)",
        "How much Crr grows per m/s above 29 km/h. An estimate with no solid experimental "
        "backing."),
    "crr1_normal": (
        "Crr: change with speed (normal)",
        "The same for asphalt in good condition. An estimate with no experimental backing of our "
        "own."),
    "crr1_rugoso": (
        "Crr: change with speed (rough)",
        "The same for rough surfaces, where speed penalises more. An estimate."),
    "velocidad_maxima": (
        "Maximum speed (descent cap)",
        "Safety cap: the simulation never goes above this on any descent, however much the "
        "physics would allow."),
    "limite_curvatura": (
        "Limit speed through corners",
        "Limits the speed in each corner to what the maximum lateral acceleration allows, with "
        "braking propagated backwards. Turn it off to see the theoretical ceiling without "
        "braking for corners."),
    "aceleracion_lateral": (
        "Maximum lateral acceleration in corners",
        "How much lateral acceleration you accept in a corner. 3 m/s² is conservative and typical "
        "of riding carefully; 5–6 is already riding on the limit."),
    "deceleracion_frenada": (
        "Maximum braking deceleration",
        "Hardest braking used to reach each corner's speed. It stops the cornering limit from "
        "implying instantaneous braking."),
    "ventana_elevacion": (
        "Elevation smoothing window",
        "Length over which the GPX altitude is smoothed before computing the gradient. 150 m is "
        "the default. If your GPX has noisy GPS altitude (σ ≥ 3 m), raise it to 200 m; if you "
        "lower it too much, noise turns into fake gradients."),
    "ventana_trazado": (
        "Track smoothing window",
        "The same for the coordinates, before computing curvature. A wider window means more open "
        "corners and less fake braking caused by GPS noise."),
    "paso_remuestreo": (
        "Resampling step",
        "Length of each segment the route is split into. Shorter gives more detail and more "
        "computing time; 20 m is a good compromise."),
    "razon_velocidad_par": (
        "Impossible-pair threshold",
        "Speed ratio above which an out-and-back pair is discarded as impossible: 1.5 means that "
        "if one pass is more than 1.5 times as fast as the other it cannot be the same flat road "
        "in both directions. Measured on the reference rides: the highest legitimate ratio is "
        "1.42 and the discarded ones range from 2.1 to 3.2. Lower it to be stricter about "
        "pairing."),
}


def param_label(spec, idioma: str) -> str:
    """Etiqueta del parámetro en el idioma pedido."""
    if normaliza(idioma) == "en" and spec.key in PARAM_EN:
        return PARAM_EN[spec.key][0]
    return spec.label


def param_help(spec, idioma: str) -> str:
    """Ayuda (tooltip) del parámetro en el idioma pedido."""
    if normaliza(idioma) == "en" and spec.key in PARAM_EN:
        return PARAM_EN[spec.key][1]
    return spec.help


# --------------------------------------------------------------------------- cabeceras de tabla
#: Nombre técnico de columna -> cabecera que se muestra. Los CSV conservan el nombre técnico.
COLUMNAS: Dict[str, Dict[str, str]] = {
    "tramo_km": {"es": "tramo (km)", "en": "segment (km)"},
    "largo_km": {"es": "largo (km)", "en": "length (km)"},
    "cda": {"es": "CdA", "en": "CdA"},
    "±": {"es": "±", "en": "±"},
    "cda_min": {"es": "CdA mín.", "en": "CdA min"},
    "cda_max": {"es": "CdA máx.", "en": "CdA max"},
    "desnivel_m": {"es": "desnivel (m)", "en": "elev. change (m)"},
    "pendiente_%": {"es": "pendiente (%)", "en": "gradient (%)"},
    "v_media_kmh": {"es": "v media (km/h)", "en": "avg speed (km/h)"},
    "potencia_media_w": {"es": "potencia media (W)", "en": "avg power (W)"},
    "aero_%": {"es": "aero (%)", "en": "aero (%)"},
    "rumbo": {"es": "rumbo (°)", "en": "bearing (°)"},
    "utilizable": {"es": "utilizable", "en": "usable"},
    "duracion_s": {"es": "duración (s)", "en": "duration (s)"},
    "sin_pedalear_%": {"es": "sin pedalear (%)", "en": "not pedalling (%)"},
    "viento_1ms_±": {"es": "viento 1 m/s ±", "en": "wind 1 m/s ±"},
    "err_altitud": {"es": "error altitud", "en": "altitude error"},
    "err_crr": {"es": "error Crr", "en": "Crr error"},
    "err_potencia": {"es": "error potencia", "en": "power error"},
    "densidad_aire": {"es": "densidad aire", "en": "air density"},
    "actividad": {"es": "actividad", "en": "activity"},
    "ida_km": {"es": "ida (km)", "en": "outbound (km)"},
    "rumbo_ida": {"es": "rumbo ida", "en": "outbound bearing"},
    "cda_ida": {"es": "CdA ida", "en": "outbound CdA"},
    "vuelta_km": {"es": "vuelta (km)", "en": "return (km)"},
    "rumbo_vuelta": {"es": "rumbo vuelta", "en": "return bearing"},
    "cda_vuelta": {"es": "CdA vuelta", "en": "return CdA"},
    "CdA_par": {"es": "CdA del par", "en": "pair CdA"},
    "viento_ms": {"es": "viento (m/s)", "en": "wind (m/s)"},
    "separacion_m": {"es": "separación (m)", "en": "separation (m)"},
    "v_kmh": {"es": "v (km/h)", "en": "speed (km/h)"},
    "km_inicio": {"es": "km inicio", "en": "start km"},
    "km_fin": {"es": "km fin", "en": "end km"},
    "superficie": {"es": "superficie", "en": "surface"},
    "tiempo_s": {"es": "tiempo (s)", "en": "time (s)"},
    # --- criterio 30: examen de coherencia
    "cda_calibrado": {"es": "CdA calibrado", "en": "calibrated CdA"},
    "coherente": {"es": "coherente", "en": "coherent"},
    "err_llano_%": {"es": "error llano (%)", "en": "flat error (%)"},
    "err_bajada_%": {"es": "error bajada (%)", "en": "descent error (%)"},
    "err_subida_%": {"es": "error subida (%)", "en": "climb error (%)"},
    "km_llano": {"es": "km llano", "en": "flat km"},
    "km_bajada": {"es": "km bajada", "en": "descent km"},
    "km_subida": {"es": "km subida", "en": "climb km"},
    "cda_fuera_de_rango": {"es": "CdA fuera de rango", "en": "CdA out of range"},
    "patron_incoherente": {"es": "patrón incoherente", "en": "incoherent pattern"},
    "motivo": {"es": "motivo", "en": "reason"},
    # --- tabla por bloques de km (pestaña Resultados)
    "velocidad_kmh": {"es": "velocidad (km/h)", "en": "speed (km/h)"},
    "potencia_w": {"es": "potencia (W)", "en": "power (W)"},
    "cda_medio": {"es": "CdA medio", "en": "mean CdA"},
    "elevacion_fin_m": {"es": "elevación final (m)", "en": "end elevation (m)"},
    # --- informe de validación con FIT
    "name": {"es": "actividad", "en": "activity"},
    "distancia_km": {"es": "distancia (km)", "en": "distance (km)"},
    "tiempo_real_movimiento_s": {"es": "tiempo real en movimiento (s)",
                                 "en": "real moving time (s)"},
    "tiempo_predicho_s": {"es": "tiempo predicho (s)", "en": "predicted time (s)"},
    "error_tiempo_pct": {"es": "error de tiempo (%)", "en": "time error (%)"},
    "error_velocidad_medio_kmh": {"es": "error medio de velocidad (km/h)",
                                  "en": "mean speed error (km/h)"},
    "mae_velocidad_kmh": {"es": "MAE velocidad (km/h)", "en": "speed MAE (km/h)"},
    "rmse_velocidad_kmh": {"es": "RMSE velocidad (km/h)", "en": "speed RMSE (km/h)"},
    "potencia_media_real_w": {"es": "potencia media real (W)", "en": "real mean power (W)"},
    "cda_usado": {"es": "CdA usado", "en": "CdA used"},
    "criterio_<=3%": {"es": "criterio ≤ 3 %", "en": "≤ 3 % criterion"},
    # --- informe de sensibilidad
    "parametro": {"es": "parámetro", "en": "parameter"},
    "etiqueta": {"es": "nombre", "en": "name"},
    "categoria": {"es": "categoría", "en": "category"},
    "unidad": {"es": "unidad", "en": "unit"},
    "valor_base": {"es": "valor base", "en": "base value"},
    "valor_menos": {"es": "valor −10 %", "en": "value −10 %"},
    "valor_mas": {"es": "valor +10 %", "en": "value +10 %"},
    "efecto_max_%": {"es": "efecto máximo (%)", "en": "max effect (%)"},
    "relevante": {"es": "relevante", "en": "relevant"},
    "interfaz": {"es": "interfaz", "en": "interface"},
    "sugerencia": {"es": "sugerencia", "en": "suggestion"},
    "nota": {"es": "nota", "en": "note"},
}


#: Sufijos de las columnas de banda, para traducir `tiempo_s_min_modelo` y compañía sin
#: tener que enumerar cada combinación (criterio 27).
SUFIJOS_BANDA: Dict[str, Dict[str, str]] = {
    "_min_modelo": {"es": "mín. modelo", "en": "model min"},
    "_max_modelo": {"es": "máx. modelo", "en": "model max"},
    "_min_dia": {"es": "mín. día", "en": "day min"},
    "_max_dia": {"es": "máx. día", "en": "day max"},
}


def cabeceras(columnas, idioma: str) -> Dict[str, str]:
    """Mapa para renombrar las columnas de un DataFrame al mostrarlo.

    Resuelve también las columnas de banda (`tiempo_s_min_modelo`…) combinando la cabecera de
    la columna base con la del sufijo, para no tener que enumerarlas una a una.
    """
    lang = normaliza(idioma)
    out = {}
    for col in columnas:
        if col in COLUMNAS:
            out[col] = COLUMNAS[col][lang]
            continue
        for sufijo, etiqueta in SUFIJOS_BANDA.items():
            base = col[: -len(sufijo)]
            if col.endswith(sufijo) and base in COLUMNAS:
                out[col] = f"{COLUMNAS[base][lang]} · {etiqueta[lang]}"
                break
    return out


# --------------------------------------------------------------------------- cadenas de interfaz
UI: Dict[str, Dict[str, str]] = {
    # --- barra lateral
    "titulo": {"es": "🚴 Simulador triatlón / CRI", "en": "🚴 Triathlon / TT simulator"},
    "subtitulo": {"es": "Triatlón sin drafting y contrarreloj",
                  "en": "Non-drafting triathlon and time trial"},
    "idioma": {"es": "Idioma", "en": "Language"},
    "modo_oscuro": {"es": "🌙 Modo oscuro", "en": "🌙 Dark mode"},
    "modo_oscuro_ayuda": {
        "es": "Oscurece la interfaz y los gráficos. Las tablas se quedan claras: Streamlit las "
              "dibuja en un lienzo al que no llega el CSS. Para un oscuro completo, usa el tema "
              "del menú «Settings» de Streamlit, arriba a la derecha.",
        "en": "Darkens the interface and the charts. Tables stay light: Streamlit draws them on a "
              "canvas that CSS cannot reach. For fully dark tables, use the theme in Streamlit's "
              "«Settings» menu, top right."},
    "subir_gpx": {"es": "Ruta (.gpx)", "en": "Route (.gpx)"},
    "perfil_bici": {"es": "🚲 Perfil de bici", "en": "🚲 Bike profile"},
    "perfil_guardado": {"es": "Perfil guardado", "en": "Saved profile"},
    "perfil_cargar": {"es": "Cargar", "en": "Load"},
    "perfil_borrar": {"es": "Borrar", "en": "Delete"},
    "perfil_sin_perfiles": {
        "es": "Aún no hay perfiles. Ajusta los parámetros y guarda uno abajo.",
        "en": "No profiles yet. Set the parameters and save one below."},
    "perfil_cargado": {"es": "Cargado: **{nombre}** (los cambios posteriores no se guardan solos).",
                       "en": "Loaded: **{nombre}** (later changes are not saved automatically)."},
    "perfil_calibrado": {"es": "✅ Calibrado — ", "en": "✅ Calibrated — "},
    "perfil_sin_calibrar": {"es": "⚠ Sin calibrar — ", "en": "⚠ Not calibrated — "},
    "perfil_resumen": {
        "es": "CdA {cda:.3f} m² · masa total {masa:.1f} kg · actualizado {fecha}",
        "en": "CdA {cda:.3f} m² · total mass {masa:.1f} kg · updated {fecha}"},
    "guardar_perfil_titulo": {"es": "💾 Guardar estos valores como perfil",
                              "en": "💾 Save these values as a profile"},
    "guardar_nombre": {"es": "Nombre de la bici", "en": "Bike name"},
    "guardar_nombre_ph": {"es": "p. ej. Cervélo P5 (triatlón)", "en": "e.g. Cervélo P5 (triathlon)"},
    "guardar_origen": {"es": "Origen del CdA", "en": "Where the CdA comes from"},
    "guardar_origen_ph": {
        "es": "p. ej. calibrado con 2 salidas del 30-mar y 06-abr-2025",
        "en": "e.g. calibrated with 2 rides from 30-Mar and 06-Apr-2025"},
    "guardar_calibrado": {"es": "El CdA está calibrado con actividades reales",
                          "en": "The CdA is calibrated with real activities"},
    "guardar_boton": {"es": "Guardar perfil", "en": "Save profile"},
    "guardar_ok": {"es": "Perfil «{nombre}» guardado.", "en": "Profile «{nombre}» saved."},
    "guardar_nota": {
        "es": "Se guardan en `{fichero}` (junto al proyecto). Un perfil fija la masa total, el "
              "CdA, ΔCdA, η, los Crr, la superficie, la presión y la medida de rueda.",
        "en": "They are stored in `{fichero}` (next to the project). A profile fixes total mass, "
              "CdA, ΔCdA, η, the Crr values, surface, pressure and wheel size."},
    "avanzados": {"es": "Avanzados", "en": "Advanced"},
    "superficie_tramos": {"es": "**Superficie por tramos (opcional)**",
                          "en": "**Surface per section (optional)**"},
    "superficie_tramos_nota": {
        "es": "Sobrescribe la superficie global entre dos kilómetros.",
        "en": "Overrides the global surface between two kilometre marks."},
    "boton_simular": {"es": "▶ Simular", "en": "▶ Simulate"},
    "boton_simular_ayuda": {"es": "Ejecuta la simulación con los parámetros actuales.",
                            "en": "Runs the simulation with the current parameters."},
    "boton_borrar": {"es": "🗑 Borrar", "en": "🗑 Clear"},
    "boton_borrar_ayuda": {
        "es": "Devuelve todos los campos a sus valores iniciales y olvida los resultados y los "
              "ficheros subidos. No toca el idioma, el módulo ni el modo oscuro, que son cómo "
              "estás mirando la herramienta, ni los perfiles de bici guardados.",
        "en": "Resets every field to its initial value and forgets the results and uploaded "
              "files. It leaves the language, the module and dark mode alone — those are how you "
              "are viewing the tool — and does not delete saved bike profiles."},
    "falta_masa_titulo": {"es": "Falta la masa total", "en": "Total mass is missing"},
    "falta_masa": {
        "es": "Falta {faltan}: es el único dato sin valor por defecto, porque suponerlo "
              "falsearía cualquier resultado. Ponlo en la barra lateral.",
        "en": "Missing {faltan}: it is the only figure without a default, because guessing it "
              "would falsify any result. Enter it in the sidebar."},
    "falta_perimetro": {
        "es": "Has elegido la medida de rueda «manual»: introduce el perímetro medido (mm) en "
              "Equipamiento. Marca el suelo, da una vuelta completa sentado en la bici y mide "
              "entre las dos marcas.",
        "en": "You chose the «manual» wheel size: enter the measured circumference (mm) under "
              "Equipment. Mark the ground, roll one full turn while sitting on the bike and "
              "measure between the two marks."},
    "params_invalidos": {"es": "Parámetros no válidos: {error}", "en": "Invalid parameters: {error}"},
    "pie_resumen": {
        "es": "Masa total {masa:.1f} kg · CdA {cda:.3f} m² · rueda {etrto} ({per:.0f} mm de "
              "perímetro)",
        "en": "Total mass {masa:.1f} kg · CdA {cda:.3f} m² · wheel {etrto} ({per:.0f} mm "
              "circumference)"},
    "desactivado_nota": {
        "es": " — Desactivado: elige la medida de rueda «manual» para poder rellenarlo.",
        "en": " — Disabled: choose the «manual» wheel size to fill it in."},
    # --- pestañas
    "tab_resultados": {"es": "Resultados", "en": "Results"},
    "tab_sensibilidad": {"es": "Sensibilidad", "en": "Sensitivity"},
    "tab_validacion": {"es": "Validación con FIT", "en": "Validation with FIT"},
    "tab_estimador": {"es": "Estimar CdA", "en": "Estimate CdA"},
    "tab_modelo": {"es": "Acerca del modelo", "en": "About the model"},
    # --- resultados
    "pulsa_simular": {
        "es": "Ajusta los parámetros en la barra lateral y pulsa **▶ Simular**.",
        "en": "Set the parameters in the sidebar and press **▶ Simulate**."},
    "sin_gpx_demo": {"es": "Sin GPX se usará la ruta de ejemplo (sintética).",
                     "en": "With no GPX the example (synthetic) route will be used."},
    "desfasado": {
        "es": "Has cambiado parámetros o la ruta desde la última simulación: lo que se muestra "
              "abajo es el resultado anterior. Pulsa **▶ Simular** otra vez.",
        "en": "You changed parameters or the route since the last run: what is shown below is the "
              "previous result. Press **▶ Simulate** again."},
    "usando_demo": {
        "es": "Mostrando la **ruta de ejemplo (sintética)**. Sube un GPX en la barra lateral para "
              "simular tu ruta real.",
        "en": "Showing the **example (synthetic) route**. Upload a GPX in the sidebar to simulate "
              "your real route."},
    "m_tiempo": {"es": "Tiempo", "en": "Time"},
    "m_velocidad": {"es": "Velocidad media", "en": "Average speed"},
    "m_distancia": {"es": "Distancia", "en": "Distance"},
    "m_desnivel": {"es": "Desnivel +", "en": "Elevation gain"},
    "m_potencia": {"es": "Potencia media", "en": "Average power"},
    "m_np": {"es": "Potencia normalizada (NP)", "en": "Normalised power (NP)"},
    "m_vi": {"es": "Índice de variabilidad (VI)", "en": "Variability index (VI)"},
    "m_if": {"es": "Factor de intensidad (IF)", "en": "Intensity factor (IF)"},
    "m_if_sin": {"es": "— (indica FTP)", "en": "— (set FTP)"},
    "banda_titulo": {
        "es": "**Tiempo con su margen** — **precisión del modelo** (misma bici y ruta, condiciones "
              "parecidas a las de la calibración): `{a} – {b}` (±{p1:.1f} %). **Margen del día**, "
              "con el viento y las condiciones que el modelo no conoce: `{c} – {d}` "
              "(±{p2:.0f} %).",
        "en": "**Time with its margin** — **model accuracy** (same bike and route, conditions like "
              "those of the calibration): `{a} – {b}` (±{p1:.1f} %). **Margin of the day**, with "
              "the wind and conditions the model knows nothing about: `{c} – {d}` "
              "(±{p2:.0f} %)."},
    "banda_rangos": {
        "es": "Precisión del modelo: `{a} – {b}` (±{p1:.1f} %). Margen del día: `{c} – {d}` "
              "(±{p2:.0f} %).",
        "en": "Model accuracy: `{a} – {b}` (±{p1:.1f} %). Margin of the day: `{c} – {d}` "
              "(±{p2:.0f} %)."},
    "banda_ruta_nueva_corto": {
        "es": "**En una ruta nueva no hay banda verificada:** el margen del día es un suelo, no "
              "una estimación, porque no hay ninguna salida de esta bici por otra ruta.",
        "en": "**On a new route there is no verified band:** the margin of the day is a floor, "
              "not an estimate, because there is no ride of this bike on another route."},
    "banda_ruta_nueva": {
        "es": "**Ruta nueva: sin banda verificada.** El margen del día es un **suelo**, no una "
              "estimación — {aviso}.",
        "en": "**New route: no verified band.** The margin of the day is a **floor**, not an "
              "estimate — {aviso}."},
    "limites_activos": {
        "es": "Límites de velocidad activos en {n} de {total} tramos ({pct:.1f} %).",
        "en": "Speed limits active in {n} of {total} segments ({pct:.1f} %)."},
    "g_elevacion": {"es": "Elevación suavizada (m)", "en": "Smoothed elevation (m)"},
    "g_pendiente": {"es": "Pendiente suavizada (%)", "en": "Smoothed gradient (%)"},
    "g_velocidad": {"es": "Velocidad (km/h)", "en": "Speed (km/h)"},
    "g_potencia": {"es": "Potencia (W)", "en": "Power (W)"},
    "g_cda": {"es": "CdA efectivo (m²)", "en": "Effective CdA (m²)"},
    "g_potencia_perfil": {"es": "Potencia (perfil)", "en": "Power (profile)"},
    "g_potencia_aplicada": {"es": "Potencia aplicada", "en": "Applied power"},
    "tabla_bloques": {"es": "Tabla por bloques de (km)", "en": "Table in blocks of (km)"},
    "tabla_bloques_nota": {
        "es": "Las columnas de margen son el del tiempo de cada bloque: ±{p1:.1f} % de precisión "
              "del modelo y ±{p2:.0f} % de margen del día, las dos medidas. En una ruta nueva no "
              "hay banda verificada.",
        "en": "The margin columns are those of each block's time: ±{p1:.1f} % of model accuracy "
              "and ±{p2:.0f} % margin of the day, both measured. On a new route there is no "
              "verified band."},
    "descargar_bloques": {"es": "Descargar tabla por bloques (CSV)",
                          "en": "Download block table (CSV)"},
    "descargar_tramos": {"es": "Descargar detalle por tramo (CSV)",
                         "en": "Download per-segment detail (CSV)"},
    "csv_nota": {
        "es": "Los CSV conservan los nombres técnicos de columna (`tiempo_s`, `cda`…) en los dos "
              "idiomas, para no romper hojas de cálculo.",
        "en": "The CSV files keep the technical column names (`tiempo_s`, `cda`…) in both "
              "languages, so spreadsheets do not break."},
    # --- sensibilidad
    "sens_intro": {
        "es": "Efecto en el **tiempo total** de variar cada parámetro **±10 %** (uno a uno, valor "
              "literal recortado a su rango válido). Sirve para decidir qué parámetros merecen "
              "estar en la interfaz principal. Es específico de esta ruta y de los valores "
              "actuales.",
        "en": "Effect on **total time** of varying each parameter by **±10 %** (one at a time, "
              "literal value clipped to its valid range). It tells you which parameters deserve "
              "to be in the main interface. It is specific to this route and these values."},
    "sens_boton": {"es": "Calcular sensibilidad", "en": "Compute sensitivity"},
    "sens_calculando": {"es": "Calculando…", "en": "Computing…"},
    "sens_desfasado": {
        "es": "⚠ El resultado corresponde a parámetros/ruta anteriores; vuelve a calcular.",
        "en": "⚠ The result belongs to earlier parameters/route; compute it again."},
    "sens_nota": {
        "es": "Se considera relevante un efecto ≥ {umbral:g} % en el tiempo total. La temperatura "
              "se perturba ±10 % sobre su valor en °C (±1,5 °C a 15 °C).",
        "en": "An effect ≥ {umbral:g} % on total time is considered relevant. Temperature is "
              "perturbed by ±10 % of its value in °C (±1.5 °C at 15 °C)."},
    "sens_eje": {"es": "Δ tiempo total (%)", "en": "Δ total time (%)"},
    # --- validación FIT
    "val_intro": {
        "es": "Reproduce con el simulador la **potencia real** de tus actividades (.fit) y compara "
              "el tiempo en movimiento y la velocidad con los reales. **Calibra en una ruta y "
              "valida en otra.** El modelo no incluye viento: el de la salida queda absorbido en "
              "el CdA ajustado.",
        "en": "Replays your activities' **real power** (.fit) through the simulator and compares "
              "moving time and speed with the real ones. **Calibrate on one route and validate on "
              "another.** The model has no wind: the wind of that day ends up absorbed into the "
              "fitted CdA."},
    "val_subir": {"es": "Actividades (.fit) con GPS y potencia",
                  "en": "Activities (.fit) with GPS and power"},
    "val_elegir_cal": {"es": "Rutas para calibrar el CdA", "en": "Rides to calibrate the CdA"},
    "val_una_sola": {
        "es": "⚠ Con una sola salida el CdA absorbe todo lo particular de ese día (viento, "
              "paradas, forma). Usa al menos 2 salidas de la misma bici.",
        "en": "⚠ With a single ride the CdA absorbs everything specific to that day (wind, stops, "
              "form). Use at least 2 rides on the same bike."},
    "val_calibrar": {"es": "Calibrar CdA con las rutas seleccionadas",
                     "en": "Calibrate CdA with the selected rides"},
    "val_calibrando": {"es": "Calibrando…", "en": "Calibrating…"},
    "val_cda_ok": {"es": "CdA calibrado: **{cda:.3f} m²**", "en": "Calibrated CdA: **{cda:.3f} m²**"},
    "val_origen": {"es": "Origen: {origen}", "en": "Source: {origen}"},
    "val_origen_texto": {"es": "calibrado con {n} salida(s): {lista}",
                         "en": "calibrated with {n} ride(s): {lista}"},
    "val_aplicar": {"es": "Aplicar este CdA (y su origen) en la barra lateral",
                    "en": "Apply this CdA (and its source) in the sidebar"},
    "val_validar": {"es": "Validar (rutas no usadas para calibrar)",
                    "en": "Validate (rides not used for calibration)"},
    "val_reproduciendo": {"es": "Reproduciendo {nombre}…", "en": "Replaying {nombre}…"},
    "val_todas_cal": {"es": "Todas las rutas están marcadas para calibrar; sube otra para validar.",
                      "en": "Every ride is marked for calibration; upload another one to validate."},
    "val_no_cumple": {
        "es": "Hay rutas con error de tiempo > 3 %: el modelo (o su calibración) no alcanza la "
              "precisión objetivo en ellas. No se oculta.",
        "en": "Some rides have a time error > 3 %: the model (or its calibration) does not reach "
              "the target accuracy on them. This is not hidden."},
    "val_sube_fit": {"es": "Sube al menos un .fit para empezar.",
                     "en": "Upload at least one .fit to start."},
    # --- estimador
    "est_intro": {
        "es": "Calcula tu **CdA real** a partir de una actividad: elige un segmento sobre el "
              "perfil y la herramienta cierra el balance de energía en él (pedales − desnivel − "
              "rodadura − inercia = aerodinámica). **Lee los avisos**: en un segmento corto, "
              "lento o con cuesta, el desnivel pesa más que el aire y el número no vale.",
        "en": "Works out your **real CdA** from an activity: pick a segment on the profile and the "
              "tool closes the energy balance over it (pedals − elevation − rolling − inertia = "
              "aerodynamics). **Read the warnings**: on a short, slow or hilly segment the "
              "elevation weighs more than the air and the number is worthless."},
    "est_subir": {"es": "Actividad (.fit) con GPS y potencia",
                  "en": "Activity (.fit) with GPS and power"},
    "est_sube_fit": {
        "es": "Sube un .fit para empezar. Lo ideal: un tramo llano, rápido, sin tráfico y, mejor "
              "aún, el mismo tramo de ida y de vuelta para cancelar el viento.",
        "en": "Upload a .fit to start. Ideally a flat, fast stretch with no traffic and, better "
              "still, the same stretch out and back to cancel the wind."},
    "est_resumen_fit": {"es": "**{nombre}** · {km:.1f} km · {n} registros",
                        "en": "**{nombre}** · {km:.1f} km · {n} records"},
    "est_seccion_auto": {"es": "#### 1. Que lo busque la herramienta (recomendado)",
                         "en": "#### 1. Let the tool find them (recommended)"},
    "est_auto_nota": {
        "es": "Barre la actividad en ventanas de 1 a 5 km, se queda con los tramos llanos y "
              "rápidos, y para cada uno busca **la pasada de vuelta por la misma carretera**. "
              "Promediar ida y vuelta es la única forma de cancelar el viento sin modelarlo.",
        "en": "Sweeps the activity in windows of 1 to 5 km, keeps the flat and fast stretches, and "
              "for each one looks for **the return pass along the same road**. Averaging out and "
              "back is the only way to cancel the wind without modelling it."},
    "est_buscar": {"es": "🔍 Buscar tramos fiables", "en": "🔍 Find reliable stretches"},
    "est_buscando": {"es": "Barriendo la actividad…", "en": "Sweeping the activity…"},
    "est_sin_pares": {
        "es": "No he encontrado ningún tramo llano con su pasada de vuelta. Suele pasar en rutas "
              "que no repiten camino. Usa el recorrido completo como referencia o selecciona "
              "tramos a mano más abajo.",
        "en": "I found no flat stretch with a return pass. That is common on routes that never "
              "retrace their path. Use the whole ride as a reference or pick segments by hand "
              "below."},
    "est_m_pares": {"es": "CdA de ida y vuelta", "en": "Out-and-back CdA"},
    "est_m_completo": {"es": "en todo el recorrido", "en": "over the whole ride"},
    "est_m_n_pares": {"es": "pares", "en": "pairs"},
    "est_recomendado": {
        "es": "**Valor recomendado: {cda:.3f} ± {inc:.3f} m²**, la media de los pares de ida y "
              "vuelta. La incertidumbre es la dispersión entre pares, que es lo honesto: no "
              "sabemos explicarla toda.",
        "en": "**Recommended value: {cda:.3f} ± {inc:.3f} m²**, the mean of the out-and-back "
              "pairs. The uncertainty is the spread between pairs, which is the honest figure: we "
              "cannot explain all of it."},
    "est_pares_nota": {
        "es": "La columna `±` de cada par es la mitad de la diferencia entre ida y vuelta: **mide "
              "cuánto viento había**. La columna de viento lo traduce a una velocidad aproximada.",
        "en": "Each pair's `±` column is half the difference between out and back: it **measures "
              "how much wind there was**. The wind column turns that into an approximate speed."},
    "est_sueltos_titulo": {
        "es": "**Cada tramo por separado** (ida y vuelta de cada par, en una fila por tramo)",
        "en": "**Each stretch on its own** (out and back of every pair, one row per stretch)"},
    "est_ver_todas": {"es": "Ver todas las columnas", "en": "Show all columns"},
    "est_descargar_busqueda": {"es": "Descargar estos tramos (CSV)",
                               "en": "Download these stretches (CSV)"},
    "est_sesgo_medido": {
        "es": "**Sesgo de selección (medido):** los tramos encontrados van a {v_tramos:.1f} km/h "
              "frente a los {v_ruta:.1f} km/h de la ruta completa ({sesgo:+.1f} km/h), con una "
              "pendiente media de {pend:+.2f} %. Exigir velocidad alta y poco desnivel no da una "
              "muestra neutra, así que el sesgo existe siempre: lo que cambia de una actividad a "
              "otra es cuánto. Por eso manda el par de ida y vuelta, no el tramo suelto.",
        "en": "**Selection bias (measured):** the stretches found average {v_tramos:.1f} km/h "
              "against the {v_ruta:.1f} km/h of the whole ride ({sesgo:+.1f} km/h), with a mean "
              "gradient of {pend:+.2f} %. Requiring high speed and little climbing is not a "
              "neutral sample, so the bias is always there: what changes between activities is how "
              "much. That is why the out-and-back pair rules, not the single stretch."},
    "est_sesgo": {
        "es": "**Sesgo de selección, tenlo en cuenta:** los tramos encontrados van a "
              "{v_tramos:.1f} km/h de media frente a los {v_ruta:.1f} km/h de la ruta completa, "
              "con una pendiente media de {pend:+.2f} %. Exigir velocidad alta y poco desnivel no "
              "da una muestra neutra: tiende a elegir los tramos con viento a favor o bajada "
              "suave, y el CdA de un tramo suelto sale bajo. Por eso manda el par de ida y vuelta, "
              "no el tramo suelto.",
        "en": "**Selection bias, bear it in mind:** the stretches found average {v_tramos:.1f} "
              "km/h against the {v_ruta:.1f} km/h of the whole ride, with a mean gradient of "
              "{pend:+.2f} %. Demanding high speed and little elevation change is not a neutral "
              "sample: it tends to pick the stretches with a tailwind or a gentle descent, and a "
              "single stretch gives a low CdA. That is why the out-and-back pair rules, not the "
              "single stretch."},
    "est_aplicar_pares": {"es": "Aplicar este CdA en la barra lateral",
                          "en": "Apply this CdA in the sidebar"},
    "est_origen_pares": {"es": "estimado con {n} pares de ida y vuelta ({fichero})",
                         "en": "estimated from {n} out-and-back pairs ({fichero})"},
    "est_seccion_manual": {"es": "#### 2. O elige tú un segmento",
                           "en": "#### 2. Or pick a segment yourself"},
    "est_arrastra": {"es": "Arrastra sobre el gráfico para elegir el segmento, o ajústalo aquí:",
                     "en": "Drag on the chart to pick the segment, or set it here:"},
    "est_slider": {"es": "Segmento (km)", "en": "Segment (km)"},
    "est_estimar": {"es": "Estimar CdA en este segmento", "en": "Estimate CdA on this segment"},
    "est_g_altitud": {"es": "Altitud (m)", "en": "Altitude (m)"},
    "est_g_velocidad": {"es": "Velocidad (km/h)", "en": "Speed (km/h)"},
    "est_m_cda": {"es": "CdA del segmento", "en": "Segment CdA"},
    "est_utilizable": {"es": "Segmento utilizable. CdA entre **{a:.3f}** y **{b:.3f} m²**.",
                       "en": "Usable segment. CdA between **{a:.3f}** and **{b:.3f} m²**."},
    "est_no_utilizable": {
        "es": "**Segmento no utilizable**: el número de arriba no es de fiar. Mira los avisos.",
        "en": "**Segment not usable**: the number above cannot be trusted. Read the warnings."},
    "est_incert_titulo": {"es": "**De dónde viene la incertidumbre**",
                          "en": "**Where the uncertainty comes from**"},
    "est_f_altitud": {"es": "Altitud (±1 m en el desnivel)",
                      "en": "Altitude (±1 m in the elevation change)"},
    "est_f_crr": {"es": "Crr (±0,0005)", "en": "Crr (±0.0005)"},
    "est_f_potencia": {"es": "Potenciómetro (±1,5 %)", "en": "Power meter (±1.5 %)"},
    "est_f_total": {"es": "TOTAL (suma en cuadratura)", "en": "TOTAL (sum in quadrature)"},
    "est_f_viento": {"es": "Viento de 1 m/s — sesgo, NO incluido arriba",
                     "en": "1 m/s of wind — bias, NOT included above"},
    "est_col_fuente": {"es": "fuente", "en": "source"},
    "est_condiciones": {
        "es": "Parte aerodinámica de la energía disipada: {aero:.0f} % · sin pedalear: "
              "{sin_ped:.0f} % · densidad del aire: {rho:.3f} kg/m³",
        "en": "Aerodynamic share of the dissipated energy: {aero:.0f} % · not pedalling: "
              "{sin_ped:.0f} % · air density: {rho:.3f} kg/m³"},
    "est_lista_titulo": {"es": "**Segmentos que has estimado en esta sesión ({n})**",
                         "en": "**Segments you have estimated in this session ({n})**"},
    "est_lista_nota": {
        "es": "La columna aero es la parte aerodinámica de la energía disipada y «utilizable» "
              "resume si la fila se puede creer. El rumbo sirve para detectar el viento: si los "
              "tramos hacia un lado dan CdA bajo y los del contrario alto, eso es viento, no tu "
              "posición.",
        "en": "The aero column is the aerodynamic share of the dissipated energy and «usable» "
              "sums up whether the row can be believed. The bearing helps spot wind: if the "
              "stretches one way give a low CdA and those the other way a high one, that is wind, "
              "not your position."},
    "est_descargar_lista": {"es": "Descargar la tabla (CSV)", "en": "Download the table (CSV)"},
    "est_combinado": {
        "es": "**Combinado de {n} segmento(s) utilizable(s): {cda:.3f} ± {inc:.3f} m².** Si la "
              "dispersión entre segmentos es mayor que su incertidumbre, lo que estás viendo es "
              "viento: promedia ida y vuelta del mismo tramo.",
        "en": "**Combined from {n} usable segment(s): {cda:.3f} ± {inc:.3f} m².** If the spread "
              "between segments is larger than their uncertainty, what you are seeing is wind: "
              "average the same stretch out and back."},
    "est_aplicar_combinado": {"es": "Aplicar este CdA en la barra lateral",
                              "en": "Apply this CdA in the sidebar"},
    "est_origen_combinado": {"es": "estimado por balance de energía en {n} segmento(s)",
                             "en": "estimated by energy balance on {n} segment(s)"},
    "est_vaciar": {"es": "Vaciar la lista de segmentos", "en": "Clear the segment list"},
    "modelo_texto": {"es": """
**Modelo** (por tramo, balance de energía, potencia constante en el tramo):

`½·m_ef·(v₁² − v₀²) = d·(η·P/v̄ − ½·ρ·CdA(v̄)·⟨v²⟩ − Crr(v̄)·m·g·cosθ) − m·g·Δh`

- **CdA(v)**: posición aero + ΔCdA a baja velocidad con transición logística (continua). Lo que
  lleves puesto va dentro del CdA que introduces: no hay un parámetro aparte para la ropa.
- **Crr(v, p)** = (Crr_ref · (p_ref/p)^exp) + crr1·(v − 29 km/h) según superficie. El exponente de
  presión es una estimación por superficie, editable, y **no representa** el que por encima de
  cierta presión el firme rugoso se vuelva más lento.
- **Potencia por pendiente**: subida / llano / descenso con transición suave (smoothstep).
- **Límites**: tope de velocidad y límite por curvatura (√(a_lat/κ)) con frenada máxima hacia atrás.
- **Densidad del aire**: temperatura, humedad, presión (corregida con la altitud, ISA).
- **Masa**: un único valor total. El reparto entre ciclista y bici no entra en ninguna ecuación.
- **Rueda**: el perímetro sale de la medida ETRTO, o se introduce medido eligiendo «manual». Solo
  interviene en la inercia de rotación: su efecto en el tiempo es inferior al 0,001 %.

**Validado** con 5 salidas reales de la misma bici y ruta (128 km, 2200-2600 m): con un solo CdA
el error de tiempo se queda **dentro de ±2,5 % en las siete bandas de pendiente**, de −6 % a +6 %.
El punto flojo es la bajada de más del 6 %, donde lo que limita no es la física sino la frenada.

**Limitaciones**: sin viento, sin drafting, sin DEM; la pendiente depende de la calidad de la
elevación del GPX (la misma ruta mide entre 2179 y 2629 m de desnivel según el día, por ruido del
altímetro barométrico); el CdA es la mayor fuente de incertidumbre. No está verificada la
transferencia a **otra ruta**, y el viento del día puede añadir hasta un 13 % al tiempo.
Los exponentes de presión son estimaciones de orden de magnitud, no medidas tuyas: la pestaña
**Estimar CdA** sirve precisamente para medir lo tuyo.
""", "en": """
**Model** (per segment, energy balance, constant power within the segment):

`½·m_ef·(v₁² − v₀²) = d·(η·P/v̄ − ½·ρ·CdA(v̄)·⟨v²⟩ − Crr(v̄)·m·g·cosθ) − m·g·Δh`

- **CdA(v)**: aero position + ΔCdA at low speed with a logistic transition (continuous). Whatever
  you are wearing is inside the CdA you enter: there is no separate parameter for clothing.
- **Crr(v, p)** = (Crr_ref · (p_ref/p)^exp) + crr1·(v − 29 km/h) by surface. The pressure exponent
  is an estimate per surface, editable, and it **does not represent** the fact that above a certain
  pressure a rough surface becomes slower.
- **Power by gradient**: climb / flat / descent with a smooth (smoothstep) transition.
- **Limits**: speed cap and cornering limit (√(a_lat/κ)) with maximum braking propagated backwards.
- **Air density**: temperature, humidity, pressure (corrected with altitude, ISA).
- **Mass**: a single total value. How it splits between rider and bike enters no equation.
- **Wheel**: the circumference comes from the ETRTO size, or you enter a measured one by choosing
  «manual». It only enters the rotational inertia: its effect on time is below 0.001 %.

**Validated** against 5 real rides on the same bike and route (128 km, 2200-2600 m): with a single
CdA the time error stays **within ±2.5 % across all seven slope bands**, from −6 % to +6 %. The
weak spot is descents steeper than 6 %, where the limit is braking, not physics.

**Limitations**: no wind, no drafting, no DEM; the gradient depends on the quality of the GPX
elevation (the same route measures between 2179 and 2629 m of climbing depending on the day, from
barometric altimeter noise); the CdA is the largest source of uncertainty. Transfer to **another
route** is not verified, and the day's wind can add up to 13 % to the time. The pressure exponents
are order-of-magnitude estimates, not measurements of yours: the **Estimate CdA** tab is there
precisely to measure what is yours.
"""},
    # --- avisos del estimador (los genera el núcleo, pero el texto vive aquí)
    "aviso_corto": {
        "es": "Segmento corto ({d:.0f} m): por debajo de {min:.0f} m los errores de altitud "
              "dominan. Alarga la selección.",
        "en": "Short segment ({d:.0f} m): below {min:.0f} m the altitude errors dominate. Make "
              "the selection longer."},
    "aviso_breve": {
        "es": "Segmento breve ({t:.0f} s): mínimo recomendable {min:.0f} s.",
        "en": "Brief segment ({t:.0f} s): the recommended minimum is {min:.0f} s."},
    "aviso_lento": {
        "es": "Velocidad media baja ({v:.1f} km/h): la resistencia aerodinámica apenas pesa por "
              "debajo de {min:.0f} km/h y el CdA sale mal condicionado.",
        "en": "Low average speed ({v:.1f} km/h): aerodynamic drag barely matters below {min:.0f} "
              "km/h and the CdA comes out badly conditioned."},
    "aviso_poco_aero": {
        "es": "Solo el {pct:.0f} % de la energía disipada es aerodinámica: manda el desnivel o la "
              "rodadura. Busca un tramo más llano y rápido.",
        "en": "Only {pct:.0f} % of the dissipated energy is aerodynamic: elevation or rolling "
              "resistance dominates. Look for a flatter, faster stretch."},
    "aviso_desnivel": {
        "es": "Desnivel del segmento {dh:+.0f} m: en cuesta, un error de altitud se convierte "
              "directamente en error de CdA. Lo ideal es un tramo llano.",
        "en": "Segment elevation change {dh:+.0f} m: on a slope, an altitude error turns straight "
              "into a CdA error. A flat stretch is ideal."},
    "aviso_incertidumbre": {
        "es": "Incertidumbre ±{inc:.3f} m²: demasiada para sacar conclusiones (el umbral es "
              "±{max:.3f}).",
        "en": "Uncertainty ±{inc:.3f} m²: too much to draw conclusions (the threshold is "
              "±{max:.3f})."},
    "aviso_sin_pedalear": {
        "es": "El {pct:.0f} % del segmento va sin pedalear: la estimación depende entonces casi "
              "solo de la altitud, que es el dato menos fiable.",
        "en": "{pct:.0f} % of the segment is without pedalling: the estimate then depends almost "
              "entirely on the altitude, which is the least reliable input."},
    "aviso_implausible": {
        "es": "CdA estimado implausible ({cda:.3f} m²). Lo habitual es viento de cola, altitud "
              "mal medida o potencia mal registrada.",
        "en": "Implausible estimated CdA ({cda:.3f} m²). The usual causes are a tailwind, badly "
              "measured altitude or badly recorded power."},
    "aviso_viento": {
        "es": "Viento: {w:.0f} m/s ({wkmh:.0f} km/h) de frente o de cola mueven el CdA estimado "
              "±{sens:.3f} m², más que todos los demás errores juntos (±{inc:.3f}). Esa cifra NO "
              "está en la incertidumbre, porque no es ruido sino un sesgo: se quita promediando "
              "un tramo de ida con el mismo de vuelta.",
        "en": "Wind: {w:.0f} m/s ({wkmh:.0f} km/h) of head or tailwind moves the estimated CdA by "
              "±{sens:.3f} m², more than every other error put together (±{inc:.3f}). That figure "
              "is NOT in the uncertainty, because it is not noise but a bias: it goes away by "
              "averaging a stretch out and back."},

    # --- criterio 28: pares de ida y vuelta imposibles
    "est_par_rechazado": {
        "es": "Par descartado: {v_alta} km/h en un sentido y {v_baja} km/h en el otro "
              "(relación {razon}, límite {umbral}). Dos pasadas por la misma carretera llana no "
              "pueden diferir tanto: lo que el filtro ha dejado pasar es una bajada o una subida "
              "que el suavizado del altímetro aplanó.",
        "en": "Pair discarded: {v_alta} km/h one way and {v_baja} km/h the other "
              "(ratio {razon}, limit {umbral}). Two passes along the same flat road cannot differ "
              "that much: what got through the filter is a descent or a climb that altimeter "
              "smoothing flattened out."},
    "est_pares_rechazados_titulo": {
        "es": "Descartados por imposibles: {n}",
        "en": "Discarded as impossible: {n}"},

    # --- criterio 30: actividad incoherente
    "coh_titulo": {"es": "Coherencia de la actividad", "en": "Activity coherence"},
    "coh_ok": {
        "es": "Actividad coherente: el CdA calibrado ({cda:.3f} m²) es plausible y el error por "
              "banda de pendiente no muestra el patrón de una salida con viento o rebufo.",
        "en": "Coherent activity: the calibrated CdA ({cda:.3f} m²) is plausible and the error by "
              "slope band shows no sign of a windy or drafted ride."},
    "coh_cda_fuera": {
        "es": "El CdA calibrado con esta actividad ({cda:.3f} m²) cae fuera del rango plausible "
              "{bajo:.2f}–{alto:.2f} m². No es un dato aerodinámico: es el residuo de un ajuste "
              "que no cierra.",
        "en": "The CdA calibrated from this activity ({cda:.3f} m²) falls outside the plausible "
              "{bajo:.2f}–{alto:.2f} m² range. It is not an aerodynamic figure: it is the residue "
              "of a fit that does not close."},
    "coh_patron": {
        "es": "Patrón de salida más rápida de lo que permite la potencia registrada: el modelo va "
              "{llano:+.1f} % de tiempo en el llano y {bajada:+.1f} % en las bajadas. Las causas "
              "habituales son viento neto a favor, rebufo o grupo. La calibración por tiempo total "
              "baja el CdA hasta cuadrar el llano y rompe las bajadas.",
        "en": "Pattern of a ride faster than the recorded power allows: the model is "
              "{llano:+.1f} % on time over the flat and {bajada:+.1f} % on the descents. The usual "
              "causes are a net tailwind, drafting or a group. Calibrating on total time lowers "
              "CdA until the flat matches and breaks the descents."},
    "coh_no_calibrar": {
        "es": "No uses esta actividad para calibrar: metería el viento de su día en el parámetro. "
              "Sí sirve para medir cuánto cuesta no tener el viento como entrada.",
        "en": "Do not calibrate with this activity: it would bake that day's wind into the "
              "parameter. It is still useful to measure what missing wind data costs."},
    "coh_guardar_incoherente": {
        "es": "El CdA que estás a punto de guardar viene de una actividad marcada como "
              "incoherente. Revisa el aviso antes de fijarlo en un perfil de bici.",
        "en": "The CdA you are about to save comes from an activity flagged as incoherent. Check "
              "the warning before fixing it in a bike profile."},
    "coh_intro": {
        "es": "La calibración por tiempo total siempre devuelve un número, pero no dice si "
              "significa algo. Este examen separa el error por banda de pendiente y avisa si la "
              "actividad fue más rápida de lo que permite la potencia registrada —viento a favor, "
              "rebufo o grupo—, caso en el que el CdA que sale no es un dato aerodinámico.",
        "en": "Calibrating on total time always returns a number, but it does not say whether the "
              "number means anything. This check splits the error by slope band and warns when the "
              "activity was faster than the recorded power allows —tailwind, drafting or a group—, "
              "in which case the resulting CdA is not an aerodynamic figure."},
    "coh_examinar": {"es": "🔎 Examinar coherencia", "en": "🔎 Check coherence"},
    "coh_examinando": {"es": "Examinando {nombre}…", "en": "Checking {nombre}…"},
    "coh_csv": {"es": "⬇ Examen en CSV", "en": "⬇ Check as CSV"},
    "coh_resumen": {
        "es": "{n} de {total} actividades no sirven para calibrar. Déjalas fuera de la selección.",
        "en": "{n} of {total} activities are not fit for calibration. Leave them out of the "
              "selection."},
    # --- textos del informe de sensibilidad (los genera el núcleo)
    "sens_no_aplicable": {"es": "valor 0: no aplicable en variación relativa",
                          "en": "value 0: not applicable to a relative change"},
    "sens_a_principal": {"es": "candidato a pasar a la interfaz principal",
                         "en": "candidate to move to the main interface"},
    "sens_a_avanzado": {"es": "efecto < {umbral:g} % en esta ruta: candidato a avanzado",
                        "en": "effect < {umbral:g} % on this route: candidate for advanced"},
    "sens_principal": {"es": "principal", "en": "main"},
    "sens_avanzado": {"es": "avanzado", "en": "advanced"},
    "obligatorio": {"es": "Obligatorio", "en": "Required"},
    # --- errores de validación de parámetros (los lanza el núcleo, los muestra la interfaz)
    "err_opcion": {"es": "{campo}: «{valor}» no es válido (opciones: {opciones}).",
                   "en": "{campo}: «{valor}» is not valid (options: {opciones})."},
    "err_booleano": {"es": "{campo}: debe ser verdadero o falso.",
                     "en": "{campo}: must be true or false."},
    "err_obligatorio": {"es": "{campo}: es obligatorio.", "en": "{campo}: is required."},
    "err_no_numerico": {"es": "{campo}: valor no numérico ({valor}).",
                        "en": "{campo}: not a number ({valor})."},
    "err_no_finito": {"es": "{campo}: valor no finito.", "en": "{campo}: value is not finite."},
    "err_fuera_de_rango": {
        "es": "{campo}: {valor} {unidad} fuera de rango [{lo}, {hi}].",
        "en": "{campo}: {valor} {unidad} out of range [{lo}, {hi}]."},
    "err_perimetro_falta": {
        "es": "Medida de rueda «manual»: indica el perímetro medido en mm. Para medirlo, marca el "
              "suelo junto a la válvula, da una vuelta completa sentado en la bici y mide la "
              "distancia entre las dos marcas.",
        "en": "Wheel size set to «manual»: enter the measured circumference in mm. To measure it, "
              "mark the ground next to the valve, roll one full turn while sitting on the bike and "
              "measure the distance between the two marks."},
    "err_perimetro_sobra": {
        "es": "Has indicado un perímetro medido pero la medida de rueda no es «manual»: elige "
              "«manual» o borra el perímetro.",
        "en": "You entered a measured circumference but the wheel size is not «manual»: choose "
              "«manual» or clear the circumference."},
    "err_anchura_banda": {
        "es": "La anchura de la transición de potencia no puede superar el doble del umbral de "
              "pendiente (las bandas se solaparían).",
        "en": "The width of the power transition cannot exceed twice the gradient threshold (the "
              "bands would overlap)."},
    "err_tramo_forma": {
        "es": "Cada tramo de superficie debe ser (km_inicio, km_fin, superficie).",
        "en": "Each surface stretch must be (start_km, end_km, surface)."},
    "err_tramo_superficie": {"es": "Superficie «{valor}» no válida en tramos.",
                             "en": "Surface «{valor}» is not valid in stretches."},
    "err_tramo_rango": {"es": "Tramo de superficie inválido: {a}–{b} km.",
                        "en": "Invalid surface stretch: {a}–{b} km."},
    # --- avisos y errores de lectura del GPX
    "gpx_no_xml": {"es": "El archivo no es un GPX válido: {detalle}",
                   "en": "The file is not a valid GPX: {detalle}"},
    "gpx_formato": {"es": "No se pudo leer el GPX: formato de entrada no reconocido.",
                    "en": "Could not read the GPX: unrecognised input format."},
    "gpx_sin_puntos": {"es": "El GPX no contiene al menos 2 puntos de ruta.",
                       "en": "The GPX does not contain at least 2 route points."},
    "gpx_sin_coordenadas": {
        "es": "Se descartaron {n} puntos sin coordenadas válidas.",
        "en": "{n} points without valid coordinates were discarded."},
    "gpx_sin_elevacion": {
        "es": "El GPX no contiene elevación: se asume ruta plana (0 m).",
        "en": "The GPX has no elevation: the route is assumed flat (0 m)."},
    "gpx_elevacion_interpolada": {
        "es": "Se interpolaron {n} puntos sin elevación.",
        "en": "{n} points without elevation were interpolated."},
    "gpx_ruta_corta": {"es": "La ruta es demasiado corta para simular.",
                       "en": "The route is too short to simulate."},
    "simulando": {"es": "Simulando…", "en": "Simulating…"},
    "celda_si": {"es": "sí", "en": "yes"},
    "celda_no": {"es": "no", "en": "no"},
    "celda_no_enfatico": {"es": "NO", "en": "NO"},
    "sens_col_menos": {"es": "Δt −10 % (%)", "en": "Δt −10 % (%)"},
    "sens_col_mas": {"es": "Δt +10 % (%)", "en": "Δt +10 % (%)"},

    "coh_cal_con_malas": {
        "es": "Has calibrado incluyendo actividades marcadas como incoherentes ({lista}). Ese CdA "
              "lleva dentro el viento de esos días.",
        "en": "You calibrated including activities flagged as incoherent ({lista}). That CdA has "
              "those days' wind baked into it."},
# --- criterio 31: los dos módulos
    "sens_no_numerico": {
        "es": "No es un número: no se puede variar un ±10 %. Sí puede mover el tiempo: cámbialo a "
              "mano y vuelve a simular para ver cuánto.",
        "en": "Not a number: it cannot be varied by ±10 %. It can still move the time: change it "
              "by hand and simulate again to see by how much."},
    "sens_no_perturbable": {
        "es": "No se ha podido variar: los dos valores perturbados quedan fuera de lo admitido "
              "para esta configuración.",
        "en": "Could not be varied: both perturbed values fall outside what this configuration "
              "accepts."},
    "sens_sin_efecto": {
        "es": "No entra en el tiempo: o no lo usa el modelo o solo escala una métrica derivada.",
        "en": "Does not enter the time: either the model does not use it or it only scales a "
              "derived metric."},
    "sens_superficie_inactiva": {
        "es": "La superficie «{sup}» no se usa en esta ruta.",
        "en": "Surface «{sup}» is not used on this route."},
    "sens_sin_valor": {
        "es": "Opcional y sin valor: no hay nada que variar.",
        "en": "Optional and empty: there is nothing to vary."},
    "sens_presion_de_referencia": {
        "es": "La presión de neumáticos es la de referencia, así que el factor de presión vale 1 "
              "y el exponente no interviene.",
        "en": "Tyre pressure equals the reference pressure, so the pressure factor is 1 and the "
              "exponent plays no part."},
    "sens_efecto_nulo": {
        "es": "Efecto nulo en esta ruta (medido, no supuesto).",
        "en": "No effect on this route (measured, not assumed)."},
    "est_desfasado": {
        "es": "Has cambiado parámetros desde que se calculó este CdA. Vuelve a pulsar «Buscar "
              "tramos fiables» para rehacerlo con los valores de ahora.",
        "en": "You changed parameters after this CdA was computed. Press «Find reliable stretches» "
              "again to redo it with the current values."},
    "est_pie_aero": {"es": "aerodinámico", "en": "aerodynamic"},
    "etrto_manual": {"es": "manual · introduzco el perímetro medido",
                     "en": "manual · I enter the measured circumference"},
    "modulo": {"es": "Qué quieres hacer", "en": "What do you want to do"},
    "modulo_estimador": {"es": "Medir mi CdA", "en": "Measure my CdA"},
    "modulo_simulador": {"es": "Predecir una carrera", "en": "Predict a race"},
    "cab_estimador": {"es": "Estimador de CdA", "en": "CdA estimator"},
    "cab_estimador_sub": {
        "es": "Sube una actividad con potencia y GPS. La herramienta busca los tramos llanos "
              "donde la medida es fiable, los empareja de ida y vuelta para cancelar el viento, y "
              "te da el CdA de esa bici con esa posición. No hace falta ningún recorrido.",
        "en": "Upload an activity with power and GPS. The tool finds the flat stretches where the "
              "measurement holds up, pairs them out and back to cancel the wind, and gives you the "
              "CdA of that bike in that position. No route needed."},
    "cab_simulador": {"es": "Predicción de carrera", "en": "Race prediction"},
    "cab_simulador_sub": {
        "es": "Sube el recorrido de la competición y di qué potencia piensas sostener. El CdA "
              "puedes traerlo del estimador y ajustarlo a mano si tu montaje de carrera no es "
              "exactamente el que medisteis.",
        "en": "Upload the race route and say what power you plan to hold. You can bring the CdA "
              "over from the estimator and adjust it by hand if your race setup is not exactly "
              "the one you measured."},
    "pie_resumen_estimador": {
        "es": "Masa {masa:.1f} kg · rueda {etrto} ({per:.0f} mm). El CdA es la salida de este "
              "módulo, no una entrada.",
        "en": "Mass {masa:.1f} kg · wheel {etrto} ({per:.0f} mm). CdA is this module's output, "
              "not an input."},
    "cda_viene_del_estimador": {
        "es": "El CdA de abajo viene del estimador ({origen}). Puedes usarlo tal cual o "
              "corregirlo a mano.",
        "en": "The CdA below comes from the estimator ({origen}). Use it as it is or correct it "
              "by hand."},
    "est_aplicar_ayuda": {
        "es": "Lleva este CdA al simulador, donde queda como un valor editable.",
        "en": "Takes this CdA to the simulator, where it stays editable."},

    # --- criterio 32: lecturas y bandas
    # El margen de cabecera lleva **el nombre de su banda**. Sin él, el ± que acompaña a la cifra
    # grande se lee como la precisión esperable de esa predicción, y en el GPX de una carrera
    # —que es el caso de uso— esa precisión no está medida: es la de la ruta de calibración.
    "banda_margen": {"es": "{min} ({pct:.1f} %) — modelo, misma ruta",
                     "en": "{min} ({pct:.1f} %) — model, same route"},
    "banda_leyenda_modelo": {"es": "modelo ±{pct:.1f} %", "en": "model ±{pct:.1f} %"},
    # La banda del día **está medida** (peor caso real de las cinco salidas): lo que la distingue
    # de la del modelo es que su anchura depende del viento, que la herramienta no conoce. Decía
    # «sin verificar», contradiciendo al núcleo, al criterio 29 y al pie de la misma pantalla.
    "banda_leyenda_dia": {"es": "día ±{pct:.0f} %, viento desconocido",
                          "en": "day ±{pct:.0f} %, wind unknown"},
    "est_lectura_cab": {"es": "CdA de esta bici en esta posición",
                        "en": "CdA of this bike in this position"},
    "est_banda_medida": {"es": "medido ±{inc:.3f}", "en": "measured ±{inc:.3f}"},
    "est_banda_viento": {"es": "viento 1 m/s ±{sens:.3f}, sin medir",
                         "en": "wind 1 m/s ±{sens:.3f}, not measured"},
    "est_pie_descartados": {"es": "descartados", "en": "discarded"},
    "est_pie_velocidad": {"es": "en los tramos", "en": "on the stretches"},

    # --- pantallas vacías: dicen qué hacer
    "est_vacio_titulo": {"es": "Sube una actividad para empezar",
                         "en": "Upload an activity to start"},
    "est_vacio_texto": {
        "es": "Un fichero .fit con potencia y GPS. Lo mejor es una salida con el montaje y la "
              "posición que vas a llevar en carrera, y con algún tramo llano recorrido en los dos "
              "sentidos.",
        "en": "A .fit file with power and GPS. Best is a ride with the setup and position you will "
              "race in, including some flat stretch ridden in both directions."},
    "sim_vacio_titulo": {"es": "Listo para simular", "en": "Ready to simulate"},
    "sim_vacio_texto": {
        "es": "Revisa los parámetros de la izquierda y pulsa Simular.",
        "en": "Check the parameters on the left and press Simulate."},
    "sim_vacio_demo": {
        "es": "No has subido ningún recorrido, así que se usará una ruta de ejemplo. Súbela a la "
              "izquierda cuando quieras predecir la tuya, y pulsa Simular.",
        "en": "You have not uploaded a route, so an example one will be used. Upload yours on the "
              "left when you want to predict it, and press Simulate."},
    "val_vacio_titulo": {"es": "Sube las actividades a comparar",
                         "en": "Upload the activities to compare"},
    "val_vacio_texto": {
        "es": "Con dos o más .fit de la misma bici y ruta puedes calibrar con unas y comprobar el "
              "error en las otras. Antes, pasa cada una por el examen de coherencia.",
        "en": "With two or more .fit files from the same bike and route you can calibrate on some "
              "and check the error on the others. First, run each through the coherence check."},
}


def t(clave: str, idioma: str = IDIOMA_POR_DEFECTO, **formato) -> str:
    """Cadena de interfaz. Una clave desconocida se devuelve tal cual, para que se vea."""
    entrada = UI.get(clave)
    if entrada is None:
        return clave
    texto = entrada[normaliza(idioma)]
    return texto.format(**formato) if formato else texto
