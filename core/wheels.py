"""Tamaño de rueda por medida ETRTO.

La medida ETRTO se escribe `ancho-diámetro_de_llanta` en milímetros: `25-622` es un neumático de
25 mm sobre una llanta de 622 mm de diámetro de asiento (lo que se llama 700x25C).

El perímetro se calcula con la geometría nominal, suponiendo sección circular:

    perímetro = π · (diámetro_de_llanta + 2 · ancho)

Para 25-622 salen 2 111 mm. Las tablas de perímetro de rodadura de los ciclocomputadores dan
2 105 mm para esa medida, un 0,3 % menos, porque el neumático se deforma bajo carga y su sección
no es exactamente circular. **Esa diferencia es irrelevante aquí**: el radio de rueda solo entra en
la inercia de rotación `m_ef = m + I/r²`, y medido sobre una ruta real mover el radio de 0,300 a
0,370 m cambia el tiempo total menos del 0,001 %. El selector existe para no tener que introducir
un radio en metros, no porque mejore la predicción.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

#: (ETRTO, nombre comercial en español, nombre comercial en inglés). El orden es el que ve el
#: usuario en el desplegable. La parte comercial **sí se traduce** (criterio 27): hasta octubre de
#: 2026 los 21 nombres salían en castellano con la interfaz en inglés («carretera / triatlón»),
#: y el docstring de `label_for` afirmaba lo contrario. El código ETRTO es normativo y no cambia.
ETRTO_SIZES: Tuple[Tuple[str, str, str], ...] = (
    ("23-622", "700x23C — carretera", "700x23C — road"),
    ("25-622", "700x25C — carretera (lo más común)", "700x25C — road (the most common)"),
    ("28-622", "700x28C — carretera / triatlón", "700x28C — road / triathlon"),
    ("30-622", "700x30C", "700x30C"),
    ("32-622", "700x32C — gravel ligero", "700x32C — light gravel"),
    ("35-622", "700x35C — gravel", "700x35C — gravel"),
    ("40-622", "700x40C — gravel", "700x40C — gravel"),
    ("45-622", "700x45C — gravel ancho", "700x45C — wide gravel"),
    ("50-622", "29x2.0 — MTB", "29x2.0 — MTB"),
    ("54-622", "29x2.1 — MTB", "29x2.1 — MTB"),
    ("57-622", "29x2.25 — MTB", "29x2.25 — MTB"),
    ("23-571", "650x23C — carretera pequeña", "650x23C — small road"),
    ("25-571", "650x25C", "650x25C"),
    ("28-571", "650x28C", "650x28C"),
    ("40-584", "650Bx40 — gravel", "650Bx40 — gravel"),
    ("47-584", "27.5x1.9 — MTB", "27.5x1.9 — MTB"),
    ("54-584", "27.5x2.1 — MTB", "27.5x2.1 — MTB"),
    ("50-559", "26x2.0 — MTB", "26x2.0 — MTB"),
    ("54-559", "26x2.1 — MTB", "26x2.1 — MTB"),
    ("28-406", "20x1.1 — plegable / contrarreloj pequeña",
     "20x1.1 — folding / small time trial"),
    ("25-451", "20x1 — plegable", "20x1 — folding"),
)

#: ETRTO por defecto (700x28C).
DEFAULT_ETRTO = "28-622"
#: Valor especial del selector: el usuario introduce el perímetro que ha medido.
ETRTO_MANUAL = "manual"

_POR_CODIGO: Dict[str, Dict[str, str]] = {
    code: {"es": es, "en": en} for code, es, en in ETRTO_SIZES}


def etrto_codes() -> Tuple[str, ...]:
    return tuple(code for code, _, _ in ETRTO_SIZES)


def etrto_labels(idioma: str = "es") -> Tuple[str, ...]:
    """Etiquetas para el desplegable: «25-622 · 700x25C — carretera (lo más común)»."""
    return tuple(label_for(code, idioma) for code in etrto_codes())


def label_for(code: str, idioma: str = "es") -> str:
    """Etiqueta del desplegable. Los códigos ETRTO son normativos y no se traducen; el texto
    que los acompaña sí (criterio 27)."""
    from .i18n import normaliza, t

    if code == ETRTO_MANUAL:
        return t("etrto_manual", idioma)
    nombres = _POR_CODIGO.get(code)
    if not nombres:
        return code
    return f"{code} · {nombres.get(normaliza(idioma), nombres['es'])}"


def code_from_label(label: str) -> str:
    return label.split(" · ")[0].strip()


def parse_etrto(code: str) -> Tuple[float, float]:
    """Devuelve (ancho_mm, diámetro_de_llanta_mm). Acepta «25-622» y «25/622»."""
    texto = str(code).strip().replace("/", "-")
    partes = texto.split("-")
    if len(partes) != 2:
        raise ValueError(f"Medida ETRTO no reconocida: {code!r} (formato: ancho-llanta, p. ej. 25-622)")
    try:
        ancho, llanta = float(partes[0]), float(partes[1])
    except ValueError:
        raise ValueError(f"Medida ETRTO no numérica: {code!r}")
    if not (15.0 <= ancho <= 110.0) or not (200.0 <= llanta <= 700.0):
        raise ValueError(f"Medida ETRTO fuera de lo plausible: {code!r}")
    return ancho, llanta


def circumference_m(code: str) -> float:
    """Perímetro nominal en metros."""
    ancho, llanta = parse_etrto(code)
    return math.pi * (llanta + 2.0 * ancho) / 1000.0


def circumference_mm(code: str) -> float:
    return circumference_m(code) * 1000.0


def radius_m(code: str) -> float:
    """Radio exterior nominal en metros (lo que usa la inercia de rotación)."""
    ancho, llanta = parse_etrto(code)
    return (llanta + 2.0 * ancho) / 2000.0
