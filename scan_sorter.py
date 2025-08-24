#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
from scansorter import config, logger, watcher
from scansorter.mailer import send_test_email  # <-- NEU

def main() -> None:
    """
    CLI entry point. Parses args, sets debug mode, ensures base folders,
    then runs single-pass or watch loop or email test.
    """
    ap = argparse.ArgumentParser(description="Scan-Sorter (PDF/JPG sorted by topic & date)")
    ap.add_argument("--watch", action="store_true", help="Watch SCAN_DIR continuously")
    ap.add_argument("--poll", type=int, default=10, help="Polling interval in seconds (only with --watch)")
    ap.add_argument("--debug", action="store_true", help="Enable debug logging")
    ap.add_argument("--email-test", action="store_true", help="Send a test email and exit")  # <-- NEU
    args = ap.parse_args()

    logger.set_debug(args.debug)
    config.ensure_base_dirs()

    if args.email_test:
        ok = send_test_email()
        print("Email test:", "OK" if ok else "FAILED")
        return

    if args.watch:
        watcher.watch_loop(args.poll)
    else:
        watcher.process_once()

if __name__ == "__main__":
    main()
