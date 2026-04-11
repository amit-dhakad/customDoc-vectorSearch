from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
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
    Stores metadata for files uploaded to a specific session.
    
    Attributes:
        session_id (str): Foreign key linking back to the parent Session.
        filename (str): Original name of the uploaded file.
        file_type (str): Extension/MIME type (e.g., pdf, docx).
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    filename = Column(String)
    file_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # back_populates links this to the 'documents' list in the Session model.
    session = relationship("Session", back_populates="documents")

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
