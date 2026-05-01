from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.user import User
from ..models.report import Report, OrganScore, Finding, HealthPriority, ConsultationNote
from ..models.order import Order
from ..api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_or_404(report_id: int, user: User, db: Session) -> Report:
    report = (
        db.query(Report)
        .join(Order)
        .filter(Report.id == report_id, Order.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _require_published(report: Report):
    """Raise 403 if report is not published (for data endpoints)."""
    if not getattr(report, "is_published", False):
        raise HTTPException(status_code=403, detail="Report not yet published")


@router.get("/{report_id}")
def get_report(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _report_or_404(report_id, current_user, db)
    is_published = getattr(r, "is_published", False)
    # Return minimal info if not published so frontend can show "In Progress"
    if not is_published:
        return {
            "id": r.id,
            "is_published": False,
            "patient_name": r.order.patient_name,
            "booking_id": r.order.booking_id,
        }
    return {
        "id": r.id,
        "is_published": True,
        "patient_name": r.order.patient_name,
        "patient_age": r.order.patient_age,
        "patient_gender": r.order.patient_gender,
        "booking_id": r.order.booking_id,
        "coverage_index": r.coverage_index,
        "overall_severity": r.overall_severity,
        "report_date": r.report_date.strftime("%d %b %Y") if r.report_date else None,
        "next_visit": r.next_visit.strftime("%d %b %Y") if r.next_visit else None,
        "summary": r.summary,
        "finding_counts": {
            "critical": db.query(Finding).filter(Finding.report_id == r.id, Finding.severity == "critical").count(),
            "major": db.query(Finding).filter(Finding.report_id == r.id, Finding.severity == "major").count(),
            "minor": db.query(Finding).filter(Finding.report_id == r.id, Finding.severity == "minor").count(),
            "normal": db.query(Finding).filter(Finding.report_id == r.id, Finding.severity == "normal").count(),
        },
    }


@router.get("/{report_id}/organ-scores")
def get_organ_scores(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _report_or_404(report_id, current_user, db)
    _require_published(r)
    scores = db.query(OrganScore).filter(OrganScore.report_id == r.id).order_by(OrganScore.display_order).all()
    return [
        {
            "id": s.id,
            "organ_name": s.organ_name,
            "severity": s.severity,
            "risk_label": s.risk_label,
            "critical_count": s.critical_count,
            "major_count": s.major_count,
            "minor_count": s.minor_count,
            "normal_count": s.normal_count,
            "icon": s.icon,
        }
        for s in scores
    ]


@router.get("/{report_id}/findings")
def get_findings(
    report_id: int,
    severity: str = None,
    test_type: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = _report_or_404(report_id, current_user, db)
    _require_published(r)
    q = db.query(Finding).filter(Finding.report_id == r.id)
    if severity:
        q = q.filter(Finding.severity == severity)
    if test_type:
        q = q.filter(Finding.test_type == test_type)
    findings = q.all()
    return [
        {
            "id": f.id,
            "test_type": f.test_type,
            "name": f.name,
            "severity": f.severity,
            "value": f.value,
            "normal_range": f.normal_range,
            "unit": f.unit,
            "description": f.description,
            "clinical_findings": f.clinical_findings,
            "recommendations": f.recommendations,
            "extra_data": f.extra_data,
        }
        for f in findings
    ]


@router.get("/{report_id}/priorities")
def get_priorities(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _report_or_404(report_id, current_user, db)
    _require_published(r)
    priorities = db.query(HealthPriority).filter(HealthPriority.report_id == r.id).order_by(HealthPriority.priority_order).all()
    return [
        {
            "id": p.id,
            "priority_order": p.priority_order,
            "title": p.title,
            "why_important": p.why_important,
            "diet_recommendations": p.diet_recommendations,
            "exercise_recommendations": p.exercise_recommendations,
            "sleep_recommendations": p.sleep_recommendations,
            "supplement_recommendations": p.supplement_recommendations,
        }
        for p in priorities
    ]


@router.get("/{report_id}/body-age")
def get_body_age(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from ..models.report import BodyAge
    r = _report_or_404(report_id, current_user, db)
    ba = db.query(BodyAge).filter(BodyAge.report_id == r.id).first()

    # Auto-calculate on first fetch if findings exist but no body age record yet
    if not ba:
        findings = db.query(Finding).filter(Finding.report_id == r.id).all()
        if findings:
            try:
                from ..services.body_age_service import calculate_pheno_age, calculate_zen_age
                import asyncio
                pheno_result = calculate_pheno_age(findings, r.patient_age)
                zen_result = asyncio.run(calculate_zen_age(r, findings, pheno_result))
                ba = BodyAge(
                    report_id=r.id,
                    chronological_age=pheno_result.get("chronological_age"),
                    pheno_age=pheno_result.get("pheno_age"),
                    zen_age=zen_result.get("zen_age"),
                    age_difference=zen_result.get("age_difference"),
                    interpretation=zen_result.get("interpretation"),
                    markers_used=pheno_result.get("markers_found", []),
                    markers_missing=pheno_result.get("markers_missing", []),
                    confidence=zen_result.get("confidence"),
                    sub_ages=zen_result.get("sub_ages", {}),
                )
                db.add(ba)
                db.commit()
                db.refresh(ba)
            except Exception:
                # If auto-calculation fails, return None gracefully
                return None

    if not ba:
        return None

    return {
        "chronological_age": ba.chronological_age,
        "pheno_age": ba.pheno_age,
        "zen_age": ba.zen_age,
        "age_difference": ba.age_difference,
        "confidence": ba.confidence,
        "interpretation": ba.interpretation,
        "markers_used": ba.markers_used or [],
        "markers_missing": ba.markers_missing or [],
        "sub_ages": ba.sub_ages or {},
    }


@router.get("/{report_id}/notes")
def get_notes(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _report_or_404(report_id, current_user, db)
    notes = db.query(ConsultationNote).filter(ConsultationNote.report_id == r.id).all()
    return [
        {
            "id": n.id,
            "note_type": n.note_type,
            "content": n.content,
            "author": n.author,
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]
