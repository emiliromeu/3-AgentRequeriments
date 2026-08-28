@echo off
REM ====================================================================
REM  Doble clic para reparar una copia que no se puede actualizar.
REM  Windows. El gemelo de reparar.command.
REM
REM  Aqui la ventana negra SI se queda abierta: es lo que hay que leer.
REM  Todos los caminos acaban escribiendo algo y en un "pause": no hay
REM  ni una salida silenciosa.
REM
REM  Solo hace las dos cosas que Python no puede hacerse a si mismo:
REM  encontrar un Python y recuperar reparar.py si falta. Todo lo demas
REM  esta en reparar.py, en un solo sitio.
REM
REM  LO PRIMERO ES RECUPERAR reparar.py. Esto lo ejecuta quien tiene el
REM  arbol a medias, y un checkout abortado por rutas largas puede
REM  haberse llevado por delante justo el fichero que viene a arreglarlo.
REM
REM  Las reglas de siempre de este proyecto para los .bat:
REM   - python.exe, NO pythonw.exe: pythonw no tiene consola y aqui hay
REM     que leer lo que sale.
REM   - Todo entre comillas: la carpeta puede tener espacios.
REM   - cd a la carpeta del .bat y despues todo por camino relativo.
REM   - Mensajes sin tildes: la consola no siempre va en UTF-8.
REM   - Nada de parentesis dentro de un "echo": cierran el bloque.
REM ====================================================================

setlocal enableextensions
title Reparar la copia

cd /d "%~dp0" 2>nul
if errorlevel 1 goto sin_carpeta

echo.
echo ======================================================================
echo   REPARAR LA COPIA
echo ======================================================================
echo.

REM ---- 1. Sin git no hay nada que hacer ------------------------------
git --version >nul 2>&1
if errorlevel 1 goto sin_git

REM ---- 2. Recuperar reparar.py si falta ------------------------------
if exist "reparar.py" goto hay_guion
echo   Falta reparar.py: se recupera de GitHub.
git fetch --quiet >nul 2>&1
git checkout FETCH_HEAD -- reparar.py >nul 2>&1
if exist "reparar.py" goto hay_guion
git checkout HEAD -- reparar.py >nul 2>&1
if exist "reparar.py" goto hay_guion
goto sin_guion

:hay_guion

REM ---- 3. Buscar un Python -------------------------------------------
REM Orden: el del entorno, el lanzador oficial "py", y python del PATH.
REM Cada uno se PRUEBA de verdad, no se da por bueno porque exista.
set "PY="
if not exist ".venv\Scripts\python.exe" goto probar_py
".venv\Scripts\python.exe" -c "pass" >nul 2>&1
if errorlevel 1 goto probar_py
set "PY=.venv\Scripts\python.exe"
goto con_python

:probar_py
py -3 -c "pass" >nul 2>&1
if errorlevel 1 goto probar_python
set "PY=py -3"
goto con_python

:probar_python
python -c "pass" >nul 2>&1
if errorlevel 1 goto sin_python
set "PY=python"

:con_python
%PY% reparar.py %*
set CODIGO=%errorlevel%
echo.
pause
exit /b %CODIGO%

:sin_carpeta
echo.
echo   No se ha podido entrar en la carpeta del agente.
echo   Avisa a Emili.
echo.
pause
exit /b 1

:sin_git
echo   No hay git en este equipo, y sin git no se puede reparar nada.
echo   Avisa a Emili.
echo.
pause
exit /b 1

:sin_guion
echo   No se ha podido recuperar reparar.py.
echo   Avisa a Emili.
echo.
pause
exit /b 1

:sin_python
echo   No hay Python en este equipo.
echo   Instalalo desde python.org y vuelve a intentarlo.
echo.
pause
exit /b 1
