"""
docx_parser.py — DOCX document parser using python-docx.

HOW DOCX PARSING WORKS
─────────────────────────────────────────────────────────────────────────────
A .docx file is actually a ZIP archive that follows the Open XML standard
(ECMA-376 / ISO 29500).  Inside the ZIP you'll find:

    word/document.xml       ← The main body content (paragraphs, tables …)
    word/styles.xml         ← Paragraph and character style definitions
    word/numbering.xml      ← List numbering definitions
    word/footnotes.xml      ← Footnotes
    docProps/core.xml        ← Document metadata (author, created date …)
    [Content_Types].xml     ← XML namespace declarations

python-docx unzips/parses `document.xml` and exposes its content through a
Pythonic object model.  Internally:
  1. The library reads the XML byte stream.
  2. It walks the XML tree to find `<w:p>` (paragraph) and `<w:tbl>` (table)
     elements.
  3. Each `<w:p>` element contains one or more `<w:r>` (run) elements, each
     carrying a fragment of text and its character-level formatting.
  4. python-docx concatenates the text of all runs within a paragraph to
     produce `paragraph.text`.

WHAT WE EXTRACT
─────────────────────────────────────────────────────────────────────────────
We focus on two content sources:

  A) Body paragraphs  (`doc.paragraphs`)
     These include headings (Heading 1–9 styles), normal body text, bullet
     lists, numbered lists, and captions.
     Headings are prefixed with "#" markers so the text retains semantic
     structure that the chunker can use as natural split points.

  B) Tables  (`doc.tables`)
     DOCX tables are stored as a grid of cells, each cell containing its own
     list of paragraphs.  We flatten each row into a tab-separated line so
     the table data is readable as plain text (e.g. for Q&A over spreadsheet-
     like documents).

WHAT WE SKIP
─────────────────────────────────────────────────────────────────────────────
  • Headers and footers — usually contain page numbers / company logos; rarely
    useful for semantic search.
  • Embedded images — require a separate OCR step.
  • Text inside shapes / text boxes — accessible via `doc.inline_shapes`, but
    omitted here for simplicity; add if needed.
  • Comments and tracked changes — hidden annotations; can add via the raw XML
    if required.

DEPENDENCY: python-docx
    pip install python-docx
"""

from __future__ import annotations

import logging

from docx import Document  # python-docx — `pip install python-docx`
from docx.oxml.ns import qn  # Qualified-name helper for Word XML namespaces

from .base_parser import BaseParser

logger = logging.getLogger(__name__)

# ── Style-name prefix mapping ──────────────────────────────────────────────
#
# DOCX headings have style names like "Heading 1", "Heading 2", etc.
# We convert them to Markdown-style "#" prefixes so the chunker can
# optionally treat heading lines as chunk boundaries.
_HEADING_PREFIX: dict[str, str] = {
    "Heading 1": "# ",
    "Heading 2": "## ",
    "Heading 3": "### ",
    "Heading 4": "#### ",
    "Heading 5": "##### ",
    "Heading 6": "###### ",
}


class DocxParser(BaseParser):
    """
    Extracts text from DOCX files (Microsoft Word Open XML format).

    Parsing strategy:
        1. Open with `python-docx`.
        2. Iterate body paragraphs — prepend heading markers where appropriate.
        3. Iterate tables — flatten each cell into a tab-separated row.
        4. Return the combined text.
    """

    def _extract_text(self, file_path: str) -> str:
        """
        Extract text from a .docx file.

        Args:
            file_path: Path to the .docx file (already validated by BaseParser).

        Returns:
            Full document text as a single string.
        """
        # ── Open the DOCX ──────────────────────────────────────────────────
        #
        # `Document(path)` unzips the archive and parses `word/document.xml`.
        # The resulting `doc` object gives us `.paragraphs` and `.tables`.
        doc = Document(file_path)
        logger.info(
            "DocxParser: opened %s  (%d paragraphs, %d tables)",
            file_path,
            len(doc.paragraphs),
            len(doc.tables),
        )

        parts: list[str] = []

        # ── A: Extract body paragraphs ─────────────────────────────────────
        #
        # `doc.paragraphs` yields `Paragraph` objects in document order.
        # Each `Paragraph` has:
        #   .text       → concatenated text of all runs (no formatting)
        #   .style.name → the paragraph's named style (e.g. "Heading 1",
        #                 "Normal", "List Bullet")
        #
        # We skip blank paragraphs (just whitespace) — they add noise without
        # semantic value.
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue  # skip empty lines

            # Detect if this paragraph uses a heading style and prefix it
            # so the chunker can use headings as natural split boundaries.
            style_name: str = para.style.name  # e.g. "Heading 2"
            prefix: str = _HEADING_PREFIX.get(style_name, "")

            parts.append(prefix + text)

        # ── B: Extract tables ──────────────────────────────────────────────
        #
        # Tables in DOCX are stored as a grid:
        #   doc.tables[i].rows[j].cells[k].paragraphs[l].text
        #
        # We flatten this structure into one line per row, with cells
        # separated by " | " (pipe), so a 3-column table row becomes:
        #   "Cell A | Cell B | Cell C"
        #
        # This is NOT perfect for complex merged-cell tables but is a
        # good approximation for semantic search purposes.
        for table_index, table in enumerate(doc.tables):
            parts.append(f"\n[Table {table_index + 1}]")
            for row in table.rows:
                # Each cell can contain multiple paragraphs — join them with
                # a space to keep the cell text on one line.
                cell_texts = [
                    " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())
                    for cell in row.cells
                ]
                row_line = " | ".join(cell_texts)
                if row_line.strip():
                    parts.append(row_line)

        # ── Combine all parts ──────────────────────────────────────────────
        #
        # Newline between parts; the base class strips the overall result.
        return "\n".join(parts)
