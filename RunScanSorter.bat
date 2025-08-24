@echo off
setlocal
cd /d "%~dp0"

REM (Optional) kurze Wartezeit nach dem Windows-Login, damit Laufwerke/Netzwerk bereit sind
timeout /t 20 /nobreak >nul

REM venv aktivieren
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo Virtuelle Umgebung nicht gefunden. Bitte zuerst mit "py -3.12 -m venv .venv" anlegen und Pakete installieren.
  exit /b 1
)

REM Script minimiert starten; Poll-Intervall = 1800 Sekunden (30 Minuten)
start "" /min python "%~dp0scan_sorter.py" --watch --poll 1800

exit /b 0
