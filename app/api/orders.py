from fastapi import APIRouter, Depends
from ..core import mongo
from ..api.deps import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")
def get_orders(current_user=Depends(get_current_user)):
    rows = mongo.Order.find({"user_id": current_user["id"]})
    out = []
    for o in rows:
        report = mongo.Report.find_one({"order_id": o["id"]})
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
        })
    return out
