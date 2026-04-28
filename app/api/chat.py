from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..models.user import User
from ..models.report import Report, ChatMessage
from ..models.order import Order
from ..api.deps import get_current_user
from ..services.ai_service import chat_with_zeno

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.get("/{report_id}/history")
def get_chat_history(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(Report).join(Order).filter(Report.id == report_id, Order.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    msgs = db.query(ChatMessage).filter(ChatMessage.report_id == report_id).order_by(ChatMessage.created_at).all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs]


@router.post("/{report_id}/message")
def send_message(report_id: int, req: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(Report).join(Order).filter(Report.id == report_id, Order.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    reply = chat_with_zeno(report, req.message, db)
    return {"role": "assistant", "content": reply}
