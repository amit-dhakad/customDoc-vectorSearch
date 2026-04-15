import httpx
import logging
from typing import List, Optional
from app.settings import settings

"""
app/services/rag_service.py — Retrieval-Augmented Generation Orchestrator.

CORE MISSION:
─────────────────────────────────────────────────────────────────────────────
This service is the 'Conductor' of the RAG pipeline. It manages the flow 
of data between the Chat UI, the ML Service (for Search), and the 
Direct Local LLM (for Generation).

PIPELINE STEPS:
────────────────────────────────────────────────────
1. RETRIEVE: Ask the ML Service to find context in ChromaDB for the user's query.
2. ORCHESTRATE: Combine the retrieved fragments with the original question.
3. GENERATE: Send the enriched request back to the ML Service's LLM engine.
"""

logger = logging.getLogger(__name__)

class RAGService:
    """
    Orchestrates communication with the ML-Service microservice 
    to provide context-aware AI responses.
    """
    
    def __init__(self):
        self.ml_service_url = settings.ML_SERVICE_URL

    async def generate_rag_answer(self, session_id: str, query: str, model: Optional[str] = None) -> str:
        """
        Executes the full RAG cycle.
        `model` overrides the default OLLAMA_MODEL from settings (e.g. 'llama3' or 'gemma').
        """
        # Resolve which model to use — frontend choice wins, else fall back to settings
        active_model = model if model else settings.OLLAMA_MODEL

        try:
            # 1. RETRIEVAL PHASE: Get context from the session's vector collection
            retrieve_url = f"{self.ml_service_url}/retrieve"
            retrieve_payload = {
                "collection_name": session_id,
                "query": query,
                "n_results": 4
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"RAG: Retrieving context for session {session_id}...")
                retrieve_resp = await client.post(retrieve_url, json=retrieve_payload)
                
                if retrieve_resp.status_code != 200:
                    logger.error(f"RAG: Retrieval failed ({retrieve_resp.status_code}): {retrieve_resp.text}")
                    context = []
                else:
                    context = retrieve_resp.json().get("context", [])
                
                logger.info(f"RAG: Found {len(context)} relevant fragments.")

            # 2. GENERATION PHASE: Call the host's Ollama instance with context
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
                
                if gen_resp.status_code != 200:
                    logger.error(f"RAG: Ollama generation failed ({gen_resp.status_code}): {gen_resp.text}")
                    return f"Sorry, I encountered an error while communicating with Ollama at {settings.OLLAMA_URL}. Please ensure Ollama is running on your host."
                
                response_data = gen_resp.json()
                answer = response_data.get("response", "").strip()
                
                if not answer:
                    logger.warning(f"RAG: Ollama returned empty response. Full payload: {response_data}")
                    return "The model returned an empty response. Please try rephrasing your question or check if the model is loaded in Ollama."
                
                logger.info(f"RAG: Answer generated successfully ({len(answer)} chars) using '{active_model}'.")
                return answer


        except Exception as e:
            logger.error(f"RAG: High-level orchestration failed: {e}")
            return f"I'm sorry, I encountered a technical error: {str(e)}"
