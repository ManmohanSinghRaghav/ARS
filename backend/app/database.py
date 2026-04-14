"""Firebase initialization and Firestore database client."""
import os
import firebase_admin
from firebase_admin import credentials, firestore

from pathlib import Path
from app.config import BACKEND_DIR

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    cert_path_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service-account.json")
    # Resolve relative to backend's parent (the project root ARS folder)
    cert_path = BACKEND_DIR.parent / cert_path_env
    
    if cert_path.exists():
        cred = credentials.Certificate(str(cert_path))
        firebase_admin.initialize_app(cred)
    else:
        # Fallback to default application credentials if running in GCP, 
        # or it will error if no defaults exist.
        try:
            firebase_admin.initialize_app()
        except ValueError:
            print(f"Warning: Firebase Admin not fully configured. Missing {cert_path}")

db_client = None
try:
    db_client = firestore.client()
except Exception as e:
    print(f"Warning: Firestore client failed to initialize: {e}")

def get_db():
    """FastAPI dependency — yields the Firestore client."""
    from fastapi import HTTPException

    if db_client is None:
        raise HTTPException(
            status_code=503,
            detail="Firestore client is not initialized. Check FIREBASE_SERVICE_ACCOUNT_PATH and Firebase Admin config.",
        )
    yield db_client

def create_tables():
    """No-op for Firestore (NoSQL creates collections dynamically)."""
    pass
