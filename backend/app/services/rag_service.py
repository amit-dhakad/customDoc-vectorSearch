import httpx
import logging
import time
import traceback
from typing import List, Optional, Dict, Any
from app.settings import settings

"""
app/services/rag_service.py — Retrieval-Augmented Generation Orchestrator.

CORE MISSION:
─────────────────────────────────────────────────────────────────────────────
This service is the 'Conductor' of the RAG pipeline. It manages the flow 
of data between the Chat UI, the ML Service (for Search), and the 
Direct Local LLM (for Generation).
"""

logger = logging.getLogger(__name__)

class RAGService:
    """
    Orchestrates communication with the ML-Service microservice 
    to provide context-aware AI responses.
    """
    
    def __init__(self):
        self.ml_service_url = settings.ML_SERVICE_URL

    async def generate_rag_answer(
        self, 
        session_id: str, 
        query: str, 
        model: Optional[str] = None,
        search_type: str = "hybrid",
        n_results: int = 4,
        rerank: bool = True,
        enable_hyde: bool = False
    ) -> Dict[str, Any]:
        """
        Executes the full RAG cycle.
        Returns a dictionary with 'answer' and 'metrics'.
        """
        active_model = model if model else settings.OLLAMA_MODEL
        start_time = time.perf_counter()
        retrieval_latency = 0
        generation_latency = 0
        metrics = {
            "retrieval_latency_ms": 0,
            "generation_latency_ms": 0,
            "total_latency_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }

        try:
            # 0. HYDE PHASE: Generate a hypothetical answer to improve retrieval semantic matching
            retrieval_query = query
            if enable_hyde:
                try:
                    logger.info("RAG: [HyDE] Generating hypothetical intent...")
                    hyde_url = f"{settings.OLLAMA_URL}/api/generate"
                    hyde_prompt = f"Please write a short, scientific, and concise passage answering this specific question: {query}"
                    hyde_payload = {
                        "model": active_model,
                        "prompt": hyde_prompt,
                        "stream": False,
                        "options": {"num_predict": 100} # Keep it short for speed
                    }
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        h_resp = await client.post(hyde_url, json=hyde_payload)
                        if h_resp.status_code == 200:
                            retrieval_query = h_resp.json().get("response", query)
                            logger.info("RAG: [HyDE] Using synthetic answer for search expansion.")
                except Exception as e:
                    logger.warning(f"RAG: [HyDE] Failed, falling back to original query: {e}")

            # 1. RETRIEVAL PHASE: Get context from the session's vector collection
            retrieval_start = time.perf_counter()
            retrieve_url = f"{self.ml_service_url}/retrieve"
            retrieve_payload = {
                "collection_name": session_id,
                "query": retrieval_query,
                "n_results": n_results,
                "search_type": search_type,
                "rerank": rerank
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"RAG: Retrieving context for session {session_id}...")
                retrieve_resp = await client.post(retrieve_url, json=retrieve_payload)
                
                if retrieve_resp.status_code != 200:
                    logger.error(f"RAG: Retrieval failed ({retrieve_resp.status_code}): {retrieve_resp.text}")
                    context = []
                else:
                    data = retrieve_resp.json()
                    context = data.get("context", []) if isinstance(data, dict) else []
                
                retrieval_latency = (time.perf_counter() - retrieval_start) * 1000
                logger.info(f"RAG: Found {len(context)} relevant fragments in {retrieval_latency:.2f}ms.")

            # 2. GENERATION PHASE: Call the host's Ollama instance with context
            generation_start = time.perf_counter()
            generate_url = f"{settings.OLLAMA_URL}/api/generate"
            
            context_str = "\n\n".join(context) if context else "No relevant document context found."
            
            system_prompt = (
                "You are a professional AI Assistant. Use the following document fragments to answer the user's question. "
                "If the context is insufficient, explain that based on the documents provided you cannot provide a full answer, "
                "but offer a general answer if appropriate."
            )
            
            full_prompt = f"CONTEXT:\n{context_str}\n\nQUESTION: {query}\n\nANSWER:"

            generate_payload = {
                "model": active_model,
                "system": system_prompt,
                "prompt": full_prompt,
                "stream": False
            }
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.info(f"RAG: Generating answer via Ollama model='{active_model}'...")
                gen_resp = await client.post(generate_url, json=generate_payload)
                
                generation_latency = (time.perf_counter() - generation_start) * 1000
                
                if gen_resp.status_code != 200:
                    logger.error(f"RAG: Ollama generation failed ({gen_resp.status_code}): {gen_resp.text}")
                    return {
                        "answer": f"Sorry, I encountered an error while communicating with Ollama at {settings.OLLAMA_URL}.",
                        "metrics": metrics
                    }
                
                response_data = gen_resp.json()
                if not isinstance(response_data, dict):
                    logger.error(f"RAG: Unexpected Ollama response format: {type(response_data)}")
                    return { "answer": "Unexpected AI response format.", "metrics": metrics }

                answer = response_data.get("response", "").strip()
                
                # Extract Ollama native metrics
                metrics["prompt_tokens"] = response_data.get("prompt_eval_count", 0)
                metrics["completion_tokens"] = response_data.get("eval_count", 0)
                
                if not answer:
                    logger.warning(f"RAG: Ollama returned empty response. Full payload: {response_data}")
                    return { "answer": "The model returned an empty response.", "metrics": metrics }
                
                # 3. EVALUATION PHASE (Async/Background-style)
                # We compute RAGAS scores immediately for real-time metrics.
                eval_scores = {}
                try:
                    eval_url = f"{self.ml_service_url}/evaluate"
                    eval_payload = {
                        "query": query,
                        "answer": answer,
                        "context": context
                    }
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        logger.info("RAG: Evaluating quality scores...")
                        eval_resp = await client.post(eval_url, json=eval_payload)
                        if eval_resp.status_code == 200:
                            eval_scores = eval_resp.json().get("scores", {})
                except Exception as eval_err:
                    logger.warning(f"RAG: Quality evaluation skipped: {eval_err}")

                total_latency = (time.perf_counter() - start_time) * 1000
                metrics["retrieval_latency_ms"] = int(retrieval_latency)
                metrics["generation_latency_ms"] = int(generation_latency)
                metrics["total_latency_ms"] = int(total_latency)
                
                return {
                    "answer": answer,
                    "metrics": metrics,
                    "scores": eval_scores
                }

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"RAG: High-level orchestration failed: {error_msg}\n{tb}")
            return {
                "answer": f"I'm sorry, I encountered a technical error: {error_msg}. Please check the backend logs for details.",
                "metrics": metrics,
                "scores": {}
            }
