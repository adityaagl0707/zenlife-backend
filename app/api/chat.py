from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..core import mongo
from ..api.deps import get_current_user
from ..services.ai_service import chat_with_zeno

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


def _user_owns_report(report_id: int, user_id: int):
    """Returns the report dict if it exists and belongs to the user, else None."""
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        return None
    order = mongo.Order.find_one({"id": report["order_id"]})
    if not order or order.get("user_id") != user_id:
        return None
    return report


@router.get("/{report_id}/history")
def get_chat_history(report_id: int, current_user=Depends(get_current_user)):
    report = _user_owns_report(report_id, current_user["id"])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    msgs = sorted(
        mongo.ChatMessage.find({"report_id": report_id}),
        key=lambda m: m.get("created_at"),
    )
    return [
        {"role": m["role"], "content": m["content"], "created_at": m["created_at"].isoformat()}
        for m in msgs
    ]


@router.post("/{report_id}/message")
def send_message(report_id: int, req: ChatRequest, current_user=Depends(get_current_user)):
    report = _user_owns_report(report_id, current_user["id"])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    reply = chat_with_zeno(report, req.message)
    return {"role": "assistant", "content": reply}
