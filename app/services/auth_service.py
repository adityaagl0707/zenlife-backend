from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.user import User
from ..models.order import OTPSession
from ..core.security import create_access_token
from ..core.config import get_settings
import random

settings = get_settings()


def get_or_create_user(db: Session, phone: str) -> User:
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def generate_otp(db: Session, phone: str) -> str:
    otp = settings.mock_otp  # In prod: str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=settings.otp_expire_minutes)
    session = OTPSession(phone=phone, otp=otp, expires_at=expires_at)
    db.add(session)
    db.commit()
    return otp


def verify_otp(db: Session, phone: str, otp: str) -> bool:
    session = (
        db.query(OTPSession)
        .filter(
            OTPSession.phone == phone,
            OTPSession.otp == otp,
            OTPSession.used == False,
            OTPSession.expires_at > datetime.utcnow(),
        )
        .order_by(OTPSession.created_at.desc())
        .first()
    )
    if session:
        session.used = True
        db.commit()
        return True
    return False


def create_token_for_user(user: User) -> str:
    return create_access_token({"sub": str(user.id), "phone": user.phone})
