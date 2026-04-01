"""
pdf_parser.py — PDF document parser using PyMuPDF (fitz).

HOW PDF PARSING WORKS
─────────────────────────────────────────────────────────────────────────────
A PDF file is NOT plain text.  It is a binary format that stores:
  • Glyphs (visual characters) with x/y coordinates on a canvas.
  • Fonts, images, vector graphics, annotations.
  • An optional text-object layer (ToUnicode maps glyph IDs → Unicode chars).

PDF parsing means reconstructing readable text from these glyph positions.
Libraries like PyMuPDF (libmupdf under the hood) do this reconstruction by:

  1. Parsing the PDF page cross-reference table (xref) to find page objects.
  2. For each page, running a "text extraction device" that visits every
     content stream operator (BT … ET blocks in PDF syntax).
  3. Mapping glyph IDs through the font's ToUnicode CMap to Unicode code points.
  4. Reordering characters by reading order (using bounding-box heuristics)
     so the output text flows left-to-right, top-to-bottom.
  5. Inserting newlines at line breaks and paragraph boundaries.

IMPORTANT LIMITATIONS
─────────────────────────────────────────────────────────────────────────────
  • Scanned PDFs (images of printed pages) contain NO text layer.
    `page.get_text()` returns an empty string for those pages.
    True extraction from scanned PDFs requires an OCR step (e.g. Tesseract).
  • Columns, tables, and multi-column layouts can produce text in the wrong
    order because the PDF stores glyphs by draw order, not reading order.
  • Password-encrypted PDFs cannot be opened without the correct password.

WHY PAGE-BY-PAGE ITERATION?
─────────────────────────────────────────────────────────────────────────────
We iterate page-by-page (rather than using doc.get_text() on the whole doc)
because:
  a) It lets us attach page-number metadata to each chunk later in the
     pipeline (crucial for source citations in the RAG UI).
  b) It avoids loading the entire document into memory at once — useful for
     large PDFs (hundreds of pages).

DEPENDENCY: PyMuPDF
    pip install pymupdf
    Import name: `import fitz`   (fitz is the legacy PyMuPDF module name)
"""

from __future__ import annotations

import logging

import fitz  # PyMuPDF — `pip install pymupdf`

from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """
    Extracts plain text from PDF files using PyMuPDF.

    Parsing strategy:
        • Open the PDF with `fitz.open()`.
        • Iterate over every page.
        • Call `page.get_text("text")` on each page — this triggers PyMuPDF's
          built-in text reconstruction pipeline described above.
        • Join pages with a `\\n\\n` separator so downstream chunkers can
          recognise page boundaries as natural split points.
    """

    def _extract_text(self, file_path: str) -> str:
        """
        Extract text from a PDF file page by page.

        Args:
            file_path: Path to the .pdf file (already validated by BaseParser).

        Returns:
            All pages' text joined by double newlines.

        Raises:
            Any fitz exception propagates to BaseParser which wraps it in
            RuntimeError with a uniform message.
        """
        page_texts: list[str] = []

        # ── Open the PDF document ──────────────────────────────────────────
        #
        # `fitz.open()` parses the PDF's cross-reference table and prepares
        # page objects.  It does NOT load all page content into RAM yet —
        # individual pages are decoded lazily when accessed.
        #
        # `with` ensures the file handle is released after we're done,
        # even if an exception occurs mid-iteration.
        with fitz.open(file_path) as doc:
            total_pages = doc.page_count
            logger.info(
                "PDFParser: opening %s  (%d pages)", file_path, total_pages
            )

            for page_index in range(total_pages):
                # ── Load one page ──────────────────────────────────────────
                #
                # `doc[page_index]` returns a `fitz.Page` object.
                # The raw PDF page content stream is decoded here.
                page = doc[page_index]

                # ── Extract text from this page ────────────────────────────
                #
                # `get_text("text")` mode:
                #   • Reconstructs text in reading order (top→bottom,
                #     left→right) using bounding-box heuristics.
                #   • Inserts newlines between text lines.
                #   • Returns an empty string for image-only pages.
                #
                # Other available modes (not used here):
                #   "html"  → HTML with styled spans (useful if you want to
                #             preserve bold/italic for later processing)
                #   "dict"  → structured dict with spans, fonts, bboxes
                #             (useful for table extraction or metadata mining)
                #   "words" → list of (x0,y0,x1,y1,word,…) tuples
                page_text: str = page.get_text("text")

                if page_text.strip():
                    # Prepend a page marker comment so the chunker can
                    # optionally use it as a metadata signal.
                    page_texts.append(f"[Page {page_index + 1}]\n{page_text}")
                else:
                    # Log but do NOT raise — a scanned page inside a
                    # mixed PDF is normal.  The ingestion will simply
                    # produce fewer chunks for this page.
                    logger.warning(
                        "PDFParser: page %d of %s yielded no text "
                        "(possibly a scanned/image page).",
                        page_index + 1,
                        file_path,
                    )

        # ── Join all pages ─────────────────────────────────────────────────
        #
        # Double newlines ("\n\n") between pages act as a strong paragraph
        # boundary.  RecursiveCharacterTextSplitter (used in the chunker)
        # treats "\n\n" as a preferred split point, so page boundaries will
        # naturally align with chunk boundaries when the page text is short.
        return "\n\n".join(page_texts)
