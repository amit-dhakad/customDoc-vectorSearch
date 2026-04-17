# CustomDoc: Master Technical Architecture & System Design

## 1. Executive Summary
**CustomDoc** is a comprehensive, local-first Retrieval-Augmented Generation (RAG) platform designed for high-precision document intelligence. Unlike generic wrappers, it implements a decoupled microservice architecture with specialized engines for OCR, semantic segmentation, and high-dimensional vector search.

The system is engineered for **Data Sovereignty**, ensuring that every byte of text, metadata, and high-density vector stays within the host infrastructure, utilizing local LLMs (via Ollama) for final inference.

---

## 2. Distributed System Design
The platform is split into two primary backend services to isolate the I/O-heavy orchestration from the compute-heavy machine learning workloads.

### 2.1 Component Stack
![RAG Pipeline Architecture](./frontend/public/rag_pipeline_architecture.png)

- **Frontend**: React 18 + Vite (Glassmorphism UI, Framer Motion, Lucide Icons).
- **Backend Orchestrator**: FastAPI (Python 3.10) + SQLAlchemy + SQLite.
- **ML Intelligence Service**: FastAPI + PyTorch + SentenceTransformers + Rank-BM25.
- **Reranker Engine**: Cross-Encoders (ms-marco-MiniLM-L-6-v2).
- **LLM Engine**: Ollama (Running on host, proxied via Backend).
- **Evaluation Engine**: RAGAS (Integrated into RAG Service).
- **Infrastructure**: Docker Compose with Healthcheck awareness.

### 2.2 System Modules

#### Backend Orchestrator (FastAPI)
- **Role**: State management, session tracking, and RAG orchestration.
- **Database**: SQLite (SQLAlchemy) for relational metadata (Sessions, Messages, Documents, Chunks).
- **Communication**: Bridges requests between the UI and the ML-Service; Proxies LLM requests to the host's Ollama instance.
- **RAG Logic**: Handles query expansion, Top-K retrieval merging, and context-aware prompt construction.

#### ML Intelligence Service (FastAPI + PyTorch)
- **Role**: Heavy-lifting service for parsing, OCR, and embedding generation.
- **Compute**: Native CUDA integration for GPU acceleration; Fallback to MPS (Apple Silicon) or CPU.
- **Persistence**: Manages local ChromaDB instances for session-isolated vector storage.
- **The Bridge**: Implements a real-time progress reporting system that pipes logs back to the UI via the Backend.

---

## 3. High-Fidelity Extraction Pipeline
The ingestion tier transforms raw binaries into structured "Intelligence Fragments" via a 5-step wizard or an auto-chunking background task.

### 3.1 Advanced Parsing Engines
| Engine | Technology | Best For |
|---|---|---|
| **Fitz (MuPDF)** | C++ bindings | Ultra-fast digital-born PDFs with complex layouts. |
| **pdfplumber** | Geometry-based | Complex table extraction and multi-column document trees. |
| **OCR (Tesseract 5)** | LSTM-based vision | Scanned docs, handwriting, and low-contrast images. |
| **Python-Docx** | XML traversal | Native Microsoft Word structure preservation. |

### 3.2 The Logging Bridge
To prevent UI "blackouts" during long OCR tasks, each parser reports its status (e.g., `Page 5/10: OCR in progress`) to a thread-safe singleton. This status is then broadcast via **WebSockets** to the frontend, providing a live "Neural Indexing Stream."

---

## 4. Semantic Intelligence Layer
Raw text is meaningless to an LLM without structure. **CustomDoc** implements several advanced segmentation strategies.

### 4.1 Chunking Strategies
- **Recursive Character**: The industry standard. Splits by paragraph, then sentence, then word, ensuring semantic boundaries are respected within a target token window.
- **Semantic Segmentation**: (Optional) Uses local embeddings to find natural "meaning breaks" in the document, creating chunks based on conceptual shifts rather than character counts.
- **Structural Awareness**: In Advanced mode, the system preserves parent-child relationships (e.g., keeping a sub-header linked to its body text).

### 4.2 Multi-Stage Retrieval Pipeline
CustomDoc moves beyond simple Top-K retrieval by implementing a verified multi-stage pipeline:

1.  **Stage 1: Sparse Retrieval (BM25)**: Index-based keyword search to find exact term matches and technical jargon.
2.  **Stage 2: Dense Retrieval (Vector)**: Neural search using `all-MiniLM-L6-v2` to capture semantic intent.
3.  **Stage 3: Hybrid Fusion (RRF)**: We use **Reciprocal Rank Fusion** to merge sparse and dense results without requiring score normalization.
4.  **Stage 4: Neural Reranking (Cross-Encoder)**: The top fused results are passed to a `ms-marco-MiniLM-L-6-v2` Cross-Encoder. This re-scores query-chunk pairs based on deep attention, significantly boosting precision and filtering out "semantic noise."

### 4.3 Automated Evaluation (RAGAS)
Every interaction is scientifically scored using the **RAGAS** framework:
- **Faithfulness**: LLM-based Judge verifies if the answer claims are grounded in the retrieved chunks.
- **Answer Relevancy**: Measures the semantic alignment between the user query and the answer.
- **Context Precision/Recall**: Evaluates the signal quality of the retrieved context.

---

## 5. RAG Orchestration & LLM Integration
When a user asks a question, the **RAG Controller** follows this precise execution path:

1. **Embedding**: The user's query is converted into a vector in the `ml-service`.
2. **Context Retrieval**: The Top-K most relevant chunks (default 4) are retrieved from ChromaDB.
3. **Neighbor Expansion**: (Advanced) Optionally retrieves surrounding chunks of the top results to provide broader context.
4. **Prompt Construction**:
   ```text
   Context: [Chunk 1] ... [Chunk N]
   Question: [User Query]
   Constraint: Answer based ONLY on the context provided.
   ```
5. **Inference**: The prompt is sent to the local **Ollama** instance via the Backend proxy.

---

## 6. Hardware Acceleration & Optimization
The system is built to utilize every ounce of local hardware.

- **GPU Passthrough**: The Docker architecture utilizes the `nvidia-container-runtime`. The `ml-service` container detects and initializes CUDA devices automatically.
- **Parallel Workers**: FastAPI's `anyio` backend handles concurrent uploads, while the ML-Service uses a serialized queue for GPU-heavy tasks to prevent VRAM overflow.
- **Memory Management**: ChromaDB instances are session-bound and lazily loaded, ensuring that RAM is only consumed for active conversation contexts.

---

## 7. Operational Observability
The system implements Enterprise-Grade telemetry for real-time performance monitoring.

- **Latency Tracking**: Every RAG cycle logs `retrieval_latency`, `generation_latency`, and `total_time`.
- **Quality Trending**: Scores from the RAGAS engine are persisted to SQLite and visualized in the Performance Dashboard via daily aggregations.
- **Structured Logging**: Unified logging format (`Timestamp | Level | Component | Message`) across all services for rapid debugging.

---


## 8. Frontend Design System
The UI is a custom-built **Glassmorphism Design System** focusing on depth and motion.

- **Theme Engine**: Dual-mode HSL tokens (`Amber/Blue` or `Indigo/Emerald` variations).
- **Framer Motion**: State transitions for the "Thinking Bubble" and extraction wizard.
- **Lucide Integration**: Contextual iconography for file types and device status indicators.
