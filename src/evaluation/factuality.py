"""
Factuality Evaluator

Evaluates factual accuracy of LLM responses using:
1. LLM-as-a-judge (primary method)
2. Semantic similarity (fallback/complement)
"""

import re
from typing import Dict, Optional
from sentence_transformers import SentenceTransformer, util
from src.evaluation.base import BaseEvaluator, EvaluationResult
from src.common.logger import get_logger

logger = get_logger(__name__)


class FactualityEvaluator(BaseEvaluator):
    """
    Evaluates factual accuracy of responses.
    
    Methods:
    1. LLM Judge: Use another LLM to judge accuracy
    2. Semantic Similarity: Compare embeddings to ground truth
    """
    
    DEFAULT_JUDGE_PROMPT = """You are evaluating the factual accuracy of an AI response.

Question: {prompt}

AI Response:
{response}

Ground Truth (Expected Answer):
{ground_truth}

Rate the factual accuracy of the AI response from 0.0 to 1.0:
- 1.0: Completely accurate, all facts correct
- 0.8-0.9: Mostly accurate with minor errors or omissions
- 0.6-0.7: Partially accurate, some key facts correct
- 0.4-0.5: Partially accurate, many errors
- 0.0-0.3: Mostly or completely inaccurate

Respond with ONLY a single number between 0.0 and 1.0, nothing else.
"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(name="factuality", config=config)
        
        # Configuration
        self.use_llm_judge = self.config.get('use_llm_judge', True)
        self.judge_model = self.config.get('judge_model', 'claude-sonnet-4')
        self.judge_prompt_template = self.config.get(
            'judge_prompt_template',
            self.DEFAULT_JUDGE_PROMPT
        )
        self.threshold = self.config.get('threshold', 0.8)
        self.fallback_to_similarity = self.config.get('fallback_to_similarity', True)
        self.max_retries = self.config.get('max_retries', 2)
        
        # Initialize semantic similarity model (fallback)
        if self.fallback_to_similarity:
            self.logger.info("Loading semantic similarity model for fallback...")
            self.similarity_model = SentenceTransformer('all-mpnet-base-v2')
        else:
            self.similarity_model = None
        
        self.logger.info(
            f"Factuality evaluator initialized with LLM judge={self.use_llm_judge}, "
            f"threshold={self.threshold}"
        )
    
    async def _evaluate_with_llm_judge(
        self,
        prompt: str,
        response: str,
        ground_truth: str
    ) -> Optional[float]:
        """
        Use an LLM to judge factuality
        
        Returns:
            Factuality score 0.0-1.0, or None if failed
        """
        try:
            # Format judge prompt
            judge_prompt = self.judge_prompt_template.format(
                prompt=prompt,
                response=response,
                ground_truth=ground_truth
            )
            
            # Call LLM API (you need to implement this based on your LLM provider)
            # This is a placeholder - you'll need to integrate with your actual LLM API
            score = await self._call_llm_judge(judge_prompt)
            
            return score
            
        except Exception as e:
            self.logger.error(f"LLM judge evaluation failed: {e}")
            return None
    
    async def _call_llm_judge(self, prompt: str) -> Optional[float]:
        """
        Call LLM API to get judgment
        
        This is a placeholder - implement based on your provider (Anthropic, OpenAI, etc.)
        """
        # TODO: Implement actual API call
        # Example for Anthropic:
        # from anthropic import Anthropic
        # client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        # message = client.messages.create(
        #     model=self.judge_model,
        #     max_tokens=10,
        #     messages=[{"role": "user", "content": prompt}]
        # )
        # response_text = message.content[0].text
        # score = self._extract_score(response_text)
        # return score
        
        self.logger.warning("LLM judge not implemented, using fallback")
        return None
    
    def _extract_score(self, text: str) -> Optional[float]:
        """Extract numerical score from LLM response"""
        try:
            # Look for a number between 0 and 1
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                score = float(match.group(1))
                # Normalize if needed
                if score > 1.0:
                    score = score / 10.0  # In case it returned 0-10 scale
                if 0.0 <= score <= 1.0:
                    return score
            return None
        except:
            return None
    
    def _evaluate_with_similarity(
        self,
        response: str,
        ground_truth: str
    ) -> float:
        """
        Evaluate using semantic similarity between response and ground truth
        
        Returns:
            Similarity score 0.0-1.0
        """
        if self.similarity_model is None:
            self.logger.error("Similarity model not loaded")
            return 0.0
        
        try:
            # Generate embeddings
            embedding1 = self.similarity_model.encode(response, convert_to_tensor=True)
            embedding2 = self.similarity_model.encode(ground_truth, convert_to_tensor=True)
            
            # Calculate cosine similarity
            similarity = util.cos_sim(embedding1, embedding2).item()
            
            # Convert from [-1, 1] to [0, 1]
            similarity = (similarity + 1) / 2
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    async def evaluate(self, prompt: str, response: str, **kwargs) -> EvaluationResult:
        """
        Evaluate factual accuracy
        
        Args:
            prompt: Original question/prompt
            response: Model's response
            ground_truth: Expected/correct answer (required in kwargs)
            **kwargs: Additional arguments
        
        Returns:
            EvaluationResult with factuality score
        """
        ground_truth = kwargs.get('ground_truth')
        
        if not ground_truth:
            self.logger.warning("No ground truth provided, cannot evaluate factuality")
            return EvaluationResult(
                metric_type="factuality",
                value=0.0,
                metadata={'error': 'no_ground_truth'},
                passed=None  # Cannot determine
            )
        
        factuality_score = None
        method_used = None
        
        # Method 1: LLM Judge
        if self.use_llm_judge:
            for attempt in range(self.max_retries):
                factuality_score = await self._evaluate_with_llm_judge(
                    prompt, response, ground_truth
                )
                if factuality_score is not None:
                    method_used = "llm_judge"
                    break
                self.logger.warning(f"LLM judge attempt {attempt + 1} failed")
        
        # Method 2: Semantic Similarity (fallback or complement)
        similarity_score = None
        if factuality_score is None or self.fallback_to_similarity:
            similarity_score = self._evaluate_with_similarity(response, ground_truth)
            
            if factuality_score is None:
                # Use similarity as primary score
                factuality_score = similarity_score
                method_used = "semantic_similarity"
        
        # Default to 0 if all methods failed
        if factuality_score is None:
            factuality_score = 0.0
            method_used = "failed"
        
        # Determine pass/fail
        passed = factuality_score >= self.threshold
        
        metadata = {
            'method': method_used,
            'threshold': self.threshold,
            'ground_truth_length': len(ground_truth),
            'response_length': len(response)
        }
        
        if similarity_score is not None:
            metadata['semantic_similarity'] = similarity_score
        
        # Log low scores
        if factuality_score < self.threshold:
            self.logger.warning(
                f"Low factuality score: {factuality_score:.3f} "
                f"(threshold: {self.threshold})"
            )
        
        return EvaluationResult(
            metric_type="factuality",
            value=factuality_score,
            metadata=metadata,
            passed=passed
        )


# Simple exact match evaluator (for structured outputs like IOCs)
class ExactMatchEvaluator(BaseEvaluator):
    """
    Simple exact match comparison
    Useful for structured outputs where exact matching is appropriate
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(name="exact_match", config=config)
        self.case_sensitive = self.config.get('case_sensitive', False)
        self.normalize_whitespace = self.config.get('normalize_whitespace', True)
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison"""
        if self.normalize_whitespace:
            text = ' '.join(text.split())
        if not self.case_sensitive:
            text = text.lower()
        return text
    
    async def evaluate(self, prompt: str, response: str, **kwargs) -> EvaluationResult:
        """Evaluate using exact match"""
        
        ground_truth = kwargs.get('ground_truth')
        
        if not ground_truth:
            return EvaluationResult(
                metric_type="exact_match",
                value=0.0,
                metadata={'error': 'no_ground_truth'},
                passed=None
            )
        
        # Normalize
        response_norm = self._normalize(response)
        ground_truth_norm = self._normalize(ground_truth)
        
        # Check match
        is_match = response_norm == ground_truth_norm
        score = 1.0 if is_match else 0.0
        
        return EvaluationResult(
            metric_type="exact_match",
            value=score,
            metadata={
                'case_sensitive': self.case_sensitive,
                'normalize_whitespace': self.normalize_whitespace
            },
            passed=is_match
        )