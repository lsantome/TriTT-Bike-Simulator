"""Perfiles de bici: guardar y recuperar los parámetros calibrados de cada montura.

Un perfil guarda lo que es propio de la bici y del ciclista (masas, CdA, Crr, eficiencia) para
no recalibrar en cada sesión, junto con el **origen** del CdA: de qué salidas sale y si se
calibró o se estimó. Sin ese origen un CdA guardado es un número sin trazabilidad.

Almacenamiento: un único JSON. Ruta por defecto `perfiles_bici.json` en la raíz del proyecto,
sobreescribible con la variable de entorno `SIMCICLISMO_PERFILES` (los tests la usan).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from .params import ParamError, Params

#: Parámetros que un perfil de bici fija. El resto (potencias, meteorología, ruta) no es de la bici.
PROFILE_KEYS = ("masa_total", "cda", "delta_cda", "eficiencia",
                "crr_liso", "crr_normal", "crr_rugoso", "superficie",
                "presion_neumaticos", "etrto", "perimetro_mm", "inercia_ruedas")

_ENV_VAR = "SIMCICLISMO_PERFILES"
_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "perfiles_bici.json"


@dataclass
class BikeProfile:
    nombre: str
    masa_total: float
    cda: float
    delta_cda: float
    eficiencia: float
    crr_liso: float
    crr_normal: float
    crr_rugoso: float
    superficie: str
    presion_neumaticos: float
    etrto: str
    inercia_ruedas: float
    perimetro_mm: Optional[float] = None
    origen_cda: str = "sin calibrar (valor por defecto)"
    calibrado: bool = False
    actualizado: str = field(default_factory=lambda: date.today().isoformat())

    def as_dict(self) -> dict:
        return asdict(self)


def profiles_path() -> Path:
    """Ruta del JSON de perfiles (configurable con SIMCICLISMO_PERFILES)."""
    env = os.environ.get(_ENV_VAR)
    return Path(env) if env else _DEFAULT_PATH


def profile_from_params(nombre: str, params: Params, *, origen_cda: str = "",
                        calibrado: bool = False) -> BikeProfile:
    """Extrae de unos parámetros lo que pertenece a la bici."""
    nombre = (nombre or "").strip()
    if not nombre:
        raise ParamError("El perfil necesita un nombre.")
    origen_cda = (origen_cda or "").strip()
    if calibrado and not origen_cda:
        # la trazabilidad es parte del criterio: un CdA "calibrado" sin decir de dónde sale
        # no se puede auditar después, así que no se admite ni desde el núcleo
        raise ParamError("Un CdA marcado como calibrado necesita su origen: "
                         "indica de qué actividades sale.")
    datos = {k: getattr(params, k) for k in PROFILE_KEYS}
    extra = {}
    if origen_cda:
        extra["origen_cda"] = origen_cda
    return BikeProfile(nombre=nombre, calibrado=bool(calibrado), **datos, **extra)


def apply_profile(params: Params, profile: BikeProfile) -> Params:
    """Devuelve los parámetros con los valores del perfil aplicados (el resto intacto)."""
    return params.con(**{k: getattr(profile, k) for k in PROFILE_KEYS})


def load_profiles(path: Optional[Path] = None) -> Dict[str, BikeProfile]:
    """Lee el JSON de perfiles. Si no existe o está corrupto, devuelve un diccionario vacío."""
    p = Path(path) if path else profiles_path()
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    validos = {f.name for f in fields(BikeProfile)}
    out: Dict[str, BikeProfile] = {}
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        datos = {k: v for k, v in item.items() if k in validos}
        try:
            prof = BikeProfile(**datos)
        except TypeError:
            continue              # perfil incompleto de una versión anterior: se ignora
        if prof.calibrado and not (prof.origen_cda or "").strip():
            # editado a mano o escrito por una versión anterior: se degrada, no se cree
            prof.calibrado = False
            prof.origen_cda = "sin calibrar (el perfil guardado no indicaba su origen)"
        out[prof.nombre] = prof
    return out


def _write(profiles: Dict[str, BikeProfile], path: Optional[Path] = None) -> Path:
    p = Path(path) if path else profiles_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    datos = [prof.as_dict() for prof in sorted(profiles.values(), key=lambda x: x.nombre.lower())]
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)                # escritura atómica: un fallo no deja el JSON a medias
    return p


def save_profile(profile: BikeProfile, path: Optional[Path] = None) -> Path:
    """Guarda (o reemplaza) un perfil por nombre."""
    profiles = load_profiles(path)
    profile.actualizado = date.today().isoformat()
    profiles[profile.nombre] = profile
    return _write(profiles, path)


def delete_profile(nombre: str, path: Optional[Path] = None) -> bool:
    """Borra un perfil. Devuelve True si existía."""
    profiles = load_profiles(path)
    if nombre not in profiles:
        return False
    del profiles[nombre]
    _write(profiles, path)
    return True


def profile_names(path: Optional[Path] = None) -> List[str]:
    return sorted(load_profiles(path), key=str.lower)
