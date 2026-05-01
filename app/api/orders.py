from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.user import User
from ..models.order import Order
from ..api.deps import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")
def get_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()
    return [
        {
            "id": o.id,
            "booking_id": o.booking_id,
            "patient_name": o.patient_name,
            "patient_age": o.patient_age,
            "patient_gender": o.patient_gender,
            "scan_type": o.scan_type,
            "status": o.status,
            "scan_date": o.scan_date.isoformat() if o.scan_date else None,
            "amount": o.amount,
            "has_report": o.report is not None,
            "report_id": o.report.id if o.report else None,
            "is_published": getattr(o.report, "is_published", False) if o.report else False,
        }
        for o in orders
    ]
