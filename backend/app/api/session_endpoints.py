from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from ..database import get_db
from .. import models, schemas

"""
Session & Chat Management
-------------------------
Handles the lifecycle of chat sessions, message persistence, 
document associations, and user feedback.
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
