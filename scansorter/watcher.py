# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import os, time

from . import config, logger
from .topics import load_topics
from .file_ops import acquire_to_staging
from .processor import process_file
from .ocr import ensure_ocr_paths, get_ocr_paths, pdfplumber, convert_from_path, pypdfium2, pytesseract, Image

def _libs_debug_banner() -> None:
    """
    Print a one-time banner with library availability and OCR paths.
    """
    tess, pop = ensure_ocr_paths()
    logger.log(f"[DEBUG] libs: pdfplumber={bool(pdfplumber)} pdf2image={bool(convert_from_path)} pypdfium2={bool(pypdfium2)} pytesseract={bool(pytesseract)} PIL={bool(Image)}")
    logger.log(f"[DEBUG] topics.json path: {config.TOPIC_CONFIG_PATH}")
    logger.log(f"[DEBUG] Tesseract exe: {tess}")
    logger.log(f"[DEBUG] Poppler bin : {pop}")

def _process_staging_all(topics: dict) -> None:
    """
    Process any leftover files in the staging folder.
    """
    if config.STAGING_DIR.exists():
        for entry in os.listdir(config.STAGING_DIR):
            p = os.path.join(config.STAGING_DIR, entry)
            if os.path.isfile(p) and Path(p).suffix.lower() in config.VALID_EXTS:
                try:
                    process_file(p, topics)
                except Exception as e:
                    print(f"⚠️ error (staging) {entry}: {e}")

def process_once() -> None:
    """
    Single-pass processing: stage stable files, then process them.
    """
    topics = load_topics(config.TOPIC_CONFIG_PATH)
    if not os.path.isdir(config.SCAN_DIR):
        print(f"Scan folder not found: {config.SCAN_DIR}")
        return

    _libs_debug_banner()
    _process_staging_all(topics)

    for entry in os.listdir(config.SCAN_DIR):
        src = os.path.join(config.SCAN_DIR, entry)
        if not os.path.isfile(src):
            continue
        if Path(src).parent in (config.STAGING_DIR, config.QUARANTINE_DIR):
            continue
        if Path(src).suffix.lower() in config.VALID_EXTS:
            try:
                s1 = os.path.getsize(src); time.sleep(2.0); s2 = os.path.getsize(src)
                if s1 != s2:
                    continue
                staged = acquire_to_staging(src)
                if staged:
                    process_file(staged, topics)
            except Exception as e:
                print(f"⚠️ error {entry}: {e}")

def watch_loop(poll_seconds: int = 10) -> None:
    """
    Continuous watch loop: periodically stage & process new files.

    Args:
        poll_seconds (int): Seconds between scans.
    """
    print(f"👀 Watching {config.SCAN_DIR} (every {poll_seconds}s) ...  [Ctrl+C to stop]")
    topics = load_topics(config.TOPIC_CONFIG_PATH)
    _libs_debug_banner()
    _process_staging_all(topics)

    seen: set[str] = set()
    while True:
        try:
            current: set[str] = set()
            for entry in os.listdir(config.SCAN_DIR):
                p = os.path.join(config.SCAN_DIR, entry)
                if os.path.isfile(p):
                    if Path(p).parent in (config.STAGING_DIR, config.QUARANTINE_DIR):
                        continue
                    current.add(p)
                    if p not in seen:
                        try:
                            s1 = os.path.getsize(p); time.sleep(2.0); s2 = os.path.getsize(p)
                            if s1 == s2 and Path(p).suffix.lower() in config.VALID_EXTS:
                                staged = acquire_to_staging(p)
                                if staged:
                                    process_file(staged, topics)
                        except Exception as e:
                            print(f"⚠️ watch error {entry}: {e}")
            seen = current
            time.sleep(poll_seconds)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
