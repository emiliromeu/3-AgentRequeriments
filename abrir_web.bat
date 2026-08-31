@echo off
REM ABRIR EL AGENTE EN EL NAVEGADOR. Doble clic. Windows.
REM
REM ESTE FICHERO ES NUEVO Y NO SUSTITUYE A NADA TODAVIA. `abrir_agente.bat`
REM -el de siempre, con la ventana- SIGUE INTACTO y es el que usa el despacho.
REM Cuando la web este verde, el cambio es UNA LINEA: `interfaz.py` pasa a ser
REM `servidor.py` alli. La vuelta atras es esa misma linea al reves.
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
REM EL CORPUS LO DECIDE QUIEN SABE CUANTAS NORMAS HAY, NO ESTE FICHERO. Aqui
REM habia tres normas escritas a mano; cuando el corpus paso a trece, esta
REM lista se quedo igual y el camino rapido daba «todo listo» con diez normas
REM ausentes. `instalar.py --revisar` solo mira ficheros: ni corpus ni red.
"%PY%" instalar.py --revisar >nul 2>&1
if errorlevel 1 goto instalar
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

REM ---------------------------------------------------------------------
REM SIN CONSOLA NEGRA DETRAS, Y SIN PROCESO HUERFANO
REM ---------------------------------------------------------------------
REM
REM pythonw.exe abre sin consola, igual que con la ventana. La diferencia es
REM que aqui NO hay ventana que cerrar: quien decide cuando morir es el propio
REM servidor. Ver la nota de las dos senales en servidor.py.
REM
REM EL NAVEGADOR LO ABRE PYTHON con `webbrowser`, que sabe cual es el de por
REM defecto en cada equipo. Aqui habria que adivinarlo.
start "" "%PYW%" servidor.py %*

REM SI EL NAVEGADOR NO ABRIO, LA DIRECCION SE ENSENA PARA PEGARLA A MANO.
REM Con pythonw.exe no hay consola donde leer nada, asi que esta ventana se
REM queda hasta que alguien la cierre: es la unica forma de que la direccion
REM se pueda copiar si el navegador no arranco solo.
timeout /t 3 /nobreak >nul
if exist "datos\servidor.json" (
  echo.
  echo   El agente esta en marcha.
  echo   Si el navegador no se ha abierto solo, copia esta direccion:
  echo.
  "%PY%" -c "import json;d=json.load(open('datos/servidor.json'));print('      http://127.0.0.1:%%d/?t=%%s' %% (d['puerto'], d['testigo']))"
  echo.
  echo   Puedes cerrar esta ventana: el agente sigue en marcha.
  echo.
  pause
) else (
  echo.
  echo ======================================================================
  echo   EL AGENTE NO HA LLEGADO A ARRANCAR
  echo ======================================================================
  echo.
  echo   Mira datos\arranque.log y avisa a Emili.
  echo.
  pause
)
exit /b 0
