@echo off
rem Arranca el simulador en el navegador. Windows: doble clic en este archivo.
rem
rem   run.bat                      arranque normal
rem   run.bat --estimador   arranca directamente en el estimador de CdA
rem   run.bat --tests              instala las dependencias de test y ejecuta pytest
rem   run.bat --reinstalar         rehace el entorno desde cero
rem   run.bat --reinstalar --tests rehace el entorno y ejecuta los tests
rem
rem La primera vez crea un entorno virtual en .venv e instala las dependencias (tarda un par de
rem minutos). Las siguientes veces arranca directamente.
rem
rem NOTA para quien edite este archivo: `cmd` expande un bloque entre paréntesis ENTERO antes de
rem ejecutarlo, así que `shift` y `%1` no pueden convivir dentro de un bloque (el `%1` ya estaría
rem expandido). Por eso el parseo de argumentos usa etiquetas y `goto`, no bloques.
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "VENV=.venv"
set "VPY=%VENV%\Scripts\python.exe"
set "MARCA=%VENV%\.requirements.hash"
set "MARCA_DEV=%VENV%\.requirements-dev.hash"
set "CODIGO=0"

echo Simulador de ciclismo - triatlon / CRI

rem --- 1. parseo de argumentos (fuera de bloques) ------------------------------------------------
set "REINSTALAR="
set "TESTS="
set "ESTIMADOR="
set "RESTO="

if /i "%~1"=="--reinstalar" goto :flag_reinstalar
if /i "%~1"=="--tests" goto :flag_tests
if /i "%~1"=="--estimador" goto :flag_estimador
goto :recoger

:flag_reinstalar
set "REINSTALAR=1"
shift
if /i "%~1"=="--tests" goto :flag_tests
if /i "%~1"=="--estimador" goto :flag_estimador
goto :recoger

:flag_tests
set "TESTS=1"
shift
goto :recoger

:flag_estimador
set "ESTIMADOR=1"
shift
goto :recoger

rem `%*` ignora los `shift`, así que los argumentos restantes se recogen uno a uno.
:recoger
if "%~1"=="" goto :recogido
set "RESTO=!RESTO! %1"
shift
goto :recoger
:recogido

rem --- 2. buscar un Python valido (3.9 o superior) -----------------------------------------------
set "PYTHON="
for %%C in ("py -3" "python" "python3") do (
    if not defined PYTHON (
        %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON=%%~C"
    )
)
if not defined PYTHON (
    echo.
    echo [ERROR] No encuentro Python 3.9 o superior.
    echo   Instalalo desde https://www.python.org/downloads/ marcando
    echo   "Add Python to PATH", y vuelve a ejecutar este archivo.
    set "CODIGO=1"
    goto :fin
)
for /f "delims=" %%V in ('%PYTHON% --version 2^>^&1') do echo   Python: %%V

rem --- 3. entorno virtual -----------------------------------------------------------------------
if defined REINSTALAR (
    echo   Borrando el entorno anterior...
    if exist "%VENV%" rmdir /s /q "%VENV%"
)

if not exist "%VPY%" (
    echo   Creando el entorno virtual ^(solo la primera vez^)...
    %PYTHON% -m venv "%VENV%"
    if errorlevel 1 (
        echo.
        echo [ERROR] No he podido crear el entorno virtual.
        set "CODIGO=1"
        goto :fin
    )
)
if not exist "%VPY%" (
    echo.
    echo [ERROR] El entorno virtual esta incompleto. Ejecuta:  run.bat --reinstalar
    set "CODIGO=1"
    goto :fin
)

rem --- 4. tests o app ---------------------------------------------------------------------------
if not defined TESTS goto :modo_app
call :instalar requirements-dev.txt "%MARCA_DEV%"
rem `if errorlevel 1 goto :fin` perderia el codigo de salida: hay que fijarlo antes de saltar, y
rem comprobar el errorlevel ANTES de cualquier `set` (un `set` con exito lo resetea).
if not errorlevel 1 goto :dev_ok
set "CODIGO=1"
goto :fin
:dev_ok
echo   Ejecutando los tests...
"%VPY%" -m pytest!RESTO!
set "CODIGO=!errorlevel!"
goto :fin

:modo_app
call :instalar requirements.txt "%MARCA%"
if not errorlevel 1 goto :app_ok
set "CODIGO=1"
goto :fin
:app_ok
echo.
if defined ESTIMADOR goto :app_estimador
echo   Abriendo el simulador en el navegador. Para cerrarlo, pulsa Ctrl+C en esta ventana.
echo.
"%VPY%" -m streamlit run app\streamlit_app.py!RESTO!
set "CODIGO=!errorlevel!"
goto :fin

:app_estimador
echo   Abriendo el estimador de CdA. Para cerrarlo, pulsa Ctrl+C en esta ventana.
echo.
"%VPY%" -m streamlit run app\streamlit_app.py!RESTO! -- --modo=estimador
set "CODIGO=!errorlevel!"
goto :fin

rem --- instalar dependencias solo si el requirements ha cambiado --------------------------------
rem El hash se calcula a un archivo temporal y se lee con `set /p`: meter el comando dentro de un
rem `for /f in ('...')` rompe con las comillas simples del codigo Python. Si el hash no se puede
rem calcular, se instala igualmente (fallar hacia el lado seguro, nunca saltarse la instalacion).
:instalar
set "REQ=%~1"
set "SELLO=%~2"
set "TMPHASH=%TEMP%\simciclismo_hash_%RANDOM%.txt"
set "HASH="
"%VPY%" -c "import hashlib,sys;open(sys.argv[2],'w').write(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "%REQ%" "%TMPHASH%" >nul 2>&1
if exist "%TMPHASH%" set /p HASH=<"%TMPHASH%"
if exist "%TMPHASH%" del "%TMPHASH%" >nul 2>&1
if not defined HASH goto :instalar_ahora
if not exist "%SELLO%" goto :instalar_ahora
set "PREVIO="
set /p PREVIO=<"%SELLO%"
if "!PREVIO!"=="!HASH!" exit /b 0

:instalar_ahora
echo   Instalando las dependencias de %REQ% ^(puede tardar un par de minutos^)...
"%VPY%" -m pip install --upgrade pip --quiet
"%VPY%" -m pip install -r "%REQ%" --quiet
if errorlevel 1 (
    echo.
    echo [ERROR] Ha fallado la instalacion de dependencias.
    echo   Revisa tu conexion y vuelve a intentarlo, o ejecuta:  run.bat --reinstalar
    exit /b 1
)
if defined HASH >"%SELLO%" echo !HASH!
exit /b 0

:fin
echo.
pause
exit /b %CODIGO%
