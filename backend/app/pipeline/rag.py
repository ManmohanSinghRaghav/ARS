"""
ChromaDB-based Retrieval-Augmented Generation (RAG) for research verification.
Indexes grounding spans and enables semantic retrieval during verification phase.
"""

import os
from typing import List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

# Global Chroma client
_chroma_client = None
_chroma_collection = None


def get_chroma_client():
    """Initialize or return cached Chroma client."""
    global _chroma_client
    
    if _chroma_client is not None:
        return _chroma_client
    
    settings = get_settings()
    if not settings.CHROMA_ENABLED:
        return None
    
    try:
        if settings.CHROMA_HOST:
            # Use remote Chroma server
            _chroma_client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                headers={"Authorization": f"Bearer {settings.CHROMA_API_KEY}"} if settings.CHROMA_API_KEY else {}
            )
        else:
            # Use ephemeral/in-memory client for local development
            chroma_settings = ChromaSettings(
                chroma_db_impl="duckdb",
                persist_directory=os.path.join(os.path.expanduser("~"), ".chroma"),
                anonymized_telemetry=False,
                allow_reset=True
            )
            _chroma_client = chromadb.Client(chroma_settings)
        
        print("[RAG] Chroma client initialized successfully")
        return _chroma_client
    except Exception as e:
        print(f"[RAG] Warning: Failed to initialize Chroma client: {e}")
        return None


def get_rag_collection(collection_name: str = "research_grounding_spans"):
    """Get or create a Chroma collection for storing grounding spans."""
    global _chroma_collection
    
    client = get_chroma_client()
    if client is None:
        return None
    
    try:
        # Get or create collection with metadata for filtering
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        _chroma_collection = collection
        return collection
    except Exception as e:
        print(f"[RAG] Warning: Failed to get/create collection: {e}")
        return None


def index_grounding_spans(run_id: str, topic: str, grounding_spans: List[dict]):
    """
    Index research grounding spans into Chroma for semantic retrieval.
    
    Args:
        run_id: Unique identifier for the research run
        topic: Research topic for context
        grounding_spans: List of dicts with keys: {'text': str, 'source': str, 'url': str}
    """
    collection = get_rag_collection()
    if collection is None:
        print(f"[RAG] ChromaDB not configured; skipping span indexing for run {run_id}")
        return
    
    try:
        documents = []
        metadatas = []
        ids = []
        
        for i, span in enumerate(grounding_spans):
            doc_id = f"{run_id}_span_{i}"
            documents.append(span.get("text", ""))
            metadatas.append({
                "run_id": run_id,
                "topic": topic,
                "source": span.get("source", "unknown"),
                "url": span.get("url", ""),
            })
            ids.append(doc_id)
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            print(f"[RAG] Indexed {len(documents)} grounding spans for run {run_id}")
    except Exception as e:
        print(f"[RAG] Warning: Failed to index grounding spans: {e}")


def retrieve_grounding_spans(query: str, run_id: Optional[str] = None, top_k: int = 5) -> List[dict]:
    """
    Retrieve relevant grounding spans for a query using semantic search.
    
    Args:
        query: User/verification query
        run_id: Optional filter to retrieve spans only from a specific run
        top_k: Number of top results to return
    
    Returns:
        List of dicts with keys: {'text', 'source', 'url', 'distance'}
    """
    collection = get_rag_collection()
    if collection is None:
        return []
    
    try:
        where_filter = {"run_id": {"$eq": run_id}} if run_id else None
        
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter if where_filter else None,
        )
        
        if not results or not results.get("documents") or not results["documents"][0]:
            return []
        
        retrieved_spans = []
        for doc, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0] if results.get("distances") else [0] * len(results["documents"][0])
        ):
            retrieved_spans.append({
                "text": doc,
                "source": metadata.get("source", "unknown"),
                "url": metadata.get("url", ""),
                "distance": distance,
            })
        
        return retrieved_spans
    except Exception as e:
        print(f"[RAG] Warning: Failed to retrieve grounding spans: {e}")
        return []


def clear_run_spans(run_id: str):
    """Delete all grounding spans for a specific run."""
    collection = get_rag_collection()
    if collection is None:
        return
    
    try:
        collection.delete(
            where={"run_id": {"$eq": run_id}}
        )
        print(f"[RAG] Cleared grounding spans for run {run_id}")
    except Exception as e:
        print(f"[RAG] Warning: Failed to clear run spans: {e}")
