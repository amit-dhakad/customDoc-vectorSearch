# ML Service — Document Parsing Architecture & Interview Prep

This document details the professional-grade parsing system we've integrated into the **ML Service**. It is designed to prepare you for technical discussions about RAG ingestion pipelines and document engineering.

---

### 1. The Strategy: Modular Implementation
We've moved all parsing logic to `ml-service/app/core/parsers/`. By using an **Abstract Base Class (`BaseParser`)**, we ensure that all parsers (PDF, Docx, Txt, OCR) share the same uniform interface. 

#### Q1: Why not just use one PDF library?
- **Answer**: No single library is perfect. 
- **`fitz` (PyMuPDF)**: Extremely fast (C-based) and handles simple files brilliantly. 
- **`pdfplumber`**: Excels at visual fidelity—preserving margins, spacing, and tables that `fitz` might scramble.
- **Our choice**: We built a **Dual-Engine Parser**. This gives the *caller* the power to choose `fitz` for speed or `pdfplumber` for structured accuracy.

---

### 2. OCR Strategy (Optical Character Recognition)

#### Q2: What is the difference between "Text Layer Extraction" and "OCR"?
- **Answer**: 
    - **Text Layer**: Most PDFs (born-digital) have a hidden layer of Unicode characters mapped to glyph positions. Libraries like `fitz` or `pdfplumber` read this layer directly without "seeing" the page.
    - **OCR**: Used for scanned documents where no text layer exists. We must render the page as an image (bitmap) and use a neural network (Tesseract) to recognize character shapes.
- **Trade-off**: OCR is 10-50x slower and requires more hardware resources.

#### Q3: How do we handle "Mixed" Documents (Some pages scanned, some digital)?
- **Answer**: Our `PDFParser` uses an **Automatic Fallback** mechanism. It first attempts to extract the text layer. If a page returns an empty string, it assumes the page is an image and triggers the OCR engine (`pytesseract`) specifically for that page. This saves time on pages that don't need OCR.

---

### 3. Document Structure & Tables

#### Q4: How do we handle Tables in documents?
- **Answer**: 
    - In **Word (Docx)**, we iterate through the XML table structure and join cells with a pipe (`|`) to maintain the grid relationship.
    - In **PDF**, we use `pdfplumber` which is specialized in "table discovery." It identifies lines and gutters to reconstruct the columns and rows as clear text blocks.
- **Why it matters**: Simply extracting raw text from a table usually scrambles the columns, making the data unusable for an LLM (RAG).

---

### 4. Text Encodings & Security

#### Q5: Why do we use a "Fallback Chain" for plain-text files?
- **Answer**: Text files (`.txt`, `.csv`) don't have a header that declares their encoding. We try **`utf-8-sig`** first (to catch Windows BOM marks), then fallback to **`latin-1`**. 
- **Interview Detail**: `latin-1` is important because it can decode any sequence of bytes without throwing an error, acting as a "safe" final fallback for corrupted or legacy files.

#### Q6: How do we handle file security during the /parse request?
- **Answer**: We use **FastAPI's UploadFile** which is a "Spool" file implementation—it keeps small files in memory and only writes large files to a temporary disk location. After parsing, we use a `finally` block to ensure the temporary file is deleted, preventing disk-bloat or data leakage.

---

### 5. API & Containerization

#### Q7: Why Dockerize this service instead of just running it locally?
- **Answer**: Our service has complex system dependencies like **`tesseract-ocr`** and **`poppler-utils`**. 
- On a developer's machine, these might be missing or different versions. 
- **Docker** guarantees that the exact versions of these binaries exist in the production environment, eliminating "it works on my machine" bugs.

#### Q8: Why use FastAPI over Flask or Django for this use-case?
- **Answer**: 
    1. **Asynchrony**: FastAPI handles concurrent I/O (like file uploads) without blocking the thread.
    2. **Auto-Swagger**: It generates OpenAPI docs instantly, allowing frontend teams to test the parser in 5 seconds.
    3. **Pydantic**: It validates the incoming files and parameters automatically.

---

### 6. RAG Specifics (The "Advanced" Layer)

#### Q9: How does the choice of parser impact the RAG system's accuracy?
- **Answer**: If a parser returns "noisy" text (e.g., footers, page numbers, or scrambled tables), the **Embeddings Model** will create a poor vector representation of that chunk. Clean text extraction from `fitz` or `pdfplumber` leads to higher quality retrieval and fewer LLM hallucinations.

#### Q10: What is the next logical step after this parsing service?
- **Answer**: **Semantic Chunking**. Once we have the text, we need to split it into chunks that preserve meaning (e.g., not cutting a sentence in half). We would typically use a `RecursiveCharacterTextSplitter` from LangChain to break the text down into 500-1000 character pieces for the vector database.
