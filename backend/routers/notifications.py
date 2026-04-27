# routers/notifications.py
import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from supabase_client import require_auth, supabase_get, supabase_post, supabase_delete

router = APIRouter()

VAPID_PUBLIC_KEY  = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_EMAIL       = os.getenv("VAPID_EMAIL", "admin@opsystem.com")


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict
    userAgent: Optional[str] = None


async def send_push_to_user(user_id: str, payload: dict):
    """Send push notification to all subscriptions of a user"""
    if not VAPID_PRIVATE_KEY:
        return

    try:
        subs = await supabase_get(
            f"push_subscriptions?select=endpoint,p256dh,auth&user_id=eq.{user_id}"
        )
        if not subs:
            return

        from pywebpush import webpush, WebPushException
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub["endpoint"],
                        "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                    },
                    data=json.dumps({
                        "title": payload.get("title", "OpsSystem"),
                        "body": payload.get("body", ""),
                        "tag": payload.get("tag", "default"),
                        "icon": "/icons/icon-192.png",
                        "data": payload.get("data", {}),
                    }),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{VAPID_EMAIL}"},
                )
            except WebPushException as e:
                if e.response and e.response.status_code in (404, 410):
                    await supabase_delete("push_subscriptions", {"endpoint": sub["endpoint"]})
    except Exception as e:
        print(f"[Push] Error: {e}")


@router.get("/vapid-public-key")
async def get_vapid_key():
    return {"publicKey": VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe(body: PushSubscription, profile=Depends(require_auth)):
    try:
        existing = await supabase_get(
            f"push_subscriptions?select=id&user_id=eq.{profile['id']}&endpoint=eq.{body.endpoint}&limit=1"
        )
        if not existing:
            await supabase_post("push_subscriptions", {
                "user_id": profile["id"],
                "endpoint": body.endpoint,
                "p256dh": body.keys.get("p256dh"),
                "auth": body.keys.get("auth"),
                "user_agent": body.userAgent,
            })
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_push(profile=Depends(require_auth)):
    await send_push_to_user(profile["id"], {
        "title": "🔔 Test Notification",
        "body": "OpsSystem push notifications are working!",
        "tag": "test",
    })
    return {"success": True}
