# routers/attendance.py
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from supabase_client import require_auth, supabase_get, supabase_post, supabase_patch

router = APIRouter()


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(dist, 1)


class CheckInRequest(BaseModel):
    latitude: float
    longitude: float
    task_id: Optional[str] = None
    notes: Optional[str] = None


class CompleteRequest(BaseModel):
    task_id: str
    latitude: float
    longitude: float


@router.post("/checkin")
async def check_in(body: CheckInRequest, profile=Depends(require_auth)):
    is_within = True
    distance = 0.0

    if body.task_id:
        tasks = await supabase_get(
            f"tasks?select=*&id=eq.{body.task_id}&limit=1"
        )
        if not tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        task = tasks[0]
        if task.get("assigned_to") != profile["id"]:
            raise HTTPException(status_code=403, detail="Not your task")

        distance = haversine(body.latitude, body.longitude, task["latitude"], task["longitude"])
        is_within = distance <= 100

        if is_within and task.get("status") == "assigned":
            await supabase_patch("tasks", {"status": "in_progress"}, {"id": body.task_id})

    log = await supabase_post("attendance_logs", {
        "staff_id": profile["id"],
        "task_id": body.task_id,
        "check_in_lat": body.latitude,
        "check_in_lng": body.longitude,
        "distance_meters": distance,
        "is_within_fence": is_within,
        "notes": body.notes,
    })
    result = log[0] if isinstance(log, list) else log

    msg = "✅ Check-in successful — you are within the task zone." if is_within else \
          f"⚠️ You are {distance}m away from the task location (limit: 100m)."

    return {
        "log": result,
        "geofence": {"isWithin": is_within, "distanceMeters": distance},
        "message": msg,
    }


@router.post("/complete")
async def complete_task(body: CompleteRequest, profile=Depends(require_auth)):
    tasks = await supabase_get(f"tasks?select=*&id=eq.{body.task_id}&limit=1")
    if not tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[0]

    if task.get("assigned_to") != profile["id"]:
        raise HTTPException(status_code=403, detail="Not your task")

    distance = haversine(body.latitude, body.longitude, task["latitude"], task["longitude"])
    if distance > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete task — you are {distance}m away. Must be within 100m."
        )

    result = await supabase_patch("tasks", {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }, {"id": body.task_id})
    updated = result[0] if isinstance(result, list) else result

    await supabase_post("attendance_logs", {
        "staff_id": profile["id"],
        "task_id": body.task_id,
        "check_in_lat": body.latitude,
        "check_in_lng": body.longitude,
        "distance_meters": distance,
        "is_within_fence": True,
        "notes": "Task completed",
    })

    return {"task": updated, "message": "✅ Task marked as completed!"}


@router.get("")
async def get_logs(profile=Depends(require_auth)):
    if profile["role"] in ("admin", "manager"):
        logs = await supabase_get(
            "attendance_logs?select=*,staff:profiles!attendance_logs_staff_id_fkey(id,full_name,email),task:tasks(id,title,type,location_name)&order=check_in_time.desc&limit=200"
        )
    else:
        logs = await supabase_get(
            f"attendance_logs?select=*,task:tasks(id,title,type,location_name)&staff_id=eq.{profile['id']}&order=check_in_time.desc&limit=100"
        )
    return {"logs": logs}
