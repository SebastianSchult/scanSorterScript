# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, List, Tuple
import json, re
from pathlib import Path
from . import logger

def load_topics(config_path: Path) -> Dict[str, list[str]]:
    """
    Load topics from JSON, or return defaults if file missing.

    Args:
        config_path (Path): Path to topics.json.

    Returns:
        Dict[str, list[str]]: {topic: [keywords...]}
    """
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
        logger.log(f"[DEBUG] topics.json missing → defaults")
        return defaults
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_topics = json.load(f)
        logger.log(f"[DEBUG] topics.json loaded: {config_path}")
        return user_topics
    except Exception as e:
        print(f"⚠️ Could not load topics.json ({e}) → using defaults")
        return defaults

def _normalize(s: str) -> str:
    """
    Remove non-alphanumeric chars (incl. German umlauts preserved).

    Args:
        s (str): Input string.

    Returns:
        str: Normalized string.
    """
    return re.sub(r"[^a-z0-9äöüß]", "", s.lower())

def detect_topic(text: str, topics: dict, filename: str = "") -> Tuple[str, list[str]]:
    """
    Detect topic by keyword matching on text and filename, with a
    normalized fallback match (logo/spacing resilient).

    Args:
        text (str): OCR or PDF text.
        topics (dict): {topic: [keywords...]}
        filename (str): Original filename (optional).

    Returns:
        Tuple[str, list[str]]: (topic, matched_keywords)
    """
    hay = (text + "\n" + (filename or "")).lower()
    norm_hay = _normalize(hay)
    best_topic, best_score, matched = "Sonstiges", 0, []
    for topic, kws in topics.items():
        if not kws:
            continue
        score = 0
        hits: list[str] = []
        for kw in kws:
            kw = (kw or "").strip().lower()
            if not kw:
                continue
            # precise word boundary
            if re.search(rf"\b{re.escape(kw)}\b", hay, flags=re.IGNORECASE):
                score += 1; hits.append(kw); continue
            # fallback normalized search
            if _normalize(kw) and _normalize(kw) in norm_hay:
                score += 1; hits.append(kw)
        if score > best_score:
            best_topic, best_score, matched = topic, score, hits
    return best_topic, matched
