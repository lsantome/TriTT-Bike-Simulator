"""Criterios 15 (perfiles de bici) y 16 (incertidumbre a la vista)."""
import json

import pytest

from core import Params
from core.params import ParamError
from core.profiles import (PROFILE_KEYS, apply_profile, delete_profile, load_profiles,
                           profile_from_params, profile_names, profiles_path, save_profile)
from core.uncertainty import (AVISO_RUTA_NUEVA, DIA_PCT, MODELO_PCT, PEOR_ERROR_DIA_PCT,
                              PEOR_ERROR_MODELO_PCT, SUFIJOS, band_dia, band_modelo, bands,
                              with_bands)


@pytest.fixture(autouse=True)
def perfiles_aislados(tmp_path, monkeypatch):
    """Cada test escribe en su propio JSON: nunca se toca el del usuario."""
    destino = tmp_path / "perfiles_bici.json"
    monkeypatch.setenv("SIMCICLISMO_PERFILES", str(destino))
    assert profiles_path() == destino
    return destino


# --------------------------------------------------------------------------- criterio 15
def test_c15_guardar_y_recuperar_un_perfil_conserva_los_valores_de_la_bici():
    p = Params(masa_total=90.0, cda=0.2688, eficiencia=0.97,
               crr_normal=0.0050, superficie="liso")
    prof = profile_from_params("Cervélo P5", p, origen_cda="2 salidas 30-mar y 06-abr-2025",
                               calibrado=True)
    save_profile(prof)

    recuperado = load_profiles()["Cervélo P5"]
    for k in PROFILE_KEYS:
        assert getattr(recuperado, k) == pytest.approx(getattr(p, k)) if isinstance(
            getattr(p, k), float) else getattr(recuperado, k) == getattr(p, k)
    assert recuperado.calibrado and "30-mar" in recuperado.origen_cda
    assert recuperado.masa_total == pytest.approx(90.0)


def test_c15_aplicar_un_perfil_cambia_la_bici_y_no_el_resto():
    base = Params(masa_total=78.0, cda=0.30, p_subida=300.0,
                  temperatura=25.0, velocidad_maxima=80.0)
    prof = profile_from_params("otra", Params(masa_total=90.0, cda=0.2688))
    nuevo = apply_profile(base, prof)
    assert nuevo.cda == pytest.approx(0.2688) and nuevo.masa_total == pytest.approx(90.0)
    # lo que no es de la bici no se toca
    assert nuevo.p_subida == 300.0 and nuevo.temperatura == 25.0 and nuevo.velocidad_maxima == 80.0


def test_c15_el_perfil_registra_el_origen_del_cda_y_por_defecto_no_esta_calibrado():
    prof = profile_from_params("sin calibrar", Params(masa_total=85.0))
    assert prof.calibrado is False and "sin calibrar" in prof.origen_cda.lower()
    assert prof.actualizado                      # fecha de actualización siempre presente


def test_c15_guardar_reemplaza_por_nombre_y_borrar_funciona():
    p = Params(masa_total=90.0)
    save_profile(profile_from_params("bici", p.con(cda=0.27)))
    save_profile(profile_from_params("bici", p.con(cda=0.25)))
    assert profile_names() == ["bici"]
    assert load_profiles()["bici"].cda == pytest.approx(0.25)
    assert delete_profile("bici") is True
    assert delete_profile("bici") is False and profile_names() == []


def test_c15_el_nucleo_rechaza_un_cda_calibrado_sin_origen():
    """La trazabilidad no puede depender solo de la interfaz: el núcleo también la exige."""
    p = Params(masa_total=90.0)
    with pytest.raises(ParamError):
        profile_from_params("bici", p, calibrado=True)
    with pytest.raises(ParamError):
        profile_from_params("bici", p, origen_cda="   ", calibrado=True)
    # con origen sí se admite
    assert profile_from_params("bici", p, origen_cda="2 salidas de abril", calibrado=True).calibrado


def test_c15_un_perfil_editado_a_mano_como_calibrado_sin_origen_se_degrada(perfiles_aislados):
    """Si alguien edita el JSON y marca calibrado:true sin origen, no se le cree."""
    perfiles_aislados.write_text(json.dumps([{
        "nombre": "manipulada", "masa_total": 90.0, "cda": 0.25,
        "delta_cda": 0.25, "eficiencia": 0.975, "crr_liso": 0.0035, "crr_normal": 0.0045,
        "crr_rugoso": 0.007, "superficie": "normal", "presion_neumaticos": 7.0,
        "etrto": "28-622", "inercia_ruedas": 0.14,
        "perimetro_mm": None, "origen_cda": "", "calibrado": True}]), encoding="utf-8")
    prof = load_profiles()["manipulada"]
    assert prof.calibrado is False and "sin calibrar" in prof.origen_cda.lower()


def test_c15_nombre_vacio_se_rechaza():
    with pytest.raises(ParamError):
        profile_from_params("   ", Params())


def test_c15_un_json_corrupto_o_incompleto_no_rompe_la_app(perfiles_aislados):
    perfiles_aislados.write_text("{no es json", encoding="utf-8")
    assert load_profiles() == {}
    perfiles_aislados.write_text(json.dumps([{"nombre": "incompleto", "cda": 0.3}]), encoding="utf-8")
    assert load_profiles() == {}                 # le faltan campos: se ignora, no revienta


def test_c15_guardado_atomico_no_deja_restos(perfiles_aislados):
    save_profile(profile_from_params("bici", Params(masa_total=90.0)))
    assert perfiles_aislados.exists()
    assert not list(perfiles_aislados.parent.glob("*.tmp"))


# --------------------------------------------------------------------------- criterios 16 y 29
def test_c29_dos_bandas_verificadas_y_la_del_dia_es_la_ancha():
    b_modelo, b_dia = bands(3600.0)
    # las dos están medidas: la diferencia entre ellas es QUÉ miden, no si se han comprobado
    assert b_modelo.verificada is True and b_dia.verificada is True
    assert b_dia.pct > b_modelo.pct
    assert b_modelo.pct == pytest.approx(MODELO_PCT) and b_dia.pct == pytest.approx(DIA_PCT)
    assert (b_modelo.clave, b_dia.clave) == ("modelo", "dia")


def test_c29_cada_banda_cubre_el_peor_error_que_se_midio():
    """Una banda que no cubre su propia peor observación no es una banda, es un deseo.

    Aquí solo se comprueba la relación. Que los peores errores declarados sean los que de verdad
    se miden lo vigila `test_c29_los_peores_errores_declarados_son_los_que_se_miden`, en
    `tests/test_coherencia_y_pares.py`, que los vuelve a medir sobre los fixtures en vez de
    creerse la cifra escrita aquí.
    """
    assert MODELO_PCT >= PEOR_ERROR_MODELO_PCT
    assert DIA_PCT >= PEOR_ERROR_DIA_PCT
    # La banda cubre el peor caso **y queda pegada a él**: el redondeo hacia arriba que se permite
    # es el de la cifra que se enseña (un decimal en la del modelo, entero en la del día), no un
    # margen libre. Con el `* 1.5` anterior se podía inflar la banda del día hasta el 21,4 % sin
    # que fallara nada, que es justo lo que una banda no debe poder hacer.
    assert MODELO_PCT - PEOR_ERROR_MODELO_PCT < 0.1, (
        f"la banda del modelo ({MODELO_PCT} %) se aleja del peor error medido "
        f"({PEOR_ERROR_MODELO_PCT} %): redondea al siguiente decimal, no más")
    assert DIA_PCT - PEOR_ERROR_DIA_PCT < 1.0, (
        f"la banda del día ({DIA_PCT} %) se aleja del peor error medido "
        f"({PEOR_ERROR_DIA_PCT} %): redondea al siguiente entero, no más")


def test_c29_la_banda_del_dia_es_un_suelo_para_ruta_nueva_no_una_estimacion():
    """El ±11 % anterior se retiró por ser menor que el margen por viento ya medido."""
    assert "sin verificar" in AVISO_RUTA_NUEVA
    assert "suelo" in AVISO_RUTA_NUEVA
    # no queda ninguna banda que se presente como la precisión en una ruta nueva
    assert not any("ruta nueva" in b.origen for b in bands(1000.0))


def test_c29_los_limites_de_la_banda_son_coherentes():
    b = band_modelo(3600.0)
    assert b.low_s < 3600.0 < b.high_s
    assert b.margen_s == pytest.approx(3600.0 * MODELO_PCT / 100.0)
    assert b.high_s - b.low_s == pytest.approx(2 * b.margen_s)
    assert band_dia(3600.0).margen_s > b.margen_s


def test_c16_cada_banda_declara_su_origen_y_dice_que_midio():
    for b in bands(1000.0):
        assert len(b.origen) > 20
        assert "medido" in b.origen          # ninguna banda es teórica
    assert "3 salidas coherentes" in band_modelo(1000.0).origen
    # la del día se mide con el protocolo que la herramienta recomienda, no con el más benévolo
    origen_dia = band_dia(1000.0).origen
    assert "protocolo recomendado" in origen_dia
    assert "coherentes" in origen_dia and "incoherentes" in origen_dia


def test_c16_with_bands_anade_las_cuatro_columnas_junto_al_tiempo():
    import pandas as pd

    df = pd.DataFrame({"km": [1.0, 2.0], "tiempo_s": [100.0, 200.0], "otra": [1, 2]})
    out = with_bands(df, "tiempo_s")
    cols = list(out.columns)
    esperadas = ["tiempo_s" + s for s in SUFIJOS]
    assert cols == ["km", "tiempo_s"] + esperadas + ["otra"]      # insertadas tras su columna
    assert out["tiempo_s_min_modelo"].iloc[0] == pytest.approx(100.0 * (1 - MODELO_PCT / 100))
    assert out["tiempo_s_max_dia"].iloc[1] == pytest.approx(200.0 * (1 + DIA_PCT / 100))
    # la banda del día envuelve a la del modelo, fila a fila
    assert (out["tiempo_s_min_dia"] < out["tiempo_s_min_modelo"]).all()
    assert (out["tiempo_s_max_dia"] > out["tiempo_s_max_modelo"]).all()
    assert df.columns.tolist() == ["km", "tiempo_s", "otra"]      # no muta el original


def test_c16_with_bands_falla_si_la_columna_no_existe():
    import pandas as pd

    with pytest.raises(KeyError):
        with_bands(pd.DataFrame({"a": [1]}), "tiempo_s")


# --------------------------------------------------------------------------- perfil de ejemplo
def test_c15_el_perfil_de_ejemplo_del_paquete_carga_de_verdad(monkeypatch):
    """Se envía un `perfiles_bici.ejemplo.json`: si se queda atrás del esquema, carga vacío.

    Pasó: el ejemplo seguía con `masa_ciclista`, `masa_equipo` y `radio_rueda` después de
    retirarlos del modelo, y `load_profiles` lo descartaba en silencio. Este test lo impide.
    """
    from pathlib import Path

    ejemplo = Path(__file__).resolve().parents[1] / "perfiles_bici.ejemplo.json"
    assert ejemplo.exists(), "falta el perfil de ejemplo del paquete"
    monkeypatch.setenv("SIMCICLISMO_PERFILES", str(ejemplo))

    perfiles = load_profiles()
    assert perfiles, "el perfil de ejemplo no carga: se habrá quedado atrás del esquema actual"
    prof = next(iter(perfiles.values()))
    for k in PROFILE_KEYS:
        assert hasattr(prof, k), k
    # y lo que promete: calibrado, con origen trazable y un CdA plausible
    assert prof.calibrado and len(prof.origen_cda) > 40
    assert 0.20 < prof.cda < 0.35
    assert prof.masa_total == pytest.approx(90.0)


def test_c14_ninguna_cifra_se_presenta_como_precision_en_una_ruta_nueva():
    """La prohibición del criterio 14, vigilada: ni el código ni la documentación pueden dar un
    número como precisión esperable fuera de la ruta de calibración.

    El ±11 % que la v9 daba para «ruta nueva» quedó retirado en la v10 por incoherente —era menor
    que el margen por viento medido en la propia ruta de calibración— y esto impide que vuelva.
    """
    import re
    from pathlib import Path

    # `11 %` a secas también aparece dentro de cualquier cifra que acabe en 11 (`−5,11 %`), y por
    # eso el barrido con `in` daba un falso positivo en la tabla de bandas de pendiente del informe
    # de validación. Se exige que el 11 no venga pegado a otro dígito ni a un separador decimal.
    patron_11 = re.compile(r"(?<![\d,.])(±\s?11\b|11\s?%)")
    # control del patrón: si se estrechara de más, el barrido dejaría de barrer sin que nada avise
    assert patron_11.search("la banda de ±11 % para ruta nueva")
    assert patron_11.search("un 11 % de margen esperable")
    assert not patron_11.search("| subida > 6 % | −5,11 % | +1,02 % |")
    assert not patron_11.search("111 % de la potencia umbral")
    raiz = Path(__file__).resolve().parents[1]
    # Todos los ficheros que el usuario puede leer o que generan texto, no una lista escrita a
    # mano: la lista anterior tenía tres nombres y dejaba fuera `app/streamlit_app.py` y los
    # informes en markdown, y en uno de ellos (`*.validacion.md`) el ±11 % seguía vivo.
    ficheros = sorted(
        [p for p in raiz.glob("*.md")]
        + [p for p in (raiz / "core").glob("*.py")]
        + [p for p in (raiz / "app").glob("*.py")])
    assert len(ficheros) >= 12, f"el barrido solo encuentra {len(ficheros)} ficheros"
    for ruta in ficheros:
        nombre = ruta.relative_to(raiz).as_posix()
        lineas = ruta.read_text(encoding="utf-8").splitlines()
        for i, linea in enumerate(lineas):
            if not patron_11.search(linea):
                continue
            # la frase puede partirse en varias líneas, así que se mira el párrafo alrededor
            ventana = " ".join(lineas[max(0, i - 2):i + 3]).lower()
            assert any(p in ventana for p in ("retirad", "anterior", "quedó")), (
                f"{nombre}: ±11 % presentado como cifra vigente -> {linea.strip()}")
    # y la banda de ruta nueva no existe como número: es un suelo declarado
    assert "suelo" in AVISO_RUTA_NUEVA and "sin verificar" in AVISO_RUTA_NUEVA
    assert not any(b.clave == "ruta_nueva" for b in bands(1000.0))
