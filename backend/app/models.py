from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

"""
backend/app/models.py — SQLAlchemy ORM Definitions

WHAT IS AN ORM?
─────────────────────────────────────────────────────────────────────────────
Object-Relational Mapping (ORM) translates Python classes directly into SQL 
tables and relationships. Instead of writing raw `CREATE TABLE` and `SELECT` 
statements, we simply instantiate Python objects like `Session(title="Chat")`.

THE DOMAIN SCHEMA
─────────────────────────────────────────────────────────────────────────────
We are modeling a hierarchical RAG (Retrieval-Augmented Generation) chat system:
  • `Session` (The Parent Container)
      → has many `Message`s (Conversation history)
      → has many `Document`s (Uploaded context files)
      
By defining `cascade="all, delete-orphan"` on the `Session`, we enforce 
Referential Integrity. If a user deletes a Chat Session from the UI, the 
database automatically sweeps and deletes all 50 messages and 10 documents 
attached to it, preventing orphan rows from bloating the database.
"""

class Session(Base):
    """
    Represents a logical conversation thread or project.
    
    Attributes:
        id (str): Unique identifier (client-generated or random string).
        title (str): Display name for the session.
        created_at (datetime): Timestamp of session initialization.
        messages (list): Relationship to all messages in this session.
        documents (list): Relationship to all documents attached to this session.
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # cascade="all, delete-orphan" ensures that if a Session is deleted, 
    # all its associated messages and documents are also purged.
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")

class Document(Base):
    """
    RAG Metadata Repository: The Source Document Model.
    
    PURPOSE:
    ─────────────────────────────────────────────
    This model acts as the relational 'Master Record' for every uploaded file.
    While the high-dimensional vectors are stored in ChromaDB, the critical 
    file metadata and ownership reside here in the SQL layer.

    WHY DUAL PERSISTENCE?
    ─────────────────────────────────────────────
    1. RELATIONAL INTEGRITY: We use SQLite to maintain strict relationships 
       between Users, Sessions, and Documents using Foreign Keys.
    2. SCALABILITY: We offload the heavy text fragments to the 'chunks' table, 
       allowing the master Document table to remain lightweight and searchable.
    3. RECOVERY: Storing the raw chunk text in SQL acts as a backup and 
       allows for audit-logging and UI previews without hitting the Vector DB.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    filename = Column(String)
    file_type = Column(String, nullable=True)
    raw_content = Column(Text, nullable=True) # Persistent storage for extracted data
    created_at = Column(DateTime, default=datetime.utcnow)

    # back_populates links this to the 'documents' list in the Session model.
    session = relationship("Session", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    """
    The Intelligence Fragment: Relational Text Segmentation.
    
    WHAT THIS IS:
    ─────────────────────────────────────────────
    A 'Chunk' is a semantically meaningful slice of a document. If a PDF is a 
    book, a Chunk is a logical page or paragraph.

    HOW IT WORKS:
    ─────────────────────────────────────────────
    1. SEGMENTATION: Generated during the Intelligence Pipeline (Step 3/4).
    2. INDEXING: Every row here has a corresponding 384-dimensional vector in 
       ChromaDB.
    3. RETRIEVAL: During a chat, we search ChromaDB for the best vectors, then 
       map them back to these SQL records to serve the text to the LLM.

    WHY THIS MODEL IS BEST:
    ─────────────────────────────────────────────
    - SEQUENTIAL AWARENESS: The 'index' column allows us to retrieve 'neighbor' 
      chunks (surrounding context), which is a key advanced RAG technique.
    - PERFORMANCE: Indexed ForeignKey lookups ensure that even with millions 
      of chunks, metadata retrieval remains O(log n).
    """
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    content = Column(Text)
    index = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")

class Message(Base):
    """
    Individual chat interactions between the user and the assistant.
    
    Attributes:
        role (str): Identifies the sender ('user' or 'assistant').
        content (text): The raw text of the message (supports markdown).
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Performance & Evaluation Metrics
    total_latency_ms = Column(Integer, nullable=True)     # Overall request time
    retrieval_latency_ms = Column(Integer, nullable=True) # Time spent in Vector Search
    generation_latency_ms = Column(Integer, nullable=True)# Time spent in LLM Inference
    prompt_tokens = Column(Integer, nullable=True)        # Input tokens (if provided by LLM)
    completion_tokens = Column(Integer, nullable=True)    # Output tokens (if provided by LLM)
    
    # RAGAS Quality Scores (0.0 - 1.0)
    faithfulness = Column(Float, nullable=True)
    answer_relevancy = Column(Float, nullable=True)
    context_precision = Column(Float, nullable=True)
    context_recall = Column(Float, nullable=True)
    
    session = relationship("Session", back_populates="messages")
    
    # uselist=False indicates a One-to-One relationship for feedback.
    feedback = relationship("Feedback", back_populates="message", uselist=False)

class Feedback(Base):
    """
    Optional user-submitted sentiment for an assistant response.
    
    Attributes:
        is_positive (bool): True for Thumbs Up, False for Thumbs Down.
        comment (text): Optional qualitative feedback text.
    """
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    is_positive = Column(Boolean)  # True for thumbs up, False for thumbs down
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="feedback")
    
# Boilerplate for creating tables if they don't exist.
# NOTE: In production environments, database migrations (like Alembic) 
# should be used instead of metadata.create_all().
from .database import engine
Base.metadata.create_all(bind=engine)
