from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "CustomDoc VectorSearch Backend"
    API_V1_STR: str = "/api/v1"

    # ML Service endpoint (Docker service name by default)
    ML_SERVICE_URL: str = os.getenv("ML_SERVICE_URL", "http://ml-service:8000")
    
    # Storage for uploaded files
    UPLOAD_DIR: str = os.path.join(os.getcwd(), "app", "data", "uploads")
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
