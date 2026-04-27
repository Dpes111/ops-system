# backend/supabase_client.py
import os
import httpx
from fastapi import HTTPException, Header
from typing import Optional

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")


def get_headers(use_service_key=True):
    key = SUPABASE_SERVICE_KEY if use_service_key else SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def supabase_get(path: str, params: dict = None):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers=get_headers(),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()


async def supabase_post(path: str, data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers=get_headers(),
            json=data,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()


async def supabase_patch(path: str, data: dict, match: dict):
    params = {k: f"eq.{v}" for k, v in match.items()}
    async with httpx.AsyncClient() as client:
        r = await client.patch(
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers=get_headers(),
            json=data,
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()


async def supabase_delete(path: str, match: dict):
    params = {k: f"eq.{v}" for k, v in match.items()}
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers=get_headers(),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()


async def get_user_from_token(token: str):
    """Verify JWT token and return user from Supabase Auth"""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
        if r.status_code != 200:
            return None
        return r.json()


async def require_auth(authorization: Optional[str] = Header(None)):
    """FastAPI dependency — validates Bearer token and returns profile"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.split(" ")[1]
    user = await get_user_from_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get profile
    try:
        profiles = await supabase_get(
            f"profiles?select=*&id=eq.{user['id']}&limit=1"
        )
        if not profiles:
            # Auto-create profile
            email = user.get("email", "")
            new_profile = await supabase_post("profiles", {
                "id": user["id"],
                "full_name": email.split("@")[0],
                "email": email,
                "role": "staff",
                "is_active": True,
            })
            profile = new_profile[0] if isinstance(new_profile, list) else new_profile
        else:
            profile = profiles[0]

        if not profile.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account inactive")

        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile error: {str(e)}")


def require_role(*roles):
    """Role guard — use as FastAPI dependency"""
    async def checker(profile: dict = None):
        if profile and profile.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {' or '.join(roles)}"
            )
        return profile
    return checker
