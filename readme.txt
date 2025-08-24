ScanSorter (Windows + Synology) — README

A small, reliable tool that watches a scanner drop folder, extracts text from new PDFs/images, detects a topic and document date, then files the document into local and NAS folders using the pattern:

  <LOCAL_BASE>\<Topic>\YYYY-MM-DD_<Topic>.<ext>
  <NAS_BASE>\<Topic>\YYYY-MM-DD_<Topic>.<ext>   (if reachable)

Optionally, it emails you a short summary and attaches the filed document.

---------------------------------------------------------------------
FEATURES
---------------------------------------------------------------------
- PDF text extraction (direct) + OCR fallbacks (Tesseract).
- Works without Poppler (pypdfium2 OCR fallback).
- Topic detection via configurable topics.json (+ filename hints).
- Document date parsing (German formats); fallback to scan timestamp.
- Staging folder to avoid file-lock issues during scanning.
- Optional email notification with attachment.
- Clean, modular package layout.

---------------------------------------------------------------------
REQUIREMENTS
---------------------------------------------------------------------
- Windows 10/11
- Python 3.12+
- Tesseract OCR (Windows installer, include German language if possible)
- Optional: Poppler for faster pdf2image (pypdfium2 fallback works fine)

---------------------------------------------------------------------
PROJECT LAYOUT
---------------------------------------------------------------------
scanscript/
  scan_sorter.py                # CLI entry point
  topics.json                   # (optional) your custom topics
  email.json                    # non-sensitive mail settings (tracked)
  email.secrets.json            # secrets (NOT tracked)
  scansorter/
    __init__.py
    config.py
    logger.py
    ocr.py
    dates.py
    topics.py
    file_ops.py
    processor.py
    watcher.py

---------------------------------------------------------------------
QUICK START
---------------------------------------------------------------------
1) Open PowerShell in the project root (scanscript\):
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   py -m pip install --upgrade pip
   pip install pdfplumber pdf2image pytesseract pillow pypdfium2

2) Run in watch mode:
   python .\scan_sorter.py --watch --poll 60 --debug

3) Drop a PDF into C:\Users\sschu\Documents\Scan
   The file will be sorted into C:\Users\sschu\Documents\Belege\<Topic>\...

---------------------------------------------------------------------
CONFIGURATION
---------------------------------------------------------------------
1) Paths & folders (scansorter/config.py)
   SCAN_DIR   = r"C:\Users\sschu\Documents\Scan"
   LOCAL_BASE = r"C:\Users\sschu\Documents\Belege"
   NAS_BASE   = r"Z:\\"

2) Topics (topics.json, optional)
   {
     "Toom": ["toom", "toom baumarkt", "baumarkt", "renovierung", "baustoffe"],
     "Strom": ["strom", "energie", "stromrechnung", "ewe", "vattenfall"],
     "Internet": ["internet", "dsl", "kabel", "router", "telekom", "vodafone"],
     "Sonstiges": []
   }

3) Email (optional)
   - email.json (tracked, without passwords):
     {
       "enabled": true,
       "smtp_host": "smtp.gmail.com",
       "smtp_port": 465,
       "security": "SSL",
       "from_addr": "you@example.com",
       "to_addrs": ["you@example.com"],
       "username": "you@example.com"
     }

   - email.secrets.json (NOT tracked, add to .gitignore):
     { "password": "APP-PASSWORD-HERE" }

   - Or set a user-level environment variable instead of secrets file:
     [Environment]::SetEnvironmentVariable("SCANSORTER_SMTP_PASS","APP-PASSWORD-HERE","User")

   - Outlook/Office365 tip: host smtp.office365.com, port 587, security STARTTLS

4) .gitignore (repo root)
   __pycache__/
   *.pyc
   .venv/
   .vscode/
   .idea/
   email.secrets.json
   *.secrets.json
   .env

---------------------------------------------------------------------
RUNNING
---------------------------------------------------------------------
Watch mode (recommended):
  python .\scan_sorter.py --watch --poll 1800 --debug   # every 30 minutes

Single pass (process current files only):
  python .\scan_sorter.py

Flags:
  --watch    keep watching the folder
  --poll     seconds between scans (watch mode only)
  --debug    verbose logs

---------------------------------------------------------------------
AUTOSTART ON WINDOWS
---------------------------------------------------------------------
A) Startup folder:
  Create runsorter.bat in project root:
    @echo off
    setlocal
    cd /d "%~dp0"
    if exist ".venv\Scripts\activate.bat" (
      call ".venv\Scripts\activate.bat"
    ) else (
      echo Missing venv. Create with: py -m venv .venv
      pause
      exit /b 1
    )
    python scan_sorter.py --watch --poll 1800 --debug >> sorter.log 2>&1

  Put a shortcut to runsorter.bat into: shell:startup

B) Task Scheduler:
  - Trigger: At logon
  - Action: Start program -> cmd.exe /c runsorter.bat
  - Start in: your project folder
  - “Run only when user is logged on” (mapped drives visible)

---------------------------------------------------------------------
TROUBLESHOOTING
---------------------------------------------------------------------
- Topic falls back to “Sonstiges”:
  * Extend keywords in topics.json, enable --debug to inspect hits

- Poppler warning (“Unable to get page count”):
  * Harmless if OCR(pypdfium2) follows; install Poppler only for speed

- File in use / cannot delete:
  * Staging + quarantine handle locks; external locks may still delay deletion

- Email send failed:
  * Verify host/port/security, use app passwords, or env var for password

- NAS copy fails:
  * Make sure the drive letter is mounted at login; use Task Scheduler option
    “Run only when user is logged on”

---------------------------------------------------------------------
LICENSE & CONTACT
---------------------------------------------------------------------
- License: Non-commercial use permitted. For commercial use, contact:
  contact@sebastian-schult-dev.de
- Full license text: see license.txt

Copyright (c) 2025 Sebastian Schult
