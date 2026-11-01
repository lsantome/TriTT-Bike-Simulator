@echo off
rem ===========================================================================
rem  TriTT Bike Simulator - lanzador del paquete autocontenido de Windows.
rem
rem  Usa el Python que viaja en la subcarpeta "python": no hace falta instalar
rem  nada. Abre el navegador solo, en una direccion local (localhost).
rem
rem  Uso:  TriTT.bat                 abre la aplicacion
rem        TriTT.bat --estimador     abre directamente la estimacion de CdA
rem ===========================================================================
setlocal EnableExtensions

rem Trabajar siempre desde la carpeta del paquete, pase lo que pase con el
rem directorio desde el que se haya llamado al lanzador. NO es lo que hace que
rem se encuentre el paquete `core`: de eso se encarga el fichero `._pth` del
rem interprete embebido, que es lo unico que define sus rutas de busqueda. El
rem `cd` hace falta para que Streamlit encuentre `.streamlit\config.toml` y
rem para que las rutas relativas de la aplicacion apunten donde deben.
cd /d "%~dp0"

set "PYTHON=%~dp0python\python.exe"
if not exist "%PYTHON%" goto :sin_python

rem Por higiene, no por necesidad: el interprete embebido ignora PYTHONPATH y
rem PYTHONHOME mientras exista su `._pth`. Se vacian igualmente para que, si
rem algun dia se dejara de usar el `._pth`, un valor heredado del sistema no
rem desvie el interprete a otra instalacion de Python.
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

rem Los perfiles de bici se guardan en la carpeta del usuario, no junto al
rem programa: si el paquete acaba en una ruta de solo lectura, guardar un
rem perfil fallaria. La aplicacion lee esta variable (ver core/profiles.py).
set "DATOS=%APPDATA%\TriTT-Bike-Simulator"
if not exist "%DATOS%" mkdir "%DATOS%"
set "SIMCICLISMO_PERFILES=%DATOS%\perfiles_bici.json"

rem Streamlit pide un correo electronico la primera vez que se ejecuta si no
rem encuentra este fichero. Para quien solo quiere abrir la aplicacion es un
rem obstaculo sin sentido, asi que se crea vacio.
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
    >"%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >>"%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

set "MODO="
if /i "%~1"=="--estimador" set "MODO=-- --modo=estimador"

echo.
echo  Abriendo TriTT Bike Simulator en el navegador...
echo  NO CIERRES ESTA VENTANA mientras uses la aplicacion.
echo  Para salir: cierra esta ventana o pulsa Ctrl+C.
echo.

"%PYTHON%" -m streamlit run "app\streamlit_app.py" %MODO%
set "CODIGO=%ERRORLEVEL%"

if not "%CODIGO%"=="0" goto :fallo
endlocal
exit /b 0

:sin_python
echo.
echo  ERROR: no encuentro "python\python.exe".
echo.
echo  Lo mas probable es que estes ejecutando el programa desde dentro del
echo  fichero ZIP. Descomprime la carpeta COMPLETA en algun sitio (por
echo  ejemplo en el Escritorio) y abre TriTT.bat desde ahi.
echo.
pause
endlocal
exit /b 1

:fallo
echo.
echo  La aplicacion termino con un error (codigo %CODIGO%).
echo  Copia el texto de arriba si quieres que alguien lo revise.
echo.
echo  Si dice que el puerto 8501 ya esta en uso, es que la aplicacion ya
echo  estaba abierta: buscala en una pestana del navegador.
echo.
pause
endlocal
exit /b %CODIGO%
