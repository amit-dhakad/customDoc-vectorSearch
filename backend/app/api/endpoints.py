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
Modular API Endpoints
---------------------
This module contains the primary business routes for the application, 
including document parsing and system health monitoring. It acts as an 
orchestrator between the frontend, the database, and the ML microservice.
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
    ocr: Optional[bool] = Form(True),      # Toggle for OCR-on-demand
    client_id: Optional[str] = Form(None),  # Unique frontend session tracking
    session_id: Optional[str] = Form(None), # Database session to link the document to
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
                logger_error_msg = f"ML Service error: {response.text}"
                await send_log(request, client_id, f"ERROR: {logger_error_msg}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=logger_error_msg
                )
            
            result = response.json()
            
            # Persistence Logic:
            # Link the newly parsed document to the current chat session for future reference.
            if session_id:
                db_doc = models.Document(
                    session_id=session_id,
                    filename=file.filename,
                    file_type=file.content_type
                )
                db.add(db_doc)
                db.commit()
                db.refresh(db_doc)
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
        except Exception as e:
            await send_log(request, client_id, f"ERROR: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Unexpected Error: {str(e)}"
            )


