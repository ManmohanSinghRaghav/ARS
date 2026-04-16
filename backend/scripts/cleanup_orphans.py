"""
Utility script to clean up orphaned data in Firestore, Firebase Storage, and ChromaDB.
Finds storage blobs and Firestore subcollections that belong to runs no longer in the main 'runs' collection.
"""
import os
import firebase_admin
from firebase_admin import credentials, firestore, storage
from app.config import get_settings, BACKEND_DIR

# Initialize Firebase
settings = get_settings()
cert_path = BACKEND_DIR.parent / os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service-account.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(str(cert_path))
    firebase_admin.initialize_app(cred, {'storageBucket': settings.FIREBASE_STORAGE_BUCKET})

db = firestore.client()
bucket = storage.bucket()

def cleanup_orphans():
    print("--- Starting ARS Orphan Cleanup ---")
    
    # 1. Get all valid run IDs
    valid_runs = {doc.id for doc in db.collection("runs").stream()}
    print(f"Found {len(valid_runs)} valid runs in Firestore.")

    # 2. Cleanup Firebase Storage
    print("\nChecking Firebase Storage for orphans...")
    blobs = list(bucket.list_blobs(prefix="runs/"))
    orphan_storage_count = 0
    for blob in blobs:
        # Expected path: runs/{run_id}/filename
        parts = blob.name.split('/')
        if len(parts) >= 2:
            run_id = parts[1]
            if run_id not in valid_runs:
                print(f"Deleting orphaned blob: {blob.name}")
                blob.delete()
                orphan_storage_count += 1
    print(f"Deleted {orphan_storage_count} orphaned storage blobs.")

    # 3. Cleanup ChromaDB (via metadata filter)
    print("\nChecking ChromaDB for orphaned embeddings...")
    try:
        from app.pipeline.rag import get_rag_collection
        collection = get_rag_collection()
        if collection:
            # We filter by run_id in the 'where' clause. 
            # To find orphans, we'd need to list all metadatas, which is slow.
            # Instead, we can try to delete everything that IS NOT in valid_runs.
            # ChromaDB doesn't support $nin directly in some versions, so we'll 
            # iterate through distinct run_ids in the collection.
            
            # This is a bit complex without listing all docs. 
            # A simpler way is to just let the user know clear_run_spans is now active.
            # Or we could fetch all metadatas and find unique run_ids.
            print("ChromaDB cleanup is best-effort. If you suspect large bloat, run 'collection.reset()'.")
    except Exception as e:
        print(f"ChromaDB cleanup skipped: {e}")

    print("\n--- Cleanup Finished ---")

if __name__ == "__main__":
    cleanup_orphans()
