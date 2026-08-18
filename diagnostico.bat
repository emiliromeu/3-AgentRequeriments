@echo off
REM ====================================================================
REM  UNA LINEA Y UN FICHERO QUE ENVIAR. Windows.
REM
REM  Existe porque "haz doble clic en comprobar_equipo y ensename lo que
REM  salga" no ha traido nunca nada de vuelta. Leer una ventana negra y
REM  copiarla a mano no es una tarea razonable para nadie: lo que hace
REM  falta es UN FICHERO que se pueda adjuntar.
REM
REM  Esto ejecuta lo mismo que comprobar_equipo, guarda TODO en
REM  diagnostico.txt y lo abre en el Bloc de notas. Cero llamadas a la
REM  API: no consulta nada y no cuesta nada.
REM
REM  Las reglas de Windows son las de comprobar_equipo.bat, y por los
REM  mismos motivos: python.exe y no pythonw -sin consola no se escribe
REM  nada-, todo entre comillas por si la carpeta lleva espacios, cd /d
REM  a la carpeta del .bat y despues caminos relativos, mensajes sin
REM  tildes, y ni un parentesis dentro de un echo.
REM ====================================================================

setlocal enableextensions
title Diagnostico del agente

cd /d "%~dp0" 2>nul
if errorlevel 1 goto sin_carpeta

if not exist "comprobar_equipo.py" goto sin_ficheros

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

:tiene_python
echo.
echo   Recogiendo el diagnostico. Tarda unos segundos.
echo.
REM Se borra el de antes: un fichero viejo enviado como si fuera de hoy
REM manda a mirar un fallo que ya no existe.
if exist "diagnostico.txt" del "diagnostico.txt" >nul 2>&1
REM La salida de error va al mismo sitio que la normal: si lo que falla
REM es el propio comprobador, eso es EXACTAMENTE lo que hay que ver.
"%PY%" %PYARG% "comprobar_equipo.py" > "diagnostico.txt" 2>&1
echo   Listo. Se abre el fichero: enviaselo a Emili tal cual.
echo.
echo   Esta guardado aqui:
echo   %CD%\diagnostico.txt
echo.
start "" notepad "diagnostico.txt"
pause
exit /b 0

:sin_python
echo.
echo   No hay Python en este equipo, que es el programa base que el
echo   agente necesita. Sin el no se puede ni diagnosticar.
echo.
echo   QUE HAY QUE HACER:
echo   Instalalo desde python.org y marca la casilla 'Add Python to
echo   PATH'. Marca tambien 'tcl/tk and IDLE', que es lo que dibuja la
echo   ventana del agente.
echo.
pause
exit /b 1

:sin_carpeta
echo.
echo   No se ha podido entrar en la carpeta del agente.
echo   Suele pasar cuando se abre desde una carpeta de red.
echo.
echo   QUE HAY QUE HACER:
echo   Copia la carpeta del agente al disco de este equipo, por ejemplo
echo   al Escritorio, y vuelve a probar.
echo.
pause
exit /b 1

:sin_ficheros
echo.
echo   Falta un fichero del agente: la carpeta esta incompleta en este
echo   equipo. Avisa a Emili.
echo.
pause
exit /b 1
