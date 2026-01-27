from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.storage.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    model_id = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=True)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    use_case = Column(String(100), nullable=False, index=True)
    meta_data = Column(JSON, nullable=True)  # Renamed from 'metadata'
    
    # Relationships
    metrics = relationship("Metric", back_populates="evaluation", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_eval_timestamp_model', 'timestamp', 'model_id'),
    )
    
    def __repr__(self):
        return f"<Evaluation(id={self.id}, model='{self.model_id}', use_case='{self.use_case}')>"


class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), nullable=False)
    metric_type = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    meta_data = Column(JSON, nullable=True)  # Renamed from 'metadata'
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Relationships
    evaluation = relationship("Evaluation", back_populates="metrics")
    
    __table_args__ = (
        Index('ix_metric_type_timestamp', 'metric_type', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<Metric(id={self.id}, type='{self.metric_type}', value={self.value})>"


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String(50), nullable=False, index=True)
    threshold_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False)  # "low", "medium", "high", "critical"
    message = Column(Text, nullable=False)
    triggered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    meta_data = Column(JSON, nullable=True)  # Renamed from 'metadata'
    
    def __repr__(self):
        return f"<Alert(id={self.id}, type='{self.metric_type}', severity='{self.severity}')>"