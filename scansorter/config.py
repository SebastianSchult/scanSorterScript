# -*- coding: utf-8 -*-
"""Configuration and path constants for the scan sorter."""

from __future__ import annotations
from pathlib import Path
import os

# --- Paths (adjust to your environment) ---
SCAN_DIR   = r"C:\Users\sschu\Documents\Scan"
LOCAL_BASE = r"C:\Users\sschu\Documents\Belege"
NAS_BASE   = r"Z:\\"  # mounted Synology drive

SCRIPT_DIR = Path(__file__).resolve().parent.parent
TOPIC_CONFIG_PATH = SCRIPT_DIR / "topics.json"

STAGING_DIR    = Path(SCAN_DIR) / "_staging"
QUARANTINE_DIR = Path(SCAN_DIR) / "_quarantine"

# File extensions that will be processed
VALID_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

def ensure_base_dirs() -> None:
    """Create required base directories if they don't exist.

    Args:
        None
    Returns:
        None
    """
    Path(LOCAL_BASE).mkdir(parents=True, exist_ok=True)
    # NAS_BASE is created on demand only when reachable.
    Path(STAGING_DIR).mkdir(parents=True, exist_ok=True)
    Path(QUARANTINE_DIR).mkdir(parents=True, exist_ok=True)
