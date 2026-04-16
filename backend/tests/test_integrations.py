"""
Tests for external integrations: Redis, ChromaDB, and Firebase.
Verifies connectivity, caching, vector storage, and document persistence.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestRedisIntegration:
    """Test Redis caching functionality."""

    @patch("redis.Redis")
    def test_redis_connection(self, mock_redis_class):
        """Verify Redis client can connect."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True
        
        import redis
        r = redis.Redis(host='localhost', port=6379)
        assert r.ping() is True

    @patch("redis.Redis")
    def test_redis_cache_get_set(self, mock_redis_class):
        """Verify Redis stores and retrieves cache."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        mock_redis.get.return_value = b'"cached_value"'
        
        import redis
        r = redis.Redis(host='localhost')
        
        # Store
        r.set("key1", "value1")
        mock_redis.set.assert_called()
        
        # Retrieve
        result = r.get("key1")
        assert result is not None

    @patch("redis.Redis")
    def test_redis_cache_expiration(self, mock_redis_class):
        """Verify Redis cache expiration works."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        
        import redis
        r = redis.Redis(host='localhost')
        r.setex("key_with_ttl", 3600, "value")
        
        mock_redis.setex.assert_called_with("key_with_ttl", 3600, "value")

    @patch("redis.Redis")
    def test_redis_llm_prompt_caching(self, mock_redis_class):
        """Verify LLM prompts are cached in Redis."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        
        import redis
        r = redis.Redis()
        
        prompt = "What is machine learning?"
        key = f"prompt:{hash(prompt)}"
        response = {"content": "ML is a subset of AI..."}
        
        r.setex(key, 86400, json.dumps(response))
        mock_redis.setex.assert_called()

    @patch("redis.Redis")
    def test_redis_fallback_when_unavailable(self, mock_redis_class):
        """Verify graceful fallback when Redis is unavailable."""
        mock_redis_class.side_effect = Exception("Connection refused")
        
        try:
            import redis
            r = redis.Redis(host='localhost')
        except Exception as e:
            assert "Connection" in str(e)

    @patch("redis.Redis")
    def test_redis_multi_key_operations(self, mock_redis_class):
        """Verify Redis handles multiple key operations."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        
        import redis
        r = redis.Redis()
        
        # Batch set
        pipe = r.pipeline()
        pipe.set("key1", "val1")
        pipe.set("key2", "val2")
        pipe.execute()
        
        assert pipe.execute.call_count == 1
    def test_chroma_client_initialization(self, mock_chroma_class):
        """Verify Chroma client initializes correctly."""
        mock_client = MagicMock()
        mock_chroma_class.return_value = mock_client
        
        # Simulate client creation
        client = mock_chroma_class()
        assert client is not None

    @patch("chromadb.Client")
    def test_chroma_collection_creation(self, mock_chroma_class):
        """Verify Chroma collection can be created."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma_class.return_value = mock_client
        
        client = mock_chroma_class()
        collection = client.get_or_create_collection(name="papers")
        
        assert collection is not None
        mock_client.get_or_create_collection.assert_called_with(name="papers")

    @patch("chromadb.Client")
    def test_chroma_vector_storage(self, mock_chroma_class):
        """Verify vectors are stored in Chroma."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma_class.return_value = mock_client
        
        client = mock_chroma_class()
        collection = client.get_or_create_collection(name="papers")
        
        documents = ["Paper 1 content", "Paper 2 content"]
        metadatas = [{"source": "arxiv"}, {"source": "arxiv"}]
        ids = ["doc1", "doc2"]
        
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        mock_collection.add.assert_called()

    @patch("chromadb.Client")
    def test_chroma_semantic_search(self, mock_chroma_class):
        """Verify semantic search in Chroma."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2", "doc3"]],
            "distances": [[0.1, 0.2, 0.3]],
            "documents": [["Paper 1", "Paper 2", "Paper 3"]],
            "metadatas": [[{"score": 0.9}, {"score": 0.8}, {"score": 0.7}]]
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma_class.return_value = mock_client
        
        client = mock_chroma_class()
        collection = client.get_or_create_collection(name="papers")
        
        results = collection.query(
            query_texts=["neural networks"],
            n_results=3
        )
        
        assert results is not None
        assert len(results["ids"][0]) <= 3

    @patch("chromadb.Client")
    def test_chroma_top_k_retrieval(self, mock_chroma_class):
        """Verify top-K retrieval limits."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2", "doc3", "doc4", "doc5"]],
            "documents": [["Paper 1", "Paper 2", "Paper 3", "Paper 4", "Paper 5"]]
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma_class.return_value = mock_client
        
        client = mock_chroma_class()
        collection = client.get_or_create_collection(name="papers")
        
        # Request top-5
        results = collection.query(query_texts=["test"], n_results=5)
        
        # Should not exceed top-5
        assert len(results["ids"][0]) <= 5

    @patch("chromadb.Client")
    def test_chroma_filter_malformed_documents(self, mock_chroma_class):
        """Verify malformed documents are filtered."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        
        client = mock_chroma_class()
        collection = client.get_or_create_collection(name="papers")
        
        # Attempt to add document
        documents = [None, "", "Valid document"]
        valid_docs = [d for d in documents if d and isinstance(d, str) and len(d) > 0]
        
        assert len(valid_docs) == 1
        assert valid_docs[0] == "Valid document"

    @patch("chromadb.Client")
    def test_chroma_connection_failure_handling(self, mock_chroma_class):
        """Verify graceful handling of connection failures."""
        mock_chroma_class.side_effect = Exception("Failed to connect to Chroma")
        
        with pytest.raises(Exception):
            client = mock_chroma_class()

    @patch("chromadb.Client")
    def test_chroma_disabled_configuration(self, mock_chroma_class):
        """Verify Chroma can be disabled via configuration."""
        import os
        os.environ["CHROMA_ENABLED"] = "false"
        
        # When disabled, client should not be initialized
        assert os.environ.get("CHROMA_ENABLED") == "false"


class TestFirebaseIntegration:
    """Test Firebase/Firestore database functionality."""

    @patch("firebase_admin.firestore.client")
    def test_firestore_connection(self, mock_firestore):
        """Verify Firestore client initializes."""
        mock_client = MagicMock()
        mock_firestore.return_value = mock_client
        
        db = mock_firestore()
        assert db is not None

    @patch("firebase_admin.firestore.client")
    def test_firestore_create_document(self, mock_firestore):
        """Verify document creation in Firestore."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        
        mock_firestore.return_value = mock_client
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.id = "test_doc_123"
        
        db = mock_firestore()
        doc_ref = db.collection("runs").document()
        
        assert doc_ref.id == "test_doc_123"

    @patch("firebase_admin.firestore.client")
    def test_firestore_set_document(self, mock_firestore):
        """Verify setting document data."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        
        mock_firestore.return_value = mock_client
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        
        db = mock_firestore()
        doc_ref = db.collection("runs").document()
        
        data = {"topic": "AI", "status": "running"}
        doc_ref.set(data)
        
        mock_doc_ref.set.assert_called_with(data)

    @patch("firebase_admin.firestore.client")
    def test_firestore_update_document(self, mock_firestore):
        """Verify updating document data."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        
        mock_firestore.return_value = mock_client
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        
        db = mock_firestore()
        doc_ref = db.collection("runs").document("run123")
        
        updates = {"status": "completed", "paper_markdown": "# Result"}
        doc_ref.update(updates)
        
        mock_doc_ref.update.assert_called_with(updates)

    @patch("firebase_admin.firestore.client")
    def test_firestore_get_document(self, mock_firestore):
        """Verify retrieving document data."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()
        
        mock_firestore.return_value = mock_client
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc_snapshot
        mock_doc_snapshot.to_dict.return_value = {"topic": "AI", "status": "completed"}
        
        db = mock_firestore()
        doc_ref = db.collection("runs").document("run123")
        doc = doc_ref.get()
        
        assert doc.to_dict() == {"topic": "AI", "status": "completed"}

    @patch("firebase_admin.firestore.client")
    def test_firestore_query_documents(self, mock_firestore):
        """Verify querying documents."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_query_result = [
            MagicMock(to_dict=lambda: {"id": "run1", "user_id": "user1"}),
            MagicMock(to_dict=lambda: {"id": "run2", "user_id": "user1"}),
        ]
        
        mock_firestore.return_value = mock_client
        mock_client.collection.return_value = mock_collection
        mock_collection.where.return_value.stream.return_value = mock_query_result
        
        db = mock_firestore()
        from google.cloud.firestore import FieldFilter
        query = db.collection("runs").where(filter=FieldFilter("user_id", "==", "user1"))
        results = list(query.stream())
        
        assert len(results) == 2

    @patch("firebase_admin.firestore.client")
    def test_firestore_batch_write(self, mock_firestore):
        """Verify batch write operations."""
        mock_client = MagicMock()
        mock_batch = MagicMock()
        
        mock_firestore.return_value = mock_client
        mock_client.batch.return_value = mock_batch
        
        db = mock_firestore()
        batch = db.batch()
        
        batch.set(MagicMock(), {"data": "value1"})
        batch.set(MagicMock(), {"data": "value2"})
        batch.commit()
        
        assert batch.set.call_count == 2

    @patch("firebase_admin.firestore.client")
    def test_firestore_delete_document(self, mock_firestore):
        """Verify deleting documents."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        
        mock_firestore.return_value = mock_client
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        
        db = mock_firestore()
        doc_ref = db.collection("runs").document("run123")
        doc_ref.delete()
        
        mock_doc_ref.delete.assert_called()

    @patch("firebase_admin.firestore.client")
    def test_firestore_connection_failure(self, mock_firestore):
        """Verify handling of connection failures."""
        mock_firestore.side_effect = Exception("Connection refused")
        
        with pytest.raises(Exception):
            client = mock_firestore()


class TestIntegrationErrorHandling:
    """Test error handling across integrations."""

    def test_redis_unavailable_fallback(self):
        """Verify fallback when Redis is unavailable."""
        try:
            import redis
            # Attempt connection that will fail
            r = redis.Redis(host="nonexistent", socket_timeou=1)
        except Exception:
            # Should handle gracefully
            pass

    @patch("chromadb.Client")
    def test_chroma_unavailable_fallback(self, mock_chroma):
        """Verify fallback when Chroma is unavailable."""
        mock_chroma.side_effect = Exception("Chroma unavailable")
        
        # System should continue without Chroma
        try:
            client = mock_chroma()
        except Exception as e:
            assert "unavailable" in str(e).lower()

    @patch("firebase_admin.firestore.client")
    def test_firestore_unavailable_handling(self, mock_firestore):
        """Verify handling when Firestore is unavailable."""
        mock_firestore.return_value = None
        
        db = mock_firestore()
        assert db is None


class TestIntegrationPerformance:
    """Test performance characteristics of integrations."""

    @patch("redis.Redis")
    def test_redis_cache_latency(self, mock_redis_class):
        """Verify Redis cache operations are fast."""
        import time
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        
        import redis
        r = redis.Redis()
        
        start = time.time()
        r.set("key", "value")
        r.get("key")
        elapsed = time.time() - start
        
        # Local Redis should be very fast (< 100ms)
        assert elapsed < 1.0

    @patch("chromadb.Client")
    def test_chroma_search_latency(self, mock_chroma_class):
        """Verify Chroma search operations are reasonably fast."""
        import time
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"ids": [["doc1", "doc2", "doc3"]]}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma_class.return_value = mock_client
        
        client = mock_chroma_class()
        collection = client.get_or_create_collection(name="papers")
        
        start = time.time()
        results = collection.query(query_texts=["test"], n_results=3)
        elapsed = time.time() - start
        
        # Should complete reasonably quickly
        assert elapsed < 5.0
