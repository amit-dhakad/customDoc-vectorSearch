# ── Backend Service Docker Image ──────────────────────────────────────────

# Use a Python 3.10-slim base image
FROM python:3.10-slim

# Prevent writing .pyc files and ensure real-time terminal logging
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Standard build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Establish the working directory
WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy our full service code
COPY . .

# Launch the FastAPI app with uvicorn
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
