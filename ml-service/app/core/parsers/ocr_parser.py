"""
app/core/parsers/ocr_parser.py — OCR Document Parser.

HOW OCR PARSING WORKS
─────────────────────────────────────────────────────────────────────────────
OCR (Optical Character Recognition) is used when a document has no text layer.
It is the standard solution for scanned PDFs, photos of forms, or screenshots.

Our OCR pipeline consists of three primary stages:
  1. RENDERING:
     Converting each PDF page or raw image into an uncompressed bitmap
     (e.g., 300 DPI for high-precision scanning).
  2. IMAGE CLEANING (via Pillow):
     Loading the image data into memory and preparing it for the OCR engine.
  3. EXTRACTION (via Tesseract):
     Applying Tesseract's neural-network-backed analysis to identify glyphs
     and group them into sentences and paragraphs.

BINARY DEPENDENCIES
─────────────────────────────────────────────────────────────────────────────
OCR is NOT pure-Python. It requires:
  • `tesseract-ocr`: The system-level OCR engine.
  • `poppler-utils`: The rendering engine used by `pdf2image`.
  These are correctly configured in our Dockerfile for high-reliability.
"""

from __future__ import annotations
import logging
import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from .base_parser import BaseParser


logger = logging.getLogger(__name__)

class OCRParser(BaseParser):
    """
    Extracts text from images and scanned documents using Tesseract OCR (CPU).
    """

    def _extract_text(self, file_path: str, dpi: int = 300, **kwargs) -> str:
        """
        Implementation of the abstract method.
        Directs the file to either an image-based or PDF-based OCR workflow.
        """
        ext = os.path.splitext(file_path)[1].lower()
        client_id = kwargs.get('client_id')
        reporter = kwargs.get('reporter')
        dpi = kwargs.get('dpi', 300)

        if ext == ".pdf":
            return self._run_scanned_pdf_ocr(file_path, dpi, client_id, reporter)
        else:
            return self._run_image_ocr(file_path, client_id, reporter)

    def _run_image_ocr(self, file_path: str, client_id: str = None, reporter: callable = None) -> str:
        """Perform OCR on a single Image file using Tesseract."""
        msg = f"OCR: Extracting via Tesseract (CPU) on image {os.path.basename(file_path)}"
        logger.info(msg)
        if reporter:
            reporter(client_id, msg)
            
        try:
            img = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(img)
            return extracted_text
        except Exception as e:
            logger.error("OCRParser: OCR failed for image %s: %s", file_path, e)
            raise RuntimeError(f"Image OCR failed: {e}")

    def _run_scanned_pdf_ocr(self, file_path: str, dpi: int, client_id: str = None, reporter: callable = None) -> str:
        """Convert each PDF page to an image and perform Tesseract OCR."""
        msg = f"OCR: Initializing Tesseract (CPU) for scanned PDF {os.path.basename(file_path)}..."
        logger.info(msg)
        if reporter:
            reporter(client_id, msg)
            
        try:
            # We convert to list to know total pages
            pages = convert_from_path(file_path, dpi=dpi)
            ocr_results: list[str] = []

            for i, page in enumerate(pages, start=1):
                prog_msg = f"OCR [Tesseract-CPU]: Processing page {i}/{len(pages)}..."
                logger.info(prog_msg)
                if reporter:
                    reporter(client_id, prog_msg)
                
                text = pytesseract.image_to_string(page)
                
                if text.strip():
                    ocr_results.append(f"[Page {i} (OCR)]\n{text}")
            
            return "\n\n".join(ocr_results)
        except Exception as e:
            logger.error("OCRParser: OCR failed for scanned PDF %s: %s", file_path, e)
            raise RuntimeError(f"Scanned PDF OCR failed: {e}")
