import os
import logging
from typing import Dict, Any, List
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
import pandas as pd

logger = logging.getLogger(__name__)

class RagasEvaluator:
    """
    RAG Performance Evaluation Suite using RAGAS.
    Supports dual-mode execution: Local (Ollama) or Cloud (OpenAI).
    """

    def __init__(self):
        # 1. Select the "Critic" LLM based on environment configuration
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
        
        if self.openai_key:
            logger.info("[EVAL] Using OpenAI (GPT-4o/3.5) as RAGAS Critic")
            self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=self.openai_key)
        else:
            logger.info(f"[EVAL] Using Local Ollama as RAGAS Critic via {self.ollama_url}")
            # Note: RAGAS works best with robust models like Llama3-70B or GPT-4.
            # Local Llama3-8B might be slightly less stable for complex reasoning.
            self.llm = ChatOllama(model="llama3", base_url=self.ollama_url)

        # Config metrics to use our selected LLM
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ]
        
        for metric in self.metrics:
            metric.llm = self.llm

    async def evaluate_qna(
        self, 
        query: str, 
        answer: str, 
        context: List[str], 
        ground_truth: str = None
    ) -> Dict[str, float]:
        """
        Evaluates a single Q&A pair.
        Returns a dictionary of scores (0.0 to 1.0).
        """
        try:
            # Prepare format for RAGAS (Dataset object)
            data = {
                "question": [query],
                "answer": [answer],
                "contexts": [context],
            }
            if ground_truth:
                data["ground_truth"] = [ground_truth]
            
            dataset = Dataset.from_dict(data)
            
            # Execute evaluation
            result = evaluate(
                dataset,
                metrics=self.metrics,
            )
            
            return result.to_pandas().iloc[0].to_dict()
        except Exception as e:
            logger.error(f"[EVAL] Single evaluation failed: {e}")
            return {}

    async def run_batch_evaluation(self, eval_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Runs evaluation on a full test set (e.g., 50-100 questions).
        Returns aggregated scores and per-row results.
        """
        try:
            # Convert list of dicts to RAGAS Dataset
            # Expected keys: question, answer, contexts, ground_truth
            df = pd.DataFrame(eval_data)
            dataset = Dataset.from_pandas(df)
            
            result = evaluate(
                dataset,
                metrics=self.metrics,
            )
            
            summary = {
                "average_scores": result,
                "total_samples": len(eval_data),
                "timestamp": pd.Timestamp.now().isoformat()
            }
            return summary
        except Exception as e:
            logger.error(f"[EVAL] Batch evaluation failed: {e}")
            return {"error": str(e)}
