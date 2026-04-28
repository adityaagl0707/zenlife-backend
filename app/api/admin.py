"""Admin API — local dev only. Allows creating patients, orders, reports, and findings via UI."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..core.database import get_db
from ..models.user import User
from ..models.order import Order
from ..models.report import Report, OrganScore, Finding, HealthPriority, ConsultationNote
from ..services.lab_classifier import parse_excel_lab_results, generate_template_excel, MARKERS, classify_severity

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreatePatient(BaseModel):
    phone: str
    name: str
    age: int
    gender: str
    email: Optional[str] = None

class CreateOrder(BaseModel):
    booking_id: str
    scan_type: str = "ZenScan"
    status: str = "completed"
    scan_date: Optional[str] = None   # ISO date string
    amount: float = 27500

class CreateReport(BaseModel):
    coverage_index: float = 90.0
    overall_severity: str = "normal"  # critical/major/minor/normal
    report_date: Optional[str] = None
    next_visit: Optional[str] = None
    summary: str = ""

class CreateOrganScore(BaseModel):
    organ_name: str
    severity: str = "normal"
    risk_label: str = "Healthy and Stable"
    icon: str = "🫀"
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    normal_count: int = 0
    display_order: int = 0

class CreateFinding(BaseModel):
    test_type: str
    name: str
    severity: str = "normal"
    value: Optional[str] = None
    normal_range: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    clinical_findings: Optional[str] = None
    recommendations: Optional[str] = None

class CreatePriority(BaseModel):
    priority_order: int = 1
    title: str
    why_important: str
    diet_recommendations: list[str] = []
    exercise_recommendations: list[str] = []
    sleep_recommendations: list[str] = []
    supplement_recommendations: list[str] = []

class CreateNote(BaseModel):
    note_type: str = "physician"
    content: str
    author: str = "Dr. ZenLife"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/patients")
def list_patients(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for u in users:
        orders = db.query(Order).filter(Order.user_id == u.id).all()
        result.append({
            "id": u.id,
            "phone": u.phone,
            "name": u.name,
            "age": u.age,
            "gender": u.gender,
            "orders": [
                {
                    "id": o.id,
                    "booking_id": o.booking_id,
                    "status": o.status,
                    "has_report": db.query(Report).filter(Report.order_id == o.id).first() is not None,
                    "report_id": (db.query(Report).filter(Report.order_id == o.id).first() or type("x", (), {"id": None})()).id,
                }
                for o in orders
            ],
        })
    return result


@router.post("/patients")
def create_patient(body: CreatePatient, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.phone == body.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Patient with this phone number already exists")
    user = User(phone=body.phone, name=body.name, age=body.age, gender=body.gender, email=body.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "phone": user.phone}


@router.post("/patients/{user_id}/orders")
def create_order(user_id: int, body: CreateOrder, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Patient not found")
    scan_date = datetime.fromisoformat(body.scan_date) if body.scan_date else datetime.now()
    order = Order(
        booking_id=body.booking_id,
        user_id=user_id,
        patient_name=user.name,
        patient_age=user.age,
        patient_gender=user.gender,
        scan_type=body.scan_type,
        status=body.status,
        scan_date=scan_date,
        next_visit=datetime(scan_date.year + 1, scan_date.month, scan_date.day),
        amount=body.amount,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"id": order.id, "booking_id": order.booking_id}


@router.post("/orders/{order_id}/report")
def create_report(order_id: int, body: CreateReport, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if db.query(Report).filter(Report.order_id == order_id).first():
        raise HTTPException(status_code=400, detail="Report already exists for this order")
    report_date = datetime.fromisoformat(body.report_date) if body.report_date else datetime.now()
    next_visit = datetime.fromisoformat(body.next_visit) if body.next_visit else datetime(report_date.year + 1, report_date.month, report_date.day)
    report = Report(
        order_id=order_id,
        coverage_index=body.coverage_index,
        overall_severity=body.overall_severity,
        report_date=report_date,
        next_visit=next_visit,
        summary=body.summary,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": report.id}


@router.post("/reports/{report_id}/organs")
def add_organ(report_id: int, body: CreateOrganScore, db: Session = Depends(get_db)):
    if not db.query(Report).filter(Report.id == report_id).first():
        raise HTTPException(status_code=404, detail="Report not found")
    organ = OrganScore(report_id=report_id, **body.model_dump())
    db.add(organ)
    db.commit()
    db.refresh(organ)
    return {"id": organ.id}


@router.delete("/reports/{report_id}/organs/{organ_id}")
def delete_organ(report_id: int, organ_id: int, db: Session = Depends(get_db)):
    organ = db.query(OrganScore).filter(OrganScore.id == organ_id, OrganScore.report_id == report_id).first()
    if not organ:
        raise HTTPException(status_code=404, detail="Organ score not found")
    db.delete(organ)
    db.commit()
    return {"ok": True}


@router.post("/reports/{report_id}/findings")
def add_finding(report_id: int, body: CreateFinding, db: Session = Depends(get_db)):
    if not db.query(Report).filter(Report.id == report_id).first():
        raise HTTPException(status_code=404, detail="Report not found")
    finding = Finding(report_id=report_id, **body.model_dump())
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return {"id": finding.id}


@router.delete("/reports/{report_id}/findings/{finding_id}")
def delete_finding(report_id: int, finding_id: int, db: Session = Depends(get_db)):
    f = db.query(Finding).filter(Finding.id == finding_id, Finding.report_id == report_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    db.delete(f)
    db.commit()
    return {"ok": True}


@router.post("/reports/{report_id}/priorities")
def add_priority(report_id: int, body: CreatePriority, db: Session = Depends(get_db)):
    if not db.query(Report).filter(Report.id == report_id).first():
        raise HTTPException(status_code=404, detail="Report not found")
    p = HealthPriority(report_id=report_id, **body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id}


@router.post("/reports/{report_id}/notes")
def add_note(report_id: int, body: CreateNote, db: Session = Depends(get_db)):
    if not db.query(Report).filter(Report.id == report_id).first():
        raise HTTPException(status_code=404, detail="Report not found")
    note = ConsultationNote(report_id=report_id, **body.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"id": note.id}


@router.get("/lab-template")
def download_lab_template():
    """Download the pre-filled Excel template for lab results."""
    content = generate_template_excel()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ZenLife_Lab_Template.xlsx"},
    )


@router.post("/upload-lab-results")
async def upload_lab_results(file: UploadFile = File(...)):
    """Parse uploaded Excel lab results and return classified findings."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are supported")
    content = await file.read()
    findings = parse_excel_lab_results(content)
    return {"findings": findings}


@router.get("/markers")
def list_markers():
    """Return the full marker list for the manual entry table."""
    return {"markers": MARKERS}


@router.post("/classify-value")
def classify_value(body: dict):
    """Classify a single lab value given value_str and normal_range."""
    severity = classify_severity(str(body.get("value", "")), str(body.get("normal_range", "")))
    return {"severity": severity}


@router.get("/reports/{report_id}/detail")
def get_report_detail(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    organs = db.query(OrganScore).filter(OrganScore.report_id == report_id).order_by(OrganScore.display_order).all()
    findings = db.query(Finding).filter(Finding.report_id == report_id).all()
    priorities = db.query(HealthPriority).filter(HealthPriority.report_id == report_id).order_by(HealthPriority.priority_order).all()
    notes = db.query(ConsultationNote).filter(ConsultationNote.report_id == report_id).all()
    return {
        "report_id": report_id,
        "coverage_index": report.coverage_index,
        "overall_severity": report.overall_severity,
        "summary": report.summary,
        "organs": [{"id": o.id, "organ_name": o.organ_name, "severity": o.severity, "icon": o.icon, "risk_label": o.risk_label, "critical_count": o.critical_count, "major_count": o.major_count, "minor_count": o.minor_count, "normal_count": o.normal_count} for o in organs],
        "findings": [{"id": f.id, "name": f.name, "severity": f.severity, "test_type": f.test_type, "value": f.value, "unit": f.unit, "normal_range": f.normal_range} for f in findings],
        "priorities": [{"id": p.id, "title": p.title, "priority_order": p.priority_order} for p in priorities],
        "notes": [{"id": n.id, "note_type": n.note_type, "author": n.author} for n in notes],
    }
