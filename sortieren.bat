@echo off
cd /d "%~dp0"

if not exist ".dev\sortierer.py" goto :fehlt_ordner

rem Es reicht NICHT, nur zu pruefen ob "py" existiert: Windows 10 und 11
rem legen Platzhalter fuer py.exe und python.exe an, die beim Aufruf nur
rem den Microsoft Store oeffnen und sich sofort beenden. Deshalb wird hier
rem echter Python-Code ausgefuehrt - das schafft nur ein echtes Python.
set "PYSTART="

py -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYSTART=py"
if defined PYSTART goto :starten

python -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYSTART=python"
if defined PYSTART goto :starten

goto :kein_python

:starten
%PYSTART% ".dev\sortierer.py"
if errorlevel 1 goto :abgebrochen
exit /b


:fehlt_ordner
echo.
echo   Der Ordner ".dev" fehlt - ohne ihn kann nicht sortiert werden.
echo.
echo   ACHTUNG: ".dev" ist ein VERSTECKTER Ordner. Beim Kopieren auf einen
echo   anderen Computer wird er deshalb leicht vergessen.
echo.
echo   So geht es richtig: NICHT den Inhalt kopieren, sondern den ganzen
echo   Ordner. Also eine Ebene hoeher gehen, den Ordner selbst anklicken
echo   und den kopieren - dann kommt ".dev" automatisch mit.
echo.
echo   Zur Kontrolle: im Explorer unter Ansicht - Einblenden - Ausgeblendete
echo   Elemente den Haken setzen. Dann muss ".dev" zu sehen sein.
echo.
pause
exit /b


:kein_python
echo.
echo   Auf diesem Computer laeuft kein Python.
echo.
echo   Falls beim Tippen von "python" der Microsoft Store aufgeht:
echo   das ist nur ein Platzhalter, kein echtes Python.
echo.
echo   Bitte hier herunterladen:  https://www.python.org/downloads/
echo   Beim Installieren unbedingt den Haken setzen bei:
echo       "Add python.exe to PATH"
echo.
echo   Danach diese Datei hier einfach noch einmal anklicken.
echo.
pause
exit /b


:abgebrochen
echo.
echo   Das Programm wurde unerwartet beendet.
echo   Einzelheiten stehen in  .dev\sortier-log.txt
echo.
pause
exit /b
