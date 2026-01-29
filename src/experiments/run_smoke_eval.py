"""Run evaluation on cybersecurity test datasets"""

import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from src.storage.database import get_database
from src.storage.repository import EvaluationRepository
from src.evaluation import get_evaluators
from src.common.logger import get_logger

logger = get_logger(__name__)


async def run_evaluation_batch(
    dataset_path: Path, 
    model_id: str = "claude-sonnet-4"
) -> List[Dict[str, Any]]:
    """
    Run evaluations on a dataset
    
    Args:
        dataset_path: Path to JSONL dataset file
        model_id: Model identifier to use for evaluations
    
    Returns:
        List of evaluation results
    """
    # Load dataset
    with open(dataset_path) as f:
        test_cases = [json.loads(line) for line in f]
    
    logger.info(f"Loaded {len(test_cases)} test cases from {dataset_path.name}")
    
    # Get evaluators
    evaluators = get_evaluators()
    logger.info(f"Using {len(evaluators)} evaluators: {[e.name for e in evaluators]}")
    
    # Run evaluations
    db = get_database()
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"Processing test case {i}/{len(test_cases)}")
        
        start_time = time.time()
        
        with db.get_session() as session:
            repo = EvaluationRepository(session)
            
            # Create evaluation
            evaluation = repo.create_evaluation({
                'model_id': model_id,
                'model_version': '1.0',
                'prompt': test_case['prompt'],
                'response': test_case['response'],
                'use_case': test_case.get('use_case', 'general'),
                'metadata': {'dataset': dataset_path.name}
            })
            
            # Run evaluators
            eval_results = {}
            for evaluator in evaluators:
                try:
                    result = await evaluator.evaluate(
                        prompt=test_case['prompt'],
                        response=test_case['response'],
                        ground_truth=test_case.get('ground_truth'),
                        latency_ms=(time.time() - start_time) * 1000,
                        use_case=test_case.get('use_case', 'general')
                    )
                    
                    # Store metric
                    repo.add_metric(
                        eval_id=evaluation.id,
                        metric_type=result.metric_type,
                        value=result.value,
                        metadata=result.metadata
                    )
                    
                    eval_results[result.metric_type] = result.value
                    
                except Exception as e:
                    logger.error(f"Evaluator {evaluator.name} failed: {e}")
            
            session.commit()
            
            results.append({
                'test_case_id': i,
                'evaluation_id': evaluation.id,
                'metrics': eval_results
            })
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"EVALUATION SUMMARY: {dataset_path.name}")
    logger.info("=" * 60)
    logger.info(f"Total test cases: {len(test_cases)}")
    logger.info(f"Total evaluations: {len(results)}")
    
    # Aggregate metrics
    all_metrics = {}
    for result in results:
        for metric_type, value in result['metrics'].items():
            if metric_type not in all_metrics:
                all_metrics[metric_type] = []
            all_metrics[metric_type].append(value)
    
    for metric_type, values in all_metrics.items():
        if values:
            avg = sum(values) / len(values)
            logger.info(
                f"{metric_type}: avg={avg:.2f}, "
                f"min={min(values):.2f}, max={max(values):.2f}"
            )
    
    logger.info("")
    
    return results


async def main():
    """Run evaluations on all test datasets"""
    data_dir = Path(__file__).parent.parent.parent / "data" / "golden"
    
    datasets = [
        data_dir / "smoke.jsonl",
        data_dir / "threat_intel.jsonl",
        data_dir / "malware_analysis.jsonl"
    ]
    
    all_results = {}
    
    for dataset_path in datasets:
        if dataset_path.exists():
            logger.info(f"\n{'='*60}")
            logger.info(f"Running evaluations on: {dataset_path.name}")
            logger.info(f"{'='*60}\n")
            
            try:
                results = await run_evaluation_batch(dataset_path)
                all_results[dataset_path.name] = results
            except Exception as e:
                logger.error(f"Failed to process {dataset_path.name}: {e}")
        else:
            logger.warning(f"Dataset not found: {dataset_path}")
    
    # Overall summary
    logger.info("\n" + "=" * 60)
    logger.info("OVERALL SUMMARY")
    logger.info("=" * 60)
    for dataset_name, results in all_results.items():
        logger.info(f"{dataset_name}: {len(results)} evaluations completed")
    logger.info("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())