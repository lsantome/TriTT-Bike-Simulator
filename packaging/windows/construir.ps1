<#
.SYNOPSIS
    Construye el paquete autocontenido de Windows: un ZIP que se descomprime y funciona, sin
    instalar Python ni nada más.

.DESCRIPTION
    No congela la aplicación (nada de PyInstaller). Monta un árbol de Python normal:

      TriTT-Bike-Simulator\
        TriTT.bat            lanzador: lo que el usuario abre
        LEEME.txt            instrucciones para quien no ha visto una terminal nunca
        python\              Python embebido de python.org, con las dependencias dentro
        app\  core\  .streamlit\   la aplicación tal cual
        README.md  LICENSE  *.spec.md  *.validacion.md

    Se hace así a propósito. Congelar Streamlit es frágil: arranca por su propio CLI, carga
    estáticos desde el paquete y lee metadatos con `importlib.metadata`, de modo que cada
    actualización puede romper el empaquetado. Aquí no hay nada congelado: es el mismo Python
    ejecutando el mismo código, solo que el intérprete viaja en la carpeta.

.PARAMETER VersionPython
    Versión del paquete «Windows embeddable» de python.org. Tiene que ser una para la que existan
    ruedas (wheels) de numpy, pandas, plotly y streamlit.

.PARAMETER Salida
    Carpeta donde se monta el paquete y se deja el ZIP.

.EXAMPLE
    pwsh -File packaging\windows\construir.ps1
#>
[CmdletBinding()]
param(
    [string]$VersionPython = "3.12.8",
    [string]$Salida = "dist"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# La raíz del repositorio, dos niveles por encima de este script.
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Nombre = "TriTT-Bike-Simulator"
$DirSalida = Join-Path $Raiz $Salida
$DirPaquete = Join-Path $DirSalida $Nombre
$DirPython = Join-Path $DirPaquete "python"

function Paso($texto) { Write-Host "==> $texto" -ForegroundColor Cyan }

# --------------------------------------------------------------------------- limpieza
if (Test-Path $DirPaquete) { Remove-Item -Recurse -Force $DirPaquete }
New-Item -ItemType Directory -Force -Path $DirPaquete | Out-Null

# --------------------------------------------------------------------------- Python embebido
Paso "Descargando Python $VersionPython embebido"
$UrlPython = "https://www.python.org/ftp/python/$VersionPython/python-$VersionPython-embed-amd64.zip"
$ZipPython = Join-Path $DirSalida "python-embed.zip"
Invoke-WebRequest -Uri $UrlPython -OutFile $ZipPython -UseBasicParsing
Expand-Archive -Path $ZipPython -DestinationPath $DirPython -Force
Remove-Item $ZipPython

# El paquete embebido viene con `import site` desactivado y sin `Lib\site-packages` en la ruta de
# búsqueda, así que no encontraría las dependencias. Hay que habilitar las dos cosas en el `._pth`.
Paso "Habilitando site-packages en el intérprete embebido"
$Pth = Get-ChildItem -Path $DirPython -Filter "python*._pth" | Select-Object -First 1
if (-not $Pth) { throw "No encuentro el fichero ._pth del Python embebido." }
$lineas = Get-Content $Pth.FullName | Where-Object { $_ -notmatch '^\s*#?\s*import\s+site\s*$' }
$lineas = @($lineas) + @("Lib\site-packages", "import site")
Set-Content -Path $Pth.FullName -Value $lineas -Encoding ASCII

# --------------------------------------------------------------------------- dependencias
# Se instalan con el pip del runner contra el destino embebido. `--only-binary=:all:` y
# `--python-version` obligan a bajar ruedas de esa versión exacta: si alguna dependencia no tuviera
# rueda para ella, el build falla aquí y no en el ordenador del usuario.
Paso "Instalando dependencias en el paquete"
$SitePackages = Join-Path $DirPython "Lib\site-packages"
$corta = ($VersionPython -split '\.')[0..1] -join '.'
python -m pip install `
    --target $SitePackages `
    --requirement (Join-Path $Raiz "requirements.txt") `
    --only-binary=:all: `
    --python-version $corta `
    --implementation cp `
    --upgrade
if ($LASTEXITCODE -ne 0) { throw "pip install falló con código $LASTEXITCODE" }

# Los .pyc y los tests de las dependencias no hacen falta y pesan.
Paso "Quitando lastre de las dependencias"
Get-ChildItem -Path $SitePackages -Include "__pycache__" -Recurse -Directory -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $SitePackages -Include "*.pyi" -Recurse -File -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

# --------------------------------------------------------------------------- la aplicación
Paso "Copiando la aplicación"
foreach ($dir in @("app", "core", ".streamlit")) {
    Copy-Item -Recurse -Force (Join-Path $Raiz $dir) (Join-Path $DirPaquete $dir)
}
# `__pycache__` del repositorio, si lo hubiera, no viaja.
Get-ChildItem -Path $DirPaquete -Include "__pycache__" -Recurse -Directory -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Documentación que viaja con el paquete. El README enlaza a la especificación y al informe de
# validación con rutas relativas, así que van dentro para que los enlaces no queden roto.
$sueltos = @(
    "README.md",
    "LICENSE",
    "perfiles_bici.ejemplo.json",
    "simulador-ciclismo-triatlon.spec.md",
    "simulador-ciclismo-triatlon.validacion.md"
)
foreach ($f in $sueltos) {
    $origen = Join-Path $Raiz $f
    if (Test-Path $origen) { Copy-Item -Force $origen (Join-Path $DirPaquete $f) }
}

Paso "Copiando el lanzador y las instrucciones"
Copy-Item -Force (Join-Path $PSScriptRoot "TriTT.bat") (Join-Path $DirPaquete "TriTT.bat")
Copy-Item -Force (Join-Path $PSScriptRoot "LEEME.txt") (Join-Path $DirPaquete "LEEME.txt")

# --------------------------------------------------------------------------- comprobación
# El intérprete empaquetado tiene que poder importar la aplicación. Si esto falla, el ZIP no sale:
# es mejor romper el build que repartir una carpeta que no arranca.
Paso "Comprobando que el paquete importa la aplicación"
$exe = Join-Path $DirPython "python.exe"
Push-Location $DirPaquete
try {
    & $exe -c "import numpy, pandas, plotly, streamlit, fitdecode; from core.simulate import simulate; from core.cda_estimator import estimate_cda; print('importa correctamente')"
    if ($LASTEXITCODE -ne 0) { throw "El paquete no puede importar la aplicación (código $LASTEXITCODE)" }
} finally {
    Pop-Location
}

# --------------------------------------------------------------------------- ZIP
Paso "Comprimiendo"
$Zip = Join-Path $DirSalida "$Nombre-windows.zip"
if (Test-Path $Zip) { Remove-Item -Force $Zip }
Compress-Archive -Path $DirPaquete -DestinationPath $Zip -CompressionLevel Optimal

$mb = [math]::Round((Get-Item $Zip).Length / 1MB, 1)
$mbDesc = [math]::Round(((Get-ChildItem -Recurse -File $DirPaquete | Measure-Object -Sum Length).Sum / 1MB), 1)
Write-Host ""
Write-Host "Paquete listo: $Zip" -ForegroundColor Green
Write-Host "  ZIP: $mb MB   ·   descomprimido: $mbDesc MB"
