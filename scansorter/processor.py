# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import shutil, gc, os

from . import config, logger
from .ocr import extract_text_from_pdf, extract_text_from_image
from .dates import find_date_in_text, get_scan_datetime
from .topics import detect_topic
from .file_ops import safe_name, unique_path, safe_remove

def process_file(src_path: str, topics: dict) -> None:
    """
    Process one file: extract text, detect date and topic, copy to target
    folders (local + NAS), then remove staging source.

    Args:
        src_path (str): Path to a file (already in STAGING_DIR).
        topics (dict): Topics map {topic: [keywords...]}

    Returns:
        None
    """
    ext = Path(src_path).suffix.lower()
    text = ""
    if ext == ".pdf":
        text = extract_text_from_pdf(src_path)
    elif ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"):
        text = extract_text_from_image(src_path)

    # date: document -> scan timestamp
    doc_dt = find_date_in_text(text) if text else None
    scan_dt = get_scan_datetime(src_path)
    dt = doc_dt or scan_dt
    date_str = dt.strftime("%Y-%m-%d")
    if doc_dt:
        logger.log(f"[DEBUG] document date: {doc_dt.date()} (content)")
    else:
        logger.log(f"[DEBUG] using scan date fallback: {scan_dt.date()}")

    filename = Path(src_path).name
    topic, hits = detect_topic(text or "", topics, filename)
    logger.log(f"[DEBUG] file='{filename}' topic='{topic}' hits={hits} textlen={len(text)}")

    # target dirs
    local_topic_dir = Path(config.LOCAL_BASE) / topic
    nas_topic_dir   = Path(config.NAS_BASE) / topic

    local_topic_dir.mkdir(parents=True, exist_ok=True)
    if os.path.isdir(config.NAS_BASE):
        try:
            nas_topic_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.log(f"[DEBUG] NAS mkdir failed: {e}")

    # filename
    base_name = safe_name(f"{date_str}_{topic}{ext}")

    # copy
    local_target = unique_path(str(local_topic_dir), base_name)
    shutil.copy2(src_path, local_target)
    if os.path.isdir(config.NAS_BASE):
        try:
            nas_target = unique_path(str(nas_topic_dir), base_name)
            shutil.copy2(src_path, nas_target)
        except Exception as e:
            logger.log(f"[DEBUG] NAS copy failed: {e}")

    # release handles + remove staging source
    gc.collect()
    if not safe_remove(src_path):
        logger.log(f"[DEBUG] could not remove/move: {src_path}")

    print(f"✅ {Path(src_path).name} → {local_target}")
