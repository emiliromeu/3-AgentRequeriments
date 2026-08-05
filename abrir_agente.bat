@echo off
REM ABRIR EL AGENTE. Doble clic. Windows.
REM
REM Este fichero solo sabe hacer las dos cosas que Python no puede hacerse a si
REM mismo: ENCONTRAR un Python y CREAR el entorno virtual. Todo lo demas -las
REM librerias, la clave, el corpus- lo hace instalar.py, que es el mismo en
REM Windows y en Mac. Escribir esa logica dos veces, una en cmd y otra en bash,
REM es garantizar que dentro de un mes hagan cosas distintas.
REM
REM La ventana NO se cierra sola cuando algo falla: lo que salga hay que poder
REM leerlo.

setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
set "PYW=.venv\Scripts\pythonw.exe"

REM --- CAMINO RAPIDO ---------------------------------------------------
REM Si esta todo, se abre y ya. Tres comprobaciones de fichero, sin arrancar
REM Python: en un arranque normal esto no se nota.
if not exist "%PYW%" goto instalar
if not exist ".env" goto instalar
REM La libreria tambien: sin ella el agente abre y falla en la primera
REM consulta, que es justo el descubrimiento tardio que esto viene a evitar.
if not exist ".venv\Lib\site-packages\anthropic" goto instalar
if not exist "datos\corpus\BOE-A-1992-28740.jsonl" goto instalar
if not exist "datos\corpus\BOE-A-1992-28925.jsonl" goto instalar
if not exist "datos\corpus\BOE-A-2003-23186.jsonl" goto instalar
findstr /b /c:"ANTHROPIC_API_KEY=sk-" ".env" >nul 2>&1
if errorlevel 1 goto instalar
goto abrir

:instalar
REM --- 1. HAY PYTHON? --------------------------------------------------
REM Es lo unico que necesita a una persona: no se puede instalar Python solo.
if exist "%PY%" goto tienevenv

REM SIN "&&" Y SIN PARENTESIS, A PROPOSITO. En cmd, el "&&" NO se agrupa
REM dentro del if: "if not defined X orden && set Y" se lee como
REM "(if not defined X orden) && (set Y)", asi que el set se ejecuta segun el
REM errorlevel que hubiera antes, aunque el if sea falso. Escrito de la forma
REM bonita, este fichero elegia "python" aunque "py -3" ya hubiera funcionado.
REM Es un fallo que solo se ve en Windows, y aqui no hay Windows.
set "BASE="
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "BASE=py -3"
if defined BASE goto creavenv

python -c "import sys" >nul 2>&1
if not errorlevel 1 set "BASE=python"
if defined BASE goto creavenv

echo.
echo ======================================================================
echo   FALTA PYTHON EN ESTE EQUIPO
echo ======================================================================
echo.
echo   El agente necesita Python y este equipo no lo tiene. Es lo unico
echo   que hay que instalar a mano; el resto se hace solo.
echo.
echo     1. Entra en   https://www.python.org/downloads/
echo     2. Descarga la version para Windows y ejecutala.
echo     3. IMPORTANTE: en la primera pantalla del instalador, MARCA la
echo        casilla  "Add Python to PATH"  antes de darle a Install.
echo        Si no la marcas, el agente seguira sin encontrarlo.
echo.
echo   Cuando termine, vuelve a hacer doble clic en abrir_agente.
echo.
pause
exit /b 1

:creavenv
REM --- 2. CREAR EL ENTORNO ---------------------------------------------
echo.
echo   Preparando el agente por primera vez. No cierres esta ventana.
echo.
echo   [1/2] Creando el espacio de trabajo del programa...
%BASE% -m venv .venv
if not exist "%PY%" (
  echo.
  echo ======================================================================
  echo   NO SE HA PODIDO PREPARAR EL AGENTE
  echo ======================================================================
  echo.
  echo   No se ha podido crear el espacio de trabajo del programa.
  echo   Suele ser que la instalacion de Python esta incompleta: reinstalala
  echo   desde python.org marcando "Add Python to PATH".
  echo.
  echo   Avisa a Emili y ensenale esta ventana.
  echo.
  pause
  exit /b 1
)
echo         Listo.

:tienevenv
REM --- 3 a 5. LIBRERIAS, CLAVE Y CORPUS --------------------------------
"%PY%" instalar.py
if errorlevel 1 (
  echo.
  pause
  exit /b 1
)

:abrir
REM --- 6. ABRIR LA VENTANA ---------------------------------------------
REM pythonw.exe abre la ventana SIN consola negra detras. Si falta, Windows
REM saca su propio error, que no le dice nada a nadie.
if not exist "%PYW%" (
  echo.
  echo ======================================================================
  echo   NO SE HA PODIDO ABRIR EL AGENTE
  echo ======================================================================
  echo.
  echo   Falta pythonw.exe en la instalacion de Python.
  echo   Hay que reinstalar Python desde python.org.
  echo.
  echo   Avisa a Emili y ensenale esta ventana.
  echo.
  pause
  exit /b 1
)

if not exist "datos" mkdir "datos"

REM Arranque de prueba: si el programa se cae al empezar, se ve AQUI y la
REM ventana no se cierra. Si arranca bien, se relanza sin consola y se sale.
"%PY%" -c "import interfaz" >datos\arranque.log 2>&1
if errorlevel 1 (
  echo.
  echo ======================================================================
  echo   NO SE HA PODIDO ABRIR EL AGENTE
  echo ======================================================================
  echo.
  echo   El programa no arranca.
  echo.
  type datos\arranque.log
  echo.
  echo   Avisa a Emili y ensenale esta ventana.
  echo.
  pause
  exit /b 1
)

start "" "%PYW%" interfaz.py %*
exit /b 0
