from datetime import datetime, timedelta
from ..core import mongo
from ..core.security import create_access_token
from ..core.config import get_settings

settings = get_settings()


def get_or_create_user(phone: str):
    user = mongo.User.find_one({"phone": phone})
    if user:
        return user
    new_user = {
        "phone": phone,
        "name": None,
        "email": None,
        "age": None,
        "gender": None,
        "is_active": True,
        "created_at": mongo.now(),
    }
    mongo.User.insert(new_user)
    return mongo.doc(new_user)


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
