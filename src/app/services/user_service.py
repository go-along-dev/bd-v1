from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from uuid import UUID

from app.models.user import User
from app.schemas.user import UserUpdateRequest


# ─── Get User By ID ───────────────────────────
async def get_user_by_id(
    db: AsyncSession,
    user_id: UUID,
) -> User | None:
    """Fetch user by primary key. Used for public profile views."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


# ─── Update Profile ───────────────────────────
async def update_profile(
    db: AsyncSession,
    user: User,
    data: UserUpdateRequest,
) -> User:
    """
    Partial update — only non-None fields are updated.
    Phone cannot be changed here (managed by Supabase Auth).
    """
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.profile_photo is not None:
        user.profile_photo = data.profile_photo

    await db.commit()
    await db.refresh(user)
    return user