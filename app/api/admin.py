"""Admin API — local dev only. Allows creating patients, orders, reports, and findings via UI."""
import base64
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from datetime import timedelta
from ..core import mongo
from ..core.security import create_access_token
from ..services import auth_service
from ..services.lab_classifier import parse_excel_lab_results, generate_template_excel, MARKERS, classify_severity
from ..services.section_params import SECTION_PARAMETERS, SECTION_META, filter_params_by_gender, PARAM_PAIRS


def _patient_gender_for_report(report_id):
    """Look up the patient gender for a given report id."""
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        return None
    order = mongo.Order.find_one({"id": report.get("order_id")}) or {}
    g = order.get("patient_gender")
    if not g and order.get("user_id"):
        u = mongo.User.find_one({"id": order["user_id"]})
        g = (u or {}).get("gender")
    return g
from ..services.ai_service import extract_report_parameters, generate_priorities, generate_health_plan
from ..services.dexa_calc import autocompute_dexa
from ..services.organ_param_map import ORGAN_DEFINITIONS, RISK_LABELS, canon

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreatePatient(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    email: Optional[str] = None

class CreateOrder(BaseModel):
    booking_id: str
    scan_type: str = "ZenScan"
    status: str = "completed"
    scan_date: Optional[str] = None
    amount: float = 27500

class CreateReport(BaseModel):
    coverage_index: float = 90.0
    overall_severity: str = "normal"
    report_date: Optional[str] = None
    next_visit: Optional[str] = None
    summary: str = ""

class UpdateReport(BaseModel):
    coverage_index: Optional[float] = None
    overall_severity: Optional[str] = None
    summary: Optional[str] = None
    next_visit: Optional[str] = None

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

def _compute_patient_status(orders_meta: list[dict], has_self_report: bool = False) -> str:
    """Compute a single status for the patient.
    - registered_unpaid: no orders, no self-uploaded report
    - self_uploaded_report: patient has a finalized self-uploaded report
        and no ZenScan orders. Surfaces patients who self-served instead
        of (or before) booking a ZenScan.
    - paid_test_pending: ZenScan order exists but tests not yet complete
    - test_done_report_awaited: tests complete but ZenScan report not published
    - report_published: published ZenScan report exists
    ZenScan progression always wins over self_uploaded_report — once a
    patient has a clinic order, that's the more meaningful status.
    """
    if not orders_meta:
        return "self_uploaded_report" if has_self_report else "registered_unpaid"
    if any(o.get("is_published") for o in orders_meta):
        return "report_published"
    if any(o.get("tests_complete") and not o.get("is_published") for o in orders_meta):
        return "test_done_report_awaited"
    return "paid_test_pending"


@router.post("/patients/{user_id}/impersonate")
def impersonate_patient(user_id: int):
    """Issue a short-lived JWT for `user_id` so admin can open the
    patient-facing report in a new tab. Local-dev admin has no auth, so
    this is intentionally unauthenticated like all other /admin/*
    endpoints. Token is short-lived (30 min) and patient-scoped.
    """
    user = mongo.User.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Patient not found")
    token = create_access_token(
        {"sub": str(user_id)},
        expires_delta=timedelta(minutes=30),
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/patients")
def list_patients():
    users = mongo.User.find()
    result = []
    for u in users:
        orders = mongo.Order.find({"user_id": u["id"]})
        order_list = []
        for o in orders:
            r = mongo.Report.find_one({"order_id": o["id"]})
            tests_complete = False
            if r:
                statuses = r.get("test_statuses") or {}
                required = _required_tests_for(o.get("patient_gender") or u.get("gender"))
                tests_complete = bool(required) and all(statuses.get(t) == "complete" for t in required)
            order_list.append({
                "id": o["id"],
                "booking_id": o.get("booking_id"),
                "status": o.get("status"),
                "has_report": r is not None,
                "report_id": r["id"] if r else None,
                "is_published": bool(r.get("is_published")) if r else False,
                "tests_complete": tests_complete,
            })
        # Self-uploaded report (patient-initiated, no order). Only counts
        # once finalized (otherwise unfinalized drafts would inflate
        # admin's view). See self_upload.finalize().
        # Soft-deleted reports (deleted_at set) still show on admin so
        # support can see the tombstone, but are gated out of patient flows.
        sr = mongo.Report.find_one({"user_id": u["id"], "source": "self_uploaded"})
        sr_deleted = bool(sr and sr.get("deleted_at"))
        sr_finalized = bool(sr and sr.get("finalized_at") and not sr_deleted)
        self_report = None
        if sr and (sr_finalized or sr_deleted):
            self_report = {
                "report_id": sr["id"],
                "uploaded_sections": sr.get("uploaded_sections") or [],
                "coverage_index": sr.get("coverage_index") or 0,
                "overall_severity": sr.get("overall_severity") or "normal",
                "deleted": sr_deleted,
            }

        result.append({
            "id": u["id"],
            "phone": u.get("phone"),
            "name": u.get("name"),
            "zen_id": u.get("zen_id"),
            "age": u.get("age"),
            "gender": u.get("gender"),
            "orders": order_list,
            "self_report": self_report,
            "status": _compute_patient_status(order_list, has_self_report=sr_finalized),
        })
    return result


@router.post("/patients")
def create_patient(body: CreatePatient):
    if body.phone and mongo.User.find_one({"phone": body.phone}):
        raise HTTPException(status_code=400, detail="Patient with this phone number already exists")
    user = {
        "phone": body.phone,
        "name": body.name,
        "age": body.age,
        "gender": body.gender,
        "email": body.email,
        "zen_id": auth_service._generate_zen_id(),
        # Admin-created patients get a default password and are forced to
        # change it on first login.
        "password_hash": auth_service.hash_password("123456"),
        "must_change_password": True,
        "is_active": True,
        "created_at": mongo.now(),
    }
    mongo.User.insert(user)
    return {"id": user["id"], "name": user["name"], "phone": user["phone"], "zen_id": user["zen_id"]}


@router.post("/patients/{user_id}/orders")
def create_order(user_id: int, body: CreateOrder):
    user = mongo.User.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Patient not found")
    scan_date = datetime.fromisoformat(body.scan_date) if body.scan_date else datetime.now()
    next_visit = datetime(scan_date.year + 1, scan_date.month, scan_date.day)
    order = {
        "booking_id": body.booking_id,
        "user_id": user_id,
        "patient_name": user.get("name"),
        "patient_age": user.get("age"),
        "patient_gender": user.get("gender"),
        "scan_type": body.scan_type,
        "status": body.status,
        "scan_date": scan_date,
        "next_visit": next_visit,
        "amount": body.amount,
        "created_at": mongo.now(),
    }
    mongo.Order.insert(order)
    return {"id": order["id"], "booking_id": order["booking_id"]}


@router.post("/orders/{order_id}/report")
def create_report(order_id: int, body: CreateReport):
    order = mongo.Order.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if mongo.Report.find_one({"order_id": order_id}):
        raise HTTPException(status_code=400, detail="Report already exists for this order")
    report_date = datetime.fromisoformat(body.report_date) if body.report_date else datetime.now()
    next_visit = datetime.fromisoformat(body.next_visit) if body.next_visit else datetime(report_date.year + 1, report_date.month, report_date.day)
    report = {
        "order_id": order_id,
        "coverage_index": body.coverage_index,
        "overall_severity": body.overall_severity,
        "report_date": report_date,
        "next_visit": next_visit,
        "summary": body.summary,
        "is_published": False,
    }
    mongo.Report.insert(report)
    return {"id": report["id"]}


@router.patch("/reports/{report_id}")
def update_report(report_id: int, body: UpdateReport):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    update = {}
    if body.coverage_index is not None:
        update["coverage_index"] = body.coverage_index
    if body.overall_severity is not None:
        update["overall_severity"] = body.overall_severity
    if body.summary is not None:
        update["summary"] = body.summary
    if body.next_visit:
        update["next_visit"] = datetime.fromisoformat(body.next_visit)
    if update:
        mongo.Report.update_one({"id": report_id}, {"$set": update})
    return {"ok": True}


# ── Pre-generate review: unfilled / ignored params ───────────────────────────

@router.get("/reports/{report_id}/unfilled-params")
def get_unfilled_params(report_id: int):
    """List every canonical parameter that has no value AND is not in the
    report's ignored list, grouped by section. Used by the admin's
    'Generate Report' pre-flight drawer.
    """
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    gender = _patient_gender_for_report(report_id)
    ignored = set(report.get("ignored_params") or [])

    sections = {s["section_type"]: s for s in mongo.ReportSection.find({"report_id": report_id})}
    out: dict[str, list[dict]] = {}
    for sec_key, defs in SECTION_PARAMETERS.items():
        meta = SECTION_META.get(sec_key, {})
        # Skip whole sections that don't apply to this patient (e.g. mammography
        # for males). Param-level gender filter still runs for mixed sections.
        if meta.get("female_only") and gender == "M":
            continue
        if meta.get("male_only") and gender == "F":
            continue
        defs = filter_params_by_gender(defs, gender)
        sec_doc = sections.get(sec_key) or {}
        params = sec_doc.get("parameters") or {}
        # Skip the secondary of a CBC twin pair — counted via the primary
        secondaries = set(PARAM_PAIRS.keys())
        unfilled = []
        for d in defs:
            if d["name"] in secondaries:
                continue
            if d["name"] in ignored:
                continue
            v = params.get(d["name"])
            val = v.get("value") if isinstance(v, dict) else v
            # Also check the paired secondary's value (count + % share status)
            sec_name = next((k for k, p in PARAM_PAIRS.items() if p == d["name"]), None)
            sec_val = None
            if sec_name:
                sv = params.get(sec_name)
                sec_val = sv.get("value") if isinstance(sv, dict) else sv
            if val in (None, "", "—", "-", "Not Found") and sec_val in (None, "", "—", "-", "Not Found"):
                unfilled.append({
                    "name": d["name"],
                    "unit": d.get("unit", ""),
                    "normal": d.get("normal", ""),
                    "paired_secondary": sec_name,
                })
        if unfilled:
            out[sec_key] = unfilled
    return {
        "ignored_params": list(ignored),
        "unfilled_by_section": out,
        "section_meta": SECTION_META,
    }


class IgnoredParamsBody(BaseModel):
    add: Optional[list[str]] = None
    remove: Optional[list[str]] = None


@router.patch("/reports/{report_id}/ignored-params")
def update_ignored_params(report_id: int, body: IgnoredParamsBody):
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    current = set(report.get("ignored_params") or [])
    if body.add:
        current.update(body.add)
    if body.remove:
        current.difference_update(body.remove)
    mongo.Report.update_one({"id": report_id}, {"$set": {"ignored_params": sorted(current)}})
    return {"ok": True, "ignored_params": sorted(current)}


@router.post("/reports/{report_id}/publish")
def publish_report(report_id: int):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    mongo.Report.update_one({"id": report_id}, {"$set": {"is_published": True}})
    return {"ok": True, "is_published": True}


@router.post("/reports/{report_id}/unpublish")
def unpublish_report(report_id: int):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    mongo.Report.update_one({"id": report_id}, {"$set": {"is_published": False}})
    return {"ok": True, "is_published": False}


# ── Per-test status (Test Status tab) ────────────────────────────────────────

# Tests that count toward "all tests complete". Mammography is gender-aware:
# only counted as required for female patients; ignored for males.
ALL_TEST_KEYS = ["blood", "urine", "dexa", "calcium_score", "ecg", "chest_xray", "usg", "mri", "mammography"]


def _required_tests_for(gender: Optional[str]) -> list[str]:
    g = (gender or "").upper()
    if g in ("F", "FEMALE"):
        return ALL_TEST_KEYS
    # Skip mammography for non-female patients
    return [t for t in ALL_TEST_KEYS if t != "mammography"]


@router.get("/reports/{report_id}/test-status")
def get_test_status(report_id: int):
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    order = mongo.Order.find_one({"id": report.get("order_id")}) or {}
    required = _required_tests_for(order.get("patient_gender"))
    saved = report.get("test_statuses") or {}
    # Default any missing tests to "pending"
    return {
        "test_statuses": {t: saved.get(t, "pending") for t in required},
        "required_tests": required,
    }


class UpdateTestStatus(BaseModel):
    test_statuses: Dict[str, str]


@router.put("/reports/{report_id}/test-status")
def update_test_status(report_id: int, body: UpdateTestStatus):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    # Whitelist values
    cleaned = {k: v for k, v in body.test_statuses.items() if v in ("pending", "complete") and k in ALL_TEST_KEYS}
    mongo.Report.update_one({"id": report_id}, {"$set": {"test_statuses": cleaned}})
    return {"ok": True, "test_statuses": cleaned}


@router.delete("/reports/{report_id}/clear-data")
def clear_report_data(report_id: int):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    mongo.Finding.delete_many({"report_id": report_id})
    mongo.OrganScore.delete_many({"report_id": report_id})
    mongo.ReportSection.delete_many({"report_id": report_id})
    mongo.HealthPriority.delete_many({"report_id": report_id})
    mongo.BodyAgeDoc.delete_many({"report_id": report_id})
    mongo.Report.update_one(
        {"id": report_id},
        {"$set": {
            "coverage_index": 0.0,
            "overall_severity": "normal",
            "summary": "",
            "is_published": False,
            "test_statuses": {},
        }},
    )
    return {"ok": True}


@router.post("/reports/{report_id}/organs")
def add_organ(report_id: int, body: CreateOrganScore):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    organ = {"report_id": report_id, **body.model_dump()}
    mongo.OrganScore.insert(organ)
    return {"id": organ["id"]}


@router.delete("/reports/{report_id}/organs/{organ_id}")
def delete_organ(report_id: int, organ_id: int):
    deleted = mongo.OrganScore.delete_one({"id": organ_id, "report_id": report_id})
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Organ score not found")
    return {"ok": True}


# ── Background helpers ────────────────────────────────────────────────────────

def _trigger_body_age(report_id: int) -> None:
    try:
        from ..services.body_age_service import calculate_pheno_age, calculate_zen_age

        report = mongo.Report.find_one({"id": report_id})
        if not report:
            return
        order = mongo.Order.find_one({"id": report.get("order_id")})

        findings = mongo.Finding.find({"report_id": report_id})
        if not findings:
            return

        pheno_result = calculate_pheno_age(findings)
        zen_result = calculate_zen_age(report, findings, pheno_result)

        actual_age = order.get("patient_age") if order else None
        zen_age = zen_result.get("zen_age")
        age_diff = round(zen_age - actual_age, 1) if (zen_age and actual_age) else zen_result.get("age_difference", 0)

        existing = mongo.BodyAgeDoc.find_one({"report_id": report_id})
        update = {
            "report_id": report_id,
            "chronological_age": actual_age,
            "pheno_age": pheno_result.get("pheno_age"),
            "zen_age": zen_age,
            "age_difference": age_diff,
            "interpretation": zen_result.get("interpretation", ""),
            "markers_used": pheno_result.get("markers_found", []),
            "markers_missing": pheno_result.get("markers_missing", []),
            "confidence": zen_result.get("confidence", "medium"),
            "sub_ages": zen_result.get("sub_ages", {}),
            "updated_at": mongo.now(),
        }
        if existing:
            mongo.BodyAgeDoc.update_one({"id": existing["id"]}, {"$set": update})
        else:
            update["created_at"] = mongo.now()
            mongo.BodyAgeDoc.insert(update)
    except Exception:
        pass


def _sync_organs_bg(report_id: int) -> None:
    try:
        report = mongo.Report.find_one({"id": report_id})
        if not report:
            return
        order = mongo.Order.find_one({"id": report.get("order_id")})
        patient_gender = order.get("patient_gender") if order else None

        canonical_names = {defn["organ_name"] for defn in ORGAN_DEFINITIONS}
        # Delete stale organ rows
        mongo.OrganScore.delete_many({
            "report_id": report_id,
            "organ_name": {"$nin": list(canonical_names)},
        })
        findings = mongo.Finding.find({"report_id": report_id})
        # Apply alias canonicalization on lookup so "Lymphocytes" /
        # "agaston score" / etc. match the canonical entries in the organ map.
        finding_sev = {canon(f["name"]): f.get("severity") for f in findings if f.get("name")}

        for defn in ORGAN_DEFINITIONS:
            organ_gender = defn.get("gender", "U")
            if organ_gender == "F" and patient_gender and patient_gender.upper() in ("M", "MALE"):
                continue
            if organ_gender == "M" and patient_gender and patient_gender.upper() in ("F", "FEMALE"):
                continue

            counts = {"critical": 0, "major": 0, "minor": 0, "normal": 0}
            for p in defn["params"]:
                sev = finding_sev.get(canon(p))
                if sev and sev in counts:
                    counts[sev] += 1
            severity = (
                "critical" if counts["critical"] > 0 else
                "major" if counts["major"] > 0 else
                "minor" if counts["minor"] > 0 else "normal"
            )
            update_doc = {
                "severity": severity,
                "risk_label": RISK_LABELS[severity],
                "critical_count": counts["critical"],
                "major_count": counts["major"],
                "minor_count": counts["minor"],
                "normal_count": counts["normal"],
                "icon": defn["icon"],
                "display_order": defn["display_order"],
            }
            existing = mongo.OrganScore.find_one({
                "report_id": report_id,
                "organ_name": defn["organ_name"],
            })
            if existing:
                mongo.OrganScore.update_one({"id": existing["id"]}, {"$set": update_doc})
            else:
                mongo.OrganScore.insert({
                    "report_id": report_id,
                    "organ_name": defn["organ_name"],
                    **update_doc,
                })
    except Exception:
        pass


@router.post("/reports/{report_id}/findings")
def add_finding(report_id: int, body: CreateFinding, background_tasks: BackgroundTasks):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    data = body.model_dump()
    val = str(data.get("value") or "")
    if not val or val.strip().lower() in ("not found", "n/a", "na", "none", "-", ""):
        data["severity"] = "normal"
    finding = {"report_id": report_id, **data}
    mongo.Finding.insert(finding)
    background_tasks.add_task(_trigger_body_age, report_id)
    background_tasks.add_task(_sync_organs_bg, report_id)
    return {"id": finding["id"]}


@router.delete("/reports/{report_id}/findings/{finding_id}")
def delete_finding(report_id: int, finding_id: int):
    deleted = mongo.Finding.delete_one({"id": finding_id, "report_id": report_id})
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"ok": True}


@router.post("/reports/{report_id}/priorities")
def add_priority(report_id: int, body: CreatePriority):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    p = {"report_id": report_id, **body.model_dump()}
    mongo.HealthPriority.insert(p)
    return {"id": p["id"]}


@router.post("/reports/{report_id}/notes")
def add_note(report_id: int, body: CreateNote):
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    note = {"report_id": report_id, **body.model_dump(), "created_at": mongo.now()}
    mongo.ConsultationNote.insert(note)
    return {"id": note["id"]}


@router.get("/lab-template")
def download_lab_template(report_id: Optional[int] = None, section: Optional[str] = None):
    patient_ctx = None
    if report_id:
        report = mongo.Report.find_one({"id": report_id})
        if report:
            order = mongo.Order.find_one({"id": report.get("order_id")}) or {}
            user = mongo.User.find_one({"id": order.get("user_id")}) if order.get("user_id") else None
            scan_dt = order.get("scan_date")
            patient_ctx = {
                "patient_name": order.get("patient_name") or (user.get("name") if user else None),
                "zen_id": (user.get("zen_id") if user else None),
                "booking_id": order.get("booking_id"),
                "scan_date": scan_dt.strftime("%d %b %Y") if scan_dt else None,
                "age": order.get("patient_age") or (user.get("age") if user else None),
                "gender": order.get("patient_gender") or (user.get("gender") if user else None),
            }
    content = generate_template_excel(patient=patient_ctx, section=section)

    # Filename: ZenLife_<Section>_<Name>.xlsx
    section_label = {
        "blood": "BloodReport",
        "urine": "UrineAnalysis",
    }.get((section or "").lower(), "Lab_Template")
    safe = (patient_ctx or {}).get("patient_name") or ""
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in safe).strip().replace(" ", "_")
    if safe:
        filename = f"ZenLife_{section_label}_{safe}.xlsx"
    else:
        filename = f"ZenLife_{section_label}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/upload-lab-results")
async def upload_lab_results(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are supported")
    content = await file.read()
    findings = parse_excel_lab_results(content)
    return {"findings": findings}


@router.get("/markers")
def list_markers():
    return {"markers": MARKERS}


@router.post("/classify-value")
def classify_value(body: dict):
    severity = classify_severity(str(body.get("value", "")), str(body.get("normal_range", "")))
    return {"severity": severity}


@router.get("/reports/{report_id}/detail")
def get_report_detail(report_id: int):
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    organs = sorted(
        mongo.OrganScore.find({"report_id": report_id}),
        key=lambda o: o.get("display_order", 0),
    )
    findings = mongo.Finding.find({"report_id": report_id})
    priorities = sorted(
        mongo.HealthPriority.find({"report_id": report_id}),
        key=lambda p: p.get("priority_order", 0),
    )
    notes = mongo.ConsultationNote.find({"report_id": report_id})
    return {
        "report_id": report_id,
        "coverage_index": report.get("coverage_index"),
        "overall_severity": report.get("overall_severity"),
        "summary": report.get("summary"),
        "is_published": bool(report.get("is_published")),
        "organs": [{"id": o["id"], "organ_name": o.get("organ_name"), "severity": o.get("severity"), "icon": o.get("icon"), "risk_label": o.get("risk_label"), "critical_count": o.get("critical_count", 0), "major_count": o.get("major_count", 0), "minor_count": o.get("minor_count", 0), "normal_count": o.get("normal_count", 0)} for o in organs],
        "findings": [{"id": f["id"], "name": f.get("name"), "severity": f.get("severity"), "test_type": f.get("test_type"), "value": f.get("value"), "unit": f.get("unit"), "normal_range": f.get("normal_range")} for f in findings],
        "priorities": [{"id": p["id"], "title": p.get("title"), "priority_order": p.get("priority_order")} for p in priorities],
        "notes": [{"id": n["id"], "note_type": n.get("note_type"), "author": n.get("author")} for n in notes],
    }


# ── Report Sections ───────────────────────────────────────────────────────────

@router.get("/section-params")
def get_section_params(report_id: Optional[int] = None, gender: Optional[str] = None):
    """Return the parameter map for all sections.
    If a report_id (or explicit gender) is provided, sex-specific params
    that don't apply to this patient are filtered out.
    """
    if report_id and not gender:
        gender = _patient_gender_for_report(report_id)
    return {
        "sections": SECTION_META,
        "parameters": {
            k: filter_params_by_gender(v, gender)
            for k, v in SECTION_PARAMETERS.items()
        },
        "pairs": PARAM_PAIRS,
    }


@router.get("/reports/{report_id}/sections")
def get_all_sections(report_id: int):
    sections = mongo.ReportSection.find({"report_id": report_id})
    return {
        s["section_type"]: {
            "key_findings": s.get("key_findings"),
            "parameters": s.get("parameters") or {},
            "updated_at": s["updated_at"].isoformat() if s.get("updated_at") else None,
        }
        for s in sections
    }


@router.get("/reports/{report_id}/sections/{section_type}")
def get_section(report_id: int, section_type: str):
    section = mongo.ReportSection.find_one({"report_id": report_id, "section_type": section_type})
    gender = _patient_gender_for_report(report_id)
    param_defs = filter_params_by_gender(SECTION_PARAMETERS.get(section_type, []), gender)
    saved = section.get("parameters") or {} if section else {}
    return {
        "section_type": section_type,
        "key_findings": section.get("key_findings", "") if section else "",
        "parameters": saved,
        "param_definitions": param_defs,
        "meta": SECTION_META.get(section_type, {}),
        "pairs": PARAM_PAIRS,
    }


class SaveSectionBody(BaseModel):
    key_findings: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


@router.put("/reports/{report_id}/sections/{section_type}")
def save_section(report_id: int, section_type: str, body: SaveSectionBody):
    if section_type not in SECTION_PARAMETERS:
        raise HTTPException(status_code=400, detail=f"Unknown section type: {section_type}")
    # Auto-compute DEXA derived metrics (ALM, ASMI, FMI) when their inputs
    # are present but the report didn't print them.
    if section_type == "dexa" and body.parameters is not None:
        gender = _patient_gender_for_report(report_id)
        body.parameters, _ = autocompute_dexa(body.parameters, gender)

    section = mongo.ReportSection.find_one({"report_id": report_id, "section_type": section_type})
    if section:
        update = {"updated_at": mongo.now()}
        if body.key_findings is not None:
            update["key_findings"] = body.key_findings
        if body.parameters is not None:
            update["parameters"] = body.parameters
        mongo.ReportSection.update_one({"id": section["id"]}, {"$set": update})
    else:
        mongo.ReportSection.insert({
            "report_id": report_id,
            "section_type": section_type,
            "key_findings": body.key_findings or "",
            "parameters": body.parameters or {},
            "updated_at": mongo.now(),
        })
    return {"ok": True, "section_type": section_type}


@router.post("/reports/{report_id}/sections/{section_type}/extract")
async def extract_section(report_id: int, section_type: str, file: UploadFile = File(...)):
    if section_type not in SECTION_PARAMETERS:
        raise HTTPException(status_code=400, detail=f"Unknown section type: {section_type}")

    content = await file.read()
    file_b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"

    gender = _patient_gender_for_report(report_id)
    extracted = extract_report_parameters(section_type, file_b64, mime, gender=gender)

    if "_parse_error" in extracted or "error" in extracted:
        raise HTTPException(status_code=422, detail=extracted.get("_parse_error") or extracted.get("error"))

    # Auto-compute DEXA derived metrics from the extracted inputs.
    if section_type == "dexa":
        extracted, _ = autocompute_dexa(extracted, gender)

    section = mongo.ReportSection.find_one({"report_id": report_id, "section_type": section_type})
    if section:
        mongo.ReportSection.update_one(
            {"id": section["id"]},
            {"$set": {"parameters": extracted, "updated_at": mongo.now()}},
        )
    else:
        mongo.ReportSection.insert({
            "report_id": report_id,
            "section_type": section_type,
            "parameters": extracted,
            "updated_at": mongo.now(),
        })
    return {"ok": True, "extracted": extracted}


@router.post("/reports/{report_id}/sections/{section_type}/import-findings")
def import_section_as_findings(report_id: int, section_type: str, background_tasks: BackgroundTasks):
    section = mongo.ReportSection.find_one({"report_id": report_id, "section_type": section_type})
    if not section or not section.get("parameters"):
        raise HTTPException(status_code=404, detail="No saved parameters for this section")

    param_defs = {p["name"]: p for p in SECTION_PARAMETERS.get(section_type, [])}
    created = 0
    for param_name, data in section["parameters"].items():
        if isinstance(data, dict):
            value = data.get("value", "")
        else:
            value = str(data)

        p = param_defs.get(param_name, {})

        is_missing = not value or str(value).strip().lower() in ("not found", "n/a", "na", "none", "-", "")
        if is_missing:
            severity = "normal"
            clinical = ""
            recs = ""
            value = "Not Found"
        else:
            severity = data.get("severity", "normal") if isinstance(data, dict) else "normal"
            clinical = data.get("clinical_findings", "") if isinstance(data, dict) else ""
            recs = data.get("recommendations", "") if isinstance(data, dict) else ""

        existing = mongo.Finding.find_one({"report_id": report_id, "name": param_name})
        if existing:
            if not is_missing or existing.get("value") in ("Not Found", None, ""):
                mongo.Finding.update_one(
                    {"id": existing["id"]},
                    {"$set": {
                        "value": str(value),
                        "severity": severity,
                        "clinical_findings": clinical,
                        "recommendations": recs,
                    }},
                )
        else:
            mongo.Finding.insert({
                "report_id": report_id,
                "test_type": section_type,
                "name": param_name,
                "severity": severity,
                "value": str(value),
                "normal_range": p.get("normal", ""),
                "unit": p.get("unit", ""),
                "clinical_findings": clinical,
                "recommendations": recs,
            })
            created += 1

    background_tasks.add_task(_trigger_body_age, report_id)
    background_tasks.add_task(_sync_organs_bg, report_id)
    return {"ok": True, "imported": created}


@router.post("/reports/{report_id}/sync-organs")
def sync_organs(report_id: int):
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    order = mongo.Order.find_one({"id": report.get("order_id")})
    patient_gender = order.get("patient_gender") if order else None

    canonical_names = {defn["organ_name"] for defn in ORGAN_DEFINITIONS}
    stale_count = mongo.OrganScore.delete_many({
        "report_id": report_id,
        "organ_name": {"$nin": list(canonical_names)},
    })

    findings = mongo.Finding.find({"report_id": report_id})
    finding_sev = {canon(f["name"]): f.get("severity") for f in findings if f.get("name")}

    organs_synced = 0
    for defn in ORGAN_DEFINITIONS:
        organ_gender = defn.get("gender", "U")
        if organ_gender == "F" and patient_gender and patient_gender.upper() in ("M", "MALE"):
            continue
        if organ_gender == "M" and patient_gender and patient_gender.upper() in ("F", "FEMALE"):
            continue

        counts = {"critical": 0, "major": 0, "minor": 0, "normal": 0}
        for p in defn["params"]:
            sev = finding_sev.get(canon(p))
            if sev and sev in counts:
                counts[sev] += 1

        severity = (
            "critical" if counts["critical"] > 0 else
            "major" if counts["major"] > 0 else
            "minor" if counts["minor"] > 0 else "normal"
        )
        update_doc = {
            "severity": severity,
            "risk_label": RISK_LABELS[severity],
            "critical_count": counts["critical"],
            "major_count": counts["major"],
            "minor_count": counts["minor"],
            "normal_count": counts["normal"],
            "icon": defn["icon"],
            "display_order": defn["display_order"],
        }
        existing = mongo.OrganScore.find_one({
            "report_id": report_id,
            "organ_name": defn["organ_name"],
        })
        if existing:
            mongo.OrganScore.update_one({"id": existing["id"]}, {"$set": update_doc})
        else:
            mongo.OrganScore.insert({
                "report_id": report_id,
                "organ_name": defn["organ_name"],
                **update_doc,
            })
        organs_synced += 1

    return {"ok": True, "organs": organs_synced, "stale_rows_deleted": stale_count}


@router.post("/sync-all-organs")
def sync_all_organs():
    canonical_names = {defn["organ_name"] for defn in ORGAN_DEFINITIONS}
    all_reports = mongo.Report.find()
    deleted_total = 0

    for report in all_reports:
        order = mongo.Order.find_one({"id": report.get("order_id")})
        patient_gender = order.get("patient_gender") if order else None

        deleted_total += mongo.OrganScore.delete_many({
            "report_id": report["id"],
            "organ_name": {"$nin": list(canonical_names)},
        })

        findings = mongo.Finding.find({"report_id": report["id"]})
        finding_sev = {canon(f["name"]): f.get("severity") for f in findings if f.get("name")}

        for defn in ORGAN_DEFINITIONS:
            organ_gender = defn.get("gender", "U")
            if organ_gender == "F" and patient_gender and patient_gender.upper() in ("M", "MALE"):
                continue
            if organ_gender == "M" and patient_gender and patient_gender.upper() in ("F", "FEMALE"):
                continue

            counts = {"critical": 0, "major": 0, "minor": 0, "normal": 0}
            for p in defn["params"]:
                sev = finding_sev.get(canon(p))
                if sev and sev in counts:
                    counts[sev] += 1
            severity = (
                "critical" if counts["critical"] > 0 else
                "major" if counts["major"] > 0 else
                "minor" if counts["minor"] > 0 else "normal"
            )
            update_doc = {
                "severity": severity,
                "risk_label": RISK_LABELS[severity],
                "critical_count": counts["critical"],
                "major_count": counts["major"],
                "minor_count": counts["minor"],
                "normal_count": counts["normal"],
                "icon": defn["icon"],
                "display_order": defn["display_order"],
            }
            existing = mongo.OrganScore.find_one({
                "report_id": report["id"],
                "organ_name": defn["organ_name"],
            })
            if existing:
                mongo.OrganScore.update_one({"id": existing["id"]}, {"$set": update_doc})
            else:
                mongo.OrganScore.insert({
                    "report_id": report["id"],
                    "organ_name": defn["organ_name"],
                    **update_doc,
                })

    return {
        "ok": True,
        "reports_synced": len(all_reports),
        "organ_systems": len(ORGAN_DEFINITIONS),
        "stale_rows_deleted": deleted_total,
    }


@router.get("/reports/{report_id}/body-age")
def get_saved_body_age(report_id: int):
    """Return the persisted body age document (or null) so the admin UI
    can rehydrate after remount instead of showing 'No body age calculated'."""
    if not mongo.Report.find_one({"id": report_id}):
        raise HTTPException(status_code=404, detail="Report not found")
    ba = mongo.BodyAgeDoc.find_one({"report_id": report_id})
    if not ba:
        return None
    return {
        "ok": True,
        "chronological_age": ba.get("chronological_age"),
        "pheno_age": ba.get("pheno_age"),
        "zen_age": ba.get("zen_age"),
        "age_difference": ba.get("age_difference"),
        "confidence": ba.get("confidence", "medium"),
        "interpretation": ba.get("interpretation", ""),
        "markers_used": ba.get("markers_used") or [],
        "markers_missing": ba.get("markers_missing") or [],
        "sub_ages": ba.get("sub_ages") or {},
    }


@router.post("/reports/{report_id}/calculate-body-age")
def calculate_body_age_endpoint(report_id: int):
    from ..services.body_age_service import calculate_pheno_age, calculate_zen_age

    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    order = mongo.Order.find_one({"id": report.get("order_id")})
    findings = mongo.Finding.find({"report_id": report_id})
    actual_age = order.get("patient_age") if order else None

    pheno_result = calculate_pheno_age(findings)
    zen_result = calculate_zen_age(report, findings, pheno_result)

    zen_age = zen_result.get("zen_age")
    age_diff = round(zen_age - actual_age, 1) if (zen_age and actual_age) else zen_result.get("age_difference", 0)

    update = {
        "report_id": report_id,
        "chronological_age": actual_age,
        "pheno_age": pheno_result.get("pheno_age"),
        "zen_age": zen_age,
        "age_difference": age_diff,
        "interpretation": zen_result.get("interpretation", ""),
        "markers_used": pheno_result.get("markers_found", []),
        "markers_missing": pheno_result.get("markers_missing", []),
        "confidence": zen_result.get("confidence", "medium"),
        "sub_ages": zen_result.get("sub_ages", {}),
        "updated_at": mongo.now(),
    }
    existing = mongo.BodyAgeDoc.find_one({"report_id": report_id})
    if existing:
        mongo.BodyAgeDoc.update_one({"id": existing["id"]}, {"$set": update})
    else:
        update["created_at"] = mongo.now()
        mongo.BodyAgeDoc.insert(update)

    return {
        "ok": True,
        "chronological_age": update["chronological_age"],
        "pheno_age": update["pheno_age"],
        "zen_age": update["zen_age"],
        "age_difference": update["age_difference"],
        "confidence": update["confidence"],
        "interpretation": update["interpretation"],
        "markers_used": update["markers_used"],
        "markers_missing": update["markers_missing"],
        "sub_ages": update["sub_ages"],
    }


@router.post("/reports/{report_id}/generate-priorities")
def auto_generate_priorities(report_id: int):
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    findings = mongo.Finding.find({"report_id": report_id})
    organs = sorted(
        mongo.OrganScore.find({"report_id": report_id}),
        key=lambda o: o.get("display_order", 0),
    )

    priorities = generate_priorities(report, findings, organs)
    if not priorities:
        raise HTTPException(status_code=422, detail="AI could not generate priorities. Check API key or try again.")

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

    return {"ok": True, "count": len(priorities)}


@router.post("/reports/{report_id}/generate-health-plan")
def auto_generate_health_plan(report_id: int):
    """Generate (or refresh) the integrated AI health plan for a report.
    Stored as `health_plan` field on the Report document — it's a single
    JSON blob so a separate collection isn't needed."""
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    findings = mongo.Finding.find({"report_id": report_id})
    organs = sorted(
        mongo.OrganScore.find({"report_id": report_id}),
        key=lambda o: o.get("display_order", 0),
    )
    priorities = sorted(
        mongo.HealthPriority.find({"report_id": report_id}),
        key=lambda p: p.get("priority_order", 0),
    )

    plan = generate_health_plan(report, findings, organs, priorities)
    if not plan:
        raise HTTPException(status_code=422, detail="AI could not generate health plan. Check API key or try again.")

    mongo.Report.update_one({"id": report_id}, {"$set": {"health_plan": plan}})
    return {"ok": True, "plan": plan}
