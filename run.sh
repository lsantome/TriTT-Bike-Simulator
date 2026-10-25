#!/usr/bin/env bash
# Arranca el simulador en el navegador. macOS y Linux.
#
#   ./run.sh                 arranque normal (predicción de carrera)
#   ./run.sh --estimador     arranca directamente en el estimador de CdA
#   ./run.sh --tests         instala las dependencias de test y ejecuta pytest
#   ./run.sh --reinstalar    rehace el entorno desde cero
#
# La primera vez crea un entorno virtual en .venv e instala las dependencias (tarda un par de
# minutos). Las siguientes veces arranca directamente.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")"

VENV=".venv"
MARCA="$VENV/.requirements.hash"
PY_MIN_MAYOR=3
PY_MIN_MENOR=9

error() { printf '\n[ERROR] %s\n' "$*" >&2; exit 1; }
info()  { printf '  %s\n' "$*"; }

# --- 1. buscar un Python válido -----------------------------------------------------------------
buscar_python() {
    for cmd in python3 python; do
        if command -v "$cmd" >/dev/null 2>&1 && "$cmd" -c "
import sys
sys.exit(0 if sys.version_info >= ($PY_MIN_MAYOR, $PY_MIN_MENOR) else 1)
" 2>/dev/null; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

PYTHON="$(buscar_python)" || error "No encuentro Python ${PY_MIN_MAYOR}.${PY_MIN_MENOR} o superior.
  Instálalo desde https://www.python.org/downloads/ y vuelve a ejecutar este script.
  En macOS también sirve:  brew install python"

echo "Simulador de ciclismo — triatlón / CRI"
info "Python: $("$PYTHON" --version 2>&1) ($(command -v "$PYTHON"))"

# --- 2. entorno virtual -------------------------------------------------------------------------
if [ "${1:-}" = "--reinstalar" ]; then
    info "Borrando el entorno anterior…"
    rm -rf "$VENV"
    shift || true
fi

if [ ! -d "$VENV" ]; then
    info "Creando el entorno virtual (solo la primera vez)…"
    "$PYTHON" -m venv "$VENV" || error "No he podido crear el entorno virtual.
  En Debian o Ubuntu puede faltar el paquete del módulo venv:  sudo apt install python3-venv"
fi

VPY="$VENV/bin/python"
[ -x "$VPY" ] || error "El entorno virtual está incompleto. Ejecuta:  ./run.sh --reinstalar"

# --- 3. dependencias: solo si requirements.txt ha cambiado ---------------------------------------
hash_requirements() {
    local f="$1"
    if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$f" | cut -d' ' -f1
    elif command -v sha256sum >/dev/null 2>&1; then sha256sum "$f" | cut -d' ' -f1
    else "$VPY" -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$f"
    fi
}

instalar_si_hace_falta() {
    local req="$1" marca="$2"
    local actual
    actual="$(hash_requirements "$req")"
    if [ -f "$marca" ] && [ "$(cat "$marca")" = "$actual" ]; then
        return 0
    fi
    info "Instalando las dependencias de $req (puede tardar un par de minutos)…"
    "$VPY" -m pip install --upgrade pip --quiet
    "$VPY" -m pip install -r "$req" --quiet || error "Ha fallado la instalación de dependencias.
  Revisa tu conexión y vuelve a intentarlo, o ejecuta:  ./run.sh --reinstalar"
    printf '%s' "$actual" > "$marca"
}

# --- 4. tests o app ------------------------------------------------------------------------------
if [ "${1:-}" = "--tests" ]; then
    shift
    instalar_si_hace_falta "requirements-dev.txt" "$VENV/.requirements-dev.hash"
    info "Ejecutando los tests…"
    exec "$VPY" -m pytest "$@"
fi

# --estimador abre directamente el módulo de medida del CdA (criterio 31). El módulo se
# selecciona por la URL, así que basta con decirle a Streamlit con qué parámetros abrirla.
MODULO_INICIAL=""
if [ "${1:-}" = "--estimador" ]; then
    shift
    MODULO_INICIAL="estimador"
fi

instalar_si_hace_falta "requirements.txt" "$MARCA"
echo
if [ -n "$MODULO_INICIAL" ]; then
    info "Abriendo el estimador de CdA. Para cerrarlo, pulsa Ctrl+C en esta ventana."
    echo
    exec "$VPY" -m streamlit run app/streamlit_app.py "$@" -- --modo="$MODULO_INICIAL"
fi
info "Abriendo el simulador en el navegador. Para cerrarlo, pulsa Ctrl+C en esta ventana."
echo
exec "$VPY" -m streamlit run app/streamlit_app.py "$@"
