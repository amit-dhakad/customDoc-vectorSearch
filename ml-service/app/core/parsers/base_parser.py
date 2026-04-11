"""
Abstract Parser Foundation
--------------------------
This module defines the BaseParser class, which implements the Template Method 
design pattern. It provides a consistent interface for all extraction engines 
(PDF, DOCX, etc.) while handling universal concerns like file validation, 
error wrapping, and quality checks.

WHY AN ABSTRACT BASE CLASS?
─────────────────────────────────────────────────────────────────────────────
Every document format (PDF, DOCX, TXT, etc.) needs to be parsed differently,
but the ingestion pipeline always wants the same thing from any parser:
    → a plain Python string of the document's text content.

By defining a single interface (BaseParser.parse), we:
  1. Force every new parser to honour the same contract.
  2. Let the ingestion service call `parser.parse(path)` without knowing
     or caring which concrete parser it's talking to (Open/Closed Principle).
  3. Make unit-testing easy: swap in a FakeParser that returns canned text.

DESIGN PATTERN: Template Method
─────────────────────────────────────────────────────────────────────────────
  • `parse()` — The PUBLIC method the pipeline calls. It handles common concerns
                shared by ALL parsers: file existence, file size, and error wrapping.
  • `_extract_text()` — The ABSTRACT hook each subclass must implement.
                        Contains the format-specific heavy-lifting.
"""

from __future__ import annotations
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """
    Abstract parser that all concrete format parsers must subclass.

    Standard Workflow:
      1. Pipeline calls `parser.parse(file_path)`
      2. BaseParser validates the file exists and isn't 0 bytes.
      3. BaseParser calls the subclass's `_extract_text()` implementation.
      4. BaseParser cleans up whitespace and logs quality warnings.
    """

    def parse(self, file_path: str, **kwargs) -> str:
        """
        Public entry-point for text extraction.

        Args:
            file_path: Absolute or relative path to the document.
            **kwargs: Extra parameters passed to subclasses (e.g., engine="pdfplumber").

        Returns:
            The document's text as a single cleaned string.

        Raises:
            FileNotFoundError: If the file is missing.
            ValueError: If the file is empty.
            RuntimeError: If the format-specific extraction fails.
        """
        # ── Step 1: Universal Validation ───────────────────────────────────
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Parser: File not found → {file_path!r}")

        if os.path.getsize(file_path) == 0:
            raise ValueError(f"Parser: File is empty (0 bytes) → {file_path!r}")

        logger.info("Parsing file: %s (parser=%s)", file_path, self.__class__.__name__)

        # ── Step 2: Format-Specific Extraction ─────────────────────────────
        try:
            # We delegate the actual parsing to the subclass's implementation
            raw_text: str = self._extract_text(file_path, **kwargs)
        except Exception as exc:
            # Shield the rest of the app from library-specific exceptions
            raise RuntimeError(
                f"Parser [{self.__class__.__name__}] failed on {file_path!r}: {exc}"
            ) from exc

        # ── Step 3: Global Post-Processing ─────────────────────────────────
        text: str = raw_text.strip()

        # Quality check: A document with <50 chars is often a 'fail' (e.g. image-only PDF)
        if len(text) < 50:
            logger.warning(
                "Parser [%s] extracted very little text (%d chars). "
                "Document may be image-only or corrupted.",
                self.__class__.__name__, len(text)
            )

        return text

    @abstractmethod
    def _extract_text(self, file_path: str, **kwargs) -> str:
        """
        The abstract hook that subclasses MUST override.
        This contains the byte-level logic for libraries like PyMuPDF or Docx.
        """
        pass
