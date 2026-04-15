"""
Pytest configuration for the ARS backend test suite.
Defines fixtures, markers, and global test configuration.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


# ── Pytest Configuration ──
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "modal: mark test as Modal-related"
    )


# ── Environment Fixtures ──
@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["REDIS_URL"] = ""
    os.environ["CHROMA_ENABLED"] = "false"
    yield
    # Cleanup


@pytest.fixture
def mock_db():
    """Fixture providing mock Firestore database."""
    db = MagicMock()
    collection = MagicMock()
    doc_ref = MagicMock()
    
    db.collection.return_value = collection
    collection.document.return_value = doc_ref
    
    return db


@pytest.fixture
def mock_redis():
    """Fixture providing mock Redis client."""
    redis = MagicMock()
    redis.ping.return_value = True
    redis.get.return_value = None
    redis.set.return_value = True
    redis.setex.return_value = True
    
    return redis


@pytest.fixture
def mock_chroma():
    """Fixture providing mock Chroma client."""
    client = MagicMock()
    collection = MagicMock()
    
    client.get_or_create_collection.return_value = collection
    collection.query.return_value = {
        "ids": [["doc1", "doc2", "doc3"]],
        "documents": [["Content 1", "Content 2", "Content 3"]],
        "distances": [[0.1, 0.2, 0.3]]
    }
    
    return client


@pytest.fixture
def mock_user():
    """Fixture providing mock authenticated user."""
    from app.auth.dependencies import User
    return User(
        id="test_user_123",
        email="test@example.com",
        username="testuser",
        role="user"
    )


@pytest.fixture
def mock_admin_user():
    """Fixture providing mock admin user."""
    from app.auth.dependencies import User
    return User(
        id="test_admin_123",
        email="admin@example.com",
        username="admin",
        role="admin"
    )


# ── Data Fixtures ──
@pytest.fixture
def sample_run_data():
    """Fixture providing sample run data."""
    return {
        "id": "run_test_123",
        "user_id": "user_123",
        "topic": "Novel AI Architecture",
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "Transformer models with adaptive attention mechanisms improve efficiency.",
        "generated_code": "import torch\nmodel = AdaptiveTransformer()\n",
        "execution_output": "Model accuracy: 0.95",
        "paper_markdown": "# Research Paper\n\n## Abstract\nThis paper proposes...",
        "summary_json": {
            "novelty_score": 8.5,
            "feasibility_score": 8.0,
            "impact_score": 7.5,
            "domain": "Machine Learning"
        },
        "error_message": ""
    }


@pytest.fixture
def sample_llm_config():
    """Fixture providing sample LLM configuration."""
    return {
        "vibe": "Deep Academic",
        "llm_backend": "ollama",
        "model": "neural-chat",
        "temperature": 0.7,
        "max_tokens": 2000,
        "top_p": 0.95,
        "commands": "Focus on novel applications"
    }


@pytest.fixture
def sample_search_result():
    """Fixture providing sample search results."""
    return {
        "arxiv_papers": [
            {
                "id": "2301.12345",
                "title": "Novel Efficient Transformers",
                "summary": "We propose...",
                "published": "2023-01-15"
            },
            {
                "id": "2301.12346",
                "title": "Attention Mechanisms Revisited",
                "summary": "...",
                "published": "2023-01-16"
            },
            {
                "id": "2301.12347",
                "title": "Scalable AI",
                "summary": "...",
                "published": "2023-01-17"
            }
        ],
        "web_results": [
            {
                "url": "https://example.com/1",
                "title": "AI Research Blog",
                "content": "..."
            },
            {
                "url": "https://example.com/2",
                "title": "ML Tutorial",
                "content": "..."
            },
            {
                "url": "https://example.com/3",
                "title": "Paper Summary",
                "content": "..."
            }
        ]
    }


@pytest.fixture
def sample_generated_code():
    """Fixture providing sample generated Python code."""
    return """
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def run_experiment():
    X = np.random.randn(100, 10)
    y = np.random.randint(0, 2, 100)
    
    clf = RandomForestClassifier(n_estimators=100)
    clf.fit(X, y)
    
    score = clf.score(X, y)
    return {"accuracy": float(score)}

if __name__ == "__main__":
    results = run_experiment()
    print(results)
"""


# ── Mock Patches ──
@pytest.fixture
def patch_firebase():
    """Fixture to patch Firebase initialization."""
    with patch("firebase_admin.initialize_app"):
        with patch("firebase_admin.firestore.client"):
            yield


@pytest.fixture
def patch_litellm():
    """Fixture to patch LiteLLM."""
    with patch("litellm.completion"):
        yield


@pytest.fixture
def patch_tavily():
    """Fixture to patch Tavily search."""
    with patch("tavily.TavilyClient"):
        yield


@pytest.fixture
def patch_arxiv():
    """Fixture to patch ArXiv client."""
    with patch("arxiv.Client"):
        yield


# ── Helper Fixtures ──
@pytest.fixture
def capture_stdout(monkeypatch):
    """Fixture to capture stdout."""
    import io
    import sys
    
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    
    return captured


@pytest.fixture
def temp_file(tmp_path):
    """Fixture providing a temporary file."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test content")
    return file_path


# ── Test Markers ──
@pytest.fixture
def mark_unit():
    """Decorator to mark test as unit test."""
    return pytest.mark.unit


@pytest.fixture
def mark_integration():
    """Decorator to mark test as integration test."""
    return pytest.mark.integration


@pytest.fixture
def mark_slow():
    """Decorator to mark test as slow."""
    return pytest.mark.slow


# ── Performance Fixtures ──
@pytest.fixture
def performance_timer():
    """Fixture providing a performance timer."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, *args):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.end_time is None:
                return time.time() - self.start_time
            return self.end_time - self.start_time
    
    return Timer


# ── Cleanup ──
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Any cleanup code here
    from unittest.mock import patch
    patch.stopall()
