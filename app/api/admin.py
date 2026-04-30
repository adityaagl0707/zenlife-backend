"""Admin API — local dev only. Allows creating patients, orders, reports, and findings via UI."""
import base64
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from ..core.database import get_db
from ..models.user import User
from ..models.order import Order
from ..models.report import Report, OrganScore, Finding, HealthPriority, ConsultationNote, ReportSection
from ..services.lab_classifier import parse_excel_lab_results, generate_template_excel, MARKERS, classify_severity
from ..services.section_params import SECTION_PARAMETERS, SECTION_META
from ..services.ai_service import extract_report_parameters, generate_priorities
from ..services.organ_param_map import ORGAN_DEFINITIONS, RISK_LABELS

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


def _trigger_body_age(report_id: int, db: Session) -> None:
    """Background helper: (re)calculate body age whenever findings change."""
    try:
        from ..services.body_age_service import calculate_pheno_age, calculate_zen_age
        from ..models.report import BodyAge

        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return

        findings = db.query(Finding).filter(Finding.report_id == report_id).all()
        if not findings:
            return

        pheno_result = calculate_pheno_age(findings)
        zen_result = calculate_zen_age(report, findings, pheno_result)

        actual_age = report.order.patient_age if report.order else None
        zen_age = zen_result.get("zen_age")
        age_diff = round(zen_age - actual_age, 1) if (zen_age and actual_age) else zen_result.get("age_difference", 0)

        existing = db.query(BodyAge).filter(BodyAge.report_id == report_id).first()
        ba = existing if existing else BodyAge(report_id=report_id)
        if not existing:
            db.add(ba)

        ba.chronological_age = actual_age
        ba.pheno_age = pheno_result.get("pheno_age")
        ba.zen_age = zen_age
        ba.age_difference = age_diff
        ba.interpretation = zen_result.get("interpretation", "")
        ba.markers_used = pheno_result.get("markers_found", [])
        ba.markers_missing = pheno_result.get("markers_missing", [])
        ba.confidence = zen_result.get("confidence", "medium")
        ba.sub_ages = zen_result.get("sub_ages", {})

        db.commit()
    except Exception:
        pass  # Never fail the response due to body-age errors


@router.post("/reports/{report_id}/findings")
def add_finding(report_id: int, body: CreateFinding, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not db.query(Report).filter(Report.id == report_id).first():
        raise HTTPException(status_code=404, detail="Report not found")
    finding = Finding(report_id=report_id, **body.model_dump())
    db.add(finding)
    db.commit()
    db.refresh(finding)
    background_tasks.add_task(_trigger_body_age, report_id, db)
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


# ── Report Sections ───────────────────────────────────────────────────────────

@router.get("/section-params")
def get_section_params():
    """Return all section types with their parameter definitions."""
    return {
        "sections": SECTION_META,
        "parameters": {k: v for k, v in SECTION_PARAMETERS.items()},
    }


@router.get("/reports/{report_id}/sections")
def get_all_sections(report_id: int, db: Session = Depends(get_db)):
    """Get all saved sections for a report."""
    sections = db.query(ReportSection).filter(ReportSection.report_id == report_id).all()
    return {
        s.section_type: {
            "key_findings": s.key_findings,
            "parameters": s.parameters or {},
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sections
    }


@router.get("/reports/{report_id}/sections/{section_type}")
def get_section(report_id: int, section_type: str, db: Session = Depends(get_db)):
    """Get a single section with its saved parameters."""
    section = (
        db.query(ReportSection)
        .filter(ReportSection.report_id == report_id, ReportSection.section_type == section_type)
        .first()
    )
    param_defs = SECTION_PARAMETERS.get(section_type, [])
    saved = section.parameters or {} if section else {}
    return {
        "section_type": section_type,
        "key_findings": section.key_findings if section else "",
        "parameters": saved,
        "param_definitions": param_defs,
        "meta": SECTION_META.get(section_type, {}),
    }


class SaveSectionBody(BaseModel):
    key_findings: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


@router.put("/reports/{report_id}/sections/{section_type}")
def save_section(report_id: int, section_type: str, body: SaveSectionBody, db: Session = Depends(get_db)):
    """Save (create or update) a report section with its parameters and key findings."""
    if section_type not in SECTION_PARAMETERS:
        raise HTTPException(status_code=400, detail=f"Unknown section type: {section_type}")
    section = (
        db.query(ReportSection)
        .filter(ReportSection.report_id == report_id, ReportSection.section_type == section_type)
        .first()
    )
    if section:
        if body.key_findings is not None:
            section.key_findings = body.key_findings
        if body.parameters is not None:
            section.parameters = body.parameters
        section.updated_at = datetime.utcnow()
    else:
        section = ReportSection(
            report_id=report_id,
            section_type=section_type,
            key_findings=body.key_findings or "",
            parameters=body.parameters or {},
        )
        db.add(section)
    db.commit()
    db.refresh(section)
    return {"ok": True, "section_type": section_type}


@router.post("/reports/{report_id}/sections/{section_type}/extract")
async def extract_section(report_id: int, section_type: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a report file, extract parameter values via Claude AI, and save to section."""
    if section_type not in SECTION_PARAMETERS:
        raise HTTPException(status_code=400, detail=f"Unknown section type: {section_type}")

    content = await file.read()
    file_b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"

    extracted = extract_report_parameters(section_type, file_b64, mime)

    if "_parse_error" in extracted or "error" in extracted:
        raise HTTPException(status_code=422, detail=extracted.get("_parse_error") or extracted.get("error"))

    # Save extracted data to the section
    section = (
        db.query(ReportSection)
        .filter(ReportSection.report_id == report_id, ReportSection.section_type == section_type)
        .first()
    )
    if section:
        section.parameters = extracted
        section.updated_at = datetime.utcnow()
    else:
        section = ReportSection(
            report_id=report_id,
            section_type=section_type,
            parameters=extracted,
        )
        db.add(section)
    db.commit()
    return {"ok": True, "extracted": extracted}


@router.post("/reports/{report_id}/sections/{section_type}/import-findings")
def import_section_as_findings(report_id: int, section_type: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Convert all saved section parameters into Finding records on the report."""
    section = (
        db.query(ReportSection)
        .filter(ReportSection.report_id == report_id, ReportSection.section_type == section_type)
        .first()
    )
    if not section or not section.parameters:
        raise HTTPException(status_code=404, detail="No saved parameters for this section")

    param_defs = {p["name"]: p for p in SECTION_PARAMETERS.get(section_type, [])}
    created = 0
    for param_name, data in section.parameters.items():
        if isinstance(data, dict):
            value = data.get("value", "")
        else:
            value = str(data)

        if not value or value == "Not Found":
            continue

        p = param_defs.get(param_name, {})
        severity = data.get("severity", "normal") if isinstance(data, dict) else "normal"
        clinical = data.get("clinical_findings", "") if isinstance(data, dict) else ""
        recs = data.get("recommendations", "") if isinstance(data, dict) else ""

        # Skip if finding already exists for this report+name
        exists = db.query(Finding).filter(Finding.report_id == report_id, Finding.name == param_name).first()
        if exists:
            exists.value = str(value)
            exists.severity = severity
            exists.clinical_findings = clinical
            exists.recommendations = recs
        else:
            db.add(Finding(
                report_id=report_id,
                test_type=section_type,
                name=param_name,
                severity=severity,
                value=str(value),
                normal_range=p.get("normal", ""),
                unit=p.get("unit", ""),
                clinical_findings=clinical,
                recommendations=recs,
            ))
            created += 1

    db.commit()
    background_tasks.add_task(_trigger_body_age, report_id, db)
    return {"ok": True, "imported": created}


@router.post("/reports/{report_id}/sync-organs")
def sync_organs(report_id: int, db: Session = Depends(get_db)):
    """
    Auto-create or update all organ score records (one per organ system in ORGAN_DEFINITIONS),
    computing severity counts from the report's Finding records via the organ-parameter mapping.
    """
    if not db.query(Report).filter(Report.id == report_id).first():
        raise HTTPException(status_code=404, detail="Report not found")

    findings = db.query(Finding).filter(Finding.report_id == report_id).all()
    finding_sev = {f.name.lower().strip(): f.severity for f in findings}

    for defn in ORGAN_DEFINITIONS:
        counts = {"critical": 0, "major": 0, "minor": 0, "normal": 0}
        for p in defn["params"]:
            sev = finding_sev.get(p)
            if sev and sev in counts:
                counts[sev] += 1

        if counts["critical"] > 0:
            severity = "critical"
        elif counts["major"] > 0:
            severity = "major"
        elif counts["minor"] > 0:
            severity = "minor"
        else:
            severity = "normal"

        risk_label = RISK_LABELS[severity]

        existing = (
            db.query(OrganScore)
            .filter(OrganScore.report_id == report_id, OrganScore.organ_name == defn["organ_name"])
            .first()
        )
        if existing:
            existing.severity = severity
            existing.risk_label = risk_label
            existing.critical_count = counts["critical"]
            existing.major_count = counts["major"]
            existing.minor_count = counts["minor"]
            existing.normal_count = counts["normal"]
        else:
            db.add(OrganScore(
                report_id=report_id,
                organ_name=defn["organ_name"],
                severity=severity,
                risk_label=risk_label,
                icon=defn["icon"],
                critical_count=counts["critical"],
                major_count=counts["major"],
                minor_count=counts["minor"],
                normal_count=counts["normal"],
                display_order=defn["display_order"],
            ))

    db.commit()
    return {"ok": True, "organs": len(ORGAN_DEFINITIONS)}


@router.post("/sync-all-organs")
def sync_all_organs(db: Session = Depends(get_db)):
    """
    Run organ sync for EVERY report in the database.
    Useful after adding new organ systems — ensures all reports get the new organ rows.
    """
    all_reports = db.query(Report).all()
    results = []

    for report in all_reports:
        findings = db.query(Finding).filter(Finding.report_id == report.id).all()
        finding_sev = {f.name.lower().strip(): f.severity for f in findings}

        for defn in ORGAN_DEFINITIONS:
            counts = {"critical": 0, "major": 0, "minor": 0, "normal": 0}
            for p in defn["params"]:
                sev = finding_sev.get(p)
                if sev and sev in counts:
                    counts[sev] += 1

            severity = (
                "critical" if counts["critical"] > 0 else
                "major"    if counts["major"] > 0 else
                "minor"    if counts["minor"] > 0 else
                "normal"
            )
            risk_label = RISK_LABELS[severity]

            existing = (
                db.query(OrganScore)
                .filter(OrganScore.report_id == report.id, OrganScore.organ_name == defn["organ_name"])
                .first()
            )
            if existing:
                existing.severity        = severity
                existing.risk_label      = risk_label
                existing.critical_count  = counts["critical"]
                existing.major_count     = counts["major"]
                existing.minor_count     = counts["minor"]
                existing.normal_count    = counts["normal"]
                existing.icon            = defn["icon"]
                existing.display_order   = defn["display_order"]
            else:
                db.add(OrganScore(
                    report_id    = report.id,
                    organ_name   = defn["organ_name"],
                    severity     = severity,
                    risk_label   = risk_label,
                    icon         = defn["icon"],
                    critical_count  = counts["critical"],
                    major_count     = counts["major"],
                    minor_count     = counts["minor"],
                    normal_count    = counts["normal"],
                    display_order   = defn["display_order"],
                ))

        results.append(report.id)

    db.commit()
    return {"ok": True, "reports_synced": len(results), "organ_systems": len(ORGAN_DEFINITIONS)}


@router.post("/reports/{report_id}/calculate-body-age")
def calculate_body_age_endpoint(report_id: int, db: Session = Depends(get_db)):
    """Calculate body age using PhenoAge formula + Claude AI synthesis."""
    from ..services.body_age_service import calculate_pheno_age, calculate_zen_age
    from ..models.report import BodyAge

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    findings = db.query(Finding).filter(Finding.report_id == report_id).all()
    actual_age = report.order.patient_age if report.order else None

    # Step 1: PhenoAge
    pheno_result = calculate_pheno_age(findings)

    # Step 2: ZenAge (Claude AI)
    zen_result = calculate_zen_age(report, findings, pheno_result)

    zen_age = zen_result.get("zen_age")
    if zen_age and actual_age:
        age_diff = round(zen_age - actual_age, 1)
    else:
        age_diff = zen_result.get("age_difference", 0)

    # Upsert BodyAge record
    existing = db.query(BodyAge).filter(BodyAge.report_id == report_id).first()
    if existing:
        ba = existing
    else:
        ba = BodyAge(report_id=report_id)
        db.add(ba)

    ba.chronological_age = actual_age
    ba.pheno_age = pheno_result.get("pheno_age")
    ba.zen_age = zen_age
    ba.age_difference = age_diff
    ba.interpretation = zen_result.get("interpretation", "")
    ba.markers_used = pheno_result.get("markers_found", [])
    ba.markers_missing = pheno_result.get("markers_missing", [])
    ba.confidence = zen_result.get("confidence", "medium")
    ba.sub_ages = zen_result.get("sub_ages", {})

    db.commit()
    db.refresh(ba)

    return {
        "ok": True,
        "chronological_age": ba.chronological_age,
        "pheno_age": ba.pheno_age,
        "zen_age": ba.zen_age,
        "age_difference": ba.age_difference,
        "confidence": ba.confidence,
        "interpretation": ba.interpretation,
        "markers_used": ba.markers_used,
        "markers_missing": ba.markers_missing,
        "sub_ages": ba.sub_ages,
    }


@router.post("/reports/{report_id}/generate-priorities")
def auto_generate_priorities(report_id: int, db: Session = Depends(get_db)):
    """Use Claude to generate health priorities from findings and organ scores."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    findings = db.query(Finding).filter(Finding.report_id == report_id).all()
    organs = db.query(OrganScore).filter(OrganScore.report_id == report_id).order_by(OrganScore.display_order).all()

    priorities = generate_priorities(report, findings, organs)
    if not priorities:
        raise HTTPException(status_code=422, detail="AI could not generate priorities. Check API key or try again.")

    # Replace existing priorities
    db.query(HealthPriority).filter(HealthPriority.report_id == report_id).delete()

    for i, p in enumerate(priorities, 1):
        db.add(HealthPriority(
            report_id=report_id,
            priority_order=i,
            title=p.get("title", ""),
            why_important=p.get("why_important", ""),
            diet_recommendations=p.get("diet_recommendations", []),
            exercise_recommendations=p.get("exercise_recommendations", []),
            sleep_recommendations=p.get("sleep_recommendations", []),
            supplement_recommendations=p.get("supplement_recommendations", []),
        ))

    db.commit()
    return {"ok": True, "count": len(priorities)}
