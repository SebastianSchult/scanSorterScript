# -*- coding: utf-8 -*-
"""Configuration and path constants for the scan sorter."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import os
import json

# --- Paths (adjust to your environment) ---
SCAN_DIR   = r"C:\Users\sschu\Documents\Scan"
LOCAL_BASE = r"C:\Users\sschu\Documents\Belege"
NAS_BASE   = r"Z:\\"  # mounted Synology drive

SCRIPT_DIR = Path(__file__).resolve().parent.parent
TOPIC_CONFIG_PATH = SCRIPT_DIR / "topics.json"

STAGING_DIR    = Path(SCAN_DIR) / "_staging"
QUARANTINE_DIR = Path(SCAN_DIR) / "_quarantine"

# Email configs (split non-sensitive vs. secrets)
EMAIL_CONFIG_PATH  = SCRIPT_DIR / "email.json"          # tracked (no passwords)
EMAIL_SECRETS_PATH = SCRIPT_DIR / "email.secrets.json"  # NOT tracked (passwords, tokens)

# File extensions that will be processed
VALID_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

def ensure_base_dirs() -> None:
    """Create required base directories if they don't exist."""
    Path(LOCAL_BASE).mkdir(parents=True, exist_ok=True)
    # NAS_BASE is created on demand only when reachable.
    Path(STAGING_DIR).mkdir(parents=True, exist_ok=True)
    Path(QUARANTINE_DIR).mkdir(parents=True, exist_ok=True)

# ---------------- Email settings loader ----------------

def _load_json(path: Path) -> Dict[str, Any]:
    """Safely load JSON file; return {} if missing/invalid."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _normalize_email_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize email config and fill sensible defaults."""
    out = dict(cfg) if cfg else {}
    out.setdefault("enabled", False)
    out.setdefault("smtp_port", 465)
    out.setdefault("security", "SSL")  # SSL | STARTTLS | PLAIN
    # normalize recipients
    if isinstance(out.get("to_addrs"), str):
        out["to_addrs"] = [out["to_addrs"]]
    # env var override for password (preferred over file)
    env_pw = os.environ.get("SCANSORTER_SMTP_PASS")
    if env_pw:
        out["password"] = env_pw
    return out

def load_email_settings() -> Dict[str, Any]:
    """
    Load email settings from:
      1) email.json          (tracked, non-sensitive)
      2) email.secrets.json  (NOT tracked, secrets override)
      3) Env var SCANSORTER_SMTP_PASS overrides 'password'

    Returns:
        dict: {
          enabled: bool,
          smtp_host: str,
          smtp_port: int,
          security: "SSL"|"STARTTLS"|"PLAIN",
          username: str|None,
          password: str|None,
          from_addr: str,
          to_addrs: [str, ...]
        }
    """
    base = _load_json(EMAIL_CONFIG_PATH)
    secrets = _load_json(EMAIL_SECRETS_PATH)
    merged = {**base, **secrets}  # secrets win
    return _normalize_email_cfg(merged)
