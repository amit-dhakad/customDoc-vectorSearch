# ── ML Service Dockerfile — GPU-aware with CPU fallback ───────────────────
#
# Base image: Python 3.10 Slim. PyTorch bundles its own lightweight CUDA dependencies.
FROM python:3.10-slim

# Prevent .pyc files and ensure real-time terminal logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Avoid interactive prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (Tesseract OCR, PDF tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


# Establish the working directory
WORKDIR /app

# Standardize pip and increase resilience for large package downloads
RUN pip install --no-cache-dir --upgrade pip

# Copy and install Python dependencies
COPY requirements.txt .

# Install PyTorch with CUDA 12.1 first (so other packages pick up GPU-enabled torch)
# We use high timeout and retry counts to survive slow/unstable network connections
RUN pip install --no-cache-dir --default-timeout=1000 --retries 50 torch --index-url https://download.pytorch.org/whl/cu121

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy full service code
COPY . .

# Launch the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
