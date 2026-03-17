from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services import user_service
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


# ─── GET /users/me ────────────────────────────
@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile."""
    return current_user


# ─── PUT /users/me ────────────────────────────
@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdateRequest,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user's profile. Only provided fields are updated."""
    return await user_service.update_profile(
        db=db,
        user=current_user,
        data=payload,
    )

from uuid import UUID
from fastapi import HTTPException

# ─── GET /users/{user_id} ─────────────────────
@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: UUID,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a user's public profile.
    Used by passenger viewing driver profile or vice versa.
    Returns limited fields only.
    """
    user = await user_service.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    return user