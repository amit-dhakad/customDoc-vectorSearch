# 📐 RAG System Design Patterns & Architectural Notes
## How CustomDoc Solves Complex AI Engineering Challenges

This document outlines the core **Design Patterns** and **Architectural Decisions** implemented in CustomDoc. Understanding these patterns is key to scaling and maintaining production-grade RAG systems.

---

## 🏗️ 1. The Orchestrator Pattern (Core Backend)
**Problem**: Managing LLM logic, session state, and heavy ML tasks in one process causes blocking issues and scaling bottlenecks.
**Pattern**: We use a **Centralized Orchestrator** (FastAPI Backend) that acts as the "Brain."
- It manages the **Contextual State** (SQLite).
- It delegating compute-heavy tasks (OCR, Embeddings) to a secondary service.
- **Benefit**: The UI stays responsive even when the GPU is busy, as the Orchestrator handles requests asynchronously.

---

## 🤖 2. The Worker-Delegate Pattern (ML Intelligence)
**Problem**: Hardware-intensive tasks (GPU inference) can crash the main API or cause VRAM fragmentation if not handled carefully.
**Pattern**: The **ML-Service** acts as a specialized **Worker-Delegate**.
- It encapsulates all PyTorch/CUDA dependencies.
- It exposes a clean REST interface to the Orchestrator.
- **Benefit**: You can scale the ML Worker independently (e.g., move it to a GPU-rich node) without touching the user-facing API.

---

## 📡 3. The Push-based Observer Pattern (Live Logs)
**Problem**: Document parsing (OCR/Layout) takes minutes. Client-side polling ("Is it done?") adds massive overhead and feels slow.
**Pattern**: We implement a **WebSocket-based Observer Pattern**.
- The ML Service "publishes" progress updates.
- The Backend "observes" and broadcasts these via WebSockets (`ConnectionManager`).
- **Benefit**: Real-time feedback for the user with zero polling overhead.

---

## 🔍 4. The Multi-Stage Retrieval Strategy Pattern
**Problem**: Vector search (Dense) misses exact keywords, while Keyword search (Sparse) misses semantic intent.
**Pattern**: A **Hybrid Strategy** with **Reciprocal Rank Fusion (RRF)**.
- **Stage 1**: Parallel execution of BM25 and Dense Search.
- **Stage 2**: Fusion of results using RRF math ($score = \sum \frac{1}{k + rank}$).
- **Stage 3**: **Neural Reranking** (Cross-Encoder) for the final "sanity check."
- **Benefit**: Maximally accurate context retrieval for complex technical queries.

---

## 🛡️ 5. The Sidecar/Service-Mesh Pattern (Ollama API)
**Problem**: Running an LLM directly inside a Python app consumes massive memory and is hard to update.
**Pattern**: **Ollama** runs as a **Local Sidecar service**.
- The Backend communicates with Ollama over a local network.
- **Benefit**: The LLM lifecycle is managed independently. You can swap models or update the engine without restarting the application code.

---

## 🗄️ 6. The Multi-Tenant Isolation Pattern (Vector DB)
**Problem**: Storing all user data in one massive vector index causes "Context Poisoning" (the model sees other people's data).
**Pattern**: **Session-level Collection Isolation**.
- Every session in CustomDoc creates a unique **ChromaDB Collection**.
- **Benefit**: Guaranteed data privacy. Deleting a session physically purges the vector index for that specific user context.

---

## 🔄 7. The Lifecycle Hook Pattern (Docker Healthchecks)
**Problem**: Containers start simultaneously, but Vector DBs take time to initialize. The Backend usually crashes because it tries to connect to a DB that isn't ready.
**Pattern**: **Dependency-aware Healthchecks**.
- We use `depends_on: { condition: service_healthy }` in Docker Compose.
- The Backend waits for the `chromadb/heartbeat` signal before starting.
- **Benefit**: Robust "cold-starts" with zero manual intervention.

---

## 📝 8. The Singleton Pattern (Manager Objects)
**Problem**: Repeatedly initializing heavy objects (VectorManager, DB Engines) consumes CPU and memory.
**Pattern**: **Lazy-loaded Singletons**.
- We ensure only one instance of the `VectorManager` and `ConnectionManager` exists per process life-cycle.
- **Benefit**: Efficient resource utilization and centralized state management.

---

## 🌐 9. The API Gateway Pattern
**Problem**: The frontend shouldn't need to know the IP addresses of the ML Service, the DB, or Ollama.
**Pattern**: The Backend acts as a **Unified Gateway**.
- It provides a single entry point for all UI requests.
- It hides the complexity of the internal microservice network.
- **Benefit**: Secure, simplified frontend-backend communication.

---

## 📊 10. The Observability-as-State Pattern
**Problem**: Performance metrics (latency, quality) are usually lost in logs.
**Pattern**: **Metric Persistence**.
- Every interaction results in a telemetry payload that is saved directly into the **relational database**.
- **Benefit**: Allows for the creation of the **Performance Dashboard**, turning ephemeral logs into long-term strategic insights.
