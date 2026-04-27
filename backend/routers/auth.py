# routers/auth.py
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from supabase_client import require_auth, supabase_get, supabase_post, supabase_patch, SUPABASE_URL, SUPABASE_SERVICE_KEY

router = APIRouter()


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str
    phone: Optional[str] = None


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    phone: Optional[str] = None


@router.get("/users")
async def get_users(profile=Depends(require_auth)):
    if profile["role"] not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Forbidden")
    users = await supabase_get(
        "profiles?select=id,full_name,email,role,is_active,created_at,phone&order=created_at.desc"
    )
    return {"users": users}


@router.post("/users")
async def create_user(body: CreateUserRequest, profile=Depends(require_auth)):
    if profile["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if body.role not in ("admin", "manager", "staff"):
        raise HTTPException(status_code=400, detail="Invalid role")

    # Create auth user via Supabase Admin API
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
                "user_metadata": {"full_name": body.full_name, "role": body.role},
            },
            timeout=15,
        )
        auth_data = r.json()
        if r.status_code not in (200, 201):
            raise HTTPException(
                status_code=400,
                detail=auth_data.get("message") or auth_data.get("msg") or "Failed to create auth user"
            )

    # Insert profile
    new_profile = await supabase_post("profiles", {
        "id": auth_data["id"],
        "full_name": body.full_name,
        "email": body.email,
        "role": body.role,
        "phone": body.phone,
        "is_active": True,
    })
    result = new_profile[0] if isinstance(new_profile, list) else new_profile
    return {"user": result}


@router.patch("/users/{user_id}")
async def update_user(user_id: str, body: UpdateUserRequest, profile=Depends(require_auth)):
    if profile["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    updates = body.model_dump(exclude_none=True)
    result = await supabase_patch("profiles", updates, {"id": user_id})
    data = result[0] if isinstance(result, list) else result
    return {"user": data}


@router.delete("/users/{user_id}")
async def deactivate_user(user_id: str, profile=Depends(require_auth)):
    if profile["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if user_id == profile["id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    await supabase_patch("profiles", {"is_active": False}, {"id": user_id})
    return {"success": True}
