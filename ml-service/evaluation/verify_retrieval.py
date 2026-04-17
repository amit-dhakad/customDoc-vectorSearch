import time
import argparse
import logging
import sys
import os

# Add parent directory to path to allow imports from app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.chunking import VectorManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_benchmark(collection_name: str, query: str):
    vm = VectorManager(host="localhost", port=8000) # Assumes local port mapping for testing
    
    print(f"\n{'='*60}")
    print(f"RAG RETRIEVAL BENCHMARK")
    print(f"Query: '{query}'")
    print(f"Collection: '{collection_name}'")
    print(f"{'='*60}\n")
    
    # 1. Dense Only
    start = time.perf_counter()
    dense_results = vm.retrieve_context(
        collection_name, query, n_results=4, search_type="dense", rerank=False
    )
    dense_time = (time.perf_counter() - start) * 1000
    print(f"[1] DENSE ONLY - {dense_time:.2f}ms")
    for i, res in enumerate(dense_results):
        print(f"  {i+1}. {res[:100]}...")
    
    # 2. Hybrid (Dense + BM25)
    start = time.perf_counter()
    hybrid_results = vm.retrieve_context(
        collection_name, query, n_results=4, search_type="hybrid", rerank=False
    )
    hybrid_time = (time.perf_counter() - start) * 1000
    print(f"\n[2] HYBRID SEARCH (RRF) - {hybrid_time:.2f}ms")
    for i, res in enumerate(hybrid_results):
        print(f"  {i+1}. {res[:100]}...")
        
    # 3. Hybrid + Reranking
    start = time.perf_counter()
    rerank_results = vm.retrieve_context(
        collection_name, query, n_results=4, search_type="hybrid", rerank=True
    )
    rerank_time = (time.perf_counter() - start) * 1000
    print(f"\n[3] HYBRID + CROSS-ENCODER RERANK - {rerank_time:.2f}ms")
    for i, res in enumerate(rerank_results):
        print(f"  {i+1}. {res[:100]}...")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f" - Reranking added {rerank_time - hybrid_time:.2f}ms overhead")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark RAG retrieval strategies.")
    parser.add_argument("--session", required=True, help="Collection name (session ID)")
    parser.add_argument("--query", required=True, help="Search query")
    
    args = parser.parse_args()
    try:
        run_benchmark(args.session, args.query)
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
