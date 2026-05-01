from fastapi import APIRouter, Depends, HTTPException
from ..core import mongo
from ..api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_or_404(report_id: int, user) -> dict:
    """Fetch a report and ensure it belongs to the current user. Returns dict
    with the report fields plus its embedded `order` for convenience."""
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    order = mongo.Order.find_one({"id": report["order_id"]})
    if not order or order.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Report not found")
    report["order"] = order
    return report


def _require_published(report: dict):
    if not report.get("is_published"):
        raise HTTPException(status_code=403, detail="Report not yet published")


def _date_str(d):
    return d.strftime("%d %b %Y") if d else None


@router.get("/{report_id}")
def get_report(report_id: int, current_user=Depends(get_current_user)):
    r = _report_or_404(report_id, current_user)
    order = r["order"]
    if not r.get("is_published"):
        return {
            "id": r["id"],
            "is_published": False,
            "patient_name": order.get("patient_name"),
            "booking_id": order.get("booking_id"),
        }
    finding_counts = {
        sev: mongo.Finding.count({"report_id": r["id"], "severity": sev})
        for sev in ("critical", "major", "minor", "normal")
    }
    return {
        "id": r["id"],
        "is_published": True,
        "patient_name": order.get("patient_name"),
        "patient_age": order.get("patient_age"),
        "patient_gender": order.get("patient_gender"),
        "booking_id": order.get("booking_id"),
        "coverage_index": r.get("coverage_index"),
        "overall_severity": r.get("overall_severity"),
        "report_date": _date_str(r.get("report_date")),
        "next_visit": _date_str(r.get("next_visit")),
        "summary": r.get("summary"),
        "finding_counts": finding_counts,
    }


@router.get("/{report_id}/organ-scores")
def get_organ_scores(report_id: int, current_user=Depends(get_current_user)):
    r = _report_or_404(report_id, current_user)
    _require_published(r)
    scores = sorted(
        mongo.OrganScore.find({"report_id": r["id"]}),
        key=lambda s: s.get("display_order", 0),
    )
    return [
        {
            "id": s["id"],
            "organ_name": s.get("organ_name"),
            "severity": s.get("severity"),
            "risk_label": s.get("risk_label"),
            "critical_count": s.get("critical_count", 0),
            "major_count": s.get("major_count", 0),
            "minor_count": s.get("minor_count", 0),
            "normal_count": s.get("normal_count", 0),
            "icon": s.get("icon"),
        }
        for s in scores
    ]


@router.get("/{report_id}/findings")
def get_findings(
    report_id: int,
    severity: str = None,
    test_type: str = None,
    current_user=Depends(get_current_user),
):
    r = _report_or_404(report_id, current_user)
    _require_published(r)
    q = {"report_id": r["id"]}
    if severity:
        q["severity"] = severity
    if test_type:
        q["test_type"] = test_type
    findings = mongo.Finding.find(q)
    return [
        {
            "id": f["id"],
            "test_type": f.get("test_type"),
            "name": f.get("name"),
            "severity": f.get("severity"),
            "value": f.get("value"),
            "normal_range": f.get("normal_range"),
            "unit": f.get("unit"),
            "description": f.get("description"),
            "clinical_findings": f.get("clinical_findings"),
            "recommendations": f.get("recommendations"),
            "extra_data": f.get("extra_data"),
        }
        for f in findings
    ]


@router.get("/{report_id}/priorities")
def get_priorities(report_id: int, current_user=Depends(get_current_user)):
    r = _report_or_404(report_id, current_user)
    _require_published(r)
    priorities = sorted(
        mongo.HealthPriority.find({"report_id": r["id"]}),
        key=lambda p: p.get("priority_order", 0),
    )
    return [
        {
            "id": p["id"],
            "priority_order": p.get("priority_order"),
            "title": p.get("title"),
            "why_important": p.get("why_important"),
            "diet_recommendations": p.get("diet_recommendations"),
            "exercise_recommendations": p.get("exercise_recommendations"),
            "sleep_recommendations": p.get("sleep_recommendations"),
            "supplement_recommendations": p.get("supplement_recommendations"),
        }
        for p in priorities
    ]


@router.get("/{report_id}/body-age")
def get_body_age(report_id: int, current_user=Depends(get_current_user)):
    r = _report_or_404(report_id, current_user)
    ba = mongo.BodyAgeDoc.find_one({"report_id": r["id"]})

    # Auto-calculate on first fetch if findings exist but no body age record yet
    if not ba:
        findings = mongo.Finding.find({"report_id": r["id"]})
        if findings:
            try:
                from ..services.body_age_service import calculate_pheno_age, calculate_zen_age
                order = r["order"]
                pheno_result = calculate_pheno_age(findings)
                zen_result = calculate_zen_age(r, findings, pheno_result)
                ba_doc = {
                    "report_id": r["id"],
                    "chronological_age": pheno_result.get("chronological_age"),
                    "pheno_age": pheno_result.get("pheno_age"),
                    "zen_age": zen_result.get("zen_age"),
                    "age_difference": zen_result.get("age_difference"),
                    "interpretation": zen_result.get("interpretation"),
                    "markers_used": pheno_result.get("markers_found", []),
                    "markers_missing": pheno_result.get("markers_missing", []),
                    "confidence": zen_result.get("confidence"),
                    "sub_ages": zen_result.get("sub_ages", {}),
                    "created_at": mongo.now(),
                    "updated_at": mongo.now(),
                }
                mongo.BodyAgeDoc.insert(ba_doc)
                ba = mongo.doc(ba_doc)
            except Exception:
                return None

    if not ba:
        return None

    return {
        "chronological_age": ba.get("chronological_age"),
        "pheno_age": ba.get("pheno_age"),
        "zen_age": ba.get("zen_age"),
        "age_difference": ba.get("age_difference"),
        "confidence": ba.get("confidence"),
        "interpretation": ba.get("interpretation"),
        "markers_used": ba.get("markers_used") or [],
        "markers_missing": ba.get("markers_missing") or [],
        "sub_ages": ba.get("sub_ages") or {},
    }


@router.get("/{report_id}/notes")
def get_notes(report_id: int, current_user=Depends(get_current_user)):
    r = _report_or_404(report_id, current_user)
    notes = mongo.ConsultationNote.find({"report_id": r["id"]})
    return [
        {
            "id": n["id"],
            "note_type": n.get("note_type"),
            "content": n.get("content"),
            "author": n.get("author"),
            "created_at": n["created_at"].isoformat() if n.get("created_at") else None,
        }
        for n in notes
    ]
