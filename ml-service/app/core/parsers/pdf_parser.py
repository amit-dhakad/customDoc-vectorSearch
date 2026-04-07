"""
app/core/parsers/pdf_parser.py — The Dual-Engine PDF Extraction Suite.

HOW PDF PARSING WORKS
─────────────────────────────────────────────────────────────────────────────
A PDF is a binary container format, not a plain text file. It stores:
  • Glyphs (visual characters) with absolute (x,y) coordinates.
  • Fonts, vector graphics, and metadata.
  • An optional /ToUnicode map (ID → Unicode characters).

Parsing involves reconstructing readable text from these glyph positions.
Different libraries use different heuristics to achieve this.

OUR DUAL-ENGINE STRATEGY
─────────────────────────────────────────────────────────────────────────────
We provide two distinct engines, allowing the caller to prioritize:
  1. FITZ (PyMuPDF - Default):
     • PROS: Extreme speed (C-based), handles large files easily.
     • CONS: Can sometimes scramble complex multi-column layouts or tables.
  2. PDFPLUMBER:
     • PROS: High visual fidelity. Preserves layout, margins, and whitespace.
     • CONS: Significantly slower (pure Python-based processing). Best for
             complex tables or documents where formatting is crucial.

AUTOMATIC OCR FALLBACK
─────────────────────────────────────────────────────────────────────────────
If a page has no text layer (e.g. it is a scanned document), the parser
can fallback to OCR (Tesseract) to "see" the text visually.
"""

from __future__ import annotations
import logging
from typing import Literal
import fitz  # PyMuPDF
import pdfplumber

from .base_parser import BaseParser

# Optional OCR Support
try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

logger = logging.getLogger(__name__)

class PDFParser(BaseParser):
    """
    Modular PDF extractor supporting dynamic engine selection (fitz vs pdfplumber).
    """

    def __init__(self, ocr_fallback: bool = True) -> None:
        """
        Args:
            ocr_fallback: If True, attempt OCR when a page is found to be empty.
                          Requires pytesseract and tesseract binary.
        """
        self.ocr_enabled = ocr_fallback and HAS_OCR
        if ocr_fallback and not HAS_OCR:
            logger.warning("PDFParser: OCR requested but dependencies not found.")

    def _extract_text(self, file_path: str, engine: Literal["fitz", "pdfplumber"] = "fitz", **kwargs) -> str:
        """
        Implementation of the abstract method.
        Routes the request to the specified PDF engine.
        """
        logger.info("PDFParser: Extraction starting (engine=%s, file=%s)", engine, file_path)

        if engine == "pdfplumber":
            return self._run_pdfplumber(file_path)
        else:
            return self._run_fitz(file_path)

    def _run_fitz(self, file_path: str) -> str:
        """
        PyMuPDF Engine — Focus: High Performance.
        Iterates page-by-page, visiting every text operator in the PDF stream.
        """
        page_texts: list[str] = []
        with fitz.open(file_path) as doc:
            for i, page in enumerate(doc, start=1):
                text: str = page.get_text("text")

                if text.strip():
                    page_texts.append(f"[Page {i}]\n{text}")
                elif self.ocr_enabled:
                    # Fallback to OCR for scanned pages
                    ocr_text = self._ocr_page_fitz(page)
                    if ocr_text.strip():
                        page_texts.append(f"[Page {i} (OCR)]\n{ocr_text}")
                else:
                    logger.warning("PDFParser [fitz]: Page %d yielded no text layer.", i)

        return "\n\n".join(page_texts)

    def _run_pdfplumber(self, file_path: str) -> str:
        """
        pdfplumber Engine — Focus: Visual Precision.
        Best for documents with complex grid-based layouts or tables.
        """
        page_texts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text: str | None = page.extract_text()

                if text and text.strip():
                    page_texts.append(f"[Page {i}]\n{text}")
                else:
                    logger.warning("PDFParser [pdfplumber]: Page %d yielded no text layer.", i)

        return "\n\n".join(page_texts)

    def _ocr_page_fitz(self, page: fitz.Page) -> str:
        """Helper to render a PDF page at 300 DPI and run Tesseract OCR."""
        try:
            # 300 DPI for high-quality OCR (72 is standard, so 300/72 = 4.16 zoom)
            zoom = 300 / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # raw bytes -> PIL -> Tesseract
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return pytesseract.image_to_string(img)
        except Exception as e:
            logger.error("PDFParser: OCR failed for page %d: %s", page.number + 1, e)
            return ""
