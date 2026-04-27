from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

from routers import auth, tasks, attendance, notifications

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 OpsSystem API starting...")
    yield
    print("OpsSystem API shutting down...")

app = FastAPI(title="OpsSystem API", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:8080"),
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://ops-system-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,          prefix="/api/auth",          tags=["auth"])
app.include_router(tasks.router,         prefix="/api/tasks",         tags=["tasks"])
app.include_router(attendance.router,    prefix="/api/attendance",    tags=["attendance"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "OpsSystem API", "version": "1.0.0"}
