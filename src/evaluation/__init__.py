from typing import List
from src.evaluation.base import BaseEvaluator
from src.evaluation.latency import LatencyEvaluator
from src.evaluation.toxicity import ToxicityEvaluator
from src.evaluation.factuality import FactualityEvaluator
from src.evaluation.ioc_extractor import IOCExtractorEvaluator
from src.common.config import get_config

def get_evaluators() -> List[BaseEvaluator]:
    """
    Get all enabled evaluators based on config
    """
    config = get_config()
    evaluators = []
    
    eval_config = config.evaluators
    
    if eval_config.get('latency', {}).get('enabled', True):
        evaluators.append(LatencyEvaluator(config=eval_config.get('latency')))
    
    if eval_config.get('toxicity', {}).get('enabled', True):
        evaluators.append(ToxicityEvaluator(config=eval_config.get('toxicity')))
    
    if eval_config.get('factuality', {}).get('enabled', True):
        evaluators.append(FactualityEvaluator(config=eval_config.get('factuality')))
    
    # Always include IOC extractor for cybersecurity use cases
    evaluators.append(IOCExtractorEvaluator())
    
    return evaluators

__all__ = ['get_evaluators', 'BaseEvaluator']