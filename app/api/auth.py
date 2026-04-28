from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class SendOTPRequest(BaseModel):
    phone: str


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str


@router.post("/send-otp")
def send_otp(req: SendOTPRequest, db: Session = Depends(get_db)):
    if len(req.phone) != 10 or not req.phone.isdigit():
        raise HTTPException(status_code=400, detail="Invalid phone number")
    auth_service.get_or_create_user(db, req.phone)
    otp = auth_service.generate_otp(db, req.phone)
    # In prod: send via SMS gateway
    return {"message": "OTP sent successfully", "debug_otp": otp}


@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    valid = auth_service.verify_otp(db, req.phone, req.otp)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    user = auth_service.get_or_create_user(db, req.phone)
    token = auth_service.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": {
        "id": user.id, "phone": user.phone, "name": user.name
    }}
