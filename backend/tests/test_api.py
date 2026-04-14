import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user, User
from app.database import get_db

# ── Mocks ──
def mock_get_current_user():
    """Bypasses Firebase Authentication natively."""
    return User(id="test_admin_uid_123", email="admin@test.com", username="admin_user", role="admin")

# Inject Mocks inside FastAPI natively
app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

def test_health_check():
    """Verify backend starts and responds to unauthenticated requests."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "Firebase Firestore" in response.json().get("service", "ARS Backend") or "ARS" in response.json()["service"]


def test_list_runs_authenticated():
    """Verify the mocked token allows access to protected routes."""
    # Since get_current_user is mocked, this doesn't need an actual Authorization header!
    response = client.get("/api/runs?skip=0&limit=5")
    
    # 200 means auth passed successfully and Firestore didn't reject the query layout!
    # If Firestore isn't configured locally, the API now returns 503 (service unavailable)
    # instead of crashing.
    assert response.status_code in (200, 503)
    
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_auth_me_authenticated():
    """Verify /api/auth/me exists and returns the current user."""
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "test_admin_uid_123"


def test_download_paper_pdf_mocked_db():
    """Verify /api/runs/{id}/paper.pdf returns a valid PDF response."""

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
        def __init__(self, runs):
            self._runs = runs

        def collection(self, name: str):
            if name != "runs":
                return _Collection({})
            return _Collection(self._runs)

    run_id = "run_pdf_test_1"
    fake_db = _DB(
        {
            run_id: {
                "id": run_id,
                "user_id": "test_admin_uid_123",
                "topic": "Test Topic",
                "paper_markdown": "# Hello\n\nThis is a test paper.",
            }
        }
    )

    def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        res = client.get(f"/api/runs/{run_id}/paper.pdf")
        assert res.status_code == 200
        assert res.headers.get("content-type", "").startswith("application/pdf")
        assert res.content[:4] == b"%PDF"
    finally:
        app.dependency_overrides.pop(get_db, None)
