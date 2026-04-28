from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    coverage_index = Column(Float, default=90.0)
    overall_severity = Column(String, default="normal")  # normal, minor, major, critical
    report_date = Column(DateTime, default=datetime.utcnow)
    next_visit = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)

    order = relationship("Order", back_populates="report")
    organ_scores = relationship("OrganScore", back_populates="report")
    findings = relationship("Finding", back_populates="report")
    priorities = relationship("HealthPriority", back_populates="report")
    notes = relationship("ConsultationNote", back_populates="report")
    chat_messages = relationship("ChatMessage", back_populates="report")


class OrganScore(Base):
    __tablename__ = "organ_scores"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    organ_name = Column(String)
    severity = Column(String)  # critical, major, minor, normal
    risk_label = Column(String)
    critical_count = Column(Integer, default=0)
    major_count = Column(Integer, default=0)
    minor_count = Column(Integer, default=0)
    normal_count = Column(Integer, default=0)
    icon = Column(String, nullable=True)
    display_order = Column(Integer, default=0)

    report = relationship("Report", back_populates="organ_scores")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    test_type = Column(String)  # blood_urine, dexa, calcium_score, lung, ecg, mri
    name = Column(String)
    severity = Column(String)  # critical, major, minor, normal
    value = Column(String, nullable=True)
    normal_range = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    clinical_findings = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)

    report = relationship("Report", back_populates="findings")


class HealthPriority(Base):
    __tablename__ = "health_priorities"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    priority_order = Column(Integer)
    title = Column(String)
    why_important = Column(Text)
    diet_recommendations = Column(JSON, nullable=True)
    exercise_recommendations = Column(JSON, nullable=True)
    sleep_recommendations = Column(JSON, nullable=True)
    supplement_recommendations = Column(JSON, nullable=True)

    report = relationship("Report", back_populates="priorities")


class ConsultationNote(Base):
    __tablename__ = "consultation_notes"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    note_type = Column(String, default="doctor")  # doctor, patient
    content = Column(Text)
    author = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="notes")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    role = Column(String)  # user, assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="chat_messages")
