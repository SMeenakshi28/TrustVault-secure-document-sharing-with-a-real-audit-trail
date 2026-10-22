
import os
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET_NAME = "trustvault-documents"


def storage_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def _headers(content_type: str = "application/octet-stream") -> dict:
    if not storage_configured():
        raise RuntimeError(
            "Supabase Storage configuration is missing. Check backend/.env."
        )

    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type,
    }


def _object_url(storage_path: str) -> str:
    safe_path = quote(storage_path, safe="/")
    return f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{safe_path}"


def upload_object(
    storage_path: str,
    file_bytes: bytes,
    content_type: str,
) -> None:
    try:
        response = httpx.post(
            _object_url(storage_path),
            headers={
                **_headers(content_type),
                "x-upsert": "false",
            },
            content=file_bytes,
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="File upload to secure storage failed.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to secure storage.",
        ) from exc


def download_object(storage_path: str) -> bytes:
    try:
        response = httpx.get(
            _object_url(storage_path),
            headers=_headers(),
            timeout=60.0,
        )
        response.raise_for_status()
        return response.content
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve the stored file.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to secure storage.",
        ) from exc



def delete_object(storage_path: str) -> None:
    try:
        response = httpx.delete(
            _object_url(storage_path),
            headers=_headers(),
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print("Storage delete failed:", exc.response.status_code)
        print("Storage response:", exc.response.text[:1000])
        raise HTTPException(
            status_code=502,
            detail="Could not delete the stored file. Check backend terminal.",
        ) from exc
    except httpx.RequestError as exc:
        print("Storage connection failed:", str(exc))
        raise HTTPException(
            status_code=502,
            detail="Could not connect to secure storage.",
        ) from exc
