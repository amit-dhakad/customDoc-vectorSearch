"""
ml-service/main.py — FastAPI entry point.
Exposes the document parsing suite as a professional HTTP API.
"""
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
import os
import shutil
import logging
from typing import Literal

# ── Dynamic Import of our core parsers ─────────────────────────────────────
from app.core.parsers.pdf_parser import PDFParser
from app.core.parsers.docx_parser import DocxParser
from app.core.parsers.txt_parser import TxtParser
from app.core.parsers.ocr_parser import OCRParser

# ── App Setup ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="ML Service — Parsing Suite",
    description="Unified API for Document Extraction (PDF, DOCX, TXT, OCR Images)",
    version="2.0.0"
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Uploads directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "app", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Helper: Format Router ──────────────────────────────────────────────────

def get_parser_by_extension(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return PDFParser()
    elif ext == ".docx":
        return DocxParser()
    elif ext in [".txt", ".md", ".log", ".csv"]:
        return TxtParser()
    elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
        return OCRParser()
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format: {ext}"
        )

# ── Endpoints ──────────────────────────────────────────────────────────────

@app.post("/parse", tags=["Parsing"])
async def parse_document(
    file: UploadFile = File(...),
    pdf_engine: Literal["fitz", "pdfplumber"] = Query(
        "fitz", description="Select PDF engine: 'fitz' for speed, 'pdfplumber' for accuracy."
    ),
    use_ocr: bool = Query(
        False, description="Enable OCR (Tesseract) for this file."
    )
):
    """
    Primary endpoint for document text extraction.
    Automatically detects file format and applies preferred PDF engine.
    """
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # 1. Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Routing logic
        if use_ocr or os.path.splitext(file.filename)[1].lower() in [".png", ".jpg", ".jpeg"]:
            parser = OCRParser()
        else:
            parser = get_parser_by_extension(file.filename)
        
        # 3. Execution
        logger.info("Parsing file [%s] using engine [%s]", file.filename, pdf_engine)
        text = parser.parse(file_path, engine=pdf_engine)
        
        return {
            "filename": file.filename,
            "engine_used": pdf_engine if not use_ocr else "OCR",
            "text": text,
            "status": "success"
        }
        
    except Exception as e:
        logger.error("Parsing failed for %s: %s", file.filename, str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 4. Clean up the disk
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/", tags=["Health"])
def health():
    return {"status": "online", "service": "ml-service"}
