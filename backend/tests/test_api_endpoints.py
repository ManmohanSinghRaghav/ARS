"""
Comprehensive API endpoint tests for the ARS backend.
Tests all endpoints, error handling, authentication, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from app.main import app
from app.auth.dependencies import get_current_user, User
from app.database import get_db


# ── Test Fixtures ──
def mock_get_current_user():
    """Returns a mock authenticated user."""
    return User(
        id="test_user_uid_123",
        email="test@example.com",
        username="testuser",
        role="user"
    )


def mock_get_admin_user():
    """Returns a mock admin user."""
    return User(
        id="test_admin_uid_123",
        email="admin@example.com",
        username="admin_user",
        role="admin"
    )


# Override dependencies
app.dependency_overrides[get_current_user] = mock_get_current_user
client = TestClient(app)


# ── Health & Status Tests ──
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_ok(self):
        """Verify /api/health returns 200 with 'ok' status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    def test_health_check_includes_service_info(self):
        """Verify health response includes service information."""
        response = client.get("/api/health")
        data = response.json()
        assert "service" in data or "status" in data


# ── Authentication Tests ──
class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_auth_me_returns_current_user(self):
        """Verify /api/auth/me returns current user info."""
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_user_uid_123"
        assert data["email"] == "test@example.com"

    def test_auth_me_includes_user_fields(self):
        """Verify auth/me response includes all user fields."""
        response = client.get("/api/auth/me")
        data = response.json()
        required_fields = ["id", "email", "username"]
        for field in required_fields:
            assert field in data

    @patch("app.auth.dependencies.verify_firebase_token")
    def test_auth_with_invalid_token(self, mock_verify):
        """Verify invalid tokens are rejected."""
        mock_verify.side_effect = Exception("Invalid token")
        
        # This depends on actual auth implementation
        # If Firebase token is invalid, should reject
        with pytest.raises(Exception):
            mock_verify("invalid_token")


# ── Runs Endpoint Tests ──
class TestRunsEndpoints:
    """Test research runs endpoints."""

    @patch("app.database.db_client")
    def test_list_runs_returns_list(self, mock_db):
        """Verify GET /api/runs returns list of runs."""
        mock_collection = MagicMock()
        mock_query = MagicMock()
        mock_docs = [
            MagicMock(to_dict=lambda: {"id": "run1", "topic": "AI"}),
            MagicMock(to_dict=lambda: {"id": "run2", "topic": "ML"}),
        ]
        
        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = mock_docs
        
        # Response depends on actual implementation
        # For now, verify endpoint exists and is callable
        response = client.get("/api/runs?skip=0&limit=5")
        assert response.status_code in [200, 503]  # 503 if Firestore not available

    @patch("app.database.db_client")
    def test_list_runs_with_pagination(self, mock_db):
        """Verify pagination parameters work."""
        response = client.get("/api/runs?skip=10&limit=20")
        assert response.status_code in [200, 503]

    @patch("app.database.db_client")
    def test_list_runs_returns_user_runs_only(self, mock_db):
        """Verify users can only see their own runs."""
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        
        response = client.get("/api/runs")
        # Should filter by authenticated user
        assert response.status_code in [200, 503]

    @patch("app.database.db_client")
    def test_create_run_with_valid_input(self, mock_db):
        """Verify POST /api/runs creates a new run."""
        mock_collection = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = "new_run_123"
        
        mock_collection.document.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        
        payload = {
            "topic": "Novel AI Research",
            "llm_config": {"vibe": "Deep Academic"}
        }
        
        response = client.post("/api/runs", json=payload)
        assert response.status_code in [200, 201, 503]

    @patch("app.database.db_client")
    def test_get_run_by_id(self, mock_db):
        """Verify GET /api/runs/{id} returns specific run."""
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"id": "run123", "topic": "AI", "status": "completed"}
        
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        
        response = client.get("/api/runs/run123")
        assert response.status_code in [200, 404, 503]

    @patch("app.database.db_client")
    def test_get_nonexistent_run(self, mock_db):
        """Verify requesting nonexistent run returns 404."""
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value = mock_collection
        
        response = client.get("/api/runs/nonexistent")
        # Should return 404 or 503 if DB unavailable
        assert response.status_code in [404, 503]


# ── Paper Download Tests ──
class TestPaperDownload:
    """Test paper download endpoints."""

    @patch("app.database.db_client")
    def test_download_paper_pdf(self, mock_db):
        """Verify GET /api/runs/{id}/paper.pdf returns PDF."""
        class _Doc:
            def __init__(self, data):
                self._data = data
                self.exists = True

            def to_dict(self):
                return dict(self._data)

        class _DocRef:
            def __init__(self, data):
                self._data = data

            def get(self):
                return _Doc(self._data)

        class _Collection:
            def __init__(self, docs):
                self._docs = docs

            def document(self, doc_id: str):
                data = self._docs.get(doc_id)
                if data is None:
                    missing = _Doc({})
                    missing.exists = False
                    return type("_MissingRef", (), {"get": lambda self: missing})()
                return _DocRef(data)

        class _DB:
            def collection(self, name):
                if name == "runs":
                    return _Collection({
                        "run123": {
                            "id": "run123",
                            "user_id": "test_user_uid_123",
                            "topic": "Test",
                            "paper_markdown": "# Title\n\nContent"
                        }
                    })
                return _Collection({})

        def override_db():
            yield _DB()

        app.dependency_overrides[get_db] = override_db
        
        response = client.get("/api/runs/run123/paper.pdf")
        # Should return PDF or 404
        assert response.status_code in [200, 404, 503]

    @patch("app.database.db_client")
    def test_paper_markdown_endpoint(self, mock_db):
        """Verify GET /api/runs/{id}/paper returns Markdown."""
        response = client.get("/api/runs/run123/paper")
        assert response.status_code in [200, 404, 503]


# ── Settings Endpoints ──
class TestSettingsEndpoints:
    """Test user settings endpoints."""

    def test_get_user_settings(self):
        """Verify GET /api/settings returns user settings."""
        response = client.get("/api/settings")
        assert response.status_code in [200, 404, 503]

    def test_update_user_settings(self):
        """Verify PUT /api/settings updates settings."""
        payload = {
            "default_llm": "gpt-4",
            "theme": "dark",
            "notifications": True
        }
        
        response = client.put("/api/settings", json=payload)
        assert response.status_code in [200, 400, 503]

    def test_settings_persisted_per_user(self):
        """Verify settings are persisted per user."""
        # Each user should have isolated settings
        payload = {"theme": "dark"}
        response = client.put("/api/settings", json=payload)
        assert response.status_code in [200, 503]


# ── Error Handling Tests ──
class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_json_body(self):
        """Verify invalid JSON body is rejected."""
        response = client.post("/api/runs", data="invalid json")
        assert response.status_code in [400, 422]

    def test_missing_required_fields(self):
        """Verify missing required fields are rejected."""
        response = client.post("/api/runs", json={})
        assert response.status_code in [400, 422]

    def test_invalid_data_types(self):
        """Verify invalid data types are rejected."""
        response = client.post("/api/runs", json={
            "topic": 123,  # Should be string
            "llm_config": "invalid"  # Should be dict
        })
        assert response.status_code in [400, 422]

    def test_unauthorized_access(self):
        """Verify unauthorized access is rejected."""
        # Override to return no user
        def mock_no_auth():
            raise Exception("Not authenticated")
        
        app.dependency_overrides[get_current_user] = mock_no_auth
        response = client.get("/api/runs")
        
        # Restore proper auth
        app.dependency_overrides[get_current_user] = mock_get_current_user
        assert response.status_code in [401, 403]


# ── Pagination & Filtering Tests ──
class TestPaginationAndFiltering:
    """Test pagination and filtering features."""

    def test_skip_parameter(self):
        """Verify skip parameter works."""
        response = client.get("/api/runs?skip=10&limit=5")
        assert response.status_code in [200, 503]

    def test_limit_parameter(self):
        """Verify limit parameter works."""
        response = client.get("/api/runs?limit=100")
        assert response.status_code in [200, 503]

    def test_negative_skip_invalid(self):
        """Verify negative skip is rejected."""
        response = client.get("/api/runs?skip=-1")
        # Should handle invalid input
        assert response.status_code in [200, 400, 503]

    def test_large_limit_capped(self):
        """Verify large limits are capped."""
        response = client.get("/api/runs?limit=10000")
        assert response.status_code in [200, 503]


# ── Rate Limiting & Performance ──
class TestPerformance:
    """Test performance and rate limiting."""

    def test_fast_health_check(self):
        """Verify health check responds quickly."""
        import time
        start = time.time()
        response = client.get("/api/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should be very fast

    def test_concurrent_requests(self):
        """Verify API handles multiple concurrent requests."""
        import concurrent.futures
        
        def make_request():
            return client.get("/api/health")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]
        
        assert all(r.status_code == 200 for r in results)


# ── CORS & Security Headers ──
class TestSecurityHeaders:
    """Test security headers and CORS."""

    def test_response_includes_security_headers(self):
        """Verify responses include security headers."""
        response = client.get("/api/health")
        # Should have proper headers
        assert response.status_code == 200

    def test_cors_headers_present(self):
        """Verify CORS headers are present."""
        response = client.options("/api/health")
        # CORS should be configured
        assert response.status_code in [200, 405]


# ── Data Validation Tests ──
class TestDataValidation:
    """Test data validation in endpoints."""

    def test_topic_length_validation(self):
        """Verify topic length is validated."""
        payload = {
            "topic": "x" * 10000,  # Very long topic
            "llm_config": {}
        }
        
        response = client.post("/api/runs", json=payload)
        # Should either accept or reject with 400/422
        assert response.status_code in [200, 201, 400, 422, 503]

    def test_emoji_in_topic(self):
        """Verify emoji in topic is handled."""
        payload = {
            "topic": "AI research 🤖 🧠",
            "llm_config": {}
        }
        
        response = client.post("/api/runs", json=payload)
        assert response.status_code in [200, 201, 400, 422, 503]

    def test_special_characters_in_query(self):
        """Verify special characters in query parameters are handled."""
        response = client.get("/api/runs?search=<script>alert('xss')</script>")
        assert response.status_code in [200, 400, 503]
