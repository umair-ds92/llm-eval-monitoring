"""
Latency Evaluator
Latency is a primary operational metric for LLM systems. Tracking p50/p95/p99
helps catch regressions, routing mistakes, infrastructure issues, and vendor slowdowns.

This module provides:
- Latency measurement with statistical analysis (p50/p95/p99)
- Threshold-based evaluation
- Integration with the evaluation framework
"""

import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from src.evaluation.base import BaseEvaluator, EvaluationResult
from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LatencyStats:
    """Statistical summary of latency measurements"""
    n: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float


class LatencyEvaluator(BaseEvaluator):
    """
    Measures and evaluates response latency
    
    Can both measure latency and evaluate against thresholds
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(name="latency", config=config)
        
        # Threshold configuration
        self.thresholds = self.config.get('thresholds', {
            'p50_ms': 1000,   # 1 second
            'p95_ms': 2000,   # 2 seconds
            'p99_ms': 5000,   # 5 seconds
            'mean_ms': 1500   # 1.5 seconds
        })
        
        self.logger.info(f"Latency evaluator initialized with thresholds: {self.thresholds}")
    
    @staticmethod
    def _percentile(sorted_vals: List[float], p: float) -> float:
        """
        Calculate percentile from sorted values
        
        Args:
            sorted_vals: Sorted list of values
            p: Percentile (0-100)
        
        Returns:
            Percentile value
        """
        if not sorted_vals:
            return 0.0
        
        # Nearest-rank approximation
        k = int(round((p / 100.0) * (len(sorted_vals) - 1)))
        k = max(0, min(k, len(sorted_vals) - 1))
        return float(sorted_vals[k])
    
    @staticmethod
    def calculate_stats(latencies_ms: List[float]) -> LatencyStats:
        """
        Calculate statistical summary of latencies
        
        Args:
            latencies_ms: List of latency measurements in milliseconds
        
        Returns:
            LatencyStats with p50/p95/p99 and other metrics
        """
        if not latencies_ms:
            return LatencyStats(
                n=0,
                mean_ms=0.0,
                p50_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                min_ms=0.0,
                max_ms=0.0
            )
        
        vals = sorted(float(x) for x in latencies_ms)
        mean_ms = sum(vals) / len(vals)
        
        return LatencyStats(
            n=len(vals),
            mean_ms=mean_ms,
            p50_ms=LatencyEvaluator._percentile(vals, 50),
            p95_ms=LatencyEvaluator._percentile(vals, 95),
            p99_ms=LatencyEvaluator._percentile(vals, 99),
            min_ms=vals[0],
            max_ms=vals[-1]
        )
    
    @staticmethod
    def measure_latency_ms(
        fn: Callable[[], Any],
        repeats: int = 5
    ) -> Dict[str, Any]:
        """
        Measure latency of a callable function
        
        Usage:
            result = LatencyEvaluator.measure_latency_ms(
                lambda: model.generate(prompt),
                repeats=10
            )
        
        Args:
            fn: Callable to measure (should be a lambda or function)
            repeats: Number of times to repeat the measurement
        
        Returns:
            Dictionary with raw latencies and statistical summary
        """
        latencies: List[float] = []
        
        for i in range(max(1, int(repeats))):
            t0 = time.perf_counter()
            try:
                _ = fn()
            except Exception as e:
                logger.error(f"Error during latency measurement (attempt {i+1}): {e}")
                raise
            t1 = time.perf_counter()
            
            latency_ms = (t1 - t0) * 1000.0
            latencies.append(latency_ms)
        
        stats = LatencyEvaluator.calculate_stats(latencies)
        
        return {
            "latencies_ms": latencies,
            "stats": {
                "n": stats.n,
                "mean_ms": stats.mean_ms,
                "p50_ms": stats.p50_ms,
                "p95_ms": stats.p95_ms,
                "p99_ms": stats.p99_ms,
                "min_ms": stats.min_ms,
                "max_ms": stats.max_ms
            }
        }
    
    async def measure_async(
        self,
        fn: Callable,
        repeats: int = 5
    ) -> Dict[str, Any]:
        """
        Measure latency of an async callable
        
        Args:
            fn: Async callable to measure
            repeats: Number of times to repeat
        
        Returns:
            Dictionary with latencies and stats
        """
        latencies: List[float] = []
        
        for i in range(max(1, int(repeats))):
            t0 = time.perf_counter()
            try:
                await fn()
            except Exception as e:
                self.logger.error(f"Error during async latency measurement (attempt {i+1}): {e}")
                raise
            t1 = time.perf_counter()
            
            latency_ms = (t1 - t0) * 1000.0
            latencies.append(latency_ms)
        
        stats = self.calculate_stats(latencies)
        
        return {
            "latencies_ms": latencies,
            "stats": {
                "n": stats.n,
                "mean_ms": stats.mean_ms,
                "p50_ms": stats.p50_ms,
                "p95_ms": stats.p95_ms,
                "p99_ms": stats.p99_ms,
                "min_ms": stats.min_ms,
                "max_ms": stats.max_ms
            }
        }
    
    def _check_thresholds(self, latency_ms: float) -> Dict[str, bool]:
        """
        Check latency against configured thresholds
        
        Args:
            latency_ms: Single latency measurement
        
        Returns:
            Dictionary of threshold checks
        """
        checks = {}
        
        # Check against mean threshold (treating single value as mean)
        if 'mean_ms' in self.thresholds:
            checks['mean_threshold_passed'] = latency_ms <= self.thresholds['mean_ms']
        
        # Check against p95 threshold (conservative for single measurement)
        if 'p95_ms' in self.thresholds:
            checks['p95_threshold_passed'] = latency_ms <= self.thresholds['p95_ms']
        
        return checks
    
    async def evaluate(
        self,
        prompt: str,
        response: str,
        **kwargs
    ) -> EvaluationResult:
        """
        Evaluate latency from metadata
        
        Expects either:
        - 'latency_ms': Single latency value
        - 'latencies_ms': List of latency values for statistical analysis
        
        Args:
            prompt: Original prompt (not used for latency)
            response: Model response (not used for latency)
            **kwargs: Must contain 'latency_ms' or 'latencies_ms'
        
        Returns:
            EvaluationResult with latency metrics
        """
        # Check for multiple measurements
        latencies_ms = kwargs.get('latencies_ms')
        
        if latencies_ms:
            # Multiple measurements - calculate stats
            stats = self.calculate_stats(latencies_ms)
            
            # Check against thresholds
            threshold_checks = {}
            
            if 'mean_ms' in self.thresholds:
                threshold_checks['mean'] = stats.mean_ms <= self.thresholds['mean_ms']
            
            if 'p50_ms' in self.thresholds:
                threshold_checks['p50'] = stats.p50_ms <= self.thresholds['p50_ms']
            
            if 'p95_ms' in self.thresholds:
                threshold_checks['p95'] = stats.p95_ms <= self.thresholds['p95_ms']
            
            if 'p99_ms' in self.thresholds:
                threshold_checks['p99'] = stats.p99_ms <= self.thresholds['p99_ms']
            
            # Overall pass if all thresholds pass
            passed = all(threshold_checks.values()) if threshold_checks else True
            
            # Use p95 as primary value for scoring
            primary_value = stats.p95_ms
            
            if not passed:
                self.logger.warning(
                    f"Latency thresholds exceeded: "
                    f"p50={stats.p50_ms:.1f}ms, p95={stats.p95_ms:.1f}ms, "
                    f"p99={stats.p99_ms:.1f}ms"
                )
            
            return EvaluationResult(
                metric_type="latency",
                value=primary_value,
                metadata={
                    'n': stats.n,
                    'mean_ms': stats.mean_ms,
                    'p50_ms': stats.p50_ms,
                    'p95_ms': stats.p95_ms,
                    'p99_ms': stats.p99_ms,
                    'min_ms': stats.min_ms,
                    'max_ms': stats.max_ms,
                    'thresholds': self.thresholds,
                    'threshold_checks': threshold_checks,
                    'unit': 'milliseconds'
                },
                passed=passed
            )
        
        # Single measurement
        latency_ms = kwargs.get('latency_ms')
        
        if latency_ms is None:
            self.logger.warning("No latency_ms or latencies_ms provided in kwargs")
            return EvaluationResult(
                metric_type="latency",
                value=0.0,
                metadata={'error': 'latency_ms not provided'},
                passed=None
            )
        
        # Check against thresholds
        threshold_checks = self._check_thresholds(latency_ms)
        passed = all(threshold_checks.values()) if threshold_checks else True
        
        if not passed:
            self.logger.warning(
                f"Latency threshold exceeded: {latency_ms:.1f}ms"
            )
        
        return EvaluationResult(
            metric_type="latency",
            value=latency_ms,
            metadata={
                'thresholds': self.thresholds,
                'threshold_checks': threshold_checks,
                'unit': 'milliseconds'
            },
            passed=passed
        )


# Utility function for backwards compatibility
def measure_latency_ms(fn: Callable[[], Any], repeats: int = 5) -> Dict[str, Any]:
    """
    Convenience function to measure latency
    
    This is a wrapper around LatencyEvaluator.measure_latency_ms()
    for backwards compatibility and ease of use.
    
    Args:
        fn: Callable to measure
        repeats: Number of repetitions
    
    Returns:
        Dictionary with latencies and statistics
    """
    return LatencyEvaluator.measure_latency_ms(fn, repeats)


def summarize_latencies_ms(latencies_ms: List[float]) -> LatencyStats:
    """
    Convenience function to calculate latency statistics
    
    This is a wrapper around LatencyEvaluator.calculate_stats()
    for backwards compatibility.
    
    Args:
        latencies_ms: List of latency measurements
    
    Returns:
        LatencyStats object
    """
    return LatencyEvaluator.calculate_stats(latencies_ms)