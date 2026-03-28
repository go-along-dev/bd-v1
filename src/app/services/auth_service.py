from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.auth import AuthSyncRequest
import random
import string


# ─── Referral Code Generator ──────────────────
def generate_referral_code(length: int = 8) -> str:
    return ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=length)
    )


# ─── Sync User ────────────────────────────────
async def sync_user(
    db: AsyncSession,
    supabase_uid: str,
    data: AuthSyncRequest,
) -> tuple[User, bool]:
    """
    Called after Flutter authenticates with Supabase.
    Upserts user row — creates if first time, updates if existing.
    Returns (user, is_new_user).
    """
    # 1. Look up existing user
    result = await db.execute(
        select(User).where(User.supabase_uid == supabase_uid)
    )
    user = result.scalar_one_or_none()

    # 2. New user — create row + wallet
    if user is None:
        user = User(
            supabase_uid=supabase_uid,
            name=data.name,
            email=data.email,
            phone=data.phone,
            profile_photo=data.profile_photo,
            role=data.role if data.role else "passenger",
            is_active=True,
            referral_code=generate_referral_code(),
        )
        db.add(user)
        await db.flush()  # get user.id before creating wallet

        # Auto-create wallet for every new user
        # (only drivers use it, but we create for all for consistency)
        wallet = Wallet(user_id=user.id, balance=0.00)
        db.add(wallet)

        await db.commit()
        await db.refresh(user)
        return user, True

    # 3. Existing user — update fields if provided
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.phone is not None:
        user.phone = data.phone
    if data.profile_photo is not None:
        user.profile_photo = data.profile_photo
    if data.role is not None:
        user.role = data.role

    await db.commit()
    await db.refresh(user)
    return user, False


# ─── Update FCM Token ─────────────────────────
async def update_fcm_token(
    db: AsyncSession,
    user: User,
    fcm_token: str,
) -> None:
    """
    Updates user.fcm_token.
    Called on every app launch and when Firebase token refreshes.
    """
    user.fcm_token = fcm_token
    await db.commit()


# ─── Remove FCM Token ─────────────────────────
async def remove_fcm_token(
    db: AsyncSession,
    user: User,
) -> None:
    """Called on logout."""
    user.fcm_token = None
    await db.commit()
