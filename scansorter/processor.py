# -*- coding: utf-8 -*-
"""Document processing: OCR, topic & date detection, filing, and notifications."""

from __future__ import annotations
from pathlib import Path
import shutil
import gc
import os

from . import config, logger
from .ocr import extract_text_from_pdf, extract_text_from_image
from .dates import find_date_in_text, get_scan_datetime
from .topics import detect_topic
from .file_ops import safe_name, unique_path, safe_remove
from .mailer import notify_document_filed  # <-- email notification


def process_file(src_path: str, topics: dict) -> None:
    """Process a single staged file.

    Steps:
      1) Extract text (PDF direct text → OCR fallbacks).
      2) Detect document date from content; fallback to scan timestamp.
      3) Detect topic from text + filename using keyword rules.
      4) Copy into local and (optionally) NAS topic folders using pattern:
         YYYY-MM-DD_<Topic>.<ext>
      5) Send an email notification with a short summary and the file attached
         (if email is enabled in config).
      6) Remove the source from staging (with quarantine fallback).

    Args:
        src_path (str): Absolute path to a file located in STAGING_DIR.
        topics (dict): Mapping of topic -> list of keywords.

    Returns:
        None
    """
    ext = Path(src_path).suffix.lower()

    # --- 1) Text extraction ---
    text = ""
    if ext == ".pdf":
        text = extract_text_from_pdf(src_path)
    elif ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"):
        text = extract_text_from_image(src_path)

    # --- 2) Date detection (document → scan fallback) ---
    doc_dt = find_date_in_text(text) if text else None
    scan_dt = get_scan_datetime(src_path)
    dt = doc_dt or scan_dt
    date_str = dt.strftime("%Y-%m-%d")
    if doc_dt:
        logger.log(f"[DEBUG] document date: {doc_dt.date()} (content)")
    else:
        logger.log(f"[DEBUG] using scan date fallback: {scan_dt.date()}")

    # --- 3) Topic detection ---
    filename = Path(src_path).name
    topic, hits = detect_topic(text or "", topics, filename)
    logger.log(f"[DEBUG] file='{filename}' topic='{topic}' hits={hits} textlen={len(text)}")

    # --- 4) Target dirs & copy ---
    local_topic_dir = Path(config.LOCAL_BASE) / topic
    nas_topic_dir   = Path(config.NAS_BASE) / topic

    local_topic_dir.mkdir(parents=True, exist_ok=True)
    if os.path.isdir(config.NAS_BASE):
        try:
            nas_topic_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.log(f"[DEBUG] NAS mkdir failed: {e}")

    base_name = safe_name(f"{date_str}_{topic}{ext}")

    local_target = unique_path(str(local_topic_dir), base_name)
    shutil.copy2(src_path, local_target)

    if os.path.isdir(config.NAS_BASE):
        try:
            nas_target = unique_path(str(nas_topic_dir), base_name)
            shutil.copy2(src_path, nas_target)
        except Exception as e:
            logger.log(f"[DEBUG] NAS copy failed: {e}")

    # --- 5) Email notification (if enabled in config) ---
    try:
        notify_document_filed(
            local_path=local_target,
            topic=topic,
            date_str=date_str,
            doc_date_iso=doc_dt.strftime("%Y-%m-%d") if doc_dt else None,
            scan_date_iso=scan_dt.strftime("%Y-%m-%d"),
            text=text or "",
            hits=hits,
        )
    except Exception as e:
        logger.log(f"[DEBUG] email notify failed: {e}")

    # --- 6) Cleanup source (staging) ---
    gc.collect()
    if not safe_remove(src_path):
        logger.log(f"[DEBUG] could not remove/move: {src_path}")

    print(f"✅ {Path(src_path).name} → {local_target}")
