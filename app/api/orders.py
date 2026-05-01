from fastapi import APIRouter, Depends
from ..core import mongo
from ..api.deps import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])

# Tests required for "all tests complete". Mammography only applies to female patients.
ALL_TEST_KEYS = ["blood", "urine", "dexa", "calcium_score", "ecg", "chest_xray", "usg", "mri", "mammography"]


def _required_tests_for(gender: str | None) -> list[str]:
    g = (gender or "").upper()
    if g in ("F", "FEMALE"):
        return ALL_TEST_KEYS
    return [t for t in ALL_TEST_KEYS if t != "mammography"]


@router.get("/")
def get_orders(current_user=Depends(get_current_user)):
    rows = mongo.Order.find({"user_id": current_user["id"]})
    out = []
    for o in rows:
        report = mongo.Report.find_one({"order_id": o["id"]})
        required = _required_tests_for(o.get("patient_gender") or current_user.get("gender"))
        statuses = (report.get("test_statuses") or {}) if report else {}
        completed_tests = [t for t in required if statuses.get(t) == "complete"]
        pending_tests = [t for t in required if statuses.get(t) != "complete"]
        tests_complete = bool(report) and len(pending_tests) == 0
        out.append({
            "id": o["id"],
            "booking_id": o["booking_id"],
            "zen_id": current_user.get("zen_id"),
            "patient_name": o.get("patient_name") or current_user.get("name"),
            "patient_age": o.get("patient_age") or current_user.get("age"),
            "patient_gender": o.get("patient_gender") or current_user.get("gender"),
            "scan_type": o.get("scan_type"),
            "status": o.get("status"),
            "scan_date": o["scan_date"].isoformat() if o.get("scan_date") else None,
            "report_date": report["report_date"].isoformat() if (report and report.get("report_date")) else None,
            "next_visit": o["next_visit"].isoformat() if o.get("next_visit") else (report["next_visit"].isoformat() if (report and report.get("next_visit")) else None),
            "amount": o.get("amount"),
            "has_report": report is not None,
            "report_id": report["id"] if report else None,
            "is_published": bool(report.get("is_published")) if report else False,
            "tests_complete": tests_complete,
            "tests_total": len(required),
            "tests_completed": len(completed_tests),
            "tests_pending": pending_tests,
        })
    return out
