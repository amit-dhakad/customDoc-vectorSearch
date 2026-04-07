import httpx
import os
import shutil
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    engine: Optional[str] = Form("fitz"),  # Default to fitz
    ocr: Optional[bool] = Form(True)      # Default OCR on
):
    """
    Parse an uploaded document by forwarding it to the ML Service.
    """
    # ── 1. Create the API client ───────────────────────────────────────────
    timeout = httpx.Timeout(600.0, connect=5.0)  # OCR can be very slow for large files
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            # ── 2. Prepare the request ─────────────────────────────────────
            files = {
                "file": (file.filename, file.file, file.content_type)
            }
            params = {
                "pdf_engine": engine.lower(),
                "use_ocr": ocr
            }

            # ── 3. Call ML Service ─────────────────────────────────────────
            url = f"{settings.ML_SERVICE_URL}/parse"
            response = await client.post(url, files=files, params=params)
            
            # Handle non-200 responses from ML Service
            if response.status_code != 200:
                logger_error_msg = f"ML Service error: {response.text}"
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=logger_error_msg
                )
            
            # ── 4. Return the result ───────────────────────────────────────
            return response.json()

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503, 
                detail=f"Service Unavailable: Could not reach ML Service at {exc.request.url}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Unexpected Error: {str(e)}"
            )

