from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class OTPSession(Base):
    __tablename__ = "otp_sessions"

    id = Column(Integer, primary_key=True)
    phone = Column(String, index=True)
    otp = Column(String)
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="otp_sessions")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    patient_name = Column(String)
    patient_age = Column(Integer)
    patient_gender = Column(String)
    scan_type = Column(String, default="ZenScan")
    status = Column(String, default="pending")  # pending, scheduled, completed
    scan_date = Column(DateTime, nullable=True)
    next_visit = Column(DateTime, nullable=True)
    amount = Column(Float, default=27500)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    report = relationship("Report", back_populates="order", uselist=False)
