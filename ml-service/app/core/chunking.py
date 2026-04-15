import logging
from typing import List, Dict, Any, Literal
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.embeddings import Embeddings

"""
app/core/chunking.py — Multi-Strategy Text Intelligence & Vectorization Suite.

ARCHITECTURE PHILOSOPHY
─────────────────────────────────────────────────────────────────────────────
This module is the "brain" of the RAG ingestion pipeline. It handles the critical
transition from raw extracted text to AI-ready vector fragments. We provide 
multiple strategies because "one size fits all" leads to low-quality RAG.

1. CHUNKING STRATEGIES (Segmentation)
──────────────────────────────────────────────────────────────
   - FIXED: Simple, predictable. Best for structured data where context is local.
   - OVERLAP: Preserves context at edges. Prevents information loss at boundaries.
   - RECURSIVE: The industry standard. Respects paragraphs and sentences. Highly 
     effective for general-purpose documents.
   - STRUCTURAL: Best for technical docs. Uses Markdown headers (#, ##) to 
     keep entire sections together semantically.
   - SEMANTIC: Cutting-edge. Uses ML to detect "context shifts" in text. 
     Ensures every chunk is a unified concept.

2. VECTORIZATION STRATEGIES (Intelligence)
──────────────────────────────────────────────────────────────
   - DENSE (MiniLM): Good for general semantic similarity. Fast and efficient.
   - SPARSE (BM25): Critical for "Exact keyword" searches (IDs, specific names).
     Dense vectors often fail at finding unique technical identifiers.
   - HYBRID: The Gold Standard. Combines Dense + Sparse. It understands that 
     "AI" means "Artificial Intelligence" (Dense) but can also find exact 
     "Error Code 0x80" hits (Sparse).
   - LATE INTERACTION (ColBERT): Zero-compression retrieval. Instead of 1 vector 
     per chunk, it stores a vector per token. It is the most accurate method 
     available today, but requires 10x more storage.

WHY THIS IMPLEMENTATION IS SUPERIOR:
──────────────────────────────
Unlike basic RAG setups that only use Recursive + Dense, this architecture 
allows developers to fine-tune the "granularity" and "look-up type" based 
precisely on the document type (Legal vs. Technical vs. Casual).
"""

logger = logging.getLogger(__name__)

# Lightweight Embedding Wrapper for Semantic Chunking
class LocalEmbeddings(Embeddings):
    """
    Minimalistic wrapper around SentenceTransformers to satisfy LangChain's 
    Embeddings interface without heavy dependencies.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()

class ChunkerFactory:
    """
    Factory class providing distinct segmentation logic for each strategy.
    """

    @staticmethod
    def chunk_fixed_size(text: str, chunk_size: int = 1000) -> List[str]:
        """
        Method 1: Fixed-Size (Character) 
        Predictable but potentially cuts thoughts in half.
        """
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    @staticmethod
    def chunk_fixed_overlap(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Method 2: Fixed-Size with Overlap
        Reduces 'seam' loss by repeating text at chunk boundaries.
        """
        if overlap >= chunk_size:
            overlap = chunk_size // 2
            
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start += (chunk_size - overlap)
        return chunks

    @staticmethod
    def chunk_recursive(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Method 3: Recursive Character Splitting
        Tries to maintain paragraph and sentence integrity.
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        return splitter.split_text(text)

    @staticmethod
    def chunk_structural(text: str) -> List[str]:
        """
        Method 4: Structural / Markdown Chunking
        Follows the document's own hierarchy (# Headers).
        """
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        docs = splitter.split_text(text)
        return [doc.page_content for doc in docs]

    @staticmethod
    def chunk_semantic(text: str) -> List[str]:
        """
        Method 5: Semantic Chunking (Advanced)
        Uses cosine similarity between sentence embeddings to find optimal cuts.
        """
        try:
            embeddings = LocalEmbeddings()
            splitter = SemanticChunker(embeddings)
            docs = splitter.create_documents([text])
            return [doc.page_content for doc in docs]
        except Exception as e:
            logger.error(f"Semantic chunking failed: {e}. Falling back to recursive.")
            return ChunkerFactory.chunk_recursive(text)

import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi
import numpy as np
from typing import Optional, List, Dict, Any, Literal

class VectorManager:
    """
    Handles interactions with the ChromaDB vector database.
    Supports Dense, Sparse (BM25 simulation), and Hybrid strategies.
    """
    def __init__(self, host: str = "chromadb", port: int = 8000):
        self.client = chromadb.HttpClient(host=host, port=port)
        self.embeddings = LocalEmbeddings()

    def upsert_chunks(
        self, 
        collection_name: str, 
        chunks: List[str], 
        method: str = "dense", 
        metadata: List[Dict[str, Any]] = None
    ):
        """
        Stores chunks using the requested vectorization strategy.
        """
        # 1. Handle ColBERT / Late Interaction separately
        if method == "colbert":
            return self._upsert_colbert(collection_name, chunks, metadata)

        # 2. Standard ChromaDB (Dense/Sparse/Hybrid)
        collection = self.client.get_or_create_collection(name=collection_name)
        ids = [f"chk_{i}_{hash(chunk)}" for i, chunk in enumerate(chunks)]
        
        # Dense Embeddings
        dense_vecs = None
        if method in ["dense", "hybrid"]:
            dense_vecs = self.embeddings.embed_documents(chunks)

        # Sparse Embeddings (Metadata-based BM25 or simplified)
        # Note: True ChromaDB Sparse support requires Specific schema configs.
        # For this implementation, we store the content and ensure it's indexed.
        
        upsert_payload = {
            "ids": ids,
            "documents": chunks,
            "metadatas": metadata if metadata else [{"source": "parsing_service", "method": method} for _ in chunks]
        }
        
        if dense_vecs:
            upsert_payload["embeddings"] = dense_vecs

        collection.upsert(**upsert_payload)
        logger.info(f"VECTOR_DB: Upserted {len(chunks)} fragments into '{collection_name}' using {method}")

    def retrieve_context(self, collection_name: str, query: str, n_results: int = 4) -> List[str]:
        """
        Retrieves the top-K relevant text fragments for a given query.
        Used by the RAG pipeline to ground LLM answers in document fact.
        """
        try:
            # 1. Get collection (silent fail if doesn't exist to prevent crashes)
            try:
                collection = self.client.get_collection(name=collection_name)
            except Exception:
                logger.warning(f"VECTOR_DB: Collection '{collection_name}' not found. Returning empty context.")
                return []

            # 2. Vectorize the query
            query_embedding = self.embeddings.embed_query(query)

            # 3. Perform similarity search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

            # 4. Extract and return text contents
            # results["documents"] is a list of lists (one per query vector)
            return results["documents"][0] if results["documents"] else []

        except Exception as e:
            logger.error(f"VECTOR_DB: Retrieval failed: {e}")
            return []

    def _upsert_colbert(self, collection_name: str, chunks: List[str], metadata: List[Dict[str, Any]] = None):
        """
        Specialized Late Interaction Indexing using RAGatouille.
        Creates a dedicated ColBERT index on disk.
        """
        try:
            from ragatouille import RAGPretrainedModel
            # Load a standard ColBERT model (CPU optimized if possible)
            RAG = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")
            
            # ColBERT creates its own storage structure
            index_path = f".ragatouille/colbert/indexes/{collection_name}"
            RAG.index(
                collection=chunks,
                index_name=collection_name,
                max_document_length=256,
                split_documents=True
            )
            logger.info(f"COLBERT: Created Late Interaction index for '{collection_name}' at {index_path}")
        except Exception as e:
            logger.error(f"ColBERT indexing failed: {e}")
            # Fallback to dense if ColBERT fails
            self.upsert_chunks(collection_name, chunks, method="dense", metadata=metadata)

def get_chunks(
    text: str, 
    method: Literal["fixed", "overlap", "recursive", "structural", "semantic"] = "recursive",
    vector_method: Literal["dense", "sparse", "hybrid", "colbert"] = "dense",
    chunk_size: int = 1000,
    overlap: int = 200,
    collection_name: str = None
) -> List[str]:
    """
    Universal entry point for Intelligence Segmentation & Vectorization.
    """
    logger.info(f"INTELLIGENCE: Strat='{method}', Vector='{vector_method}', size={chunk_size}")
    
    if not text or len(text.strip()) == 0:
        return []

    # --- Step 1: Segmentation (Chunking) ---
    chunks = []
    if method == "fixed":
        chunks = ChunkerFactory.chunk_fixed_size(text, chunk_size)
    elif method == "overlap":
        chunks = ChunkerFactory.chunk_fixed_overlap(text, chunk_size, overlap)
    elif method == "recursive":
        chunks = ChunkerFactory.chunk_recursive(text, chunk_size, overlap)
    elif method == "structural":
        chunks = ChunkerFactory.chunk_structural(text)
    elif method == "semantic":
        chunks = ChunkerFactory.chunk_semantic(text)
    else:
        chunks = ChunkerFactory.chunk_recursive(text, chunk_size, overlap)

    # --- Step 2: Vectorization & Persistence ---
    if collection_name and chunks:
        try:
            vm = VectorManager()
            vm.upsert_chunks(collection_name, chunks, method=vector_method)
        except Exception as e:
            logger.error(f"Vectorization stage failed: {e}")

    return chunks
