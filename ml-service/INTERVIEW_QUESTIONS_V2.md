# RAG System Architecture & Interview Preparation (V2)

This document is a centralized knowledge base for the **CustomDoc VectorSearch** architecture. It covers Document Parsing (ML Service), API Gateway (FastAPI), Database Design (SQLAlchemy), and Extreme Scalability.

---

## Part 1: Document Parsing & Extraction (ML Service)

### 1. Parsing Libraries & Engines

#### Q1: Why not just use one PDF library?
- **Answer**: No single library is perfect.
- **`fitz` (PyMuPDF)**: Extremely fast (C-based) and handles simple files brilliantly.
- **`pdfplumber`**: Excels at visual fidelity—preserving margins, spacing, and tables that `fitz` might scramble.
- **Design Pattern**: We use a **Factory Pattern** (`get_parser_by_extension`) to decide which engine to use at runtime. This gives the *caller* the power to choose `fitz` for speed or `pdfplumber` for structured accuracy.

#### Q2: What is the difference between "Text Layer Extraction" and "OCR"?
- **Answer**:
    - **Text Layer**: Most PDFs (born-digital) have a hidden layer of Unicode characters mapped to glyph positions. Libraries like `fitz` or `pdfplumber` read this layer directly without "seeing" the page.
    - **OCR**: Used for scanned documents where no text layer exists. We must render the page as an image (bitmap) and use a neural network (Tesseract) to recognize character shapes.
- **Trade-off**: OCR is 10-50x slower and requires more hardware resources.

#### Q3: How do we handle "Mixed" Documents (Some pages scanned, some digital)?
- **Answer**: Our `PDFParser` uses an **Automatic Fallback** mechanism. It first attempts to extract the text layer. If a page returns an empty string, it assumes the page is an image and triggers the OCR engine (`pytesseract`) specifically for that page. This saves time on pages that don't need OCR.

#### Q4: How do we handle Tables in documents?
- **Answer**: 
    - In **Word (Docx)**, we iterate through the XML table structure and join cells with a pipe (`|`) to maintain the grid relationship.
    - In **PDF**, we use `pdfplumber` which is specialized in "table discovery." It identifies lines and gutters to reconstruct the columns and rows as clear text blocks.
- **Why it matters**: Simply extracting raw text from a table usually scrambles the columns, making the data unusable for an LLM (RAG).
- **Backend/ML Research Note**: Table extraction is critical because tabular data often contains precise key-value mappings. Advanced parsing might even export to Markdown or JSON to retain schema prior to vectorization.

#### Q5: Why do we use a "Fallback Chain" for plain-text files?
- **Answer**: Text files (`.txt`, `.csv`) don't have a header that declares their encoding. We try **`utf-8-sig`** first (to catch Windows BOM marks), then fallback to **`latin-1`**. 
- **Interview Detail**: `latin-1` is important because it can decode any sequence of bytes without throwing an error, acting as a "safe" final fallback for corrupted or legacy files.

### 2. RAG Specifics (The "Advanced" Layer)

#### Q6: How does the choice of parser impact the RAG system's accuracy?
- **Answer**: If a parser returns "noisy" text (e.g., footers, page numbers, or scrambled tables), the **Embeddings Model** will create a poor vector representation of that chunk. Clean text extraction from `fitz` or `pdfplumber` leads to higher quality retrieval and fewer LLM hallucinations.

#### Q7: What is the next logical step after this parsing service?
- **Answer**: **Semantic Chunking**. Once we have the text, we need to split it into chunks that preserve meaning (e.g., not cutting a sentence in half). We would typically use a `RecursiveCharacterTextSplitter` from LangChain to break the text down into 500-1000 character pieces for the vector database.

---

## Part 2: Backend Orchestration & API Design

### 3. FastAPI & Gateway Logic

#### Q8: Why use FastAPI over Flask or Django for this use-case?
- **Answer**: 
    1. **Asynchrony**: FastAPI handles concurrent I/O (like file uploads and Microservice calls) naturally without blocking threads, using `async def`.
    2. **Auto-Swagger**: It generates OpenAPI docs instantly, acting as a contract for frontend teams.
    3. **Pydantic Validation**: It validates incoming files and parameters automatically at the edge of the system.

#### Q9: How is the project organized for growth?
- **Answer**: We use **Modular Routing** with `APIRouter`. This decouples endpoints by domain (e.g., Sessions and Documents vs. Progress Logs).
- **Middleware**: We use `CORSMiddleware` in `server.py` to securely allow the frontend (acting on a different domain/port) to communicate with the API.

#### Q10: How do we handle file security during the /parse request?
- **Answer**: We use **FastAPI's UploadFile** which is a "Spool" file implementation—it keeps small files in memory and only writes large files to a temporary disk location. After parsing, we use a `finally` block to ensure the temporary file is deleted, preventing disk-bloat or data leakage.

#### Q11: How did you implement real-time "Parsing Logs"?
- **Answer**: Using **WebSockets** and a `ConnectionManager`.
    - **Step-by-Step**: Frontend opens a WS connection with a `client_id`. During parsing, the ML Service reports progress to the Backend via an internal REST route. The Backend then "pushes" that log message to the specific frontend client via the active WebSocket.
- **System Design Benefit**: This is a **Push-based Architecture**. It avoids the network overhead and scaling issues of long "Polling".

### 4. Data Validation (Pydantic / DTOs)

#### Q12: Why separate "Schemas" (Pydantic) from "Models" (SQLAlchemy)?
- **Answer**:
    - **Privacy & Security**: ORM models contain database internals (IDs, hashes, structural metadata). Schemas act as a filter to ensure only "safe" business data is returned to the client.
    - **Validation**: Pydantic validates input types (e.g. required string length) before the request ever hits our business or database logic.
    - **Contract-First**: Defining schemas allows frontend and backend teams to start work simultaneously.

#### Q13: What does `from_attributes = True` do?
- **Answer**: It allows Pydantic to "read" data directly from class instances (SQLAlchemy objects) instead of just raw dictionaries, ensuring that DB models can be serialized to JSON effortlessly.

---

## Part 3: Data Persistence & Architecture Layering

### 5. Database Design

#### Q14: What is the "Session-per-Request" pattern?
- **Answer**: We use the `yield` pattern in our `get_db` FastAPI dependency. This ensures every HTTP request receives its own isolated DB transaction space.
- **Guarantee**: The `finally: db.close()` block ensures that under any failure, connections are returned to the pool, preventing **Connection Leakage** which would exhaust database limits.

#### Q15: `Engine` vs. `Session` vs. `Base`?
- **Answer**:
    - **Engine**: The connection pool and dialect handler (global lifecycle).
    - **Session**: The "workspace" or transaction handle (per-request lifecycle).
    - **Base**: The source of truth registry for all table and ORM model mapping metadata.

### 6. Containerization & Deployment

#### Q16: Why Dockerize this service instead of just running it locally?
- **Answer**: Real-world machine learning services have complex system dependencies that Python package managers cannot handle alone like **`tesseract-ocr`** (C++ binary) and **`poppler-utils`** (Linux libraries). 
- **Docker** guarantees that the exact OS-level versions of these binaries exist in the production container environment, entirely eliminating "it works on my machine" deployment bugs.

---

## Part 4: Extreme Scalability — 100M Simultaneous Users

Scaling a RAG system to 100 million simultaneous users (100M CCU) is a Tier-1 system design challenge. Below is the architectural blueprint for that scale.

### 1. Architectural Transformation: From Sync to Async
At 100M users, a single document parsing request cannot block an API worker.
- **The Problem**: Synchronous HTTP calls (our current `/parse` flow) will time out and crash the server under heavy load.
- **The Solution**: **Message Queues (Kafka / Redis / RabbitMQ)**.
- **Flow**: User uploads → Backend puts job in Queue (returns `202 Accepted`) → ML Workers pull from Queue at their own pace → Results stored in DB → Notification pushed via WebSockets to client.

### 2. Global Traffic Management
- **Anycast DNS + Global Load Balancing (GSLB)**: Route users to the nearest regional data center.
- **CDN (Cloudflare/Akamai)**: Serve the React SPA frontend completely from edge nodes (zero load on our origin servers).

### 3. Scaling the ML Service (The Bottleneck)
OCR and Embedding generation are heavily compute-bound.
- **Horizontal Scaling**: Use **Kubernetes (K8s) Clusters** with **HPA (Horizontal Pod Autoscaler)** scaling pods automatically based on CPU limits.
- **GPU Acceleration**: CPU-based OCR (Tesseract) is far too slow for 100M CCU. Switch to GPU-optimized models (e.g., EasyOCR or PyTorch Vision) running on NVIDIA Tensor-core instances.

### 4. Designing the Vector DB for Scale
100M concurrent users signifies billions of searchable document chunks.
- **Distributed Vector DB**: Use Qdrant or Milvus in **Distributed Mode** (Collection Sharding). Parition vectors across 100+ nodes using consistent hashing.
- **Indexing Strategy**: Ensure indexing uses **HNSW (Hierarchical Navigable Small World)** with optimized `M` bounds to balance sub-millisecond search speed and active memory usage.

### 5. Data Persistence & Caching
- **Database Sharding**: A standard single PostgreSQL instance will fail. Shard by `user_id` or use a distributed relational DB like **CockroachDB**, **Google Spanner**, or **Cassandra**.
- **The 80/20 Rule (Caching)**: Use **Redis Clusters** in front of the DB to cache frequently queried documents and session data (since 80% of users usually query the top 20% of system documents).
- **Read Replicas**: Distribute the massive READ volume via a Leader/Follower replica pattern for SQL queries.

### 6. Resilience & Reliability
- **Circuit Breakers**: If the ML cluster is overwhelmed, the API Gateway immediately trips the circuit to return 503s instead of cascading failure across the system.
- **Rate Limiting**: Implement strict "Fair Usage" per user via distributed Slide Window algorithms (Redis) to stop localized DDOS attempts.

---

> [!TIP]
> **Interviewer Hook**: "Designing for 1 user is easy. Designing for 100 million is a test of your understanding of distributed state, load shedding, and resource management."


---
