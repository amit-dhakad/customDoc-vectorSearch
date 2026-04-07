# 📄 CustomDoc VectorSearch: RAG System

This is a **Retrieval-Augmented Generation (RAG)** system designed to ingest, index, and query documents using vector embeddings.

## 🚀 Quick Start (Docker)

To run the entire stack (Backend API, ML Service, and Vector Database), use the following command:

```bash
# Build and start the containers
docker-compose up --build
```

### Access Points
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ML Service**: [http://localhost:8000/api/v1/parse](http://localhost:8000/api/v1/parse)

---

## 🏗️ Architecture

The system follows a microservices-like architecture:

1.  **Backend API (`/api/v1`)**
    -   Handles HTTP requests from the frontend.
    -   Orchestrates the RAG pipeline.
    -   **Tech**: FastAPI, Uvicorn.

2.  **ML Service (`/ml-service`)**
    -   Handles heavy lifting: Document Parsing and Embedding Generation.
    -   **Tech**: FastAPI, PyMuPDF, Pytesseract (OCR), Sentence Transformers.

3.  **Vector Database (`/vector-db`)**
    -   Stores and searches document embeddings.
    -   **Tech**: Qdrant (Vector DB).

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **API** | FastAPI | High-performance Python web framework. |
| **Parsing** | PyMuPDF (fitz), pdfplumber | Extract text and tables from PDFs. |
| **OCR** | Pytesseract | Optical Character Recognition for scanned documents. |
| **Embeddings** | Sentence Transformers | Convert text to dense vectors. |
| **Vector DB** | Qdrant | Vector similarity search. |
| **Containerization** | Docker, Docker Compose | Package and run services. |

---

## 📂 Project Structure

```
customDoc-vectorSearch/
├── backend/              # FastAPI Application
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints.py  # API Endpoints
│   │   │   └── routes.py     # Route registration
│   │   ├── core/           # Core logic
│   │   │   ├── config.py     # Configuration
│   │   │   └── rag_pipeline.py # RAG Orchestration
│   │   └── server.py       # Application entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── ml-service/           # ML Service
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── parsers/      # PDF, Docx, Txt parsers
│   │   └── server.py       # ML Service entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── vector-db/            # Qdrant Service
│   ├── docker-compose.yml  # Qdrant configuration
│   └── Dockerfile
│
└── docker-compose.yml    # Main orchestration file
```

---

## 🔌 API Endpoints

### Parse Document
Upload a document to be parsed and embedded.

**Endpoint**: `POST /api/v1/parse`

**Parameters**:
- `file`: Uploaded document (PDF, DOCX, TXT).
- `engine` (optional): `fitz` or `pdfplumber`.
- `use_ocr` (optional): `true` or `false`.

**Response**:
```json
{
  "status": "success",
  "message": "Document parsed successfully",
  "data": {
    "file_name": "example.pdf",
    "total_pages": 3,
    "parsed_pages": 3,
    "chunks_created": 5
  }
}
```

---

## ⚙️ Configuration

Environment variables are managed in `docker-compose.yml` and `.env` files.

Key variables:
- `ML_SERVICE_URL`: URL of the ML Service.
- `QDRANT_URL`: URL of the Vector Database.
- `QDRANT_API_KEY`: API key for Qdrant.
- `COLLECTION_NAME`: Name of the Qdrant collection.

---

## 🚀 Running Locally (Without Docker)

If you prefer to run services individually:

### 1. ML Service
```bash
cd ml-service
pip install -r requirements.txt
uvicorn app.server:app --reload
```

### 2. Backend API
```bash
cd backend
pip install -r requirements.txt
uvicorn app.server:app --reload
```

### 3. Vector Database
Install Qdrant locally or use the Docker container:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

---

## 🧪 Testing

Use the `/docs` endpoint to test the API:
1.  Go to [http://localhost:8000/docs](http://localhost:8000/docs).
2.  Click on `POST /api/v1/parse`.
3.  Click "Try it out".
4.  Select a document and click "Execute".

---

## 🤝 Contributing

1.  **Parse**: Upload a document via the API.
2.  **Embed**: The ML Service converts text to vectors.
3.  **Store**: Vectors are saved in Qdrant.
4.  **Retrieve**: Search for similar vectors when querying.

---

## 🧠 Interview Prep & Architecture Deep Dive

For a detailed breakdown of the document parsing architecture, OCR strategies, and technical interview questions related to this project, check out:
👉 **[Interview Questions & Architecture Deep Dive](ml-service/INTERVIEW_QUESTIONS_V2.md)**

---


## 📝 License

MIT License
