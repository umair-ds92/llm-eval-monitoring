from fastapi import APIRouter
from datetime import datetime
from sqlalchemy import text
from src.api.schemas import HealthResponse
from src.storage.database import get_database
from src.common.logger import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """API health check"""
    db_connected = False
    
    try:
        db = get_database()
        # Try to execute a simple query
        with db.get_session() as session:
            session.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        version="0.1.0"
    )