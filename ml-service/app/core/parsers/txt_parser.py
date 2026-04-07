"""
app/core/parsers/txt_parser.py — Plain-text and Markdown document parser.

HOW PLAIN-TEXT PARSING WORKS
─────────────────────────────────────────────────────────────────────────────
Unlike PDF or DOCX, text files are already human-readable sequences of bytes.
Parsing reduces to two primary concerns:
  1. CHARACTER ENCODING DETECTION:
     Files don't always declare their encoding (UTF-8, Latin-1, CP1252).
     We use a FALLBACK CHAIN strategy:
       a) Try UTF-8 first (via 'utf-8-sig' to handle Windows BOMs).
       b) Try Latin-1 (ISO-8859-1) which never fails decoding.
  2. MARKDOWN RECOGNITION:
     Headings (#) serve as natural semantic boundaries. Our parser 
     keeps them by default to help the chunker identify sections.

STRIPPING MARKDOWN
─────────────────────────────────────────────────────────────────────────────
If clean prose is needed, we provide a regex-based stripper for images,
links, bold/italic, and horizontal rules.
"""

from __future__ import annotations
import logging
import re
from .base_parser import BaseParser

logger = logging.getLogger(__name__)

# Fallback encodings for robust decoding
_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")

class TxtParser(BaseParser):
    """
    Extracts text from plain-text files (.txt, .md, .csv) with encoding detection.
    """

    def _extract_text(self, file_path: str, strip_markdown: bool = False, **kwargs) -> str:
        """
        Implementation of the abstract method.
        Tries multiple encodings to ensure successful file reading.
        """
        text: str | None = None
        used_enc: str = ""

        # ── Encoding Detection Check ───────────────────────────────────────
        for enc in _ENCODINGS:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    text = f.read()
                used_enc = enc
                break
            except UnicodeDecodeError:
                logger.debug("TxtParser: Decoding %s failed with %s", file_path, enc)

        if text is None:
            raise RuntimeError(f"TxtParser: Could not decode {file_path} with known encodings.")

        logger.info("TxtParser: Successfully read %s (encoding=%s)", file_path, used_enc)

        # ── Optional Markdown Cleanup ──────────────────────────────────────
        if strip_markdown:
            text = self._strip_markdown(text)

        return text

    def _strip_markdown(self, text: str) -> str:
        """Lightweight regex-based Markdown syntax remover."""
        # 1. Remove images ![alt](url)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        # 2. Replace links [text](url) -> "text"
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # 3. Remove heading markers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        # 4. Remove bold/italic markers
        text = re.sub(r"(\*\*|__|\*|_)(.*?)\1", r"\2", text)
        return text
