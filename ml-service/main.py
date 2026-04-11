"""
ml-service/main.py — FastAPI Gateway & Extraction Orchestrator.

ARCHITECTURE OVERVIEW
─────────────────────────────────────────────────────────────────────────────
This is the primary entry point for the Machine Learning Extraction microservice.
It receives raw files, identifies the correct extraction strategy, and executes it.

Why a Separate Service?
  Parsing large PDFs and running OCR are highly CPU-intensive, blocking tasks.
  By isolating them in a separate service:
  1. The main Backend API remains free to serve other user requests.
  2. We can scale the ML service independently under heavy load.

INTERNAL COMMUNICATION BRIDGE
─────────────────────────────────────────────────────────────────────────────
Because extraction can take seconds or minutes, this service must report 
progress back to the user. It does this via synchronous HTTP calls to an 
internal Backend reporting endpoint (`report_progress`), which the Backend 
then relays to the frontend via WebSockets.
"""
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
import os
import shutil
import logging
import httpx
import psutil
from typing import Literal, Optional

# ── Dynamic Import of Engine Implementations ───────────────────────────────
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

# Standard logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary directory for file buffering during processing
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "app", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Internal Communication Bridge ──────────────────────────────────────────
# The ML service reports progress to this internal 'log' endpoint on the backend, 
# which then relays it to the frontend via WebSockets.
BACKEND_LOG_URL = os.getenv("BACKEND_URL", "http://backend:8000") + "/api/v1/internal/log"

def report_progress(client_id: str, message: str):
    """
    Relays status messages back to the primary backend gateway.
    This bridge allows long-running OCR tasks to provide real-time feedback.
    """
    if not client_id:
        return
    try:
        # Synchronous POST is used here to avoid event loop complexity 
        # inside the core parsing logic which is heavily CPU-bound.
        httpx.post(BACKEND_LOG_URL, json={"client_id": client_id, "message": message}, timeout=0.5)
    except Exception as e:
        logger.error("Failed to report progress (Bridge might be down): %s", str(e))

@app.get("/system/stats")
async def get_system_stats():
    """
    Performance Telemetry.
    Returns real-time CPU and RAM percentage to help users monitor OCR-heavy workloads.
    """
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "memory": psutil.virtual_memory().percent
    }

# ── Factory Pattern: Parser Selection ──────────────────────────────────────

def get_parser_by_extension(filename: str):
    """
    Identifies the correct parser engine based on file extension.
    Example of the Factory Pattern in action.
    """
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
    ),
    client_id: Optional[str] = Query(
        None, description="Optional ID for tracking live logs via WebSocket."
    )
):
    """
    Primary Extraction Pipeline.
    1. Buffers the uploaded document to disk.
    2. Routes the file to the selected or auto-detected engine.
    3. Executes the extraction while reporting progress via the Bridge.
    4. Cleans up temporary files.
    """
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # 1. Buffered Input: Save raw binary to local disk for parser access
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Engine Routing: Determine if we use standard text extraction or OCR
        if use_ocr or os.path.splitext(file.filename)[1].lower() in [".png", ".jpg", ".jpeg", ".tiff"]:
            parser = OCRParser()
        else:
            parser = get_parser_by_extension(file.filename)
        
        # 3. Execution: Run the parser and relay progress reports
        logger.info("Parsing file [%s] using engine [%s]", file.filename, pdf_engine)
        text = parser.parse(
            file_path, 
            engine=pdf_engine, 
            client_id=client_id, 
            reporter=report_progress
        )
        
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
        # 4. Storage Management: Delete buffered file to prevent disk exhaustion
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/", tags=["Health"])
def health():
    return {"status": "online", "service": "ml-service"}
