# scansorter/mailer.py
# -*- coding: utf-8 -*-
"""Email notifications for processed documents."""

from __future__ import annotations
from typing import Iterable, Optional
import os, smtplib, ssl, mimetypes
from email.message import EmailMessage
from pathlib import Path

from . import logger
from .config import load_email_settings

def _attach_file(msg: EmailMessage, file_path: str) -> None:
    p = Path(file_path)
    ctype, encoding = mimetypes.guess_type(str(p))
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with open(p, "rb") as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=p.name)

def _send_via_smtp(host: str, port: int, security: str, username: Optional[str], password: Optional[str],
                   from_addr: str, to_addrs: Iterable[str], subject: str, body_text: str,
                   attachments: Iterable[str] = ()) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = ", ".join(to_addrs)
    msg.set_content(body_text)

    for ap in attachments:
        try:
            _attach_file(msg, ap)
        except Exception as e:
            logger.log(f"[DEBUG] attachment failed: {ap} ({e})")

    sec = (security or "").upper()
    if sec == "SSL":
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx) as s:
            if username and password: s.login(username, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as s:
            if sec == "STARTTLS":
                ctx = ssl.create_default_context()
                s.starttls(context=ctx)
            if username and password: s.login(username, password)
            s.send_message(msg)

def summarize_text(text: str, limit_chars: int = 600) -> str:
    if not text:
        return "(no OCR text available)"
    preview = " ".join(text.split())
    return (preview[:limit_chars].rstrip() + " …") if len(preview) > limit_chars else preview

def notify_document_filed(local_path: str, topic: str, date_str: str,
                          doc_date_iso: Optional[str], scan_date_iso: str,
                          text: str, hits: list[str]) -> None:
    cfg = load_email_settings()
    if not cfg.get("enabled"):
        logger.log("[DEBUG] email disabled (email.json missing or enabled=false)")
        return

    host   = cfg.get("smtp_host")
    port   = int(cfg.get("smtp_port", 465))
    sec    = cfg.get("security", "SSL")
    user   = cfg.get("username")
    pw     = os.environ.get("SCANSORTER_SMTP_PASS") or cfg.get("password")
    from_  = cfg.get("from_addr")
    to     = cfg.get("to_addrs") or []

    if not (host and from_ and to):
        logger.log("[DEBUG] email config incomplete (smtp_host/from_addr/to_addrs)")
        return

    subject = f"[ScanSorter] {date_str} · {topic} · {Path(local_path).name}"
    body = (
        f"New document filed.\n\n"
        f"Topic: {topic}\n"
        f"Filename: {Path(local_path).name}\n"
        f"Used date: {date_str}\n"
        f"Document date: {doc_date_iso or '-'}\n"
        f"Scan date: {scan_date_iso}\n"
        f"Keywords: {', '.join(hits) if hits else '-'}\n"
        f"Local path: {local_path}\n\n"
        f"Summary:\n{summarize_text(text, 600)}\n"
    )

    try:
        _send_via_smtp(host, port, sec, user, pw, from_, to, subject, body, attachments=[local_path])
        logger.log("[DEBUG] email sent")
    except Exception as e:
        logger.log(f"[DEBUG] email send failed: {e}")
