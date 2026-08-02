@echo off
REM Doble clic para abrir la ventana de consulta. Windows.
REM
REM Se usa pythonw.exe: abre la ventana SIN consola negra detras. Si algo
REM falla, esta ventana se queda abierta con la explicacion; nunca se cierra
REM en silencio dejando al usuario sin saber que ha pasado.

cd /d "%~dp0"

set "PYW=.venv\Scripts\pythonw.exe"
set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo.
  echo ======================================================================
  echo   NO SE HA PODIDO ABRIR EL AGENTE
  echo ======================================================================
  echo.
  echo   Falta la instalacion ^(no existe la carpeta .venv^).
  echo.
  echo   Avisa a Emili y ensenale esta ventana.
  echo.
  pause
  exit /b 1
)

"%PY%" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
  echo.
  echo ======================================================================
  echo   NO SE HA PODIDO ABRIR EL AGENTE
  echo ======================================================================
  echo.
  echo   Este Python no puede dibujar ventanas ^(le falta tkinter^).
  echo   Hay que reinstalar Python marcando "tcl/tk and IDLE".
  echo.
  echo   Avisa a Emili y ensenale esta ventana.
  echo.
  pause
  exit /b 1
)

if not exist "datos" mkdir "datos"

REM Arranque de prueba: si el programa se cae al empezar, se ve aqui y NO se
REM cierra la ventana. Si arranca bien, se relanza sin consola y se sale.
"%PY%" -c "import interfaz" >datos\arranque.log 2>&1
if errorlevel 1 (
  echo.
  echo ======================================================================
  echo   NO SE HA PODIDO ABRIR EL AGENTE
  echo ======================================================================
  echo.
  echo   El programa no arranca. Detalle tecnico en datos\arranque.log
  echo.
  type datos\arranque.log
  echo.
  echo   Avisa a Emili y ensenale esta ventana.
  echo.
  pause
  exit /b 1
)

REM pythonw.exe es el que abre la ventana SIN consola negra detras. Se comprueba
REM aparte: si falta, Windows saca su propio error, que no dice nada a nadie.
if not exist "%PYW%" (
  echo.
  echo ======================================================================
  echo   NO SE HA PODIDO ABRIR EL AGENTE
  echo ======================================================================
  echo.
  echo   Falta pythonw.exe en la instalacion.
  echo.
  echo   Avisa a Emili y ensenale esta ventana.
  echo.
  pause
  exit /b 1
)

start "" "%PYW%" interfaz.py %*
exit /b 0
