"""
base_parser.py — Abstract Base Class for all document parsers.

WHY AN ABSTRACT BASE CLASS?
─────────────────────────────────────────────────────────────────────────────
Every document format (PDF, DOCX, TXT, etc.) needs to be parsed differently,
but the ingestion pipeline always wants the same thing from any parser:
    → a plain Python string of the document's text content.

By defining a single interface (BaseParser.parse), we:
  1. Force every new parser to honour the same contract.
  2. Let the ingestion service call `parser.parse(path)` without knowing
     or caring which concrete parser it's talking to  (Open/Closed Principle).
  3. Make unit-testing easy: swap in a FakeParser that returns canned text.

DESIGN PATTERN: Template Method / Strategy (The Template Method is based on inheritance. 
It defines the skeleton of an algorithm in a base class but lets subclasses 
override specific steps without changing the algorithm's overall)
─────────────────────────────────────────────────────────────────────────────
  • `parse()`    — the PUBLIC method the pipeline calls.
                   It does generic pre/post work (validation, logging) and
                   calls `_extract_text()` internally.
  • `_extract_text()` — the ABSTRACT hook each subclass must implement.
                        Contains all the format-specific logic.

This separation means common concerns (file exists? file empty?) live here
exactly once, not repeated in every parser.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod # ABC is used to create abstract base classes, and abstractmethod is used to mark methods as abstract

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract parser that all concrete format parsers must subclass.

    Usage in the ingestion pipeline
    ────────────────────────────────
        parser: BaseParser = PDFParser()          # or DocxParser, TxtParser …
        text: str          = parser.parse(path)   # uniform call, always str
    """

    # ── Public entry-point ─────────────────────────────────────────────────

    def parse(self, file_path: str) -> str:
        """
        Parse a document at `file_path` and return its full plain-text content.

        Pipeline:
          1. Validate the file exists and is non-empty (raises on failure).
          2. Delegate to `_extract_text()` — format-specific heavy lifting.
          3. Strip leading/trailing whitespace from the result.
          4. Warn if the extracted text is suspiciously short (possible parse
             failure or an image-only / scanned PDF with no embedded text).

        Args:
            file_path: Absolute or relative path to the document on disk.

        Returns:
            The document's text as a single Python string.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError:        If the file is empty (0 bytes).
            RuntimeError:      If the concrete parser raises an unexpected error.
        """
        # ── Step 1: file validation ───────────────────────────────────────
        #
        # We validate here (in the base class) rather than in each subclass
        # so that every parser automatically gets this safety net.
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Parser: file not found → {file_path!r}")

        if os.path.getsize(file_path) == 0:
            raise ValueError(f"Parser: file is empty (0 bytes) → {file_path!r}")

        logger.info("Parsing file: %s  (parser=%s)", file_path, self.__class__.__name__)

        # ── Step 2: delegate to the concrete subclass ─────────────────────
        #
        # `_extract_text` is overridden by PDFParser, DocxParser, TxtParser.
        # Each one knows the byte-level details of its own format.
        try:
            raw_text: str = self._extract_text(file_path)
        except Exception as exc:
            # Wrap any library-level error in a uniform RuntimeError so the
            # ingestion service only needs to catch one exception type.
            raise RuntimeError(
                f"Parser [{self.__class__.__name__}] failed on {file_path!r}: {exc}"
            ) from exc

        # ── Step 3: normalise whitespace ──────────────────────────────────
        #
        # Many parsers return text with leading/trailing blank lines.
        # Stripping here keeps the chunker input clean.
        text: str = raw_text.strip()

        # ── Step 4: quality warning ───────────────────────────────────────
        #
        # A real document with <50 characters is almost certainly a parse
        # failure (e.g. a scanned PDF with no embedded text layer).
        if len(text) < 50:
            logger.warning(
                "Parser [%s] extracted very little text (%d chars) from %s. "
                "The document may be image-only or corrupted.",
                self.__class__.__name__,
                len(text),
                file_path,
            )

        logger.debug(
            "Parser [%s] extracted %d characters from %s",
            self.__class__.__name__,
            len(text),
            file_path,
        )

        return text

    # ── Abstract hook — subclasses implement this ──────────────────────────

    @abstractmethod
    def _extract_text(self, file_path: str) -> str:
        """
        Format-specific text extraction.

        Subclasses MUST override this method.  They should:
          • Open the file using the appropriate library.
          • Iterate over all content-bearing units (pages, paragraphs, lines…).
          • Concatenate the raw text.
          • Return it as a plain str (no HTML, no markdown, no metadata blobs).

        Args:
            file_path: Already-validated path to the document.

        Returns:
            Raw text extracted from the document (may have extra whitespace —
            the base class `parse()` will strip it).
        """
        ...
