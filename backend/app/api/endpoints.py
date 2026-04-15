from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
import httpx
import logging

from app.settings import settings
from app.database import get_db
from sqlalchemy.orm import Session as DBSession
from app import models

"""
backend/app/api/endpoints.py — Distributed RAG Orchestration Layer.

OFFICIAL ROLE:
─────────────────────────────────────────────────────────────────────────────
This module is the "Commander" of the application. It coordinates traffic 
between the Frontend (React), the Database (SQLite), and the Intelligence 
Engine (ML Service). 

KEY RESPONSIBILITIES:
────────────────────────────────────────────────────
1. DOCUMENT ORCHESTRATION (/parse):
   - Receives raw files and forwards them to the ML Service for heavy lifting.
   - Triggers the default "Hybrid Search Pipeline" (Dense + Sparse).
   - Manages real-time log streaming back to the user via WebSockets.

2. KNOWLEDGE MANIPULATION (/chunk):
   - Handles advanced user requests for custom segmentation.
   - Persists intelligence fragments into the relational database.
   - Coordinates the indexing of vectors into ChromaDB.

3. STATE MANAGEMENT (/documents/{id}/chunks):
   - Provides clean interfaces for the UI to preview and manage document segments.

WHY THIS IS THE BEST APPROACH:
───────────────────────────
- ASYNC EVERYTHING: Every call is non-blocking (FastAPI best practice), ensuring 
  the UI remains snappy even during 100-page document parsing.
- IDEMPOTENCY: We ensure metadata is mapped correctly to session IDs, preventing 
  duplicate data across separate chat windows.
- ERROR ISOLATION: If the ML service fails, the Backend gracefully reports the 
  error via WebSockets without crashing the main application.
"""

router = APIRouter()
logger = logging.getLogger(__name__)

async def send_log(request: Request, client_id: str, message: str):
    """
    Helper to relay processing logs back to the specific client via WebSockets.
    """
    if client_id:
        # Access the globally shared WS manager from the app state
        ws_manager = request.app.state.ws_manager
        await ws_manager.send_personal_message(message, client_id)

class LogUpdate(BaseModel):
    """Schema for internal log reporting from parsing engines."""
    client_id: str
    message: str

class ChunkConfig(BaseModel):
    """Encapsulates document text and segmentation strategy for JSON requests."""
    method: str = "recursive"
    vector_method: str = "dense"
    chunk_size: int = 1000
    overlap: int = 200
    text: Optional[str] = None
    client_id: Optional[str] = None
    session_id: Optional[str] = None  # When provided, vectors are stored under this session's collection

@router.get("/ollama/models")
async def get_ollama_models():
    """
    Proxy endpoint to fetch the list of models available in the local Ollama instance.
    Avoids CORS issues by proxying through the backend.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            if resp.status_code != 200:
                return {"models": [], "error": f"Ollama returned {resp.status_code}"}
            data = resp.json()
            models = [
                {"id": m["name"], "label": m["name"].replace(":latest", "").replace(":", " ")}
                for m in data.get("models", [])
            ]
            return {"models": models}
    except Exception as e:
        logger.warning(f"Could not reach Ollama to list models: {e}")
        return {"models": [], "error": str(e)}

@router.post("/internal/log")
async def receive_log(request: Request, log_data: LogUpdate):
    """
    Internal callback endpoint. 
    Allows the ML Service to report its progress back to the Backend, 
    which then relays it to the Frontend via WebSockets.
    """
    await send_log(request, log_data.client_id, log_data.message)
    return {"status": "ok"}

@router.get("/system/stats")
async def get_system_stats():
    """
    Hardware Monitoring.
    Calls the ML Service to get CPU/RAM usage. This is useful for users
    on lower-end hardware (like Raspberry Pi or VMs) to monitor OCR overhead.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            url = f"{settings.ML_SERVICE_URL}/system/stats"
            response = await client.get(url)
            return response.json()
        except Exception as e:
            # Fallback for when ML service is down/offline
            return {
                "cpu": 0, "memory": 0,
                "error": str(e)
            }

@router.post("/parse")
async def parse_document(
    request: Request,
    file: UploadFile = File(...),
    engine: Optional[str] = Form("fitz"),  # PDF Engine: 'fitz' (fast) or 'pdfplumber' (accurate)
    ocr: Optional[bool] = Form(False),     # Toggle for OCR-on-demand (Default to OFF for better UX)
    client_id: Optional[str] = Form(None),  # Unique frontend session tracking
    session_id: Optional[str] = Form(None), # Database session to link the document to
    auto_chunk: bool = Form(True),         # Trigger default RAG chunking immediately
    db: DBSession = Depends(get_db)
):
    """
    Document Orchestration Endpoint.
    1. Receives raw binary file from user.
    2. Streams it to the dedicated ML Service.
    3. Receives extracted text.
    4. Paradoxically stores metadata in the local SQLite DB if requested.
    """
    await send_log(request, client_id, f"INFO: Processing {file.filename}")
    await send_log(request, client_id, f"INFO: Engine set to {engine}")

    # Set a high timeout for heavy OCR or large PDFs
    timeout = httpx.Timeout(600.0, connect=5.0)
    
    # Reset file pointer to ensure consistent transmission to microservices
    await file.seek(0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            # Reconstruct the file payload for the microservice call
            files = {
                "file": (file.filename, file.file, file.content_type)
            }
            params = {
                "pdf_engine": engine.lower(),
                "use_ocr": ocr,
                "client_id": client_id
            }

            url = f"{settings.ML_SERVICE_URL}/parse"
            await send_log(request, client_id, f"DEBUG: Calling ML Service at {url}")
            
            # Forward the request to the processing engine
            response = await client.post(url, files=files, params=params)
            
            if response.status_code != 200:
                # Try to extract the clean error message from the ML Service response
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", response.text)
                except Exception:
                    detail = response.text
                
                logger_error_msg = f"ML Service error: {detail}"
                await send_log(request, client_id, f"ERROR: {logger_error_msg}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=logger_error_msg
                )
            
            result = response.json()
            extracted_text = result.get("text", "")
            
            # Persistence Logic:
            # Link the newly parsed document to the current chat session for future reference.
            if session_id:
                db_doc = models.Document(
                    session_id=session_id,
                    filename=file.filename,
                    file_type=file.content_type,
                    raw_content=extracted_text  # Persist for advanced chunking steps
                )
                db.add(db_doc)
                db.commit()
                db.refresh(db_doc)
                
                # Add doc_id to the result for the frontend to use in subsequent steps
                result["doc_id"] = db_doc.id
                
                # AUTO-CHUNKING (Direct View Flow)
                # If auto_chunk is True, we immediately trigger the default Recursive chunking.
                # Standard Chat users get RAG benefits without manual configuration.
                if extracted_text and auto_chunk:
                    await send_log(request, client_id, "INFO: Auto-triggering default Recursive chunking...")
                    try:
                        chunk_url = f"{settings.ML_SERVICE_URL}/chunk"
                        chunk_payload = {
                            "text": extracted_text,
                            "method": "recursive",
                            "vector_method": "hybrid",
                            "collection_name": session_id,
                            "client_id": client_id
                        }
                        chunk_res = await client.post(chunk_url, json=chunk_payload)
                        if chunk_res.status_code == 200:
                            chunks_data = chunk_res.json().get("chunks", [])
                            # Store in SQLite
                            for i, content in enumerate(chunks_data):
                                db_chunk = models.Chunk(
                                    document_id=db_doc.id,
                                    content=content,
                                    index=i
                                )
                                db.add(db_chunk)
                            db.commit()
                            await send_log(request, client_id, f"SUCCESS: {len(chunks_data)} chunks persisted to database.")
                    except Exception as chunk_err:
                        logger.error(f"Auto-chunking failed: {chunk_err}")
                        await send_log(request, client_id, "WARNING: Auto-chunking skipped due to internal error.")

                await send_log(request, client_id, f"INFO: Document {file.filename} associated with session {session_id}")

            await send_log(request, client_id, "SUCCESS: Document parsed successfully")
            return result

        except httpx.RequestError as exc:
            # Handle networking failures between internal containers
            await send_log(request, client_id, f"ERROR: Could not reach ML Service: {str(exc)}")
            raise HTTPException(
                status_code=503, 
                detail=f"Service Unavailable: Could not reach ML Service at {exc.request.url}"
            )
        except HTTPException:
            # Let FastAPI handle our own HTTPExceptions directly
            raise
        except Exception as e:
            await send_log(request, client_id, f"ERROR: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Unexpected Error: {str(e)}"
            )

@router.post("/chunk/{document_id}")
async def chunk_document(
    document_id: str,
    request: Request,
    config: ChunkConfig,
    db: DBSession = Depends(get_db)
):
    """
    Manual Chunking Endpoint (Advanced View).
    Receives an existing document ID (or 'demo'), chunks it via ML service, 
    and stores results in SQL & ChromaDB.
    """
    # 1. Determine collection name
    # PRIORITY: config.session_id (from AdvancedParsing) > doc.session_id > fallback
    doc_id_to_store = None
    source_text = config.text

    # Identification & Data Retrieval Logic:
    # If the user is in the 'Advanced' flow, we prioritize the data already in our SQL layer.
    if str(document_id).isdigit():
        doc = db.query(models.Document).filter(models.Document.id == int(document_id)).first()
        if doc:
            doc_id_to_store = doc.id
            if not source_text and doc.raw_content:
                source_text = doc.raw_content
            # Also update the document's session_id if provided via config (links doc to the new session)
            if config.session_id and not doc.session_id:
                doc.session_id = config.session_id
                db.commit()

    # Determine the ChromaDB collection to store vectors in
    # config.session_id wins — this is the session the user will chat in
    if config.session_id:
        collection_name = config.session_id
    elif doc_id_to_store:
        doc_check = db.query(models.Document).filter(models.Document.id == doc_id_to_store).first()
        collection_name = doc_check.session_id if doc_check and doc_check.session_id else "advanced_preview"
    else:
        collection_name = "advanced_preview"

    logger.info(f"Chunking: using collection '{collection_name}' for document_id={document_id}")

    if not source_text:
        raise HTTPException(status_code=400, detail="Intelligence Pipeline Error: No source text found for chunking. Please ensure text is provided or document is parsed.")

    # 2. Call ML Service
    async with httpx.AsyncClient(timeout=300.0) as client:
        chunk_url = f"{settings.ML_SERVICE_URL}/chunk"
        params = {
            "text": source_text,
            "method": config.method,
            "vector_method": config.vector_method,
            "chunk_size": config.chunk_size,
            "overlap": config.overlap,
            "collection_name": collection_name,
            "client_id": config.client_id
        }
        
        response = await client.post(chunk_url, json=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        chunks_data = result.get("chunks", [])

        # 3. Persistence (only if real doc exists in DB)
        if doc_id_to_store:
            # Clear old chunks for this document if re-chunking
            db.query(models.Chunk).filter(models.Chunk.document_id == doc_id_to_store).delete()
            
            for i, content in enumerate(chunks_data):
                db_chunk = models.Chunk(
                    document_id=doc_id_to_store,
                    content=content,
                    index=i
                )
                db.add(db_chunk)
            db.commit()

        return result

@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(document_id: int, db: DBSession = Depends(get_db)):
    """Retrieve all stored chunks for a specific document."""
    chunks = db.query(models.Chunk).filter(models.Chunk.document_id == document_id).all()
    return chunks

    return chunks


