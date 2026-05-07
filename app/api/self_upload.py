"""Patient-initiated upload of existing reports.

The patient is the actor here (no admin / centre involved). They upload
PDFs / images of any tests they already have; we run the same AI
extraction pipeline that admin uses, materialise findings, and render
the standard report page with a `source: "self_uploaded"` flag so the
UI can show coverage-aware gating ('not enough data' vs 'all healthy').

A self-uploaded Report is NOT tied to an Order — the patient owns it
directly via user_id. ZenScan reports remain tied to Orders.
"""
import base64
from datetime import datetime
from typing import Optional, Dict
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..core import mongo
from ..api.deps import get_current_user
from ..services.ai_service import extract_report_parameters, generate_priorities, generate_health_plan
from ..services.section_params import SECTION_PARAMETERS, filter_params_by_gender
from ..services.lab_classifier import classify_severity

router = APIRouter(prefix="/self-upload", tags=["self-upload"])


def _placeholder(v: Optional[str]) -> bool:
    return not v or str(v).strip().lower() in ("not found", "n/a", "na", "none", "-", "")


def _get_or_create_self_report(user_id: int) -> dict:
    """Each user has one self-uploaded report at a time. We grow it
    section-by-section as the patient uploads more. (Multiple-report
    support is Phase 4.)

    Soft-deleted reports (deleted_at set) are skipped so the patient
    can start fresh after deleting their previous one. Admin still sees
    the tombstone via /admin/patients."""
    existing = mongo.Report.find_one({
        "user_id": user_id,
        "source": "self_uploaded",
    })
    if existing and not existing.get("deleted_at"):
        return existing

    report = {
        "user_id": user_id,
        "source": "self_uploaded",
        "is_published": True,  # patient-owned: always visible to themselves
        "report_date": datetime.now(),
        "next_visit": None,
        "coverage_index": 0.0,
        "overall_severity": "normal",
        "summary": "",
        "uploaded_sections": [],
        "created_at": datetime.now(),
    }
    mongo.Report.insert(report)
    return report


def _user_owns_self_report(report_id: int, user_id: int) -> Optional[dict]:
    r = mongo.Report.find_one({"id": report_id, "source": "self_uploaded"})
    if not r or r.get("user_id") != user_id or r.get("deleted_at"):
        return None
    return r


def _persist_section(report_id: int, section_type: str, extracted: Dict) -> int:
    """Save extracted params into the section, then materialise Finding docs.
    Returns count of findings created/updated."""
    # 1. ReportSection
    existing = mongo.ReportSection.find_one({"report_id": report_id, "section_type": section_type})
    parameters: Dict = {}
    for name, val in (extracted or {}).items():
        if isinstance(val, dict):
            parameters[name] = val
        else:
            parameters[name] = {"value": str(val), "severity": "normal", "clinical_findings": "", "recommendations": ""}
    if existing:
        # Merge — don't lose previous values
        merged = {**(existing.get("parameters") or {}), **parameters}
        mongo.ReportSection.update_one(
            {"id": existing["id"]},
            {"$set": {"parameters": merged, "updated_at": datetime.now()}},
        )
    else:
        mongo.ReportSection.insert({
            "report_id": report_id,
            "section_type": section_type,
            "key_findings": "",
            "parameters": parameters,
            "created_at": datetime.now(),
        })

    # 2. Findings — same logic as admin import-findings
    param_defs = {p["name"]: p for p in SECTION_PARAMETERS.get(section_type, [])}
    count = 0
    for name, data in parameters.items():
        value = data.get("value") if isinstance(data, dict) else str(data)
        is_missing = _placeholder(value)
        if is_missing:
            severity = "normal"
            clinical = ""
            recs = ""
            value = "Not Found"
        else:
            severity = data.get("severity", "normal") if isinstance(data, dict) else "normal"
            clinical = data.get("clinical_findings", "") if isinstance(data, dict) else ""
            recs = data.get("recommendations", "") if isinstance(data, dict) else ""
            # Re-classify severity if AI didn't tag (uses normal_range)
            if severity == "normal":
                p = param_defs.get(name, {})
                if p.get("normal"):
                    classified = classify_severity(str(value), p["normal"])
                    if classified:
                        severity = classified

        p = param_defs.get(name, {})
        existing_f = mongo.Finding.find_one({"report_id": report_id, "name": name})
        doc = {
            "value": str(value),
            "severity": severity,
            "clinical_findings": clinical,
            "recommendations": recs,
        }
        if existing_f:
            mongo.Finding.update_one({"id": existing_f["id"]}, {"$set": doc})
        else:
            mongo.Finding.insert({
                "report_id": report_id,
                "test_type": section_type,
                "name": name,
                "normal_range": p.get("normal", ""),
                "unit": p.get("unit", ""),
                **doc,
            })
            count += 1
    return count


def _mark_uploaded(report_id: int, section_type: str) -> None:
    r = mongo.Report.find_one({"id": report_id})
    sections = list(set((r.get("uploaded_sections") or []) + [section_type]))
    mongo.Report.update_one({"id": report_id}, {"$set": {"uploaded_sections": sections}})


# ── Schemas ──────────────────────────────────────────────────────────────────

class StartResponse(BaseModel):
    report_id: int
    uploaded_sections: list[str]


class ExtractResponse(BaseModel):
    section_type: str
    findings_count: int
    extracted_param_count: int


class FinalizeResponse(BaseModel):
    coverage_pct: float
    sections_uploaded: list[str]
    overall_severity: str
    finding_counts: dict


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/start", response_model=StartResponse)
def start(current_user=Depends(get_current_user)):
    """Get (or create) the patient's self-uploaded report id."""
    r = _get_or_create_self_report(current_user["id"])
    return {"report_id": r["id"], "uploaded_sections": r.get("uploaded_sections") or []}


@router.get("/status")
def status(current_user=Depends(get_current_user)):
    """Returns the user's self-uploaded report metadata.

    Two flags drive the dashboard:
      - exists: a Report document exists in DB (may still be empty)
      - is_visible: the patient has uploaded at least one section AND has
        clicked 'View my report' (finalized) at least once. Only when this
        is True should the dashboard render the SelfReportEntry card; the
        banner (entry point) is always shown by the dashboard regardless.
    """
    r = mongo.Report.find_one({"user_id": current_user["id"], "source": "self_uploaded"})
    if not r or r.get("deleted_at"):
        return {"exists": False, "is_visible": False}
    uploaded = r.get("uploaded_sections") or []
    is_visible = bool(uploaded) and bool(r.get("finalized_at"))
    return {
        "exists": True,
        "is_visible": is_visible,
        "report_id": r["id"],
        "uploaded_sections": uploaded,
        "coverage_index": r.get("coverage_index") or 0,
        "overall_severity": r.get("overall_severity") or "normal",
        "report_date": r.get("report_date").strftime("%d %b %Y") if r.get("report_date") else None,
    }


@router.post("/{report_id}/sections/{section_type}/upload", response_model=ExtractResponse)
async def upload_section(
    report_id: int,
    section_type: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Upload a single test report (PDF or image). Runs AI extraction
    synchronously so the patient sees results immediately, then triggers
    organ score sync in the background.
    """
    r = _user_owns_self_report(report_id, current_user["id"])
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    if section_type not in SECTION_PARAMETERS:
        raise HTTPException(status_code=400, detail=f"Unknown section: {section_type}")

    # Read the file once; re-encode for the AI service
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (>25 MB)")
    file_b64 = base64.b64encode(raw).decode()
    file_mime = file.content_type or "application/pdf"

    gender = current_user.get("gender")
    extracted = extract_report_parameters(section_type, file_b64, file_mime, gender=gender)
    if not extracted:
        raise HTTPException(status_code=422, detail="AI couldn't read this file. Try a clearer scan or PDF.")

    new_count = _persist_section(report_id, section_type, extracted)
    _mark_uploaded(report_id, section_type)

    # Sync organ scores in background (uses same _sync_organs_bg as admin)
    from ..api.admin import _sync_organs_bg, _trigger_body_age
    background_tasks.add_task(_sync_organs_bg, report_id)
    background_tasks.add_task(_trigger_body_age, report_id)

    return {
        "section_type": section_type,
        "findings_count": new_count,
        "extracted_param_count": len(extracted or {}),
    }


@router.post("/{report_id}/finalize", response_model=FinalizeResponse)
def finalize(report_id: int, current_user=Depends(get_current_user)):
    """Run priority + health-plan generation once enough sections exist.
    Patient hits this after they're done uploading. Cheap to re-run as
    they add more sections."""
    r = _user_owns_self_report(report_id, current_user["id"])
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    findings = mongo.Finding.find({"report_id": report_id})
    organs = sorted(mongo.OrganScore.find({"report_id": report_id}), key=lambda o: o.get("display_order", 0))

    # Coverage = fraction of 8 standard test types we have data for
    SECTIONS = ["blood", "urine", "dexa", "calcium_score", "ecg", "chest_xray", "usg", "mri"]
    uploaded = r.get("uploaded_sections") or []
    coverage = round(len(set(uploaded) & set(SECTIONS)) / len(SECTIONS) * 100, 1)

    # Overall severity = worst severity present
    sev_counts = {"critical": 0, "major": 0, "minor": 0, "normal": 0}
    gender = current_user.get("gender")
    excluded = set()
    if gender:
        from ..services.organ_param_map import canon
        for items in SECTION_PARAMETERS.values():
            for it in items:
                g = (it.get("gender") or "U").upper()
                if (g == "F" and gender.upper() in ("M", "MALE")) or (g == "M" and gender.upper() in ("F", "FEMALE")):
                    excluded.add(canon(it["name"]))
    for f in findings:
        if (f.get("name") or "").lower().strip() in excluded:
            continue
        s = f.get("severity")
        if s in sev_counts:
            sev_counts[s] += 1

    overall = (
        "critical" if sev_counts["critical"] > 0 else
        "major" if sev_counts["major"] > 0 else
        "minor" if sev_counts["minor"] > 0 else "normal"
    )

    update = {
        "coverage_index": coverage,
        "overall_severity": overall,
    }

    # Generate the AI plan/priorities once the patient has uploaded at
    # least one section — earlier we required 25% (2 of 8) but feedback
    # was that even a single CBC should unlock priorities and a plan.
    if coverage > 0 and findings:
        priorities = generate_priorities(r, findings, organs)
        if priorities:
            mongo.HealthPriority.delete_many({"report_id": report_id})
            for i, p in enumerate(priorities, 1):
                mongo.HealthPriority.insert({
                    "report_id": report_id,
                    "priority_order": i,
                    "title": p.get("title", ""),
                    "why_important": p.get("why_important", ""),
                    "diet_recommendations": p.get("diet_recommendations", []),
                    "exercise_recommendations": p.get("exercise_recommendations", []),
                    "sleep_recommendations": p.get("sleep_recommendations", []),
                    "supplement_recommendations": p.get("supplement_recommendations", []),
                })
            saved_priorities = sorted(
                mongo.HealthPriority.find({"report_id": report_id}),
                key=lambda p: p.get("priority_order", 0),
            )
            plan = generate_health_plan(r, findings, organs, saved_priorities)
            if plan:
                update["health_plan"] = plan

    # Mark that the patient has clicked through to view at least once. This
    # is the gate the dashboard uses before rendering the SelfReportEntry
    # card — uploads alone are not enough.
    update["finalized_at"] = datetime.now()

    mongo.Report.update_one({"id": report_id}, {"$set": update})

    return {
        "coverage_pct": coverage,
        "sections_uploaded": uploaded,
        "overall_severity": overall,
        "finding_counts": sev_counts,
    }


@router.delete("/{report_id}")
def delete_self_report(report_id: int, current_user=Depends(get_current_user)):
    """Patient-initiated soft-delete of their self-uploaded report.

    We don't hard-delete because admin still wants to see a tombstone
    ("Report Deleted") on the patient card — useful for support and
    to know that the patient had a report and chose to remove it.

    Derived data (findings, sections, organ scores, body age,
    priorities, chat messages, consultation notes) IS hard-deleted to
    free storage and avoid leaking PHI through stray queries; only the
    Report doc itself stays as a marker with `deleted_at` set.
    """
    r = _user_owns_self_report(report_id, current_user["id"])
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    mongo.Finding.delete_many({"report_id": report_id})
    mongo.ReportSection.delete_many({"report_id": report_id})
    mongo.OrganScore.delete_many({"report_id": report_id})
    mongo.BodyAgeDoc.delete_many({"report_id": report_id})
    mongo.HealthPriority.delete_many({"report_id": report_id})
    mongo.ChatMessage.delete_many({"report_id": report_id})
    mongo.ConsultationNote.delete_many({"report_id": report_id})
    mongo.Report.update_one(
        {"id": report_id},
        {"$set": {
            "deleted_at": datetime.now(),
            "uploaded_sections": [],
            "coverage_index": 0,
            "overall_severity": "normal",
            "health_plan": None,
            "is_published": False,
        }},
    )
    return {"deleted": True}
