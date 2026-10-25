"""Núcleo del simulador de ciclismo (triatlón sin drafting y CRI)."""
from .params import (CATEGORIES, PARAM_SPECS, REQUIRED_PARAMS, SPEC_BY_KEY, SURFACES, ParamError, Params,
                     specs_by_category, validate_params)
from .profiles import (BikeProfile, PROFILE_KEYS, apply_profile, delete_profile, load_profiles,
                       profile_from_params, profile_names, profiles_path, save_profile)
from .wheels import ETRTO_MANUAL
from .uncertainty import Band, band_dia, band_modelo, bands, with_bands
from .route import Profile, TrackData, build_profile, parse_gpx, track_from_arrays
from .simulate import SimResult, simulate, simulate_track, table_by_km
from .coherence import CoherenceReport, check_coherence

__all__ = [
    "CATEGORIES", "PARAM_SPECS", "REQUIRED_PARAMS", "SPEC_BY_KEY", "SURFACES", "ParamError", "Params",
    "specs_by_category", "validate_params", "Profile", "TrackData", "build_profile",
    "parse_gpx", "track_from_arrays", "SimResult", "simulate", "simulate_track", "table_by_km",
    "BikeProfile", "PROFILE_KEYS", "apply_profile", "delete_profile", "load_profiles",
    "profile_from_params", "profile_names", "profiles_path", "save_profile",
    "ETRTO_MANUAL", "Band", "band_dia", "band_modelo", "bands", "with_bands",
    "CoherenceReport", "check_coherence",
]
