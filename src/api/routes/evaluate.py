from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from src.api.schemas import EvaluationRequest, EvaluationResponse, MetricResponse
from src.storage.database import get_database
from src.storage.repository import EvaluationRepository
from src.evaluation import get_evaluators
from src.common.logger import get_logger

router = APIRouter(prefix="/evaluate", tags=["evaluation"])
logger = get_logger(__name__)

def get_db_session():
    """Dependency for database session"""
    db = get_database()
    with db.get_session() as session:
        yield session

@router.post("/", response_model=EvaluationResponse)
async def evaluate_response(
    request: EvaluationRequest,
    session: Session = Depends(get_db_session)
):
    """
    Evaluate a prompt-response pair across all enabled evaluators
    """
    try:
        # Create evaluation record
        repo = EvaluationRepository(session)
        evaluation = repo.create_evaluation({
            'model_id': request.model_id,
            'model_version': request.model_version,
            'prompt': request.prompt,
            'response': request.response,
            'use_case': request.use_case,
            'metadata': request.metadata
        })
        
        # Run evaluators
        evaluators = get_evaluators()
        metrics_results = []
        all_passed = True
        
        for evaluator in evaluators:
            try:
                result = await evaluator.evaluate(
                    prompt=request.prompt,
                    response=request.response,
                    ground_truth=request.ground_truth,
                    latency_ms=request.latency_ms,
                    use_case=request.use_case
                )
                
                # Store metric
                repo.add_metric(
                    eval_id=evaluation.id,
                    metric_type=result.metric_type,
                    value=result.value,
                    metadata=result.metadata
                )
                
                metrics_results.append(MetricResponse(
                    metric_type=result.metric_type,
                    value=result.value,
                    passed=result.passed,
                    metadata=result.metadata or {}
                ))
                
                if result.passed is False:
                    all_passed = False
                    
            except Exception as e:
                logger.error(f"Evaluator {evaluator.name} failed: {e}")
                # Continue with other evaluators
        
        session.commit()
        
        return EvaluationResponse(
            evaluation_id=evaluation.id,
            timestamp=evaluation.timestamp,
            metrics=metrics_results,
            overall_passed=all_passed,
            model_id=request.model_id,
            use_case=request.use_case
        )
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recent", response_model=List[dict])
async def get_recent_evaluations(
    limit: int = 50,
    use_case: str = None,
    session: Session = Depends(get_db_session)
):
    """Get recent evaluations"""
    repo = EvaluationRepository(session)
    evaluations = repo.get_recent_evaluations(limit=limit, use_case=use_case)
    
    return [
        {
            'id': e.id,
            'timestamp': e.timestamp,
            'model_id': e.model_id,
            'use_case': e.use_case,
            'prompt': e.prompt[:100] + '...' if len(e.prompt) > 100 else e.prompt,
            'metrics_count': len(e.metrics)
        }
        for e in evaluations
    ]