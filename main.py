from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env", override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    return {"status": "ok"}
