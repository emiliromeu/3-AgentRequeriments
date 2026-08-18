@echo off
REM ====================================================================
REM  Doble clic para medir el uso de este equipo. Windows.
REM
REM  Aqui la ventana negra SI se queda abierta: es lo que hay que leer.
REM  Lo que no puede pasar es que se quede abierta y VACIA, asi que
REM  todos los caminos de este fichero acaban escribiendo algo y en un
REM  "pause". No hay ni una salida silenciosa.
REM
REM  Este fichero solo busca un Python y llama a medir_uso.py,
REM  que es donde esta la medicion. Cero red y cero API. Cero llamadas a la API.
REM
REM  Cosas de Windows que estan puestas a proposito:
REM
REM   - Se usa python.exe, NO pythonw.exe. pythonw no tiene consola: con
REM     el, este diagnostico no escribiria nada y la ventana saldria en
REM     blanco. pythonw es para abrir_agente.bat, que si quiere ocultar
REM     la consola. Aqui es justo al reves.
REM   - Todo entre comillas: la carpeta puede llamarse
REM     "Documents\agente requeriments", con espacio, y sin comillas eso
REM     se parte en dos y no arranca nada.
REM   - Primero se hace cd a la carpeta del .bat y luego se llama a todo
REM     por camino RELATIVO. Asi los espacios y las tildes de la ruta
REM     completa dejan de importar: nadie los vuelve a tocar.
REM   - Los mensajes van sin tildes. La consola de Windows no siempre va
REM     en UTF-8, y una tilde mal codificada estropea la linea entera.
REM   - Nada de parentesis dentro de los "echo": en un .bat cierran el
REM     bloque y rompen el fichero. Por eso se usan etiquetas y "goto"
REM     en vez de bloques if anidados.
REM ====================================================================

setlocal enableextensions
title Uso de este equipo

REM %~dp0 es la carpeta de ESTE fichero, con la barra final ya puesta.
REM El /d hace falta para cambiar tambien de unidad, p.ej. de C: a D:.
cd /d "%~dp0" 2>nul
if errorlevel 1 goto sin_carpeta

if not exist "medir_uso.py" goto sin_ficheros

REM ---- 1) Buscar un Python ------------------------------------------
REM Orden: el del entorno, que es el que abre el agente de verdad; luego
REM el lanzador oficial "py"; y por ultimo "python" del PATH. Cada uno
REM se PRUEBA de verdad, no se da por bueno porque el fichero exista:
REM en Windows "python" suele ser un acceso directo a la Tienda que no
REM ejecuta nada.

set "PY="
set "PYARG="

if exist ".venv\Scripts\python.exe" goto probar_venv
goto probar_py

:probar_venv
".venv\Scripts\python.exe" -c "pass" >nul 2>&1
if errorlevel 1 goto probar_py
set "PY=.venv\Scripts\python.exe"
goto tiene_python

:probar_py
py -3 -c "pass" >nul 2>&1
if errorlevel 1 goto probar_python
set "PY=py"
set "PYARG=-3"
goto tiene_python

:probar_python
python -c "pass" >nul 2>&1
if errorlevel 1 goto sin_python
set "PY=python"
goto tiene_python

REM ---- 2) Lanzar las comprobaciones ---------------------------------
:tiene_python
"%PY%" %PYARG% "medir_uso.py"
REM Fuera de un bloque con parentesis, %ERRORLEVEL% se lee bien. Dentro
REM de uno se leeria el valor de ANTES, que es el fallo clasico del .bat.
set "CODIGO=%ERRORLEVEL%"
echo.
echo   ------------------------------------------------------------------
echo   Cuando termines de leer, cierra esta ventana.
echo.
pause
exit /b %CODIGO%

REM ---- Caminos de fallo, todos con su frase y su solucion -----------
:sin_python
echo.
echo ======================================================================
echo   USO DE ESTE EQUIPO
echo ======================================================================
echo.
echo   FALTA PYTHON
echo.
echo     No hay Python en este equipo, que es el programa base que el
echo     agente necesita para funcionar.
echo.
echo     QUE HAY QUE HACER:
echo     Instalalo desde python.org y marca la casilla 'Add Python to
echo     PATH' durante la instalacion. Marca tambien 'tcl/tk and IDLE',
echo     que es lo que dibuja la ventana del agente.
echo.
echo ======================================================================
echo   NO SE HA PODIDO MEDIR EL USO
echo.
echo     Falta Python en este equipo.
echo.
echo ======================================================================
echo.
pause
exit /b 1

:sin_carpeta
echo.
echo   No se ha podido entrar en la carpeta del agente.
echo.
echo   Suele pasar cuando el agente se abre desde una carpeta de red.
echo.
echo   QUE HAY QUE HACER:
echo   Copia la carpeta del agente al disco de este equipo, por ejemplo
echo   al Escritorio, y vuelve a hacer doble clic aqui.
echo.
pause
exit /b 1

:sin_ficheros
echo.
echo   Falta un fichero del agente y no se puede medir el uso.
echo.
echo   QUE HAY QUE HACER:
echo   Avisa a Emili: la carpeta del agente esta incompleta en este
echo   equipo.
echo.
pause
exit /b 1
