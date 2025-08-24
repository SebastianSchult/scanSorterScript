@echo off
setlocal
cd /d "%~dp0"

REM Warte auf Netzwerk/NAS
timeout /t 20 /nobreak >nul

REM UTF-8 fuer Konsole/Python
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

REM venv-Python direkt (keine Aktivierung nötig)
set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
  echo Virtuelle Umgebung nicht gefunden: "%PYEXE%"
  echo Bitte im Projektordner ausfuehren:
  echo   py -m venv .venv
  echo   .\.venv\Scripts\pip.exe install pdfplumber pdf2image pytesseract pillow pypdfium2
  exit /b 1
)

REM Optional: SMTP/Poppler
REM set "SCANSORTER_SMTP_PASS=DEIN-APP-ODER-SMTP-PASSWORT"
REM set "POPPLER_PATH=C:\Program Files\poppler-xx\Library\bin"

REM Live-Konsole UND Logfile (unbuffered Python)
start "" powershell -NoExit -ExecutionPolicy Bypass -Command "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); $env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONUNBUFFERED='1'; & '%PYEXE%' -u '%~dp0scan_sorter.py' --watch --poll 900 --debug 2>&1 | Tee-Object -FilePath '%~dp0sorter.log' -Append"

exit /b 0
