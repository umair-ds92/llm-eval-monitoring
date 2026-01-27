from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from src.common.logger import get_logger

logger = get_logger(__name__)

@dataclass
class EvaluationResult:
    """Standard evaluation result format"""
    metric_type: str
    value: float
    metadata: Optional[Dict[str, Any]] = None
    passed: Optional[bool] = None
    
    def to_dict(self) -> Dict:
        return {
            'metric_type': self.metric_type,
            'value': self.value,
            'metadata': self.metadata or {},
            'passed': self.passed
        }

class BaseEvaluator(ABC):
    """Base class for all evaluators"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self.logger = get_logger(f"evaluator.{name}")
    
    @abstractmethod
    async def evaluate(self, prompt: str, response: str, **kwargs) -> EvaluationResult:
        """
        Evaluate a prompt-response pair
        
        Args:
            prompt: Input prompt
            response: Model response
            **kwargs: Additional context (ground_truth, metadata, etc.)
        
        Returns:
            EvaluationResult with metric value and metadata
        """
        pass
    
    def check_threshold(self, value: float, threshold: float, higher_is_better: bool = True) -> bool:
        """Check if value passes threshold"""
        if higher_is_better:
            return value >= threshold
        return value <= threshold
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"