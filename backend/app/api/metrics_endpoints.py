from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..database import get_db
from .. import models, schemas

router = APIRouter()

@router.get("/metrics/summary")
async def get_metrics_summary(db: DBSession = Depends(get_db)):
    """
    Returns aggregated quality and performance metrics for all RAG interactions.
    Used by the Performance Dashboard.
    """
    # 1. Aggregate Latency
    latency_stats = db.query(
        func.avg(models.Message.total_latency_ms).label("avg_total"),
        func.avg(models.Message.retrieval_latency_ms).label("avg_retrieval"),
        func.avg(models.Message.generation_latency_ms).label("avg_generation")
    ).filter(models.Message.role == "assistant").first()

    # 2. Aggregate RAGAS Scores
    ragas_stats = db.query(
        func.avg(models.Message.faithfulness).label("avg_faithfulness"),
        func.avg(models.Message.answer_relevancy).label("avg_relevancy"),
        func.avg(models.Message.context_precision).label("avg_precision"),
        func.avg(models.Message.context_recall).label("avg_recall")
    ).filter(models.Message.faithfulness.isnot(None)).first()

    # 3. Message Count (Volume)
    total_messages = db.query(models.Message).filter(models.Message.role == "assistant").count()

    return {
        "latency": {
            "avg_total_ms": round(latency_stats.avg_total or 0, 2),
            "avg_retrieval_ms": round(latency_stats.avg_retrieval or 0, 2),
            "avg_generation_ms": round(latency_stats.avg_generation or 0, 2),
        },
        "quality": {
            "avg_faithfulness": round(ragas_stats.avg_faithfulness or 0, 4),
            "avg_relevancy": round(ragas_stats.avg_relevancy or 0, 4),
            "avg_precision": round(ragas_stats.avg_precision or 0, 4),
            "avg_recall": round(ragas_stats.avg_recall or 0, 4),
        },
        "volume": {
            "total_assistant_responses": total_messages
        }
    }

@router.get("/metrics/history")
async def get_metrics_history(days: int = 7, db: DBSession = Depends(get_db)):
    """
    Returns a daily breakdown of metrics for the last N days.
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Group by day
    history = db.query(
        func.date(models.Message.timestamp).label("day"),
        func.avg(models.Message.faithfulness).label("faithfulness"),
        func.avg(models.Message.answer_relevancy).label("relevancy"),
        func.avg(models.Message.context_precision).label("precision"),
        func.avg(models.Message.context_recall).label("recall"),
        func.avg(models.Message.total_latency_ms).label("latency")
    ).filter(
        models.Message.role == "assistant",
        models.Message.timestamp >= since
    ).group_by(func.date(models.Message.timestamp)).order_by(func.date(models.Message.timestamp)).all()

    return [
        {
            "day": h.day, 
            "faithfulness": round(h.faithfulness or 0, 4), 
            "relevancy": round(h.relevancy or 0, 4),
            "precision": round(h.precision or 0, 4),
            "recall": round(h.recall or 0, 4),
            "avg_latency_ms": round(h.latency or 0, 2)
        }
        for h in history
    ]
