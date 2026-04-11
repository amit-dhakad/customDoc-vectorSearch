from pydantic_settings import BaseSettings
import os

"""
Application Configuration
-------------------------
Centralized settings management using Pydantic Settings. 
This allows the application to read configuration from environment 
variables with automatic type conversion and validation.
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
