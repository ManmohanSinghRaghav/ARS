"""
FastAPI dependencies for authentication using Firebase.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from pydantic import BaseModel

security = HTTPBearer()

class User(BaseModel):
    id: str
    email: str
    username: str
    role: str

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Extract and validate the Firebase ID Token from Authorization Bearer token."""
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token, clock_skew_seconds=60)
        return User(
            id=decoded_token.get("uid"),
            email=decoded_token.get("email", ""),
            username=decoded_token.get("name", decoded_token.get("email", "").split('@')[0]),
            role=decoded_token.get("role", "user")
        )
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require that the current user has 'admin' role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
