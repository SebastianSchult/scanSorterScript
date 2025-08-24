# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
from pathlib import Path
import os, time, shutil

from . import logger, config

def safe_name(name: str) -> str:
    """
    Sanitize filename for Windows.

    Args:
        name (str): Raw name.

    Returns:
        str: Sanitized name.
    """
    import re
    name = re.sub(r"[<>:\"/\\|?*]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def unique_path(base_dir: str, filename: str) -> str:
    """
    Produce a unique path by appending _1, _2, ... if necessary.

    Args:
        base_dir (str): Target directory.
        filename (str): Desired file name.

    Returns:
        str: Unique file path.
    """
    p = Path(base_dir) / filename
    if not p.exists():
        return str(p)
    stem, suffix, i = p.stem, p.suffix, 1
    while True:
        cand = Path(base_dir) / f"{stem}_{i}{suffix}"
        if not cand.exists():
            return str(cand)
        i += 1

def wait_until_free(path: str, retries: int = 15, delay: float = 1.0) -> bool:
    """
    Wait until a file is readable (not locked).

    Args:
        path (str): File path.
        retries (int): Max attempts.
        delay (float): Seconds between attempts.

    Returns:
        bool: True if free, else False.
    """
    for _ in range(retries):
        try:
            with open(path, "rb"):
                return True
        except Exception:
            time.sleep(delay)
    return False

def safe_remove(path: str, retries: int = 10, delay: float = 3.0) -> bool:
    """
    Remove a file with retries. If still locked, move to quarantine.

    Args:
        path (str): File path.
        retries (int): Attempts before quarantine.
        delay (float): Sleep seconds between attempts.

    Returns:
        bool: True if removed/moved, False otherwise.
    """
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
        dst = unique_path(str(config.QUARANTINE_DIR), Path(path).name)
        shutil.move(path, dst)
        logger.log(f"[DEBUG] moved to quarantine: {dst}")
        return True
    except Exception:
        return False

def acquire_to_staging(src_path: str, retries: int = 20, delay: float = 1.0) -> Optional[str]:
    """
    Atomically move a file from SCAN_DIR to STAGING_DIR when it's no longer locked.

    Args:
        src_path (str): Absolute path in SCAN_DIR.
        retries (int): Move attempts.
        delay (float): Sleep seconds between attempts.

    Returns:
        Optional[str]: New path in STAGING_DIR or None if failed.
    """
    target = unique_path(str(config.STAGING_DIR), Path(src_path).name)
    for _ in range(retries):
        try:
            os.replace(src_path, target)  # atomic within same volume
            logger.log(f"[DEBUG] staging: {src_path} -> {target}")
            return target
        except PermissionError:
            time.sleep(delay)
        except FileNotFoundError:
            return None
        except Exception:
            time.sleep(delay)
    logger.log(f"[DEBUG] staging failed: {src_path}")
    return None
