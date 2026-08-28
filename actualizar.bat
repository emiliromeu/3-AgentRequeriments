@echo off
REM ====================================================================
REM  TRAER LA VERSION NUEVA DEL AGENTE. Windows.
REM
REM  Lo pulsa una PERSONA. Nada se actualiza solo, y esa es la decision
REM  de fondo: un pull automatico que falle a medias deja el arbol roto
REM  -«unable to checkout working tree»- y quien lo sufre es quien tenia
REM  que consultar algo en ese momento. La ventana AVISA; aqui se decide.
REM
REM  Cero llamadas a la API. Habla con GitHub, no con el modelo.
REM
REM  ORDEN DE LAS COMPROBACIONES, y es el que importa: cada una se hace
REM  ANTES de la que podria romper algo, no despues.
REM
REM    1) hay git
REM    2) esto es un repositorio
REM    3) core.longpaths puesto      <- ANTES de tocar el arbol
REM    4) no hay nada sin guardar    <- ANTES de tocar el arbol
REM    5) se puede hablar con el remoto  <- fetch, que NO toca el arbol
REM    6) y solo entonces, el pull
REM
REM  Las reglas de Windows son las de comprobar_equipo.bat y por los
REM  mismos motivos: todo entre comillas, cd /d a la carpeta del .bat,
REM  mensajes sin tildes, ni un parentesis dentro de un echo, y todas
REM  las salidas con su frase y su pause.
REM ====================================================================

setlocal enableextensions
title Actualizar el agente

cd /d "%~dp0" 2>nul
if errorlevel 1 goto sin_carpeta

echo.
echo ======================================================================
echo   ACTUALIZAR EL AGENTE
echo ======================================================================
echo.

REM ---- 1) hay git ---------------------------------------------------
git --version >nul 2>&1
if errorlevel 1 goto sin_git

REM ---- 2) esto es un repositorio ------------------------------------
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 goto sin_repo

REM ---- 3) core.longpaths, ANTES de tocar nada -----------------------
REM  Windows corta las rutas a 260 caracteres CONTANDO la carpeta del
REM  usuario. Si un fichero del repositorio se pasa, `git checkout`
REM  aborta A MITAD y deja medio arbol escrito: el peor de los finales.
REM  Se pone siempre, y solo para este repositorio: no se toca la
REM  configuracion global de la maquina de nadie.
for /f "delims=" %%C in ('git config --get core.longpaths 2^>nul') do set "LP=%%C"
if /i "%LP%"=="true" goto longpaths_ok
echo   [1/4] Rutas largas ................. activandolas
git config core.longpaths true
if errorlevel 1 goto sin_longpaths
goto longpaths_hecho
:longpaths_ok
echo   [1/4] Rutas largas ................. ya estaban
:longpaths_hecho

REM ---- 4) nada sin guardar, ANTES de tocar nada ---------------------
REM  Un pull sobre cambios locales para a mitad o los pisa. Las dos
REM  cosas son peores que no actualizar, asi que aqui NO se decide por
REM  nadie: se para y se dice.
set "SUCIO="
for /f "delims=" %%S in ('git status --porcelain 2^>nul') do set "SUCIO=1"
if defined SUCIO goto hay_cambios
echo   [2/4] Cambios sin guardar .......... ninguno

REM ---- 5) se puede hablar con el remoto -----------------------------
REM  EL FETCH NO TOCA EL ARBOL DE TRABAJO: solo trae referencias. Por
REM  eso se hace ANTES del pull. Si el repositorio es privado y esta
REM  maquina no tiene credenciales, falla AQUI, sin haber movido nada,
REM  y se dice en cristiano en vez de con un error de git.
echo   [3/4] Hablando con GitHub ..........
git fetch --quiet
if errorlevel 1 goto sin_remoto
echo         se puede

REM  ¿Hay algo nuevo?
set "PENDIENTE="
for /f "delims=" %%P in ('git rev-list --count HEAD..@{u} 2^>nul') do set "PENDIENTE=%%P"
if not defined PENDIENTE goto sin_rama
if "%PENDIENTE%"=="0" goto al_dia
echo   [4/4] Novedades .................... %PENDIENTE% cambio^(s^)

REM ---- 6) y solo ahora, el pull -------------------------------------
git pull --ff-only
if errorlevel 1 goto pull_fallido

echo.
echo ======================================================================
echo   ACTUALIZADO
echo ======================================================================
echo.
echo   Ya puedes cerrar esta ventana y abrir el agente.
echo.
pause
exit /b 0

REM ---- Caminos de fallo, todos con su frase y su solucion -----------
:al_dia
echo   [4/4] Novedades .................... ninguna
echo.
echo   Ya tienes la ultima version. No hay nada que traer.
echo.
pause
exit /b 0

:pull_fallido
echo.
echo ======================================================================
echo   NO SE HA PODIDO ACTUALIZAR
echo ======================================================================
echo.
echo   El pull ha fallado. Lo importante: MIRA LA LINEA DE ARRIBA, que es
echo   lo que dice git.
echo.
echo   El agente sigue funcionando con la version que ya tenias: esto no
echo   ha roto nada. Lo que no tienes son los cambios nuevos.
echo.
echo   QUE HAY QUE HACER:
echo   Haz doble clic en "diagnostico" y enviale a Emili el fichero
echo   diagnostico.txt que deja al lado, junto con lo que pone arriba.
echo.
pause
exit /b 1

:hay_cambios
echo   [2/4] Cambios sin guardar .......... LOS HAY
echo.
echo   Hay ficheros modificados en esta carpeta y no se actualiza encima:
echo   el pull podria pararse a mitad o borrarlos.
echo.
git status --short
echo.
echo   QUE HAY QUE HACER:
echo   Casi siempre son ficheros que escribe el propio agente, y entonces
echo   esto se arregla solo. Doble clic en:   reparar.bat
echo   Si quieres ver antes que haria, sin que toque nada:
echo       reparar.bat --revisar
echo.
echo   Si reparar.bat dice que hay cambios que no reconoce, avisa a Emili
echo   y ensenale esa lista. No borres nada.
echo.
pause
exit /b 1

:sin_remoto
echo         NO se puede
echo.
echo ======================================================================
echo   NO SE PUEDE HABLAR CON GITHUB
echo ======================================================================
echo.
echo   No se ha podido conectar con el sitio donde vive el agente.
echo   No se ha tocado nada: el agente sigue igual que antes.
echo.
echo   Suele ser una de estas tres:
echo     - este equipo no tiene permiso para bajar el proyecto
echo     - no hay internet, o lo bloquea la red de la oficina
echo     - la contrasena de GitHub guardada aqui ha caducado
echo.
echo   QUE HAY QUE HACER:
echo   Avisa a Emili. Es cosa de permisos, no algo que se arregle desde
echo   este equipo.
echo.
pause
exit /b 1

:sin_longpaths
echo.
echo   No se ha podido activar el soporte de rutas largas.
echo   Sin el, la actualizacion podria quedarse a medias.
echo.
echo   QUE HAY QUE HACER:
echo   Avisa a Emili: hace falta una version de Git mas nueva en este
echo   equipo.
echo.
pause
exit /b 1

:sin_git
echo   No hay Git en este equipo, que es el programa que trae las
echo   actualizaciones.
echo.
echo   QUE HAY QUE HACER:
echo   Avisa a Emili: hay que instalarlo una vez.
echo.
pause
exit /b 1

:sin_repo
echo   Esta carpeta no es una copia del proyecto, sino ficheros sueltos.
echo   No se puede actualizar asi.
echo.
echo   QUE HAY QUE HACER:
echo   Avisa a Emili: hay que volver a instalar el agente en este equipo.
echo.
pause
exit /b 1

:sin_rama
echo   [4/4] Novedades .................... no se ha podido saber
echo.
echo   Esta copia no esta enlazada con el proyecto de GitHub, asi que no
echo   se sabe si hay novedades. No se ha tocado nada.
echo.
echo   QUE HAY QUE HACER:
echo   Avisa a Emili.
echo.
pause
exit /b 1

:sin_carpeta
echo   No se ha podido entrar en la carpeta del agente.
echo   Suele pasar cuando se abre desde una carpeta de red.
echo.
echo   QUE HAY QUE HACER:
echo   Copia la carpeta al disco de este equipo y vuelve a probar.
echo.
pause
exit /b 1
