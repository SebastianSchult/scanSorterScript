@echo off
setlocal
cd /d "%~dp0"

REM (Optional) kurze Wartezeit nach dem Windows-Login, damit Laufwerke/Netzwerk bereit sind
timeout /t 20 /nobreak >nul

REM Direkt den Python aus der venv verwenden (robuster als Aktivierung)
set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
  echo Virtuelle Umgebung nicht gefunden: "%PYEXE%"
  echo Bitte im Projektordner ausfuehren:
  echo   py -m venv .venv
  echo   .\.venv\Scripts\pip.exe install pdfplumber pdf2image pytesseract pillow pypdfium2
  exit /b 1
)

REM (Optional) Umgebungsvariablen, falls du keine email.secrets.json nutzt
REM set "SCANSORTER_SMTP_PASS=DEIN-APP-ODER-SMTP-PASSWORT"
REM set "POPPLER_PATH=C:\Program Files\poppler-xx\Library\bin"

REM Minimiert starten; Poll-Intervall = 1800 Sekunden (30 Minuten), mit Debug + Log
start "" /min cmd /c ""%PYEXE%" "%~dp0scan_sorter.py" --watch --poll 900 --debug >> "%~dp0sorter.log" 2>&1"

exit /b 0
