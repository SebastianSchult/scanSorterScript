# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
import re, os
from datetime import datetime

DATE_PATTERNS = [
    r"(\b\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}\b)",
    r"(\b\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}\b)",
    r"(\b\d{1,2}\.\s*[A-Za-zäöüÄÖÜ]+\.?\s*\d{4}\b)",
]
GER_MONTHS = {
    "januar":1,"februar":2,"märz":3,"maerz":3,"april":4,"mai":5,"juni":6,
    "juli":7,"august":8,"september":9,"oktober":10,"november":11,"dezember":12
}

def parse_date(raw: str) -> Optional[datetime]:
    """
    Parse a date from common German formats.

    Args:
        raw (str): Raw date string.

    Returns:
        Optional[datetime]: Parsed datetime or None.
    """
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

def find_date_in_text(text: str) -> Optional[datetime]:
    """
    Find first date occurrence in `text`.

    Args:
        text (str): Document text.

    Returns:
        Optional[datetime]: Found datetime or None.
    """
    for pat in DATE_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            dt = parse_date(m.group(1))
            if dt: return dt
    return None

def get_scan_datetime(path: str) -> datetime:
    """
    Fallback "scan timestamp": creation time -> modified time -> now.

    Args:
        path (str): File path.

    Returns:
        datetime: Best-effort timestamp.
    """
    for getter in (os.path.getctime, os.path.getmtime):
        try:
            return datetime.fromtimestamp(getter(path))
        except Exception:
            continue
    return datetime.now()
