"""Firebase initialization and Firestore database client with optional Cloud Storage."""

import os

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.config import BACKEND_DIR, get_settings


def _initialize_firebase_admin() -> None:
    """Initialize Firebase Admin exactly once.

    Important: if `FIREBASE_STORAGE_BUCKET` is configured, pass it via the
    `storageBucket` option so `storage.bucket()` resolves correctly.
    """
    if firebase_admin._apps:
        return

    settings = get_settings()
    options: dict = {}
    if settings.FIREBASE_STORAGE_BUCKET:
        options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET

    cert_path_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service-account.json")
    # Resolve relative to backend's parent (the project root ARS folder)
    cert_path = BACKEND_DIR.parent / cert_path_env

    if cert_path.exists():
        cred = credentials.Certificate(str(cert_path))
        firebase_admin.initialize_app(cred, options or None)
        return

    # Fallback to default application credentials if running in GCP.
    try:
        firebase_admin.initialize_app(options=options or None)
    except ValueError:
        print(f"Warning: Firebase Admin not fully configured. Missing {cert_path}")


_initialize_firebase_admin()

db_client = None
storage_bucket = None

try:
    db_client = firestore.client()
except Exception as e:
    print(f"Warning: Firestore client failed to initialize: {e}")

# Initialize Firebase Storage if bucket name is set in config
try:
    settings = get_settings()
    if settings.FIREBASE_STORAGE_BUCKET:
        # Prefer the default bucket configured via initialize_app(storageBucket=...)
        # and fall back to an explicit bucket name if needed.
        try:
            storage_bucket = storage.bucket()
        except Exception:
            storage_bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
except Exception as e:
    print(f"Warning: Firebase Storage bucket initialization failed: {e}")

def get_db():
    """FastAPI dependency — yields the Firestore client."""
    from fastapi import HTTPException

    if db_client is None:
        raise HTTPException(
            status_code=503,
            detail="Firestore client is not initialized. Check FIREBASE_SERVICE_ACCOUNT_PATH and Firebase Admin config.",
        )
    yield db_client

def get_storage_bucket():
    """Returns the Firebase Storage bucket if configured and initialized, None otherwise."""
    return storage_bucket

def create_tables():
    """No-op for Firestore (NoSQL creates collections dynamically)."""
    pass
