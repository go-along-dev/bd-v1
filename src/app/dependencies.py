from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.db.postgres import AsyncSessionLocal
from app.config import settings

security = HTTPBearer()

# ─── DB Session ───────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── Pagination ───────────────────────────────
def get_pagination(page: int = 1, per_page: int = 20):
    if page < 1:
        page = 1
    if per_page > 100:
        per_page = 100
    offset = (page - 1) * per_page
    return {"page": page, "per_page": per_page, "offset": offset}


# ─── Auth Token Payload ──────────────────────────
async def get_auth_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    
    # DEBUG: Confirm token is reaching the backend
    print(f"DEBUG: Headers Auth: Bearer {token[:15]}...")
    
    # --- Demo/Test Bypass ---
    if token == "demo-token" or settings.APP_ENV == "development" and token.startswith("test-"):
        print("🔓 Debug Token recognized")
        return {
            "sub": "00000000-0000-0000-0000-000000000000",
            "email": "demo@goalong.in",
            "aud": "authenticated"
        }
    # -------------------

    try:
        # DEBUG: Log the unverified header to see 'alg'
        header = jwt.get_unverified_header(token)
        print(f"DEBUG: Token Header: {header}")
        
        # Legacy Supabase JWT Configuration (HS256)
        # Expected Issuer: https://<project>.supabase.co/auth/v1
        expected_iss = f"{settings.SUPABASE_URL}/auth/v1".replace("http://", "https://")
        
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256", "RS256", "ES256", "EdDSA"], # Support modern Supabase ES256
            audience="authenticated",
            issuer=expected_iss,
            options={
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
            }
        )
        
        print(f"✅ AUTH: Token validated for user: {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        print("❌ AUTH: Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        print(f"❌ AUTH: Invalid token/signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (JWTError, Exception) as e:
        # Catch EVERY type of error (Signature, Deserialization, KeyError, etc.)
        # and safely return a 401 instead of crashing the server.
        print(f"❌ AUTH: Validation failed - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalid or expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Current User ─────────────────────────────
async def get_current_user(
    payload: dict = Depends(get_auth_token_payload),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User
    import uuid
    supabase_uid = payload.get("sub")

    # Find user in local DB
    try:
        result = await db.execute(
            select(User).where(User.supabase_uid == supabase_uid)
        )
        user = result.scalar_one_or_none()
    except Exception as e:
        print(f"⚠️ get_current_user DB error: {e}")
        user = None

    if user is None:
        if supabase_uid == "00000000-0000-0000-0000-000000000000":
             # Auto-create Demo User and Driver if missing
             from app.models.driver import Driver
             from app.models.wallet import Wallet
             try:
                 user = User(
                     supabase_uid=supabase_uid,
                     name="Demo User (Mock Driver)",
                     role="driver",
                     is_active=True,
                     email="demo@goalong.in",
                     phone="0000000000"
                 )
                 db.add(user)
                 await db.flush()
                 
                 driver = Driver(user_id=user.id, is_approved=True, vehicle_model="Demo Car", vehicle_number="GA-000-DEMO")
                 db.add(driver)
                 
                 wallet = Wallet(user_id=user.id, balance=0.00)
                 db.add(wallet)
                 
                 await db.commit()
                 await db.refresh(user)
                 return user
             except Exception as e:
                 await db.rollback()
                 print(f"⚠️ Failsafe: Could not create demo records in DB ({e}). Using static fallback.")
                 # Static fallback if DB is hard-locked
                 return User(
                     id=uuid.UUID("d3b07384-dead-beef-cafe-d3b07384dead"),
                     supabase_uid=supabase_uid,
                     name="Demo User (Mock)",
                     role="driver",
                     is_active=True
                 )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not synced. Perform /auth/sync first.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated"
        )

    return user


# ─── Role Guards ──────────────────────────────
async def require_driver(current_user=Depends(get_current_user)):
    if current_user.role not in ("driver", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Driver access required"
        )
    return current_user


async def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
