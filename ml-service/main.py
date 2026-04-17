"""
ml-service/main.py — Intelligence Extraction & Vectorization Gateway.

CORE MISSION
─────────────────────────────────────────────────────────────────────────────
This service acts as the "Heavy Lifter" for the RAG pipeline. It handles the 
high-compute tasks of Parsing (PDF/OCR), Segmenting (Chunking), and 
Inteligent Vectorization (Dense/Sparse/Hybrid/ColBERT).

PIPELINE STAGES:
────────────────────────────────────────────────────
1. EXTRACTION: Raw binary files go in -> Text & Metadata comes out.
   - Fast Path: PyMuPDF (fitz) for standard PDFs.
   - Accurate Path: pdfplumber for complex layouts.
   - Visual Path: Tesseract OCR for scanned images/PDFs.

2. INTELLIGENCE: Text is transformed into "Knowledge Units".
   - Multi-Strategy Chunking: Ensures semantic boundaries are respected.
   - High-Precision Vectorization: Maps text to mathematical space for search.
   - Strategy Choice: Users can optimize for speed (Dense) or accuracy (ColBERT).

3. PERSISTENCE: 
   - Fragments are pushed to ChromaDB for sub-millisecond similarity search.
   - Feedback is streamed back to the frontend via the Backend reporting bridge.

WHY THIS ARCHITECTURE WINS:
──────────────────────────
By decoupling the Intelligence Pipeline from the Main API, we ensure that:
- Long-running OCR tasks don't block the UI or the Chat engine.
- Processing can be scaled vertically (more CPU/RAM) or horizontally (more workers).
- We provide a "Professional Grade" ingestion engine that outperforms simple 
  LangChain wrappers by allowing granular control over every step.
"""
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
import os
import shutil
import logging
import httpx
import psutil
from pydantic import BaseModel
from typing import Literal, Optional

# ── Dynamic Import of Engine Implementations ───────────────────────────────
from app.core.parsers.pdf_parser import PDFParser
from app.core.parsers.docx_parser import DocxParser
from app.core.parsers.txt_parser import TxtParser
from app.core.parsers.ocr_parser import OCRParser
from app.core.chunking import get_chunks, COMPUTE_DEVICE
from app.core.evaluation import RagasEvaluator

# ── App Setup ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="ML Service — Parsing Suite",
    description="Unified API for Document Extraction (PDF, DOCX, TXT, OCR Images)",
    version="2.0.0"
)

# Activity Tracking
active_tasks = 0

# Standard logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resource Tracking
process = psutil.Process(os.getpid())
# Initialize CPU tracking so the first call doesn't return 0
process.cpu_percent()
psutil.cpu_percent()

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

def _get_container_mem():
    """Reads container memory from cgroups if available."""
    try:
        # Cgroup V2 (Standard in modern Docker/WSL2)
        if os.path.exists('/sys/fs/cgroup/memory.current'):
            with open('/sys/fs/cgroup/memory.current', 'r') as f:
                used = int(f.read())
            with open('/sys/fs/cgroup/memory.max', 'r') as f:
                limit_str = f.read().strip()
                limit = int(limit_str) if limit_str != "max" else psutil.virtual_memory().total
            return round((used / limit) * 100, 1), used // (1024**2)
        # Cgroup V1 Fallback
        elif os.path.exists('/sys/fs/cgroup/memory/memory.usage_in_bytes'):
            with open('/sys/fs/cgroup/memory/memory.usage_in_bytes', 'r') as f:
                used = int(f.read())
            with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                limit = int(f.read())
            return round((used / limit) * 100, 1), used // (1024**2)
    except:
        pass
    return None, None

@app.get("/system/stats")
async def get_system_stats():
    """
    Performance Telemetry.
    Returns real-time CPU, RAM, and GPU stats. 
    Now 'container-aware' to fix incorrect reporting in Docker/WSL2.
    """
    container_pct, container_mb = _get_container_mem()
    
    # Process-specific metrics (often what users actually care about)
    proc_mem_mb = process.memory_info().rss // (1024**2)
    proc_cpu_pct = process.cpu_percent()
    
    stats = {
        "cpu": psutil.cpu_percent(), # System/VM CPU
        "memory": container_pct or psutil.virtual_memory().percent, # Container or VM RAM
        "process_cpu": proc_cpu_pct,
        "process_mem_mb": proc_mem_mb,
        "container_mem_mb": container_mb,
        "device": COMPUTE_DEVICE,
        "pipeline_status": "PROCESSING" if active_tasks > 0 else "IDLE",
        "gpu": None,
    }

    # Attempt to read live GPU stats if CUDA is active
    if COMPUTE_DEVICE == "cuda":
        try:
            import torch
            if torch.cuda.is_available():
                gpu_props = torch.cuda.get_device_properties(0)
                allocated_mb  = torch.cuda.memory_allocated(0) / (1024 ** 2)
                reserved_mb   = torch.cuda.memory_reserved(0)  / (1024 ** 2)
                total_mb      = gpu_props.total_memory          / (1024 ** 2)
                stats["gpu"] = {
                    "name":         gpu_props.name,
                    "vram_total_mb": round(total_mb),
                    "vram_used_mb":  round(reserved_mb),
                    "vram_free_mb":  round(total_mb - reserved_mb),
                    "utilization":   round((reserved_mb / total_mb) * 100, 1),
                }
        except Exception as e:
            stats["gpu"] = {"error": str(e)}

    return stats

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

# ── Pydantic Request Models ───────────────────────────────
class ChunkRequest(BaseModel):
    """Encapsulates document text and segmentation strategy."""
    text: str
    method: Literal["fixed", "overlap", "recursive", "structural", "semantic"] = "recursive"
    vector_method: Literal["dense", "sparse", "hybrid", "colbert"] = "dense"
    chunk_size: int = 1000
    overlap: int = 200
    collection_name: Optional[str] = None
    client_id: Optional[str] = None

class RetrieveRequest(BaseModel):
    """Request schema for context retrieval."""
    collection_name: str
    query: str
    n_results: int = 4
    search_type: Literal["dense", "hybrid"] = "hybrid"
    rerank: bool = True

class EvaluateRequest(BaseModel):
    """Request schema for RAGAS evaluation."""
    query: str
    answer: str
    context: List[str]
    ground_truth: Optional[str] = None


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
    global active_tasks
    active_tasks += 1
    
    try:
        # 1. Buffered Input: Save raw binary to local disk for parser access
        contents = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        # 2. Engine Routing: Determine if we use standard text extraction or OCR
        ext = os.path.splitext(file.filename)[1].lower()
        is_image = ext in [".png", ".jpg", ".jpeg", ".tiff"]
        is_pdf = ext == ".pdf"

        if use_ocr:
            if is_pdf or is_image:
                parser = OCRParser()
            else:
                # User requested OCR but format doesn't support it
                raise HTTPException(
                    status_code=400,
                    detail=f"OCR is not supported for {ext} files. Please use standard parsing."
                )
        elif is_image:
            # Auto-routing for images even if ocr=False, as images require OCR
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
        active_tasks -= 1
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/chunk", tags=["RAG"])
async def chunk_text(request: ChunkRequest):
    """
    Segmentation & Intelligence Pipeline.
    1. Receives raw text in JSON body.
    2. Segments text using the selected strategy.
    3. Vectorizes using Dense, Sparse, Hybrid, or Late Interaction (ColBERT).
    4. Returns list of intelligent chunks.
    """
    global active_tasks
    active_tasks += 1
    try:
        if request.client_id:
            report_progress(request.client_id, f"INFO: Starting {request.method.upper()} chunking with {request.vector_method.upper()} vectorization...")
            
        chunks = get_chunks(
            request.text, 
            request.method, 
            request.vector_method, 
            request.chunk_size, 
            request.overlap, 
            request.collection_name
        )
        
        if request.client_id:
            report_progress(request.client_id, f"SUCCESS: Generated {len(chunks)} fragments.")
            
        return {
            "method": request.method,
            "vector_method": request.vector_method,
            "chunk_count": len(chunks),
            "chunks": chunks,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        active_tasks -= 1

@app.post("/retrieve", tags=["RAG"])
async def retrieve_context(request: RetrieveRequest):
    """
    Retrieval Endpoint.
    Searches ChromaDB for relevant text fragments.
    """
    try:
        vm = VectorManager()
        context = vm.retrieve_context(
            request.collection_name, 
            request.query, 
            request.n_results,
            search_type=request.search_type,
            rerank=request.rerank
        )
        return {"context": context, "status": "success"}
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate", tags=["RAG"])
async def evaluate_rag(request: EvaluateRequest):
    """
    RAG Evaluation Endpoint.
    Uses RAGAS to compute faithfulness, relevance, and precision/recall.
    """
    try:
        evaluator = RagasEvaluator()
        scores = await evaluator.evaluate_qna(
            request.query, 
            request.answer, 
            request.context,
            request.ground_truth
        )
        return {"scores": scores, "status": "success"}
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        # Return empty scores instead of crashing, as evaluation is often 'best-effort'
        return {"scores": {}, "error": str(e), "status": "error"}


@app.get("/", tags=["Health"])
def health():
    return {"status": "online", "service": "ml-service"}
