from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.schemas import MetricsSummaryResponse
from src.storage.database import get_database
from src.storage.repository import EvaluationRepository
from sqlalchemy import func
from src.storage.models import Evaluation
from datetime import datetime, timedelta

router = APIRouter(prefix="/metrics", tags=["metrics"])

def get_db_session():
    db = get_database()
    with db.get_session() as session:
        yield session

@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    hours: int = 24,
    session: Session = Depends(get_db_session)
):
    """Get aggregated metrics for time window"""
    repo = EvaluationRepository(session)
    metrics = repo.get_metrics_summary(hours=hours)
    
    # Count total evaluations
    since = datetime.utcnow() - timedelta(hours=hours)
    total = session.query(func.count(Evaluation.id)).filter(
        Evaluation.timestamp >= since
    ).scalar()
    
    return MetricsSummaryResponse(
        time_window_hours=hours,
        metrics=metrics,
        total_evaluations=total
    )