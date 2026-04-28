"""Zeno AI — ZenLife's health intelligence assistant, powered by Claude."""
import base64
import json
from anthropic import Anthropic
from sqlalchemy.orm import Session
from ..models.report import Report, Finding, OrganScore, ChatMessage
from ..core.config import get_settings
from .section_params import SECTION_PARAMETERS, SECTION_META

settings = get_settings()

ZENO_SYSTEM_PROMPT = """You are Zeno, a senior physician at ZenLife with decades of clinical experience across cardiology, endocrinology, internal medicine, and preventive health.

Your role:
You are the patient's personal health guide — not an alarm system. Your job is to help them understand their whole health picture, not just fixate on whatever is most abnormal. A patient's health is the sum of everything: what's going well, what needs watching, and what needs action. Balance all three.

Your communication style:
- Warm, conversational, and human — like a trusted doctor having a real conversation, not reading a report out loud.
- Use plain language. When you must use a medical term, explain it immediately in everyday words.
- Be BALANCED. Do not make every answer about the single worst finding. Acknowledge good results too — patients need to know what they're doing right.
- Be appropriately thorough. A good response is 4-8 sentences. Cover what the patient asked about with enough depth to be genuinely useful, but don't write an essay.
- Reference the patient's actual numbers and name — make it personal, not generic.
- Show empathy. Acknowledge what a result might feel like emotionally before explaining the clinical meaning.
- End with one clear, practical next step the patient can act on — diet, lifestyle, follow-up, or peace of mind.
- Never diagnose. Explain what a finding likely means and why it matters for how they live and feel.
- When something genuinely needs attention, say so clearly and kindly — but don't repeat the same concern in every response.
- When something is fine or good, say so with confidence. Relief and reassurance are equally valuable to a patient.

What to avoid:
- Do not open every message by highlighting the most critical finding unless the patient specifically asked about it.
- Do not give bullet-point lists of problems. Weave the picture together in natural paragraphs.
- Do not be alarmist. Severity classifications are clinical tools — translate them into real-life impact for this specific person.
- Do not give the same advice repeatedly across a conversation. Read the chat history and build on it.

Example tone:
"Your liver markers are actually looking really solid — AST and ALT are both well within range, which tells me your liver is handling things well. Your cholesterol picture is a little mixed: HDL (the protective kind) is good, but LDL is nudging slightly high. That's not urgent, but worth addressing over the next few months with some simple food swaps. Your kidney function is perfectly fine. Overall, you're in a better place than many people your age — a few targeted changes and your next scan will look even stronger."

You are NOT a replacement for in-person care. When something truly needs a specialist or urgent attention, say so warmly and directly."""


def build_report_context(report: Report, db: Session) -> str:
    findings = db.query(Finding).filter(Finding.report_id == report.id).all()
    organs = db.query(OrganScore).filter(OrganScore.report_id == report.id).all()

    critical = [f for f in findings if f.severity == "critical"]
    major    = [f for f in findings if f.severity == "major"]
    minor    = [f for f in findings if f.severity == "minor"]
    normal   = [f for f in findings if f.severity == "normal"]

    def fmt_finding(f, include_clinical=False):
        line = f"  • {f.name}: {f.value or 'N/A'} {f.unit or ''} (Normal: {f.normal_range or 'N/A'})"
        if include_clinical and f.clinical_findings:
            line += f"\n    → {f.clinical_findings}"
        return line

    lines = [
        "=== PATIENT OVERVIEW ===",
        f"Name: {report.order.patient_name}",
        f"Age: {report.order.patient_age}  |  Gender: {report.order.patient_gender}",
        f"Report Date: {report.report_date.strftime('%d %b %Y')}",
        f"Overall Health Status: {report.overall_severity.upper()}",
        f"Scan Coverage: {report.coverage_index}%",
        "",
        "=== ORGAN SYSTEM SUMMARY ===",
        "(Use this for the big-picture view of how each body system is doing)",
    ]
    for o in organs:
        lines.append(
            f"  • {o.organ_name}: {o.severity.upper()} — {o.risk_label} "
            f"({o.critical_count} critical / {o.major_count} major / {o.minor_count} minor / {o.normal_count} normal markers)"
        )

    lines += [
        "",
        f"=== WHAT'S WORKING WELL — NORMAL FINDINGS ({len(normal)} markers) ===",
        "(These are healthy. Acknowledge them positively when relevant.)",
    ]
    for f in normal:
        lines.append(f"  • {f.name}: {f.value or 'N/A'} {f.unit or ''}")

    lines += [
        "",
        f"=== NEEDS MONITORING — MINOR FINDINGS ({len(minor)} markers) ===",
        "(Mildly outside range — worth mentioning but not alarming)",
    ]
    for f in minor:
        lines.append(fmt_finding(f))

    lines += [
        "",
        f"=== NEEDS ATTENTION — MAJOR FINDINGS ({len(major)} markers) ===",
        "(Significantly abnormal — important to address, not immediately dangerous)",
    ]
    for f in major:
        lines.append(fmt_finding(f, include_clinical=True))

    lines += [
        "",
        f"=== URGENT — CRITICAL FINDINGS ({len(critical)} markers) ===",
        "(Urgently abnormal — be honest but calm; recommend specialist follow-up)",
    ]
    for f in critical:
        lines.append(fmt_finding(f, include_clinical=True))

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
        max_tokens=1536,
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


def generate_priorities(report: Report, findings: list, organs: list) -> list:
    """
    Use Claude to generate 3-5 prioritised health action plans for the patient.
    Returns a list of dicts: {title, why_important, diet, exercise, sleep, supplements}.
    """
    if not settings.anthropic_api_key:
        return []

    critical = [f for f in findings if f.severity == "critical"]
    major = [f for f in findings if f.severity == "major"]
    minor = [f for f in findings if f.severity == "minor"]

    def fmt(items):
        return "\n".join(f"  - {f.name}: {f.value or 'N/A'} {f.unit or ''}" for f in items) or "  None"

    organ_lines = "\n".join(
        f"  - {o.organ_name}: {o.severity.upper()} ({o.critical_count}C/{o.major_count}M/{o.minor_count}m/{o.normal_count}n)"
        for o in organs
    )

    prompt = f"""Patient: {report.order.patient_name}, Age: {report.order.patient_age}, Gender: {report.order.patient_gender}
Overall Severity: {report.overall_severity.upper()}

=== ORGAN SCORES ===
{organ_lines}

=== CRITICAL FINDINGS ===
{fmt(critical)}

=== MAJOR FINDINGS ===
{fmt(major)}

=== MINOR FINDINGS (sample) ===
{fmt(minor[:10])}

Based on the above, generate 3-5 personalised health priorities for this patient, ranked by urgency.
For each priority return structured JSON. Focus on actionable lifestyle changes the patient can start immediately.

Return ONLY a valid JSON array (no markdown):
[
  {{
    "title": "short action-oriented title",
    "why_important": "2-3 sentence explanation of why this matters for this specific patient",
    "diet_recommendations": ["specific food advice 1", "specific food advice 2"],
    "exercise_recommendations": ["specific exercise advice 1", "specific exercise advice 2"],
    "sleep_recommendations": ["specific sleep advice 1"],
    "supplement_recommendations": ["specific supplement if relevant, else omit"]
  }}
]"""

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except Exception:
        return []
