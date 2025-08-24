# -*- coding: utf-8 -*-
from __future__ import annotations

_DEBUG = False

def set_debug(enabled: bool) -> None:
    """
    Enable/disable debug logging.

    Args:
        enabled (bool): True to enable debug output.
    """
    global _DEBUG
    _DEBUG = enabled

def log(*args, **kwargs) -> None:
    """
    Print only if debug is enabled.

    Args:
        *args: Positional args to print.
        **kwargs: Keyword args to print.
    """
    if _DEBUG:
        print(*args, **kwargs)
