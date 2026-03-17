from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user

from app.services import auth_service
from app.models.user import User

from app.schemas.auth import AuthSyncRequest, FCMTokenRequest, AuthSyncResponse, FCMTokenResponse
from app.schemas.common import MessageResponse
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/sync", response_model=AuthSyncResponse)
async def sync_user(
    payload: AuthSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called once after first Supabase login.
    Creates user row + wallet on first login.
    Updates profile fields on subsequent logins.
    """
    user, is_new = await auth_service.sync_user(
        db=db,
        supabase_uid=current_user.supabase_uid,
        data=payload,
    )
    return {
        "message": "Welcome to GoAlong!" if is_new else "Welcome back!",
        "is_new_user": is_new,
    }


@router.post("/fcm-token", response_model=MessageResponse)
async def register_fcm_token(
    payload: FCMTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register FCM device token for push notifications."""
    await auth_service.update_fcm_token(db, current_user, payload.token)
    return {"message": "FCM token registered"}


@router.delete("/fcm-token", response_model=MessageResponse)
async def remove_fcm_token(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove FCM token on logout."""
    await auth_service.remove_fcm_token(db, current_user)
    return {"message": "FCM token removed"}