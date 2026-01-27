from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from src.storage.models import Evaluation, Metric, Alert
from src.common.logger import get_logger

logger = get_logger(__name__)

class EvaluationRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def create_evaluation(self, eval_data: Dict) -> Evaluation:
        """Create new evaluation record"""
        evaluation = Evaluation(**eval_data)
        self.session.add(evaluation)
        self.session.flush()
        return evaluation
    
    def add_metric(self, eval_id: int, metric_type: str, value: float, metadata: Dict = None) -> Metric:
        """Add metric to evaluation"""
        metric = Metric(
            evaluation_id=eval_id,
            metric_type=metric_type,
            value=value,
            metadata=metadata or {}
        )
        self.session.add(metric)
        self.session.flush()
        return metric
    
    def get_recent_evaluations(self, limit: int = 100, use_case: str = None) -> List[Evaluation]:
        """Get recent evaluations"""
        query = self.session.query(Evaluation).order_by(Evaluation.timestamp.desc())
        if use_case:
            query = query.filter(Evaluation.use_case == use_case)
        return query.limit(limit).all()
    
    def get_metrics_summary(self, hours: int = 24) -> Dict:
        """Get aggregated metrics for time window"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        results = self.session.query(
            Metric.metric_type,
            func.avg(Metric.value).label('avg'),
            func.min(Metric.value).label('min'),
            func.max(Metric.value).label('max'),
            func.count(Metric.id).label('count')
        ).filter(
            Metric.timestamp >= since
        ).group_by(Metric.metric_type).all()
        
        return {
            r.metric_type: {
                'avg': float(r.avg),
                'min': float(r.min),
                'max': float(r.max),
                'count': r.count
            }
            for r in results
        }
    
    def create_alert(self, alert_data: Dict) -> Alert:
        """Create new alert"""
        alert = Alert(**alert_data)
        self.session.add(alert)
        self.session.flush()
        return alert