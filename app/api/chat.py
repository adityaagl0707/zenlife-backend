from datetime import datetime, time, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..core import mongo
from ..api.deps import get_current_user
from ..services.ai_service import chat_with_zeno, generate_chat_starters

router = APIRouter(prefix="/chat", tags=["chat"])

# IST = UTC+5:30 — patients see "today" in India local time, so the chat
# resets at midnight IST. Easy to swap to per-user TZ if we ever need it.
_IST = timezone(timedelta(hours=5, minutes=30))


def _start_of_today_utc() -> datetime:
    """UTC datetime corresponding to today's 00:00 in IST."""
    now_ist = datetime.now(_IST)
    midnight_ist = datetime.combine(now_ist.date(), time(0, 0), tzinfo=_IST)
    return midnight_ist.astimezone(timezone.utc).replace(tzinfo=None)


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
    """Return TODAY's chat history only.

    The Ask Zeno conversation is intentionally daily — each morning the
    patient sees a fresh starter screen. Older messages stay in the DB
    (audit / future analytics) but aren't surfaced. Cutoff is midnight IST.
    """
    report = _user_owns_report(report_id, current_user["id"])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    today_start = _start_of_today_utc()
    msgs = sorted(
        mongo.ChatMessage.find({
            "report_id": report_id,
            "created_at": {"$gte": today_start},
        }),
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


@router.get("/{report_id}/starters")
def get_starter_questions(report_id: int, current_user=Depends(get_current_user)):
    """Return 4 personalised conversation-starter questions for this report."""
    report = _user_owns_report(report_id, current_user["id"])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    findings = mongo.Finding.find({"report_id": report_id})
    organs = mongo.OrganScore.find({"report_id": report_id})
    body_age = mongo.BodyAgeDoc.find_one({"report_id": report_id})
    starters = generate_chat_starters(report, findings, organs, body_age)
    return {"starters": starters}
