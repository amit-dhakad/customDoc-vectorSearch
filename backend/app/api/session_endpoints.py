from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from ..database import get_db
from .. import models, schemas

"""
backend/app/api/session_endpoints.py — RAG State & Workspace Management.

THE ANCHOR PHILOSOPHY:
─────────────────────────────────────────────────────────────────────────────
In this application, a 'Session' is more than a chat history. It is a 
logical workspace that anchors specific Documents, Chunks, and Vectors.

WHY THIS IS CRITICAL:
────────────────────────────────────────────────────
1. CONTEXT ISOLATION: By linking Documents and Vectors to a session_id, we ensure 
   that when you search your "Legal Doc" session, the AI doesn't hallucinate 
   using data from your "Tech Manual" session.
2. PERSISTENCE: Every message and file relationship is serialized to SQLite, 
   allowing for a persistent, multi-modal 'workspace' memory.
3. VECTOR MAPPING: The session_id serves as the ChromaDB collection name, 
   allowing for isolated, high-speed vector retrieval.

HOW IT BEST SERVES THE USER:
───────────────────────────
- WORKSPACE MEMORY: Users can return to a session months later and the AI still 
  possesses the "Intelligence" of the documents uploaded to that space.
- SCALABLE HISTORY: Uses SQLAlchemy lazy-loading to handle thousands of messages 
  without significantly increasing memory pressure on the API.
"""

router = APIRouter()

@router.get("/sessions", response_model=List[schemas.Session])
def get_sessions(db: Session = Depends(get_db)):
    """Retrieve all chat sessions, ordered by most recently created."""
    return db.query(models.Session).order_by(models.Session.created_at.desc()).all()

@router.post("/sessions", response_model=schemas.Session)
def create_session(session: schemas.SessionCreate, db: Session = Depends(get_db)):
    """
    Initialize a new session.
    This implementation is idempotent: if the session ID already exists, 
    it returns the existing session instead of creating a duplicate.
    """
    db_session = db.query(models.Session).filter(models.Session.id == session.id).first()
    if db_session:
        return db_session
    
    db_session = models.Session(id=session.id, title=session.title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Hard delete a session and all its associated messages/documents via cascade."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(db_session)
    db.commit()
    return {"message": "Session deleted"}

@router.get("/sessions/{session_id}/messages", response_model=List[schemas.Message])
def get_messages(session_id: str, db: Session = Depends(get_db)):
    """Fetch the full chat history for a specific session."""
    return db.query(models.Message).filter(models.Message.session_id == session_id).all()

@router.get("/sessions/{session_id}/documents", response_model=List[schemas.Document])
def get_session_documents(session_id: str, db: Session = Depends(get_db)):
    """Retrieve the list of all documents that have been parsed in this session."""
    return db.query(models.Document).filter(models.Document.session_id == session_id).all()

@router.post("/sessions/{session_id}/messages", response_model=schemas.Message)
def create_message(session_id: str, message: schemas.MessageCreate, db: Session = Depends(get_db)):
    """Record a new user or assistant message in the session history."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db_message = models.Message(
        session_id=session_id,
        role=message.role,
        content=message.content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

@router.post("/feedback", response_model=schemas.Feedback)
def submit_feedback(feedback: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    """
    Submit or update user feedback for an assistant's response.
    Each message supports exactly one feedback record (One-to-One).
    """
    db_message = db.query(models.Message).filter(models.Message.id == feedback.message_id).first()
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if feedback already exists for this message (Upsert logic)
    existing_feedback = db.query(models.Feedback).filter(models.Feedback.message_id == feedback.message_id).first()
    if existing_feedback:
        existing_feedback.is_positive = feedback.is_positive
        existing_feedback.comment = feedback.comment
        db.commit()
        db.refresh(existing_feedback)
        return existing_feedback
    
    db_feedback = models.Feedback(
        message_id=feedback.message_id,
        is_positive=feedback.is_positive,
        comment=feedback.comment
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    db.query(models.Session).filter(models.Session.id == session_id).delete()
    db.commit()
    return {"status": "deleted"}

@router.post("/sessions/{session_id}/ask")
async def ask_question(session_id: str, message: schemas.MessageCreate, db: Session = Depends(get_db)):
    """
    Primary RAG Entry Point.
    1. Saves the user question to the database.
    2. Orchestrates context retrieval and LLM generation via RAGService.
    3. Saves the AI response to the database.
    4. Returns the final answer.
    """
    # 1. Store User Message
    user_db_msg = models.Message(
        session_id=session_id,
        role="user",
        content=message.content
    )
    db.add(user_db_msg)
    db.commit()

    # 2. Trigger RAG Pipeline
    from app.services.rag_service import RAGService
    rag = RAGService()
    result = await rag.generate_rag_answer(
        session_id, 
        message.content, 
        model=message.model,
        search_type=message.search_type,
        rerank=message.enable_reranking
    )
    answer = result.get("answer", "")
    metrics = result.get("metrics", {})
    scores = result.get("scores", {})

    # 3. Store AI Response with Metrics & RAGAS Scores
    ai_db_msg = models.Message(
        session_id=session_id,
        role="assistant",
        content=answer,
        total_latency_ms=metrics.get("total_latency_ms"),
        retrieval_latency_ms=metrics.get("retrieval_latency_ms"),
        generation_latency_ms=metrics.get("generation_latency_ms"),
        prompt_tokens=metrics.get("prompt_tokens"),
        completion_tokens=metrics.get("completion_tokens"),
        # Persist RAGAS scores 
        faithfulness=scores.get("faithfulness"),
        answer_relevancy=scores.get("answer_relevancy"),
        context_precision=scores.get("context_precision"),
        context_recall=scores.get("context_recall")
    )
    db.add(ai_db_msg)
    db.commit()
    db.refresh(ai_db_msg)

    return ai_db_msg
