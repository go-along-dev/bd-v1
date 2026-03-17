import httpx
from fastapi import HTTPException, status, UploadFile
from app.config import settings


# ─── Allowed Types ────────────────────────────
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
ALLOWED_DOC_TYPES   = {"image/jpeg", "image/png", "application/pdf"}

BUCKET_CONFIG = {
    "profile-photos":   {"public": True,  "max_mb": 2, "allowed": ALLOWED_IMAGE_TYPES},
    "driver-documents": {"public": False, "max_mb": 5, "allowed": ALLOWED_DOC_TYPES},
    "toll-proofs":      {"public": False, "max_mb": 5, "allowed": ALLOWED_DOC_TYPES},
}


# ─── Validate Upload ──────────────────────────
def validate_upload(
    file_data: bytes,
    content_type: str,
    max_size_mb: int,
    allowed_types: set[str],
) -> None:
    """Validate file size and type before uploading."""
    max_bytes = max_size_mb * 1024 * 1024

    if len(file_data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {max_size_mb}MB"
        )

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {content_type}. Allowed: {', '.join(allowed_types)}"
        )


# ─── Upload File ──────────────────────────────
async def upload_file(
    bucket: str,
    path: str,
    file: UploadFile,
    content_type: str,
) -> str:
    """
    Upload a file to Supabase Storage.
    Returns public URL for public buckets, storage path for private.
    """
    # Get bucket config
    config = BUCKET_CONFIG.get(bucket)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown bucket: {bucket}"
        )

    # Read file bytes
    file_data = await file.read()

    # Validate
    validate_upload(
        file_data    = file_data,
        content_type = content_type,
        max_size_mb  = config["max_mb"],
        allowed_types= config["allowed"],
    )

    # Upload to Supabase Storage
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type":  content_type,
        "x-upsert":      "true",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, content=file_data, headers=headers)

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage upload failed: {response.text}"
        )

    # Return public URL or storage path
    if config["public"]:
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
    else:
        return f"{bucket}/{path}"   # private — use get_signed_url to access


# ─── Get Signed URL ───────────────────────────
async def get_signed_url(
    bucket: str,
    path: str,
    expires_in: int = 3600,
) -> str:
    """Generate a temporary signed URL for private files. Default: 1 hour."""
    url = f"{settings.SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type":  "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            json={"expiresIn": expires_in},
            headers=headers,
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate signed URL"
        )

    data = response.json()
    return f"{settings.SUPABASE_URL}/storage/v1{data['signedURL']}"


# ─── Delete File ──────────────────────────────
async def delete_file(bucket: str, path: str) -> bool:
    """Delete a file from Supabase Storage."""
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.delete(url, headers=headers)

    return response.status_code == 200