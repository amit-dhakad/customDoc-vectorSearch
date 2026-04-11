# 📄 CustomDoc VectorSearch: RAG System

This is a **Retrieval-Augmented Generation (RAG)** system designed to ingest, index, and query documents using vector embeddings. It features a complete stack including a modern React frontend, a FastAPI backend gateway, and a specialized ML service for document processing.

## 🚀 Quick Start (Docker)

To run the entire stack (Frontend, Backend API, and ML Service), use the following command:

```bash
# Build and start the containers
docker-compose up --build
```

### Access Points
- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ML Service API API**: [http://localhost:8001/docs](http://localhost:8001/docs)

---

## 🏗️ Architecture

The system follows a microservices architecture:

1.  **Frontend (`/frontend`)**
    -   Interactive UI for document upload, parsing visualization, and RAG chat.
    -   **Tech**: React, Vite, TailwindCSS (for styling), Axios.

2.  **Backend API (`/backend`)**
    -   Acts as an API Gateway and orchestrates the RAG pipeline.
    -   Manages chat sessions and file storage.
    -   **Tech**: FastAPI, Uvicorn, Pydantic.

3.  **ML Service (`/ml-service`)**
    -   Handles heavy lifting: Document Parsing (PDF, DOCX, TXT) and Embedding Generation.
    -   Supports OCR for scanned documents.
    -   **Tech**: FastAPI, PyMuPDF, Pytesseract (OCR), Sentence Transformers.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React + Vite | Modern, fast reactive user interface. |
| **Backend API** | FastAPI | High-performance Python web framework. |
| **Parsing** | PyMuPDF (fitz) | High-speed PDF text extraction. |
| **OCR** | Pytesseract | OCR for scanned/image-based documents. |
| **Embeddings** | Sentence Transformers | Convert text to dense vectors. |
| **Containerization** | Docker, Docker Compose | Package and run services. |

---

## 📂 Project Structure

```
customDoc-vectorSearch/
├── frontend/             # React Application
│   ├── src/
│   │   ├── components/   # UI Components (ChatWindow, AdvancedParsing, etc.)
│   │   ├── api.js        # Backend API service
│   │   └── App.jsx       # Main Application entry
│   ├── Dockerfile
│   └── package.json
│
├── backend/              # FastAPI Application (Gateway)
│   ├── app/
│   │   ├── api/          # Endpoints (Sessions, Messages, Parsing)
│   │   ├── data/         # File storage
│   │   ├── server.py     # Application entry point
│   │   └── settings.py   # Configuration
│   ├── requirements.txt
│   └── Dockerfile
│
├── ml-service/           # Specialized ML Parsing Service
│   ├── app/
│   │   ├── core/
│   │   │   └── parsers/  # PDF, Docx, Txt parsers
│   │   └── server.py     # ML Service entry point
│   ├── requirements.txt
│   └── Dockerfile
│
└── docker-compose.yml    # Main orchestration file
```

---

## 🚀 Running Locally (Without Docker)

If you prefer to run services individually:

### 1. ML Service
```bash
cd ml-service
pip install -r requirements.txt
uvicorn app.server:app --port 8001 --reload
```

### 2. Backend API
```bash
cd backend
pip install -r requirements.txt
uvicorn app.server:app --port 8000 --reload
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing

1.  Open the **Frontend** at [http://localhost:3000](http://localhost:3000).
2.  Use the **Advanced UI** to upload a document.
3.  Select a parsing engine (e.g., `fitz`) and click **Parse Document**.
4.  Monitor the logs in the side panel to see real-time processing.
5.  Once parsed, use the **Chat Interface** to ask questions about your document.

---

## 🧠 Interview Prep & Architecture Deep Dive

For a detailed breakdown of the document parsing architecture, OCR strategies, and technical interview questions related to this project, check out:
👉 **[Interview Questions & Architecture Deep Dive](ml-service/INTERVIEW_QUESTIONS_V2.md)**

---

## 📝 License

MIT License
