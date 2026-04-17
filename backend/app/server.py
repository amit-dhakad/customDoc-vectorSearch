from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
from app.api.session_endpoints import router as session_router
from app.api.metrics_endpoints import router as metrics_router
from app.settings import settings
from typing import Dict, List
import logging
import time
import sys
import json
import traceback

"""
backend/app/server.py — FastAPI Gateway & Orchestrator

ARCHITECTURE OVERVIEW
─────────────────────────────────────────────────────────────────────────────
This module serves as the system's "API Gateway". It acts as the central router 
that accepts incoming traffic from the React frontend, validates permissions via 
CORS, and delegates the workload to specialized domain routers (like `endpoints.py`).

THE WEBSOCKET PUSH ARCHITECTURE
─────────────────────────────────────────────────────────────────────────────
One of the most complex features of this backend is the `ConnectionManager`. 
Because ML extraction tasks (OCR, layout parsing) are extremely slow and CPU-bound, 
a "Polling" architecture (where the frontend asks "Are you done yet?") would 
cause massive DDOS spikes on the server.

Instead, we use a Push architecture via WebSockets:
  1. Frontend opens a persistent WebSocket connection `/ws/logs/client-123`.
  2. The ML service does the heavy lifting, posting progress via an internal route.
  3. The `ConnectionManager` instantly broadcasts this message over the socket 
     down to the correct browser instance.
"""

# Setup structured logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("backend")

# Initialize FastAPI with project metadata from settings
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Standard CORS configuration:
# Allows the frontend (or other services) to communicate with this API 
# from different domains. 'allow_origins=["*"]' is used here for development 
# flexibility but should be restricted in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MIDDLEWARE: GLOBAL ERROR HANDLER ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Prevents leaking internal stack traces to the user while ensuring we log 
    the full error for developers.
    """
    error_id = f"{int(time.time())}"
    logger.error(f"[ERROR {error_id}] Global failure on {request.url}: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal system error occurred. Our engineers have been notified.",
            "error_id": error_id,
            "error_type": type(exc).__name__
        }
    )

# ── MIDDLEWARE: REQUEST OBSERVARBILITY ───────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Logs every incoming HTTP request, its latency, and response status.
    Crucial for identifying bottlenecks and production debugging.
    """
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Duration: {duration:.4f}s"
    )
    return response

# Include modularized routers. 
# This promotes a clean directory structure by separating endpoints by domain.
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(session_router, prefix=settings.API_V1_STR, tags=["Sessions"])
app.include_router(metrics_router, prefix=settings.API_V1_STR, tags=["Metrics"])

# WebSocket Manager for real-time log streaming
class ConnectionManager:
    """
    Manages active WebSocket connections grouped by 'client_id'.
    Allows the server to push real-time parsing logs to specific frontend clients.
    """
    def __init__(self):
        # Maps client_id to a list of active WebSocket instances
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """Accepts a new connection and registers it with the client_id."""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    def disconnect(self, client_id: str, websocket: WebSocket):
        """Cleans up the connection on disconnect to prevent memory leaks."""
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str):
        """Broadcasts a message to all active tabs/windows for a specific client_id."""
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_text(message)

# Global instance of the manager
manager = ConnectionManager()

@app.websocket("/ws/logs/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket route that allows frontend clients to subscribe to parsing logs.
    Identified by a unique client_id to ensure logs reach the correct user.
    """
    await manager.connect(client_id, websocket)
    try:
        while True:
            # Keep the connection alive by waiting for data (heartbeat pattern)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        # Handle graceful cleanup when browser tab is closed
        manager.disconnect(client_id, websocket)

# Attach the manager to app.state so it's accessible within path operations (route functions)
app.state.ws_manager = manager

@app.get("/")
async def root():
    """Health check endpoint to verify backend status."""
    return {"message": "Welcome to CustomDoc VectorSearch Backend API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting backend server...")
    # Entry point for running the app directly via 'python server.py'
    uvicorn.run(app, host="0.0.0.0", port=8000)
