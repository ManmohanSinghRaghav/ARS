"""
ChromaDB-based Retrieval-Augmented Generation (RAG) for research verification.
Indexes grounding spans and enables semantic retrieval during verification phase.
"""

import os
from typing import List, Optional
from urllib.parse import urlparse

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
            # Use remote Chroma server.
            # If this is Chroma Cloud, prefer the first-party CloudClient API.
            parsed = urlparse(settings.CHROMA_HOST)
            host = parsed.netloc or parsed.path or settings.CHROMA_HOST
            ssl = (parsed.scheme == "https") or (settings.CHROMA_PORT == 443)

            headers = (
                {"X-Chroma-Token": settings.CHROMA_API_KEY}
                if settings.CHROMA_API_KEY
                else {}
            )

            is_chroma_cloud = "trychroma.com" in host or "trychroma.com" in settings.CHROMA_HOST
            if is_chroma_cloud:
                try:
                    _chroma_client = chromadb.CloudClient(
                        api_key=settings.CHROMA_API_KEY,
                        tenant=settings.CHROMA_TENANT,
                        database=settings.CHROMA_DATABASE,
                    )
                except Exception as e:
                    # Fallback to HTTP client when CloudClient isn't available in the installed chromadb build.
                    print(f"[RAG] Warning: CloudClient init failed ({e}); falling back to HttpClient")
                    _chroma_client = chromadb.HttpClient(
                        host=host,
                        port=settings.CHROMA_PORT,
                        ssl=ssl,
                        headers=headers,
                        tenant=settings.CHROMA_TENANT,
                        database=settings.CHROMA_DATABASE,
                    )
            else:
                # Generic remote HTTP Chroma
                _chroma_client = chromadb.HttpClient(
                    host=host,
                    port=settings.CHROMA_PORT,
                    ssl=ssl,
                    headers=headers,
                    tenant=settings.CHROMA_TENANT,
                    database=settings.CHROMA_DATABASE,
                )
        else:
            # Use ephemeral/in-memory client for local development
            chroma_settings = ChromaSettings(
                chroma_db_impl="duckdb",
                persist_directory=os.path.join(os.path.expanduser("~"), ".chroma"),
                anonymized_telemetry=False,
                allow_reset=True,
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
        from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
        from app.config import get_settings
        settings = get_settings()
        
        # Use Gemini embeddings to avoid unstable local model downloads in threading
        ef = GoogleGenerativeAiEmbeddingFunction(
            api_key=settings.GEMINI_API_KEY or "dummy-key-fallback",
            model_name="models/gemini-embedding-001",
        )
        
        # Get or create collection with metadata for filtering
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=ef,
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
        
        import hashlib
        
        for i, span in enumerate(grounding_spans):
            full_text = span.get("text", "")
            source = span.get("source", "unknown")
            url = span.get("url", "")
            
            # Chunking to prevent large payloads (max ~1500 chars/chunk)
            chunk_size = 1500
            for j in range(0, len(full_text), chunk_size):
                text = full_text[j:j+chunk_size]
                if len(text.strip()) < 50:
                    continue  # skip tiny artifacts
                
                # Generate a stable hash-based ID
                hash_input = f"{run_id}_{source}_{url}_{text}".encode("utf-8")
                doc_id = hashlib.md5(hash_input).hexdigest()
                
                documents.append(text)
                metadatas.append({
                    "run_id": run_id,
                    "topic": topic,
                    "source": source,
                    "url": url,
                    "chunk": j,
                })
                ids.append(doc_id)
        
        if documents:
            # Batch upserts to stay under payload limits (100 docs/req)
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                collection.upsert(
                    documents=documents[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size],
                    ids=ids[i:i+batch_size],
                )
            print(f"[RAG] Indexed {len(documents)} grounding spans in chunks for run {run_id}")
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
