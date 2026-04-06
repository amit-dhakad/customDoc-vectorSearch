"""
txt_parser.py — Plain-text and Markdown document parser.

HOW PLAIN-TEXT PARSING WORKS
─────────────────────────────────────────────────────────────────────────────
Unlike PDF or DOCX, plain text files (.txt, .md, .csv, .log, …) are already
human-readable byte sequences.  There is no container format to unpack, no
glyph mapping, and no XML tree to walk.  Parsing reduces to two concerns:

  1. CHARACTER ENCODING DETECTION
     Text files do not carry a mandatory encoding declaration.  Common
     encodings include:
       • UTF-8      (most modern tools, Linux, macOS default)
       • UTF-8 BOM  (Windows Notepad default — starts with \xEF\xBB\xBF)
       • Latin-1 / ISO-8859-1  (legacy Western European docs)
       • Windows-1252 (superset of Latin-1, common on Windows)
       • UTF-16     (some Microsoft tools)

     Attempting to open a Latin-1 file as UTF-8 raises `UnicodeDecodeError`
     (or silently corrupts characters if `errors="replace"` is used).

     Our strategy: fallback chain
       a) Try UTF-8 (handles UTF-8 BOM via `utf-8-sig` codec).
       b) Try Latin-1 (Latin-1 is a superset of ASCII, so it NEVER raises a
          decode error though multi-byte chars may be wrong).
       c) Give up with a clear RuntimeError.

     A more robust alternative is the `chardet` library which reads the byte-
     frequency distribution to guess the encoding, but it adds a dependency
     and is an over-engineering for most cases.

  2. MARKDOWN-SPECIFIC HANDLING
     For .md files we have two sub-strategies:
       a) RAW  (default): Keep the Markdown syntax (#, *, **, >, ```, …).
          The heading markers (#, ##) serve as natural split boundaries for
          the chunker — we preserve them.
       b) STRIPPED: Use the `strip_markdown()` helper to remove all Markdown
          syntax characters and return pure prose.  Useful when the downstream
          embedding model is not Markdown-aware.

     By default we use RAW because most sentence-transformer models are
     trained on web text that includes Markdown and it doesn't hurt quality.

WHAT COUNTS AS "TXT" IN OUR PIPELINE?
─────────────────────────────────────────────────────────────────────────────
Our format detector (`format_detector.py`) routes the following extensions to
this parser:
    .txt   .md   .markdown   .rst   .log   .csv   .tsv

CSV / TSV files will be returned as-is (comma/tab-separated rows).  The
chunker will split them at newlines.  For structured CSV queries a dedicated
CSV parser (pandas-based) would give better results — add it if needed.

DEPENDENCY: none (Python stdlib only)
"""

from __future__ import annotations

import logging

from .base_parser import BaseParser

logger = logging.getLogger(__name__)

# Ordered list of encodings to try.  We try "utf-8-sig" first because it
# handles both plain UTF-8 AND UTF-8 files with a BOM (the BOM is silently
# consumed by the codec).  Latin-1 is the ultimate fallback because it can
# decode any byte value without raising an error.
_ENCODING_FALLBACKS: tuple[str, ...] = ("utf-8-sig", "utf-8", "latin-1")


class TxtParser(BaseParser):
    """
    Extracts text from plain-text files (.txt, .md, .rst, .csv, …).

    Parsing strategy:
        • Attempt to decode the file with a series of encodings (fastest-first).
        • Return the decoded string as-is.
        • Optionally strip Markdown syntax (controlled by `strip_markdown`).
    """

    def __init__(self, strip_markdown: bool = False) -> None:
        """
        Args:
            strip_markdown: If True, remove Markdown syntax characters from
                            the output.  Default False (keeps headings etc.
                            as natural chunk boundaries).
        """
        self.strip_markdown = strip_markdown

    def _extract_text(self, file_path: str) -> str:
        """
        Read and decode a plain-text file.

        Args:
            file_path: Path to the text file (already validated by BaseParser).

        Returns:
            The file's decoded text content.

        Raises:
            RuntimeError: If the file cannot be decoded with any known encoding.
        """
        # ── Encoding detection via fallback chain ──────────────────────────
        #
        # Strategy: try encodings in order.  The first one that succeeds wins.
        # This is O(n) over the number of fallback encodings (typically 3)
        # and reads the whole file each attempt — acceptable for files up to
        # a few MB.  For very large files, use `chardet.detect()` on the
        # first 32 KB to detect encoding without re-reading the whole file.
        text: str | None = None
        used_encoding: str = ""

        for encoding in _ENCODING_FALLBACKS:
            try:
                # ── Read the entire file into memory ──────────────────────
                #
                # `open(..., "r", encoding=…)` uses Python's codec system to
                # decode bytes → str on the fly.  For large files you could
                # use buffered reading (`f.read(chunk_size)`) but this keeps
                # the code simple since text files are rarely >100 MB in a
                # RAG context.
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()
                used_encoding = encoding
                break  # success — stop trying further encodings
            except UnicodeDecodeError:
                # This encoding cannot decode these bytes; try the next one.
                logger.debug(
                    "TxtParser: %s not decodable as %s, trying next encoding.",
                    file_path,
                    encoding,
                )
                continue

        if text is None:
            # All encodings failed — this is likely a binary file that was
            # misclassified as text (e.g. a .txt file that is actually a ZIP).
            raise RuntimeError(
                f"TxtParser: could not decode {file_path!r} with any of "
                f"{list(_ENCODING_FALLBACKS)}.  Is this really a text file?"
            )

        logger.info(
            "TxtParser: read %s  (%d chars, encoding=%s)",
            file_path,
            len(text),
            used_encoding,
        )

        # ── Optional Markdown stripping ────────────────────────────────────
        #
        # If the caller wants clean prose (e.g. for a model that performs
        # poorly with Markdown syntax), run the lightweight stripping helper.
        if self.strip_markdown:
            text = _strip_markdown(text)
            logger.debug(
                "TxtParser: stripped Markdown syntax, %d chars remaining.",
                len(text),
            )

        return text


# ── Markdown stripping helper ──────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """
    Remove common Markdown syntax characters from text.

    This is intentionally SIMPLE — production systems typically use the
    `markdown-it-py` or `mistune` library to parse Markdown into an AST,
    then render the AST as plain text.  We use a lightweight regex/string
    approach here to avoid a heavy dependency.

    Removed:
        • Heading markers          (#, ##, ###, …)
        • Bold/italic markers      (**text**, *text*, __text__, _text_)
        • Inline code backticks    (`code`)
        • Blockquote markers       (> )
        • Horizontal rules         (---, ***, ___)
        • Image syntax             (![alt](url))
        • Link syntax, keep text   ([text](url)) → "text"
        • List bullets             (-, *, +, 1.)

    Returns:
        Plain text with Markdown syntax removed.
    """
    import re

    # Remove images entirely — they carry no text for RAG
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    # Replace links [text](url) with just the link text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    # Remove heading markers at line start
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Remove bold/italic markers (order matters — ** before *)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)

    # Remove inline code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Remove blockquote markers
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Remove list bullet markers
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)

    return text
