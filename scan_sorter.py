#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan-Sorter (Windows + Synology)
- Sortiert PDF/JPG/PNG aus SCAN_DIR nach Themen (topics.json) & Datum
- Benennt: YYYY-MM-DD_Thema.ext
- Legt Ordner lokal + auf NAS an
- Watch-Modus (--watch) mit Poll-Intervall (--poll)

Neu:
- topics.json wird relativ zum Script geladen (nicht cwd).
- Debug-Modus (--debug) mit ausführlichen Logs.
- detect_topic() nutzt auch Dateiname + "entkernte" Suche ohne Sonderzeichen.
- Automatische Pfad-Erkennung für Tesseract & Poppler (Windows).
- PDF-OCR Fallback via pypdfium2, falls Poppler fehlt.
- Bis 5 Seiten PDF analysieren.
- Stabilisierung & Staging-Ordner gegen Locks.
- Datumslogik: Beleg-Datum → Fallback Scan-Datum.
- Alle Ressourcen/Handles werden explizit geschlossen.
"""

import argparse, os, re, time, json, shutil, glob, gc
from datetime import datetime
from pathlib import Path

# ---------- Konfiguration ----------
SCAN_DIR   = r"C:\Users\sschu\Documents\Scan"
LOCAL_BASE = r"C:\Users\sschu\Documents\Belege"
NAS_BASE   = r"Z:\\"  # gemountetes Synology-Laufwerk

SCRIPT_DIR = Path(__file__).resolve().parent
TOPIC_CONFIG_PATH = SCRIPT_DIR / "topics.json"

STAGING_DIR    = Path(SCAN_DIR) / "_staging"
QUARANTINE_DIR = Path(SCAN_DIR) / "_quarantine"

# ---------- Optionale Libs ----------
try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from PIL import Image
except Exception:
    Image = None

# Optionaler Fallback ohne Poppler
try:
    import pypdfium2
except Exception:
    pypdfium2 = None

DEBUG = False
def log(*a, **k):
    if DEBUG:
        print(*a, **k)

# ---------- Auto-Erkennung: Tesseract & Poppler ----------
def _guess_tesseract_exe() -> str | None:
    exe = shutil.which("tesseract")
    if exe: return exe
    for c in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.isfile(c):
            return c
    return None

def _guess_poppler_bin() -> str | None:
    env = os.environ.get("POPPLER_PATH")
    if env and os.path.isdir(env):
        return env
    for pat in (r"C:\Program Files\poppler*\Library\bin",
                r"C:\Program Files\poppler*\bin"):
        hits = sorted(glob.glob(pat), reverse=True)
        for h in hits:
            if os.path.isdir(h):
                return h
    return None

TESSERACT_EXE = _guess_tesseract_exe()
POPPLER_BIN   = _guess_poppler_bin()

if pytesseract is not None and TESSERACT_EXE:
    try:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
    except Exception:
        pass

# ---------- Topics laden ----------
def load_topics(config_path: Path) -> dict:
    defaults = {
        "Strom": ["strom", "energie", "stromrechnung", "ewe", "vattenfall"],
        "Internet": ["internet", "dsl", "kabel", "router", "tarif", "telekom", "vodafone", "o2"],
        "Telefon": ["telefon", "festnetz", "mobilfunk", "handy", "sim"],
        "Versicherung": ["versicherung", "haftpflicht", "hausrat", "kfz-versicherung", "krankenversicherung", "beitrag"],
        "Miete": ["miete", "vermieter", "nebenkosten", "betriebsabrechnung", "hausverwaltung"],
        "KFZ": ["kfz", "fahrzeug", "kennzeichen", "tüv", "hu", "au", "werkstatt", "inspektion"],
        "Bank": ["bank", "giro", "kontoauszug", "überweisung", "abbuchung", "sparkasse", "volksbank"],
        "Steuer": ["steuer", "finanzamt", "lohnsteuer", "umsatzsteuer", "elster", "bescheid"],
        "Arzt": ["arzt", "praxis", "krankenhaus", "diagnose", "rezept", "privatrechnung"],
        "Einkauf": ["rechnung", "beleg", "kassenbon", "einkauf", "markt", "supermarkt"],
        "Gehalt": ["gehalt", "lohn", "abrechnung", "arbeitgeber"],
        "Schule": ["schule", "zeugnis", "elternbrief", "klassenfahrt"],
        "Amazon": ["amazon", "bestellung", "prime"],
        "eBay": ["ebay", "kleinanzeigen", "bestellung"],
        "Spenden": ["spende", "spendenquittung", "gemeinnützig"],
        "Toom": ["toom", "toom baumarkt", "baumarkt", "renovierung", "baustoffe"],
        "Stadt Cuxhaven": ["cuxhaven", "stadt", "abfall", "müll", "muell", "wasser", "gebühren", "gebuehren"],
        "Sonstiges": []
    }
    if not config_path.exists():
        log(f"[DEBUG] topics.json NICHT gefunden → Defaults")
        return defaults
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_topics = json.load(f)
        log(f"[DEBUG] topics.json geladen: {config_path}")
        return user_topics
    except Exception as e:
        print(f"⚠️ Konnte topics.json nicht laden ({e}) → nutze Defaults")
        return defaults

# ---------- OCR Helper ----------
def _ocr_image_to_text(img) -> str:
    if pytesseract is None:
        return ""
    try:
        return pytesseract.image_to_string(img, lang="deu")
    except Exception as e:
        if "Failed loading language 'deu'" in str(e) or "Error opening data file" in str(e):
            try:
                return pytesseract.image_to_string(img, lang="eng")
            except Exception:
                return ""
        return ""

# ---------- Text-Extraktion ----------
def extract_text_from_pdf(pdf_path: str, max_pages: int = 5) -> str:
    text = ""
    # 1) Direkter Text via pdfplumber
    if pdfplumber is not None:
        try:
            with open(pdf_path, "rb") as fh:
                with pdfplumber.open(fh) as pdf:
                    for page in pdf.pages[:max_pages]:
                        text += page.extract_text() or ""
            if text.strip():
                log(f"[DEBUG] pdfplumber Textlen={len(text)}")
                return text.strip()
        except Exception as e:
            log(f"[DEBUG] pdfplumber-Fehler: {e}")

    # 2) OCR via pdf2image + pytesseract (Poppler optional)
    if convert_from_path is not None and pytesseract is not None:
        images = None
        try:
            kwargs = {}
            if POPPLER_BIN:
                kwargs["poppler_path"] = POPPLER_BIN
            images = convert_from_path(pdf_path, first_page=1, last_page=max_pages, **kwargs)
            for img in images:
                try:
                    text += "\n" + _ocr_image_to_text(img)
                finally:
                    try: img.close()
                    except Exception: pass
            if text.strip():
                log(f"[DEBUG] OCR(pdf2image) Textlen={len(text)}  (Poppler='{POPPLER_BIN}')")
                return text.strip()
        except Exception as e:
            log(f"[DEBUG] pdf2image/pytesseract-Fehler: {e}")
        finally:
            images = None

    # 3) OCR via pypdfium2 + pytesseract (kein Context Manager!)
    if pypdfium2 is not None and pytesseract is not None:
        try:
            pdf = pypdfium2.PdfDocument(pdf_path)  # <-- NICHT als "with" benutzen
            try:
                n = min(max_pages, len(pdf))
                for i in range(n):
                    page = pdf[i]
                    pil = None
                    try:
                        pil = page.render(scale=2).to_pil()
                        text += "\n" + _ocr_image_to_text(pil)
                    finally:
                        try:
                            if pil: pil.close()
                        except Exception:
                            pass
                        try:
                            page.close()
                        except Exception:
                            pass
            finally:
                try:
                    pdf.close()   # falls vorhanden; sonst ignorieren
                except Exception:
                    pass
            if text.strip():
                log(f"[DEBUG] OCR(pypdfium2) Textlen={len(text)}")
                return text.strip()
        except Exception as e:
            log(f"[DEBUG] pypdfium2/pytesseract-Fehler: {e}")

    log(f"[DEBUG] Kein Text aus PDF extrahiert")
    return text.strip()


def extract_text_from_image(image_path: str) -> str:
    if pytesseract is None or Image is None:
        log(f"[DEBUG] Bild-OCR nicht verfügbar (pytesseract={bool(pytesseract)}, PIL={bool(Image)})")
        return ""
    try:
        with Image.open(image_path) as img:
            txt = _ocr_image_to_text(img)
        log(f"[DEBUG] Bild-OCR Textlen={len(txt)}")
        return txt
    except Exception as e:
        log(f"[DEBUG] Bild-OCR Fehler: {e}")
        return ""

# ---------- Datum ----------
DATE_PATTERNS = [
    r"(\b\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}\b)",
    r"(\b\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}\b)",
    r"(\b\d{1,2}\.\s*[A-Za-zäöüÄÖÜ]+\.?\s*\d{4}\b)",
]
GER_MONTHS = {
    "januar":1,"februar":2,"märz":3,"maerz":3,"april":4,"mai":5,"juni":6,
    "juli":7,"august":8,"september":9,"oktober":10,"november":11,"dezember":12
}
def parse_date(raw: str) -> datetime | None:
    s = raw.strip()
    for sep in (".","-","/"):
        parts = s.split(sep)
        if len(parts)==3 and len(parts[0])<=2 and len(parts[1])<=2:
            try:
                d,m,y = int(parts[0]),int(parts[1]),int(parts[2])
                if y<100: y+=2000
                return datetime(y,m,d)
            except: pass
    for sep in ("-",".","/"):
        parts = s.split(sep)
        if len(parts)==3 and len(parts[0])==4:
            try:
                y,m,d = int(parts[0]),int(parts[1]),int(parts[2])
                return datetime(y,m,d)
            except: pass
    m = re.search(r"(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\.?\s*(\d{4})", s)
    if m:
        try:
            d = int(m.group(1)); name = m.group(2).lower().replace("ä","ae").replace("ö","oe").replace("ü","ue")
            y = int(m.group(3))
            months = {k.replace("ä","ae").replace("ö","oe").replace("ü","ue"):v for k,v in GER_MONTHS.items()}
            if name in months: return datetime(y, months[name], d)
        except: pass
    return None

def find_date_in_text(text: str) -> datetime | None:
    for pat in DATE_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            dt = parse_date(m.group(1))
            if dt: return dt
    return None

# ---------- Scan-Datum (Fallback) ----------
def get_scan_datetime(path: str) -> datetime:
    for getter in (os.path.getctime, os.path.getmtime):
        try:
            return datetime.fromtimestamp(getter(path))
        except Exception:
            continue
    return datetime.now()

# ---------- Thema ----------
def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]", "", s.lower())

def detect_topic(text: str, topics: dict, filename: str = "") -> tuple[str, list[str]]:
    hay = (text + "\n" + (filename or "")).lower()
    norm_hay = _normalize(hay)
    best_topic, best_score, matched = "Sonstiges", 0, []
    for topic, kws in topics.items():
        if not kws: continue
        score = 0
        hits = []
        for kw in kws:
            kw = (kw or "").strip().lower()
            if not kw: continue
            if re.search(rf"\b{re.escape(kw)}\b", hay, flags=re.IGNORECASE):
                score += 1; hits.append(kw); continue
            if _normalize(kw) and _normalize(kw) in norm_hay:
                score += 1; hits.append(kw)
        if score > best_score:
            best_topic, best_score, matched = topic, score, hits
    return best_topic, matched

def safe_name(name: str) -> str:
    name = re.sub(r"[<>:\"/\\|?*]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def unique_path(base_dir: str, filename: str) -> str:
    p = Path(base_dir) / filename
    if not p.exists(): return str(p)
    stem, suffix, i = p.stem, p.suffix, 1
    while True:
        cand = Path(base_dir) / f"{stem}_{i}{suffix}"
        if not cand.exists(): return str(cand)
        i += 1

# ---------- Lock-/Lösch-Helper ----------
def wait_until_free(path: str, retries: int = 15, delay: float = 1.0) -> bool:
    for _ in range(retries):
        try:
            with open(path, "rb"):
                return True
        except Exception:
            time.sleep(delay)
    return False

def safe_remove(path: str, retries: int = 10, delay: float = 3.0) -> bool:
    for _ in range(retries):
        try:
            os.remove(path)
            return True
        except PermissionError:
            time.sleep(delay)
        except FileNotFoundError:
            return True
        except Exception:
            time.sleep(delay)
    try:
        os.makedirs(QUARANTINE_DIR, exist_ok=True)
        dst = unique_path(str(QUARANTINE_DIR), Path(path).name)
        shutil.move(path, dst)
        log(f"[DEBUG] In Quarantäne verschoben: {dst}")
        return True
    except Exception:
        return False

def acquire_to_staging(src_path: str, retries: int = 20, delay: float = 1.0) -> str | None:
    os.makedirs(STAGING_DIR, exist_ok=True)
    target = unique_path(str(STAGING_DIR), Path(src_path).name)
    for _ in range(retries):
        try:
            os.replace(src_path, target)  # atomar
            log(f"[DEBUG] Staging: {src_path} -> {target}")
            return target
        except PermissionError:
            time.sleep(delay)
        except FileNotFoundError:
            return None
        except Exception:
            time.sleep(delay)
    log(f"[DEBUG] Staging fehlgeschlagen: {src_path}")
    return None

# ---------- Verarbeiten ----------
def process_file(src_path: str, topics: dict) -> None:
    ext = Path(src_path).suffix.lower()
    text = ""
    if ext == ".pdf":
        text = extract_text_from_pdf(src_path)
    elif ext in (".jpg",".jpeg",".png",".tif",".tiff",".bmp"):
        text = extract_text_from_image(src_path)

    # Datum bestimmen
    doc_dt = find_date_in_text(text) if text else None
    scan_dt = get_scan_datetime(src_path)
    dt = doc_dt or scan_dt
    date_str = dt.strftime("%Y-%m-%d")
    if doc_dt:
        log(f"[DEBUG] Beleg-Datum erkannt: {doc_dt.date()} (aus Inhalt)")
    else:
        log(f"[DEBUG] Kein Beleg-Datum gefunden – Fallback Scan-Datum: {scan_dt.date()}")

    filename = Path(src_path).name
    topic, hits = detect_topic(text or "", topics, filename)
    log(f"[DEBUG] Datei='{filename}' Topic='{topic}' Hits={hits} Textlen={len(text)}  Tess='{TESSERACT_EXE}' Poppler='{POPPLER_BIN}'")

    local_topic_dir = os.path.join(LOCAL_BASE, topic)
    nas_topic_dir   = os.path.join(NAS_BASE, topic)
    os.makedirs(local_topic_dir, exist_ok=True)
    try:
        if os.path.isdir(NAS_BASE):
            os.makedirs(nas_topic_dir, exist_ok=True)
    except Exception as e:
        log(f"[DEBUG] NAS Ordneranlage fehlgeschlagen: {e}")

    base_name = f"{date_str}_{topic}{Path(src_path).suffix.lower()}"
    base_name = safe_name(base_name)

    local_target = unique_path(local_topic_dir, base_name)
    shutil.copy2(src_path, local_target)
    try:
        if os.path.isdir(NAS_BASE):
            nas_target = unique_path(nas_topic_dir, base_name)
            shutil.copy2(src_path, nas_target)
    except Exception as e:
        log(f"[DEBUG] NAS-Kopie fehlgeschlagen: {e}")

    # alles freigeben
    gc.collect()
    if not safe_remove(src_path):
        log(f"[DEBUG] Quelle nicht löschbar und nicht verschiebbar: {src_path}")

    print(f"✅ {Path(src_path).name} → {local_target}")

def process_once() -> None:
    topics = load_topics(TOPIC_CONFIG_PATH)
    if not os.path.isdir(SCAN_DIR):
        print(f"Scan-Ordner nicht gefunden: {SCAN_DIR}")
        return

    # zuerst Staging abarbeiten
    if STAGING_DIR.exists():
        for entry in os.listdir(STAGING_DIR):
            p = os.path.join(STAGING_DIR, entry)
            if os.path.isfile(p) and Path(p).suffix.lower() in (".pdf",".jpg",".jpeg",".png",".tif",".tiff",".bmp"):
                try:
                    process_file(p, topics)
                except Exception as e:
                    print(f"⚠️ Fehler (Staging) {entry}: {e}")

    # frische Dateien übernehmen
    for entry in os.listdir(SCAN_DIR):
        src = os.path.join(SCAN_DIR, entry)
        if not os.path.isfile(src):
            continue
        if Path(src).parent in (STAGING_DIR, QUARANTINE_DIR):
            continue
        if Path(src).suffix.lower() in (".pdf",".jpg",".jpeg",".png",".tif",".tiff",".bmp"):
            try:
                s1 = os.path.getsize(src); time.sleep(2.0); s2 = os.path.getsize(src)
                if s1 != s2:
                    continue
                staged = acquire_to_staging(src)
                if staged:
                    process_file(staged, topics)
            except Exception as e:
                print(f"⚠️ Fehler bei {entry}: {e}")

def watch_loop(poll_seconds: int = 10) -> None:
    print(f"👀 Überwache {SCAN_DIR} (alle {poll_seconds}s) ...  [Strg+C beendet]")
    seen = set()
    topics = load_topics(TOPIC_CONFIG_PATH)
    log(f"[DEBUG] Libs: pdfplumber={bool(pdfplumber)} pdf2image={bool(convert_from_path)} pypdfium2={bool(pypdfium2)} pytesseract={bool(pytesseract)} PIL={bool(Image)}")
    log(f"[DEBUG] topics.json Pfad: {TOPIC_CONFIG_PATH}")
    log(f"[DEBUG] Tesseract exe: {TESSERACT_EXE}")
    log(f"[DEBUG] Poppler bin : {POPPLER_BIN}")

    # evtl. Rest im Staging zuerst
    if STAGING_DIR.exists():
        for entry in os.listdir(STAGING_DIR):
            p = os.path.join(STAGING_DIR, entry)
            if os.path.isfile(p) and Path(p).suffix.lower() in (".pdf",".jpg",".jpeg",".png",".tif",".tiff",".bmp"):
                try:
                    process_file(p, topics)
                except Exception as e:
                    print(f"⚠️ Fehler (Staging) {entry}: {e}")

    while True:
        try:
            current = set()
            for entry in os.listdir(SCAN_DIR):
                p = os.path.join(SCAN_DIR, entry)
                if os.path.isfile(p):
                    if Path(p).parent in (STAGING_DIR, QUARANTINE_DIR):
                        continue
                    current.add(p)
                    if p not in seen:
                        try:
                            s1 = os.path.getsize(p); time.sleep(2.0); s2 = os.path.getsize(p)
                            if s1 == s2 and Path(p).suffix.lower() in (".pdf",".jpg",".jpeg",".png",".tif",".tiff",".bmp"):
                                staged = acquire_to_staging(p)
                                if staged:
                                    process_file(staged, topics)
                        except Exception as e:
                            print(f"⚠️ Watch-Fehler {entry}: {e}")
            seen = current
            time.sleep(poll_seconds)
        except KeyboardInterrupt:
            print("\nBeendet.")
            break

def main():
    global DEBUG
    ap = argparse.ArgumentParser(description="Scan-Sorter (PDF/JPG nach Thema & Datum)")
    ap.add_argument("--watch", action="store_true", help="Fortlaufend überwachen")
    ap.add_argument("--poll", type=int, default=10, help="Polling-Intervall in Sekunden (nur mit --watch)")
    ap.add_argument("--debug", action="store_true", help="Debug-Logs anzeigen")
    args = ap.parse_args()
    DEBUG = args.debug

    os.makedirs(LOCAL_BASE, exist_ok=True)
    if args.watch:
        watch_loop(args.poll)
    else:
        process_once()

if __name__ == "__main__":
    main()
