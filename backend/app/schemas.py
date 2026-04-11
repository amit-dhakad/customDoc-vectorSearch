from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

"""
backend/app/schemas.py — Pydantic Data Transfer Objects (DTO)

THE BOUNDARY LAYER DESIGN PATTERN
─────────────────────────────────────────────────────────────────────────────
We strictly separate our `Models` (database schema) from our `Schemas` (API payloads).
Why not just pass SQLAlchemy models directly to the frontend? 
Because that violates the principle of encapsulation and can leak sensitive 
database internals (like password hashes or hidden IDs) directly to the browser.

HOW PYDANTIC WORKS
─────────────────────────────────────────────────────────────────────────────
Pydantic is the enforcement engine. When the frontend sends a JSON payload:
  1. Pydantic instantly checks if `session_id` is a string and `id` is an int.
  2. If the data is dirty or missing, it aborts the request with a detailed 422 
     Error before our core logic ever runs. 

Using `from_attributes = True` inside the nested `Config` classes instructs 
Pydantic that it is allowed to construct itself using complex Objects rather 
than simple dictionaries, easing the serialization process.
"""

# --- Document Schemas ---

class DocumentBase(BaseModel):
    """Core document attributes shared across creation and responses."""
    filename: str
    file_type: Optional[str] = None

class DocumentCreate(DocumentBase):
    """Schema for creating a new document entry."""
    session_id: str

class Document(DocumentBase):
    """Schema for document data returned by the API."""
    id: int
    session_id: str
    created_at: datetime

    class Config:
        # from_attributes=True (formerly orm_mode) allows Pydantic to read data 
        # directly from SQLAlchemy model instances (objects) even if they aren't dicts.
        from_attributes = True

# --- Message Schemas ---

class MessageBase(BaseModel):
    """Core message content attributes."""
    role: str
    content: str

class MessageCreate(MessageBase):
    """Used for sending new messages from the client."""
    pass

class Message(MessageBase):
    """Serialized message with unique identifier and server-side timestamp."""
    id: int
    session_id: str
    timestamp: datetime

    class Config:
        from_attributes = True

# --- Session Schemas ---

class SessionBase(BaseModel):
    """Core session meta-data."""
    id: str
    title: Optional[str] = "New Chat"

class SessionCreate(SessionBase):
    """Used to initialize a new conversation session."""
    pass

class Session(SessionBase):
    """Comprehensive session view including nested messages and documents."""
    created_at: datetime
    messages: List[Message] = []
    documents: List[Document] = []

    class Config:
        from_attributes = True

# --- Feedback Schemas ---

class FeedbackCreate(BaseModel):
    """Client input for submitting message reactions."""
    message_id: int
    is_positive: bool
    comment: Optional[str] = None

class Feedback(FeedbackCreate):
    """Full feedback record including system timestamp."""
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
