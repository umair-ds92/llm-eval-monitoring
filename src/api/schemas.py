from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime

class EvaluationRequest(BaseModel):
    """Request to evaluate a prompt-response pair"""
    model_config = ConfigDict(protected_namespaces=()) 
    
    prompt: str = Field(..., description="Input prompt")
    response: str = Field(..., description="Model response")
    model_id: str = Field(..., description="Model identifier")
    model_version: Optional[str] = Field(None, description="Model version")
    use_case: str = Field(..., description="Use case (e.g., ioc_extraction)")
    ground_truth: Optional[str] = Field(None, description="Expected output for comparison")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")

class MetricResponse(BaseModel):
    """Individual metric result"""
    metric_type: str
    value: float
    passed: Optional[bool]
    metadata: Dict[str, Any]

class EvaluationResponse(BaseModel):
    """Response after evaluation"""
    model_config = ConfigDict(protected_namespaces=())
    
    evaluation_id: int
    timestamp: datetime
    metrics: List[MetricResponse]
    overall_passed: bool
    model_id: str
    use_case: str

class MetricsSummaryResponse(BaseModel):
    """Aggregated metrics summary"""
    time_window_hours: int
    metrics: Dict[str, Dict[str, float]]  # {metric_type: {avg, min, max, count}}
    total_evaluations: int

class HealthResponse(BaseModel):
    """API health check"""
    status: str
    timestamp: datetime
    database_connected: bool
    version: str