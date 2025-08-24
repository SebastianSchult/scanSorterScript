
Windows Scan-Sorter – Erste Schritte
====================================

Dieses Paket enthält:
- scan_sorter.py      → Das Python-Script
- topics.json         → Konfigurierbare Themen + Schlagwörter
- RunScanSorter.bat   → Startet das Script im Watch-Modus
- README_FIRST_STEPS.txt → Diese Anleitung

Voraussetzungen
---------------
1) Python 3.x installieren (https://www.python.org/)
2) Abhängigkeiten (optional, aber empfohlen für OCR):
     pip install pdfplumber pdf2image pytesseract pillow
   Außerdem Tesseract für Windows installieren (z. B. von UB Mannheim).
   Danach ggf. den Tesseract-Pfad zur PATH-Umgebungsvariable hinzufügen.

3) In scan_sorter.py ggf. Pfade anpassen:
   SCAN_DIR   = C:\Users\sschu\Documents\Scan
   LOCAL_BASE = C:\Users\sschu\Documents\Belege
   NAS_BASE   = Z:\

Nutzung
-------
- Einmalige Verarbeitung:
    python scan_sorter.py

- Dauerhafte Überwachung (alle 10 Sekunden):
    python scan_sorter.py --watch

  oder einfach die Batch starten:
    RunScanSorter.bat

Funktionsweise
--------------
- Das Script liest neue PDF/JPG/PNG im Scan-Ordner ein.
- Es versucht Text zu extrahieren (PDF-Text; Fallback OCR).
- Es sucht ein Datum im Dokument. Falls keins gefunden, wird das Dateidatum genutzt.
- Es ordnet das Dokument einem Thema zu (anhand topics.json).
- Es erstellt (falls nötig) einen Themenordner in LOCAL_BASE und NAS_BASE.
- Es kopiert die Datei dorthin als: YYYY-MM-DD_Thema.ext
  und löscht danach die Originaldatei im Scan-Ordner.
- Falls der Dateiname bereits existiert, hängt das Script _1, _2, ... an.

Hinweise
--------
- Themen & Schlüsselwörter kannst du in topics.json erweitern/anpassen.
- Wenn dein NAS zeitweise nicht verfügbar ist, wird nur lokal kopiert.
- Für bessere OCR-Ergebnisse setze die Sprache "deu" in Tesseract mit.
