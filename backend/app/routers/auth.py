"""Auth router — lightweight Firebase token introspection.

The frontend uses Firebase Auth directly and sends an ID token to the backend.
This endpoint allows the UI to confirm the backend can validate the token.
"""

from fastapi import APIRouter, Depends

from app.auth.dependencies import User, get_current_user


router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.get("/me", response_model=User)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
