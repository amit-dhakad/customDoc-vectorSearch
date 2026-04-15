from pydantic_settings import BaseSettings
import os

"""
backend/app/settings.py — Global Configuration Framework.

PURPOSE:
─────────────────────────────────────────────────────────────────────────────
This module serves as the 'Single Source of Truth' for all application 
variables. Using Pydantic Settings allows us to manage complex distributed 
architectures (FastAPI + ML Service + ChromaDB) with absolute type safety.

WHY THIS ARCHITECTURE IS BEST:
────────────────────────────────────────────────────
1. 12-FACTOR APP COMPLIANCE: By reading from environment variables first, 
   this setup is cloud-native and behaves perfectly inside Docker containers.
2. AUTOMATIC VALIDATION: If `CHROMA_PORT` is not an integer, the application 
   will fail to boot immediately with a clear error, rather than crashing 
   silently during a vector search.
3. ADAPTABILITY: Easily toggle between 'Localhost' development and 
   'Docker-Network' production by simply changing environment variables 
   without touching a single line of logic code.
"""

class Settings(BaseSettings):
    """
    Schema for application-wide configuration. 
    Fields can be overridden by environment variables (e.g., export PROJECT_NAME="My App").
    """
    PROJECT_NAME: str = "CustomDoc VectorSearch Backend"
    API_V1_STR: str = "/api/v1"

    # ML_SERVICE_URL:
    # Points to the extraction microservice. In the Docker Compose environment, 
    # 'ml-service' resolves to the container's internal IP via Docker DNS.
    ML_SERVICE_URL: str = os.getenv("ML_SERVICE_URL", "http://ml-service:8000")
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "chromadb")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", 8000))
    
    # OLLAMA CONFIGURATION:
    # Points to the host machine's Ollama instance.
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    
    # UPLOAD_DIR:
    # Persistent storage path for incoming documents before processing.
    # Paths are constructed relative to the application workspace.
    UPLOAD_DIR: str = os.path.join(os.getcwd(), "app", "data", "uploads")
    
    class Config:
        # Ensures that environment variables are matched exactly (e.g., API_V1_STR != api_v1_str)
        case_sensitive = True

# Singleton instance for application-wide use
settings = Settings()

# Bootstrap logic: Ensure the physical storage directory exists on startup 
# to prevent FileNotFoundError during document uploads.
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
