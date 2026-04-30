from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env", override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.database import Base, engine, SessionLocal
from app.core.config import get_settings
from app.api import auth, orders, reports, chat, admin
from app.services.seed_service import seed_demo
# Import all models so Base.metadata.create_all covers every table
import app.models.report  # noqa: F401 — registers Report, BodyAge, etc. with Base

settings = get_settings()

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ZenLife API",
    description="Backend for ZenLife — India's most advanced preventive health intelligence platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure CORS headers are present even on unhandled 500 errors
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


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed_demo(db)
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "ZenLife API v1.0", "status": "healthy"}


@app.get("/health")
def health():
    from app.core.config import get_settings
    s = get_settings()
    return {
        "status": "ok",
        "gemini_key_set": bool(s.google_api_key),
        "anthropic_key_set": bool(s.anthropic_api_key),
        "chat_model": "gemini-2.5-flash-lite",
    }
