# routers/tasks.py
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from supabase_client import require_auth, supabase_get, supabase_post, supabase_patch, supabase_delete
from routers.notifications import send_push_to_user

router = APIRouter()


class CreateTaskRequest(BaseModel):
    title: str
    type: str  # bank | delivery | party
    description: Optional[str] = None
    location_name: str
    latitude: float
    longitude: float
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("")
async def get_tasks(profile=Depends(require_auth)):
    if profile["role"] in ("admin", "manager"):
        tasks = await supabase_get(
            "tasks?select=*,assigned_to_profile:profiles!tasks_assigned_to_fkey(id,full_name,email,role),assigned_by_profile:profiles!tasks_assigned_by_fkey(id,full_name,role)&order=created_at.desc"
        )
    else:
        tasks = await supabase_get(
            f"tasks?select=*,assigned_to_profile:profiles!tasks_assigned_to_fkey(id,full_name,email,role),assigned_by_profile:profiles!tasks_assigned_by_fkey(id,full_name,role)&assigned_to=eq.{profile['id']}&order=created_at.desc"
        )
    return {"tasks": tasks}


@router.get("/staff-workload")
async def get_workload(profile=Depends(require_auth)):
    if profile["role"] not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Forbidden")
    tasks = await supabase_get(
        "tasks?select=assigned_to,assigned_to_profile:profiles!tasks_assigned_to_fkey(id,full_name)&status=in.(assigned,in_progress)&assigned_to=not.is.null"
    )
    workload = {}
    for t in tasks:
        uid = t.get("assigned_to")
        if uid:
            if uid not in workload:
                workload[uid] = {
                    "staff_id": uid,
                    "full_name": (t.get("assigned_to_profile") or {}).get("full_name", "Unknown"),
                    "active_count": 0,
                }
            workload[uid]["active_count"] += 1
    return {"workload": list(workload.values())}


@router.post("")
async def create_task(body: CreateTaskRequest, profile=Depends(require_auth)):
    if profile["role"] not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Managers only")
    if body.type not in ("bank", "delivery", "party"):
        raise HTTPException(status_code=400, detail="Invalid task type")

    task_data = {
        "title": body.title,
        "type": body.type,
        "description": body.description,
        "location_name": body.location_name,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "assigned_to": body.assigned_to,
        "assigned_by": profile["id"],
        "status": "assigned" if body.assigned_to else "pending",
        "due_date": body.due_date,
    }
    result = await supabase_post("tasks", task_data)
    task = result[0] if isinstance(result, list) else result

    # Push notification
    if body.assigned_to:
        labels = {"bank": "🏦 Bank Deposit", "delivery": "📦 Delivery", "party": "🎉 Party Visit"}
        await send_push_to_user(body.assigned_to, {
            "title": "New Task Assigned",
            "body": f"{labels.get(body.type, body.type)}: {body.title} at {body.location_name}",
            "tag": f"task-{task['id']}",
            "data": {"taskId": task["id"], "url": "/tasks.html"},
        })

    return {"task": task}


@router.patch("/{task_id}")
async def update_task(task_id: str, body: UpdateTaskRequest, profile=Depends(require_auth)):
    updates = body.model_dump(exclude_none=True)

    if profile["role"] == "staff":
        allowed = {"status"}
        if set(updates.keys()) - allowed:
            raise HTTPException(status_code=403, detail="Staff can only update status")
        if "status" in updates and updates["status"] not in ("in_progress", "completed"):
            raise HTTPException(status_code=400, detail="Invalid status")

    if updates.get("status") == "completed":
        updates["completed_at"] = datetime.now(timezone.utc).isoformat()

    result = await supabase_patch("tasks", updates, {"id": task_id})
    task = result[0] if isinstance(result, list) else result
    return {"task": task}


@router.delete("/{task_id}")
async def delete_task(task_id: str, profile=Depends(require_auth)):
    if profile["role"] not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Managers only")
    await supabase_delete("tasks", {"id": task_id})
    return {"success": True}
