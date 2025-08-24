# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
from pathlib import Path
import glob, os, shutil

from . import logger

# Optional libs
try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pypdfium2
except Exception:
    pypdfium2 = None


# --- Path discovery (Windows) -------------------------------------------------

_TESSERACT_EXE: Optional[str] = None
_POPPLER_BIN: Optional[str] = None

def _guess_tesseract_exe() -> Optional[str]:
    """
    Try to find Tesseract executable on Windows.

    Returns:
        Optional[str]: Full path or None.
    """
    exe = shutil.which("tesseract")
    if exe:
        return exe
    for c in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.isfile(c):
            return c
    return None

def _guess_poppler_bin() -> Optional[str]:
    """
    Try to find Poppler bin directory on Windows.

    Returns:
        Optional[str]: Folder containing Poppler binaries, or None.
    """
    env = os.environ.get("POPPLER_PATH")
    if env and os.path.isdir(env):
        return env
    for pat in (r"C:\Program Files\poppler*\Library\bin",
                r"C:\Program Files\poppler*\bin"):
        hits = sorted(glob.glob(pat), reverse=True)
        for h in hits:
            if os.path.isdir(h):
                return h
    return None

def ensure_ocr_paths() -> tuple[Optional[str], Optional[str]]:
    """
    Ensure OCR tool paths are wired (Tesseract + Poppler).

    Returns:
        tuple[Optional[str], Optional[str]]: (tesseract_exe, poppler_bin)
    """
    global _TESSERACT_EXE, _POPPLER_BIN
    if _TESSERACT_EXE is None:
        _TESSERACT_EXE = _guess_tesseract_exe()
        if pytesseract is not None and _TESSERACT_EXE:
            try:
                pytesseract.pytesseract.tesseract_cmd = _TESSERACT_EXE
            except Exception:
                pass
    if _POPPLER_BIN is None:
        _POPPLER_BIN = _guess_poppler_bin()
    return _TESSERACT_EXE, _POPPLER_BIN

def get_ocr_paths() -> tuple[Optional[str], Optional[str]]:
    """
    Get currently configured OCR paths.

    Returns:
        tuple[Optional[str], Optional[str]]: (tesseract_exe, poppler_bin)
    """
    return _TESSERACT_EXE, _POPPLER_BIN


# --- OCR helpers --------------------------------------------------------------

def _ocr_image_to_text(img) -> str:
    """
    Run OCR on a PIL image. Prefer 'deu', fallback to 'eng'.

    Args:
        img: PIL.Image.Image

    Returns:
        str: Extracted text (may be empty).
    """
    if pytesseract is None:
        return ""
    try:
        return pytesseract.image_to_string(img, lang="deu")
    except Exception as e:
        if "Failed loading language 'deu'" in str(e) or "Error opening data file" in str(e):
            try:
                return pytesseract.image_to_string(img, lang="eng")
            except Exception:
                return ""
        return ""


def extract_text_from_pdf(pdf_path: str, max_pages: int = 5) -> str:
    """
    Extract text from a PDF using a layered strategy:
    1) direct text (pdfplumber),
    2) OCR via pdf2image+pytesseract (Poppler optional),
    3) OCR via pypdfium2+pytesseract (no Poppler needed).

    Args:
        pdf_path (str): Path to the PDF file.
        max_pages (int): Max number of pages to analyze.

    Returns:
        str: Extracted text (may be empty).
    """
    ensure_ocr_paths()
    text = ""

    # 1) direct text
    if pdfplumber is not None:
        try:
            with open(pdf_path, "rb") as fh:
                with pdfplumber.open(fh) as pdf:
                    for page in pdf.pages[:max_pages]:
                        text += page.extract_text() or ""
            if text.strip():
                logger.log(f"[DEBUG] pdfplumber textlen={len(text)}")
                return text.strip()
        except Exception as e:
            logger.log(f"[DEBUG] pdfplumber error: {e}")

    # 2) OCR via pdf2image
    if convert_from_path is not None and pytesseract is not None:
        images = None
        try:
            kwargs = {}
            if _POPPLER_BIN:
                kwargs["poppler_path"] = _POPPLER_BIN
            images = convert_from_path(pdf_path, first_page=1, last_page=max_pages, **kwargs)
            for img in images:
                try:
                    text += "\n" + _ocr_image_to_text(img)
                finally:
                    try: img.close()
                    except Exception: pass
            if text.strip():
                logger.log(f"[DEBUG] OCR(pdf2image) textlen={len(text)} (Poppler='{_POPPLER_BIN}')")
                return text.strip()
        except Exception as e:
            logger.log(f"[DEBUG] pdf2image/pytesseract error: {e}")
        finally:
            images = None

    # 3) OCR via pypdfium2
    if pypdfium2 is not None and pytesseract is not None:
        try:
            pdf = pypdfium2.PdfDocument(pdf_path)  # NOTE: no context manager!
            try:
                n = min(max_pages, len(pdf))
                for i in range(n):
                    page = pdf[i]
                    pil = None
                    try:
                        pil = page.render(scale=2).to_pil()
                        text += "\n" + _ocr_image_to_text(pil)
                    finally:
                        try:
                            if pil: pil.close()
                        except Exception:
                            pass
                        try:
                            page.close()
                        except Exception:
                            pass
            finally:
                try:
                    pdf.close()
                except Exception:
                    pass
            if text.strip():
                logger.log(f"[DEBUG] OCR(pypdfium2) textlen={len(text)}")
                return text.strip()
        except Exception as e:
            logger.log(f"[DEBUG] pypdfium2/pytesseract error: {e}")

    logger.log("[DEBUG] no text extracted from PDF")
    return text.strip()


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from an image file via pytesseract.

    Args:
        image_path (str): Path to image (JPG/PNG/TIFF/BMP).

    Returns:
        str: Extracted text (may be empty).
    """
    if pytesseract is None or Image is None:
        logger.log(f"[DEBUG] image OCR not available (pytesseract={bool(pytesseract)}, PIL={bool(Image)})")
        return ""
    try:
        with Image.open(image_path) as img:
            txt = _ocr_image_to_text(img)
        logger.log(f"[DEBUG] image OCR textlen={len(txt)}")
        return txt
    except Exception as e:
        logger.log(f"[DEBUG] image OCR error: {e}")
        return ""
