import os
import json
import logging
from typing import List, Dict
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from ragas.testset.generator import TestsetGenerator
from ragas.testset.evolutions import simple, reasoning, multi_context
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_rag_testset(chunks_path: str, output_path: str, count: int = 50):
    """
    Generates a synthetic RAG evaluation dataset from document chunks.
    Assumes chunks are stored in a JSON format or can be loaded as LangChain Docs.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # 1. Setup Generator LLM and Embeddings
    if openai_key:
        logger.info("Using OpenAI for Testset Generation")
        generator_llm = ChatOpenAI(model="gpt-4o")
        critic_llm = ChatOpenAI(model="gpt-4o")
        embeddings = OpenAIEmbeddings()
    else:
        logger.info("Using Local Ollama (llama3) for Testset Generation")
        generator_llm = ChatOllama(model="llama3")
        critic_llm = ChatOllama(model="llama3")
        embeddings = OllamaEmbeddings(model="llama3")

    # 2. Load Chunks
    # This is a placeholder for how you load your document fragments.
    # In this project, we can fetch from the SQLite DB or a local JSON export.
    with open(chunks_path, 'r') as f:
        chunks_data = json.load(f)
    
    from langchain.docstore.document import Document
    documents = [Document(page_content=c['content'], metadata={"source": c.get('filename', 'unknown')}) for c in chunks_data]

    # 3. Create Generator
    generator = TestsetGenerator.from_langchain(
        generator_llm,
        critic_llm,
        embeddings
    )

    # 4. Generate
    # We use different 'evolutions' to create complex reasoning/multi-context questions
    distributions = {
        simple: 0.5,
        reasoning: 0.25,
        multi_context: 0.25
    }

    logger.info(f"Generating {count} synthetic questions...")
    testset = generator.generate_with_langchain_docs(documents, test_size=count, distributions=distributions)
    
    # 5. Export to JSON
    test_df = testset.to_pandas()
    test_df.to_json(output_path, orient='records', indent=4)
    logger.info(f"Testset saved to {output_path}")

if __name__ == "__main__":
    # Example usage: 
    # python generate_testset.py --input path/to/chunks.json --output evaluation/eval_dataset.json
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSON file containing document chunks")
    parser.add_argument("--output", default="evaluation/eval_dataset.json", help="Output path")
    parser.add_argument("--count", type=int, default=50, help="Number of questions to generate")
    args = parser.parse_args()
    
    generate_rag_testset(args.input, args.output, args.count)
