"""Criterio 17: scripts de arranque y coherencia de las dependencias declaradas.

El test de las dependencias existe porque en la ronda 4 se colaron los tests importando `scipy`
sin declararlo: la suite no arrancaba desde una instalación limpia. Esto lo detecta sin tener que
crear un entorno virtual.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REQ = RAIZ / "requirements.txt"
REQ_DEV = RAIZ / "requirements-dev.txt"
RUN_SH = RAIZ / "run.sh"
RUN_BAT = RAIZ / "run.bat"

#: Módulos que trae Python de serie o que son del propio proyecto: no se declaran.
#: Módulos propios del paquete, que no son dependencias que instalar. Se calculan, no se
#: enumeran: `app/theme.py` se importa como `theme` porque la app corre con `app/` en el path.
PROPIOS = ({"core", "app", "tests"}
           | {p.stem for p in (RAIZ / "app").glob("*.py")}
           | {p.stem for p in (RAIZ / "core").glob("*.py")})


def _requisitos(path: Path):
    """Nombres de paquete declarados en un requirements (sin versión ni comentarios)."""
    nombres = set()
    for linea in path.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#")[0].strip()
        if not linea or linea.startswith("-r"):
            continue
        nombres.add(re.split(r"[<>=!~\[]", linea)[0].strip().lower())
    return nombres


def _imports_de(paths):
    """Módulos de primer nivel importados por esos ficheros."""
    fuera = set()
    for p in paths:
        arbol = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                fuera.update(a.name.split(".")[0] for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                fuera.add(nodo.module.split(".")[0])
    estandar = set(sys.stdlib_module_names)
    return {m for m in fuera if m not in estandar and m not in PROPIOS}


# --------------------------------------------------------------------------- dependencias
def test_c17_todo_lo_que_importa_la_app_esta_en_requirements():
    """Si la app o el núcleo importan algo sin declarar, no arranca desde cero."""
    usados = _imports_de(sorted((RAIZ / "core").glob("*.py")) + [RAIZ / "app" / "streamlit_app.py"])
    declarados = _requisitos(REQ)
    assert usados <= declarados, f"sin declarar en requirements.txt: {sorted(usados - declarados)}"


def test_c17_todo_lo_que_importan_los_tests_esta_en_requirements_dev():
    usados = _imports_de(sorted(Path(__file__).parent.glob("*.py")))
    declarados = _requisitos(REQ_DEV) | _requisitos(REQ)
    assert usados <= declarados, f"sin declarar en requirements-dev.txt: {sorted(usados - declarados)}"


def test_c17_requirements_de_app_no_arrastra_dependencias_de_test():
    """Arrancar la app no debe instalar pytest ni scipy (scipy pesa decenas de MB)."""
    assert not ({"pytest", "scipy"} & _requisitos(REQ))
    assert {"pytest", "scipy"} <= _requisitos(REQ_DEV)
    assert "-r requirements.txt" in REQ_DEV.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- scripts
def test_c17_existen_los_dos_scripts_y_el_de_unix_es_ejecutable():
    assert RUN_SH.exists() and RUN_BAT.exists()
    assert RUN_SH.stat().st_mode & 0o111, "run.sh no tiene permiso de ejecución"


@pytest.mark.skipif(sys.platform == "win32", reason="bash no disponible")
def test_c17_run_sh_es_sintacticamente_valido():
    r = subprocess.run(["bash", "-n", str(RUN_SH)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("script", [RUN_SH, RUN_BAT], ids=["run.sh", "run.bat"])
def test_c17_los_scripts_apuntan_a_la_app_y_a_los_requirements_reales(script):
    txt = script.read_text(encoding="utf-8")
    assert "streamlit_app.py" in txt
    assert "requirements.txt" in txt and "requirements-dev.txt" in txt
    assert "--reinstalar" in txt and "--tests" in txt
    assert ".venv" in txt
    # mensaje de ayuda si falta Python, con el enlace de descarga
    assert "python.org" in txt
    # comprobación de versión mínima coherente entre los dos scripts
    assert "3, 9" in txt or "(3, 9)" in txt or ("PY_MIN_MENOR=9" in txt)


def test_c17_run_sh_se_situa_en_su_propio_directorio():
    """Doble clic desde cualquier sitio: el script no puede depender del directorio actual."""
    txt = RUN_SH.read_text(encoding="utf-8")
    assert 'cd "$(dirname' in txt
    assert "set -euo pipefail" in txt          # un fallo intermedio no sigue adelante
    assert RUN_BAT.read_text(encoding="utf-8").count('cd /d "%~dp0"') == 1


def test_c17_run_bat_deja_la_ventana_abierta_para_poder_leer_el_error():
    txt = RUN_BAT.read_text(encoding="utf-8")
    assert "pause" in txt
    assert txt.startswith("@echo off")


# --------------------------------------------------------------------------- trampas de cmd
# `run.bat` no se puede ejecutar aquí (este entorno es Linux), así que en su lugar se comprueban
# estáticamente las dos trampas de `cmd` que ya se colaron una vez. Los tests de "la cadena está
# presente" no las habrían detectado.
def _profundidad_parentesis(linea: str, inicial: int) -> int:
    """Paréntesis de bloque abiertos tras la línea, ignorando los escapados y los entrecomillados."""
    d, en_comillas, i = inicial, False, 0
    while i < len(linea):
        c = linea[i]
        if c == "^":                       # ^( y ^) son paréntesis literales, no de bloque
            i += 2
            continue
        if c == '"':
            en_comillas = not en_comillas
        elif not en_comillas and c == "(":
            d += 1
        elif not en_comillas and c == ")":
            d = max(0, d - 1)
        i += 1
    return d


def test_c17_run_bat_no_usa_shift_dentro_de_un_bloque():
    """Trampa A: `cmd` expande el bloque entre paréntesis ENTERO antes de ejecutarlo, así que un
    `%1` leído después de un `shift` del mismo bloque sigue valiendo lo de antes y el `shift` es
    código muerto. El parseo de argumentos tiene que ir con etiquetas y `goto`."""
    profundidad, culpables = 0, []
    for n, linea in enumerate(RUN_BAT.read_text(encoding="utf-8").splitlines(), 1):
        limpia = linea.strip()
        if not limpia.lower().startswith("rem ") and re.search(r"\bshift\b", limpia, re.I):
            if profundidad > 0:
                culpables.append((n, limpia))
        profundidad = _profundidad_parentesis(limpia, profundidad)
    assert not culpables, f"`shift` dentro de un bloque en run.bat: {culpables}"


def test_c17_run_bat_no_mete_comillas_simples_en_un_for_f():
    """Trampa B: en `for /f ... in ('comando')` las comillas simples delimitan el comando y no se
    pueden escapar, así que un comando de Python con `'rb'` dentro revienta o devuelve vacío. Peor
    aún, el fallo es silencioso: el hash sale vacío y se reinstala en cada arranque."""
    for n, linea in enumerate(RUN_BAT.read_text(encoding="utf-8").splitlines(), 1):
        if linea.strip().lower().startswith("rem "):
            continue
        m = re.search(r"for\s+/f\s+.*?\bin\s*\(\s*'(.*)'\s*\)", linea, re.I)
        if m:
            assert "'" not in m.group(1), f"línea {n}: comillas simples dentro de un for /f"


def test_c17_run_bat_no_se_salta_la_instalacion_si_el_hash_falla():
    """Si el hash no se puede calcular hay que instalar, no dar por bueno el sello anterior."""
    txt = RUN_BAT.read_text(encoding="utf-8")
    assert re.search(r"if\s+not\s+defined\s+HASH\s+goto\s+:instalar_ahora", txt, re.I)
    # y el sello solo se escribe si hay hash de verdad
    assert re.search(r"if\s+defined\s+HASH\s*>", txt, re.I)


def test_c17_run_bat_propaga_el_codigo_de_salida():
    """Un `goto :fin` se come el errorlevel de pytest; hay que capturarlo y devolverlo."""
    txt = RUN_BAT.read_text(encoding="utf-8")
    assert txt.count('set "CODIGO=!errorlevel!"') >= 2       # tests y app
    assert re.search(r"exit\s+/b\s+%CODIGO%", txt, re.I)


def test_c17_run_bat_sale_distinto_de_cero_en_todos_sus_caminos_de_error():
    """Punto ciego detectado en la revisión: `CODIGO` arranca en 0, así que un camino de error que
    salte a `:fin` sin fijarlo sale con 0 y parece que todo fue bien. Son 5: falta Python, fallo al
    crear el entorno, entorno incompleto y los dos fallos de instalación."""
    lineas = [l.strip() for l in RUN_BAT.read_text(encoding="utf-8").splitlines()
              if not l.strip().lower().startswith("rem ")]
    malos = [l for l in lineas if re.match(r"if\s+errorlevel\s+1\s+goto\s+:fin", l, re.I)]
    assert not malos, f"saltan a :fin sin fijar CODIGO: {malos}"
    assert sum(1 for l in lineas if l == 'set "CODIGO=1"') >= 5


@pytest.mark.parametrize("script", [RUN_SH, RUN_BAT], ids=["run.sh", "run.bat"])
def test_c17_los_dos_scripts_reenvian_los_argumentos_extra(script):
    txt = script.read_text(encoding="utf-8")
    if script is RUN_SH:
        assert '"$@"' in txt
    else:
        # `%*` ignora los `shift`, así que los restantes se recogen uno a uno
        assert "!RESTO!" in txt and ":recoger" in txt
        codigo = [l for l in txt.splitlines() if not l.strip().lower().startswith("rem ")]
        assert "%*" not in "\n".join(codigo), "`%*` no respeta los shift: usa el bucle de recogida"


def test_c17_los_dos_scripts_aceptan_reinstalar_seguido_de_tests():
    assert re.search(r"--reinstalar.*--tests|--tests.*goto", RUN_BAT.read_text(encoding="utf-8"), re.S)
    sh = RUN_SH.read_text(encoding="utf-8")
    # en run.sh: --reinstalar hace shift y luego se evalúa --tests
    assert sh.index("--reinstalar") < sh.index('"${1:-}" = "--tests"')


# --------------------------------------------------------------------------- criterio 17
def test_c17_la_configuracion_no_impide_que_se_abra_el_navegador():
    """Los dos lanzadores prometen «Abriendo el simulador en el navegador».

    `headless = true` en la configuración hace que Streamlit no lo abra, y los scripts seguirían
    diciendo que sí. Se coló al alinear el tema con la paleta en la ronda 13.
    """
    import re

    conf = (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    activos = [l.split("#")[0] for l in conf.splitlines() if not l.strip().startswith("#")]
    assert not any(re.search(r"headless\s*=\s*true", l) for l in activos), (
        "headless = true impide que los lanzadores abran el navegador")
    for nombre in ("run.sh", "run.bat"):
        texto = (RAIZ / nombre).read_text(encoding="utf-8")
        assert "navegador" in texto, nombre
