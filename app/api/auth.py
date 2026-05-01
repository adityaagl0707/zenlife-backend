from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..services import auth_service
from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SendOTPRequest(BaseModel):
    phone: str


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str


class SignupRequest(BaseModel):
    phone: str
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    age: int = Field(ge=0, le=120)
    gender: str
    password: str = Field(min_length=6)
    confirm_password: str


class PasswordLoginRequest(BaseModel):
    phone: str
    password: str


def _user_payload(user) -> dict:
    return {
        "id": user["id"],
        "phone": user["phone"],
        "name": user.get("name"),
        "zen_id": user.get("zen_id"),
        "age": user.get("age"),
        "gender": user.get("gender"),
        "must_change_password": bool(user.get("must_change_password")),
    }


@router.post("/send-otp")
def send_otp(req: SendOTPRequest):
    if len(req.phone) != 10 or not req.phone.isdigit():
        raise HTTPException(status_code=400, detail="Invalid phone number")
    auth_service.get_or_create_user(req.phone)
    otp = auth_service.generate_otp(req.phone)
    return {"message": "OTP sent successfully", "debug_otp": otp}


@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest):
    valid = auth_service.verify_otp(req.phone, req.otp)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    user = auth_service.get_or_create_user(req.phone)
    token = auth_service.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": _user_payload(user)}


@router.post("/signup")
def signup(req: SignupRequest):
    if len(req.phone) != 10 or not req.phone.isdigit():
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit mobile number")
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    g = (req.gender or "").strip().lower()
    gender_norm = {
        "m": "Male", "male": "Male",
        "f": "Female", "female": "Female",
        "o": "Other", "other": "Other",
    }.get(g)
    if not gender_norm:
        raise HTTPException(status_code=400, detail="Select a valid sex")
    try:
        user = auth_service.signup_user(
            phone=req.phone,
            first_name=req.first_name,
            last_name=req.last_name,
            age=req.age,
            gender=gender_norm,
            password=req.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    token = auth_service.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": _user_payload(user)}


@router.post("/login")
def password_login(req: PasswordLoginRequest):
    user = auth_service.login_with_password(req.phone, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid phone number or password")
    token = auth_service.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer", "user": _user_payload(user)}


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=6)
    confirm_password: str


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, current_user=Depends(get_current_user)):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    try:
        ok = auth_service.change_password(current_user["id"], req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}
