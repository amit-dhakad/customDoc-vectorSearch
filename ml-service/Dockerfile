# ── ML Service Dockerfile — GPU-aware with CPU fallback ───────────────────
#
# Base image: nvidia/cuda runtime so the container can access the host GPU
# via the NVIDIA Container Toolkit (nvidia-docker2 or docker --gpus flag).
#
# If Docker can't find an NVIDIA runtime on the host, the container still
# starts and runs on CPU — the PyTorch CUDA check in chunking.py will simply
# return False and fall back to CPU automatically.
#
# To install NVIDIA Container Toolkit on the host:
#   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
#
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Prevent .pyc files and ensure real-time terminal logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Avoid interactive prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.10 + system dependencies (Tesseract OCR, PDF tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3-pip \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Make 'python' and 'pip' point to python3.10
RUN ln -sf /usr/bin/python3.10 /usr/bin/python3 \
 && ln -sf /usr/bin/python3.10 /usr/bin/python \
 && ln -sf /usr/bin/pip3 /usr/bin/pip

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
