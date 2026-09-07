@echo off
rem Diese Datei liegt im Ordner ".dev" und arbeitet auf dem Ordner darueber.
cd /d "%~dp0"

if not exist "sortierer.py" goto :fehlt_datei

rem Siehe sortieren.bat: "py" kann ein Store-Platzhalter sein, deshalb
rem wird hier echter Python-Code zur Probe ausgefuehrt.
set "PYSTART="

py -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYSTART=py"
if defined PYSTART goto :starten

python -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYSTART=python"
if defined PYSTART goto :starten

goto :kein_python

:starten
%PYSTART% "sortierer.py" --test
if errorlevel 1 goto :abgebrochen
exit /b


:fehlt_datei
echo.
echo   Die Datei sortierer.py fehlt in diesem Ordner.
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
pause
exit /b


:abgebrochen
echo.
echo   Das Programm wurde unerwartet beendet.
echo   Einzelheiten stehen in  sortier-log.txt
echo.
pause
exit /b
