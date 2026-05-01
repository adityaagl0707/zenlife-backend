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
        tests_complete = False
        if report:
            statuses = report.get("test_statuses") or {}
            required = _required_tests_for(o.get("patient_gender"))
            tests_complete = all(statuses.get(t) == "complete" for t in required)
        out.append({
            "id": o["id"],
            "booking_id": o["booking_id"],
            "patient_name": o.get("patient_name"),
            "patient_age": o.get("patient_age"),
            "patient_gender": o.get("patient_gender"),
            "scan_type": o.get("scan_type"),
            "status": o.get("status"),
            "scan_date": o["scan_date"].isoformat() if o.get("scan_date") else None,
            "amount": o.get("amount"),
            "has_report": report is not None,
            "report_id": report["id"] if report else None,
            "is_published": bool(report.get("is_published")) if report else False,
            "tests_complete": tests_complete,
        })
    return out
