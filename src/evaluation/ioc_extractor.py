import re
from typing import Set, Dict
from src.evaluation.base import BaseEvaluator, EvaluationResult

class IOCExtractorEvaluator(BaseEvaluator):
    """
    Evaluates quality of Indicator of Compromise (IOC) extraction
    Cybersecurity-specific evaluator
    """
    
    # Regex patterns for common IOCs
    PATTERNS = {
        'ipv4': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'domain': r'\b[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+\b',
        'md5': r'\b[a-fA-F0-9]{32}\b',
        'sha256': r'\b[a-fA-F0-9]{64}\b',
        'cve': r'\bCVE-\d{4}-\d{4,7}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    }
    
    def __init__(self, config: Dict = None):
        super().__init__(name="ioc_extraction", config=config)
    
    def extract_iocs(self, text: str) -> Dict[str, Set[str]]:
        """Extract IOCs from text"""
        iocs = {}
        for ioc_type, pattern in self.PATTERNS.items():
            matches = set(re.findall(pattern, text, re.IGNORECASE))
            if matches:
                iocs[ioc_type] = matches
        return iocs
    
    async def evaluate(self, prompt: str, response: str, **kwargs) -> EvaluationResult:
        """
        Evaluate IOC extraction quality
        Compares extracted IOCs against ground truth if provided
        """
        # Extract IOCs from response
        extracted = self.extract_iocs(response)
        total_extracted = sum(len(iocs) for iocs in extracted.values())
        
        # If ground truth provided, calculate precision/recall
        ground_truth = kwargs.get('ground_truth')
        if ground_truth:
            gt_iocs = self.extract_iocs(ground_truth)
            precision, recall, f1 = self._calculate_metrics(extracted, gt_iocs)
            
            return EvaluationResult(
                metric_type="ioc_extraction_f1",
                value=f1,
                metadata={
                    'precision': precision,
                    'recall': recall,
                    'extracted_count': total_extracted,
                    'ioc_types': list(extracted.keys())
                },
                passed=f1 >= 0.8  # 80% F1 threshold
            )
        
        # Without ground truth, just report extraction count
        return EvaluationResult(
            metric_type="ioc_extraction_count",
            value=float(total_extracted),
            metadata={
                'ioc_breakdown': {k: len(v) for k, v in extracted.items()},
                'ioc_types': list(extracted.keys())
            }
        )
    
    def _calculate_metrics(self, extracted: Dict, ground_truth: Dict) -> tuple:
        """Calculate precision, recall, F1"""
        # Flatten to sets
        extracted_flat = set()
        for iocs in extracted.values():
            extracted_flat.update(iocs)
        
        gt_flat = set()
        for iocs in ground_truth.values():
            gt_flat.update(iocs)
        
        if not extracted_flat:
            return 0.0, 0.0, 0.0
        
        true_positives = len(extracted_flat & gt_flat)
        precision = true_positives / len(extracted_flat) if extracted_flat else 0
        recall = true_positives / len(gt_flat) if gt_flat else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return precision, recall, f1