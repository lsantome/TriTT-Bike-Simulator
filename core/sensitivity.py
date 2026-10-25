"""Análisis de sensibilidad: efecto en el tiempo total de variar cada parámetro ±10 %."""
from __future__ import annotations

from typing import Dict, List

from .i18n import IDIOMA_POR_DEFECTO, categoria as categoria_label, param_label, t
from .params import PARAM_SPECS, Params
from .route import TrackData, build_profile
from .simulate import simulate

RELEVANCE_THRESHOLD_PCT = 0.2   # un parámetro es "relevante" si cambia el tiempo >= 0,2 %


def _active_surfaces(p: Params) -> set:
    act = {p.superficie}
    for _, _, sup in p.tramos_superficie:
        act.add(sup)
    return act


def sensitivity(track: TrackData, params: Params, delta: float = 0.10, idioma: str = IDIOMA_POR_DEFECTO) -> List[Dict]:
    """Devuelve **una fila por parámetro**, con su efecto sobre el tiempo total o el motivo de
    que no lo tenga.

    Cada parámetro se perturba de forma literal: valor·(1 ± delta), recortado a su rango
    válido (si se recorta, `variacion_aplicada_%` lo refleja). Los parámetros con valor 0 no
    se pueden perturbar en términos relativos y se marcan como no aplicables.

    **Las exclusiones se declaran, no se callan** (corregido tras la revisión del 6-oct-2026). El
    informe omitía en silencio los parámetros no numéricos, los marcados sin sensibilidad y los Crr
    de superficies que esa ruta no usa, de modo que el criterio 12 —«lista el efecto de cada
    parámetro»— se cumplía solo sobre los que quedaban. Ahora salen todos, y los que no se pueden
    perturbar traen su motivo en `nota`.
    """
    base = simulate(build_profile(track, params), params)
    t0 = base.tiempo_s
    active = _active_surfaces(params)
    rows: List[Dict] = []
    vacia = {"valor_menos": None, "valor_mas": None, "dt_menos_%": None, "dt_mas_%": None,
             "variacion_menos_%": None, "variacion_mas_%": None, "variacion_aplicada_%": None,
             "elasticidad": None, "efecto_max_%": 0.0, "relevante": False}
    for s in PARAM_SPECS:
        cabecera = {"parametro": s.key, "etiqueta": param_label(s, idioma),
                    "categoria": categoria_label(s.category, idioma), "unidad": s.unit}
        # --- exclusiones, declaradas con su motivo.
        # Hasta octubre de 2026 la primera comprobación era `s.kind != "float"`, así que `ftp`,
        # `densidad_manual` y `perimetro_mm` —que son `optional_float`— salían con el motivo «No es
        # un número», que es falso cuando el usuario les ha dado valor. Y la bandera
        # `sensitivity=False` se usaba para excluir, con un motivo genérico que tapaba tres casos
        # distintos: «no entra en el tiempo» (ftp), «no se puede variar un ±10 %» (los parámetros
        # categóricos, que **sí** mueven el tiempo) y «sustituye a un cálculo» (densidad manual).
        # Ahora todo lo que sea numérico y tenga valor **se mide**: un efecto medido de 0,0000 es
        # mejor información que una excusa, y ya no hay forma de equivocarse en el motivo.
        valor = getattr(params, s.key)
        motivo = None
        if s.kind not in ("float", "optional_float"):
            motivo = t("sens_no_numerico", idioma)
        elif valor is None:
            motivo = t("sens_sin_valor", idioma)
        elif s.key.startswith(("crr_", "crr1_")) and s.key.split("_")[-1] not in active:
            motivo = t("sens_superficie_inactiva", idioma, sup=s.key.split("_")[-1])
        if motivo is not None:
            rows.append({**cabecera, "valor_base": valor, **vacia, "nota": motivo})
            continue
        v0 = float(valor)
        row = {**cabecera, "valor_base": v0}
        if v0 == 0.0:
            row.update({**vacia, "nota": t("sens_no_aplicable", idioma)})
            rows.append(row)
            continue
        lo = min(max(v0 * (1 - delta), s.minimum), s.maximum)
        hi = min(max(v0 * (1 + delta), s.minimum), s.maximum)
        out = {}
        for tag, val in (("menos", lo), ("mas", hi)):
            try:
                p2 = params.con(**{s.key: val})
                r = simulate(build_profile(track, p2), p2)
                out[tag] = (val, (r.tiempo_s - t0) / t0 * 100.0)
            except Exception:      # parámetro inválido tras perturbar
                out[tag] = (val, None)
        d_m, d_p = out["menos"][1], out["mas"][1]
        eff = max(abs(x) for x in (d_m, d_p) if x is not None) if (d_m is not None or d_p is not None) else 0.0
        applied = max(abs(lo - v0), abs(hi - v0)) / abs(v0) * 100.0
        el = None
        if d_m is not None and d_p is not None and hi != lo:
            el = ((d_p - d_m) / ((hi - lo) / v0 * 100.0))
        if d_m is None and d_p is None:
            nota = t("sens_no_perturbable", idioma)
        elif eff > 0.0:
            nota = ""
        elif s.key.startswith("crr_exp_") and params.presion_neumaticos == params.presion_referencia:
            nota = t("sens_presion_de_referencia", idioma)
        else:
            nota = t("sens_efecto_nulo", idioma)
        row.update({"valor_menos": lo, "valor_mas": hi, "dt_menos_%": d_m, "dt_mas_%": d_p,
                    "variacion_menos_%": (lo - v0) / abs(v0) * 100.0,
                    "variacion_mas_%": (hi - v0) / abs(v0) * 100.0,
                    "variacion_aplicada_%": applied, "elasticidad": el, "efecto_max_%": eff,
                    "relevante": eff >= RELEVANCE_THRESHOLD_PCT, "nota": nota})
        rows.append(row)
    spec_adv = {sp.key: sp.advanced for sp in PARAM_SPECS}
    for r in rows:
        avanzado = spec_adv[r["parametro"]]
        r["interfaz"] = t("sens_avanzado" if avanzado else "sens_principal", idioma)
        # La sugerencia solo tiene sentido sobre filas **medidas**: una fila excluida tiene
        # `efecto_max_% = 0` porque nadie la midió, no porque su efecto sea pequeño, y hasta
        # octubre de 2026 recibía igualmente el «candidato a avanzado».
        medida = r["dt_menos_%"] is not None or r["dt_mas_%"] is not None
        if not medida:
            r["sugerencia"] = ""
        elif r["relevante"] and avanzado:
            r["sugerencia"] = t("sens_a_principal", idioma)
        elif not r["relevante"] and not avanzado:
            r["sugerencia"] = t("sens_a_avanzado", idioma, umbral=RELEVANCE_THRESHOLD_PCT)
        else:
            r["sugerencia"] = ""
    rows.sort(key=lambda r: -r["efecto_max_%"])
    return rows
