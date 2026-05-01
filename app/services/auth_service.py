import hashlib
import os
import secrets
from datetime import datetime, timedelta
from ..core import mongo
from ..core.security import create_access_token
from ..core.config import get_settings

settings = get_settings()


# ── Password hashing (PBKDF2-SHA256) ─────────────────────────────────────────
_ITER = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITER)
    return f"pbkdf2_sha256${_ITER}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, hexhash = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return secrets.compare_digest(dk.hex(), hexhash)
    except Exception:
        return False


# ── Zen ID ───────────────────────────────────────────────────────────────────

def _generate_zen_id() -> str:
    """Generate a unique ZEN ID like ZEN000123."""
    for _ in range(8):
        seq = mongo.next_id("zen_id")
        zid = f"ZEN{seq:06d}"
        if not mongo.User.find_one({"zen_id": zid}):
            return zid
    # fallback
    return f"ZEN{secrets.randbelow(10**8):08d}"


# ── Users ────────────────────────────────────────────────────────────────────

def get_or_create_user(phone: str):
    user = mongo.User.find_one({"phone": phone})
    if user:
        # Backfill zen_id for existing users (idempotent)
        if not user.get("zen_id"):
            zid = _generate_zen_id()
            mongo.User.update_one({"id": user["id"]}, {"$set": {"zen_id": zid}})
            user["zen_id"] = zid
        return user
    new_user = {
        "phone": phone,
        "name": None,
        "email": None,
        "age": None,
        "gender": None,
        "zen_id": _generate_zen_id(),
        "is_active": True,
        "created_at": mongo.now(),
    }
    mongo.User.insert(new_user)
    return mongo.doc(new_user)


def signup_user(*, phone: str, first_name: str, last_name: str, age: int, gender: str, password: str):
    """Create a new patient via the public signup form. Errors if phone already exists."""
    existing = mongo.User.find_one({"phone": phone})
    if existing:
        raise ValueError("An account with this phone number already exists. Please sign in instead.")
    name = f"{first_name.strip()} {last_name.strip()}".strip()
    user = {
        "phone": phone,
        "name": name,
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "age": age,
        "gender": gender,
        "email": None,
        "zen_id": _generate_zen_id(),
        "password_hash": hash_password(password),
        "must_change_password": False,
        "is_active": True,
        "created_at": mongo.now(),
    }
    mongo.User.insert(user)
    return mongo.doc(user)


def change_password(user_id: int, new_password: str) -> bool:
    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters")
    user = mongo.User.find_one({"id": user_id})
    if not user:
        return False
    mongo.User.update_one(
        {"id": user_id},
        {"$set": {
            "password_hash": hash_password(new_password),
            "must_change_password": False,
        }},
    )
    return True


def login_with_password(phone: str, password: str):
    user = mongo.User.find_one({"phone": phone})
    if not user or not user.get("password_hash"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


# ── OTP ──────────────────────────────────────────────────────────────────────

def generate_otp(phone: str) -> str:
    otp = settings.mock_otp  # In prod: str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=settings.otp_expire_minutes)
    mongo.OTPSession.insert({
        "phone": phone,
        "otp": otp,
        "expires_at": expires_at,
        "used": False,
        "created_at": mongo.now(),
        "user_id": None,
    })
    return otp


def verify_otp(phone: str, otp: str) -> bool:
    session = mongo.otp_sessions.find_one(
        {
            "phone": phone,
            "otp": otp,
            "used": False,
            "expires_at": {"$gt": datetime.utcnow()},
        },
        sort=[("created_at", -1)],
    )
    if session:
        mongo.otp_sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"used": True}},
        )
        return True
    return False


def create_token_for_user(user) -> str:
    return create_access_token({"sub": str(user["id"]), "phone": user["phone"]})
