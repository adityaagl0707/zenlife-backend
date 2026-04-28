"""Zeno AI — ZenLife's health intelligence assistant, powered by Claude."""
import base64
import json
from anthropic import Anthropic
from sqlalchemy.orm import Session
from ..models.report import Report, Finding, OrganScore, ChatMessage
from ..core.config import get_settings
from .section_params import SECTION_PARAMETERS, SECTION_META

settings = get_settings()

ZENO_SYSTEM_PROMPT = """You are Zeno, a senior physician at ZenLife with decades of clinical experience across cardiology, endocrinology, and internal medicine.

Your communication style:
- Talk like a caring, trusted doctor sitting across the table from a patient — warm, human, and direct.
- Use simple everyday language. Never use medical jargon without immediately explaining it in plain words.
- Keep answers SHORT and CRISP. 3-5 sentences max per response. No bullet-point walls.
- Lead with what matters most to the patient, not clinical facts.
- Show genuine empathy. Acknowledge how a finding might feel before explaining it.
- Create a personal bond — remember the patient's name, reference their specific numbers.
- End every response with one clear, doable next step the patient can act on today.
- Never diagnose. Explain what a finding likely means and why it matters for their life.
- When something is serious, say so honestly but kindly — don't sugarcoat, but don't alarm.

Example tone: "Your LDL is a bit high — think of it as too much 'bad' fat floating in your blood. The good news is this is very manageable with a few tweaks. Let's talk about what you can do this week."

You are NOT a replacement for in-person care. If something needs urgent attention, say so clearly and warmly."""


def build_report_context(report: Report, db: Session) -> str:
    findings = db.query(Finding).filter(Finding.report_id == report.id).all()
    organs = db.query(OrganScore).filter(OrganScore.report_id == report.id).all()

    critical = [f for f in findings if f.severity == "critical"]
    major = [f for f in findings if f.severity == "major"]
    minor = [f for f in findings if f.severity == "minor"]

    lines = [
        f"Patient: {report.order.patient_name}, Age: {report.order.patient_age}, Gender: {report.order.patient_gender}",
        f"Overall Severity: {report.overall_severity.upper()}",
        f"ZenCoverage™ Index: {report.coverage_index}%",
        f"Report Date: {report.report_date.strftime('%d %b %Y')}",
        "",
        "=== CRITICAL FINDINGS ===",
    ]
    for f in critical:
        lines.append(f"- {f.name}: {f.value or 'N/A'} {f.unit or ''} (Normal: {f.normal_range or 'N/A'})")
        if f.clinical_findings:
            lines.append(f"  Clinical: {f.clinical_findings}")

    lines.append("\n=== MAJOR FINDINGS ===")
    for f in major:
        lines.append(f"- {f.name}: {f.value or 'N/A'} {f.unit or ''} (Normal: {f.normal_range or 'N/A'})")

    lines.append("\n=== MINOR FINDINGS ===")
    for f in minor:
        lines.append(f"- {f.name}: {f.value or 'N/A'} {f.unit or ''} (Normal: {f.normal_range or 'N/A'})")

    lines.append("\n=== ORGAN SCORES ===")
    for o in organs:
        lines.append(f"- {o.organ_name}: {o.severity.upper()} — {o.risk_label}")

    return "\n".join(lines)


def chat_with_zeno(report: Report, user_message: str, db: Session) -> str:
    if not settings.anthropic_api_key:
        return (
            "Zeno is currently in demo mode. Connect an Anthropic API key to enable full AI capabilities. "
            f"Based on your report, your most critical finding is your Agatston Score of 550, "
            "which indicates significant coronary artery disease requiring immediate cardiologist consultation."
        )

    client = Anthropic(api_key=settings.anthropic_api_key)
    report_context = build_report_context(report, db)

    # Load chat history (last 10 messages)
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.report_id == report.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(20)
        .all()
    )

    messages = []
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    system = f"{ZENO_SYSTEM_PROMPT}\n\n=== PATIENT REPORT CONTEXT ===\n{report_context}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=messages,
    )

    reply = response.content[0].text

    # Save to DB
    db.add(ChatMessage(report_id=report.id, role="user", content=user_message))
    db.add(ChatMessage(report_id=report.id, role="assistant", content=reply))
    db.commit()

    return reply


def extract_report_parameters(section_type: str, file_b64: str, file_mime: str) -> dict:
    """
    Use Claude vision/document to extract parameter values from an uploaded report file.
    Returns {param_name: {value, unit, normal, severity, clinical_findings, recommendations}}.
    Also classifies each value as critical/major/minor/normal and generates AI clinical findings + recommendations.
    """
    if not settings.anthropic_api_key:
        return {"error": "No API key configured"}

    params = SECTION_PARAMETERS.get(section_type, [])
    param_list = "\n".join(
        f'- "{p["name"]}" (unit: {p["unit"] or "text"}, normal: {p["normal"]})'
        for p in params
    )
    section_label = SECTION_META.get(section_type, {}).get("label", section_type)

    prompt = f"""You are a senior medical data extraction AI. Analyse this {section_label} report image/document.

Extract the value for EVERY parameter listed below. For each parameter:
1. Extract the exact value as shown in the report (or "Not Found" if absent)
2. Classify severity as one of: critical / major / minor / normal
   - critical = urgently abnormal, needs immediate medical attention
   - major = significantly abnormal, needs medical follow-up soon
   - minor = mildly abnormal, worth monitoring
   - normal = within healthy range
3. Write 1-2 sentence clinical findings explaining what this value means clinically
4. Write 1 sentence recommendation for this specific finding

Parameters to extract:
{param_list}

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "Parameter Name": {{
    "value": "extracted value or Not Found",
    "severity": "critical|major|minor|normal",
    "clinical_findings": "...",
    "recommendations": "..."
  }},
  ...
}}"""

    client = Anthropic(api_key=settings.anthropic_api_key)

    if file_mime == "application/pdf":
        content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": file_b64,
                },
            },
            {"type": "text", "text": prompt},
        ]
    else:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": file_mime,
                    "data": file_b64,
                },
            },
            {"type": "text", "text": prompt},
        ]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except Exception:
        return {"_parse_error": raw[:500]}
