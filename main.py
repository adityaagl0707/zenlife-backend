from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env", override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core import mongo
from app.core.config import get_settings
from app.api import auth, orders, reports, chat, admin, self_upload
from app.services.seed_service import seed_demo

settings = get_settings()

app = FastAPI(
    title="ZenLife API",
    description="Backend for ZenLife — preventive health intelligence platform",
    version="2.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[ZenLife] Unhandled error on {request.method} {request.url}: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
        headers={"Access-Control-Allow-Origin": "*"},
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(self_upload.router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    # Verify MongoDB connectivity and create indexes (idempotent)
    try:
        mongo.db.client.admin.command("ping")
        mongo.ensure_indexes()
        print(f"[ZenLife] Connected to MongoDB: {mongo.db.name}")
    except Exception as e:
        print(f"[ZenLife] WARNING — could not reach MongoDB: {e}")

    # Seed demo data if collections are empty
    try:
        seed_demo()
    except Exception as e:
        print(f"[ZenLife] Seed skipped: {e}")


@app.get("/")
def root():
    return {"message": "ZenLife API v2.0", "status": "healthy", "db": "mongodb"}


@app.get("/health")
def health():
    s = get_settings()
    try:
        mongo.db.client.admin.command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "mongodb",
        "db_connected": db_ok,
        "gemini_key_set": bool(s.google_api_key),
        "anthropic_key_set": bool(s.anthropic_api_key),
        "chat_model": "gemini-2.5-flash-lite",
    }
