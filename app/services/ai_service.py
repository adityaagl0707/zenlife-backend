"""Zeno AI — ZenLife's health intelligence assistant.

Chat: Google Gemini 2.0 Flash (fast, free-tier friendly)
Report extraction + health priorities: AI engine
"""
import base64
import datetime
import json
from anthropic import Anthropic
from google import genai as google_genai
from google.genai import types as google_types
from ..core import mongo
from ..core.config import get_settings
from .section_params import SECTION_PARAMETERS, SECTION_META

settings = get_settings()

# ──────────────────────────────────────────────────────────────────────────────
# PERSONA SYSTEM
# Classifies the patient's emotional state + risk profile on every turn and
# injects a tailored communication style into Zeno's system prompt.
# ──────────────────────────────────────────────────────────────────────────────

PERSONA_STYLES: dict[str, str] = {
    "celebratory": """
ACTIVE COMMUNICATION PERSONA: Celebratory & Educational
The patient is in a positive headspace — strong results, low anxiety.
- Lead with genuine enthusiasm about what's going well
- Be warm and conversational, like a friend sharing good news
- Educate them on WHY their good numbers matter and HOW to keep them
- Frame any mild concerns as easy wins, not problems to worry about
- Phrases that fit: "What's really impressive here is…", "You should feel good about…"
- Keep the energy forward-looking and motivating
- Do NOT open with caveats or problems — they earned the celebration
""",

    "calm_structured": """
ACTIVE COMMUNICATION PERSONA: Calm, Structured & Action-Oriented
The patient may be anxious or is dealing with significant findings.
- Open with reassurance — NEVER with the most alarming finding
- Use clear structure for every explanation: what it means → why it matters → what to do
- Give them a sense of control: focus on concrete, achievable next steps
- Replace alarming words: "serious" → "needs attention", "bad" → "outside the ideal range"
- Keep sentences short. Avoid long paragraphs. One idea at a time.
- Always end with ONE clear action they can take — today, this week, or at their next visit
- Phrases that fit: "Here's what we know…", "The encouraging part is…", "Your next step is simple…"
""",

    "plain_language": """
ACTIVE COMMUNICATION PERSONA: Plain Language & Analogy Mode
The patient is confused or unfamiliar with medical terminology.
- NEVER use a medical term without immediately explaining it in plain everyday words
- Use analogies and comparisons: "Think of your kidneys like a water filter…"
- One idea per sentence. Short paragraphs.
- Validate their confusion openly: "These numbers can feel overwhelming — let me break it down simply"
- No acronyms — say "red blood cells" not "RBC", "bad cholesterol" not "LDL"
- At the end, offer to go deeper: "Want me to explain any part of that differently?"
""",

    "empathetic": """
ACTIVE COMMUNICATION PERSONA: Empathetic — Acknowledge First, Explain Second
The patient is frustrated, upset, scared, or emotionally charged.
- Your FIRST sentence must acknowledge their emotion — before any clinical content
- Validate explicitly: "I completely understand why this feels worrying", "That's a fair concern"
- Do NOT rush to explain — earn the right to be heard first
- After acknowledging, be honest and clear — do not sugarcoat, but be gentle
- Never be defensive about the report or the platform
- Keep your tone unhurried, even if their message was blunt or abrupt
- Phrases that fit: "That's a completely fair concern…", "I hear you…", "Let's work through this together…"
""",
}


def classify_persona(report, user_message: str, history: list) -> str:
    """
    Rule-based persona classifier. Runs on every turn; cost = zero (no API call).
    Returns one of: 'celebratory' | 'calm_structured' | 'plain_language' | 'empathetic'

    Classification inputs:
      - report.overall_severity  (risk profile)
      - critical/major finding counts via OrganScore (already on the report object)
      - user_message content (emotional signals)
      - time of day (late-night anxiety signal)
      - conversation length (early turns are higher anxiety)
    """
    msg = user_message.lower().strip()
    hour = datetime.datetime.now().hour

    # ── Frustrated / angry signals ─────────────────────────────────────────
    frustrated = (
        any(kw in msg for kw in [
            "wrong", "mistake", "incorrect", "error", "why is", "why does",
            "ridiculous", "useless", "terrible", "horrible", "worst",
            "not right", "makes no sense", "fix this",
        ])
        or (user_message != user_message.lower() and user_message == user_message.upper() and len(user_message) > 4)
        or msg.count("!") >= 2
    )

    # ── Confused / needs-plain-language signals ────────────────────────────
    # Use specific multi-word phrases to avoid false positives (e.g. "explain" alone
    # could be a normal first question from a high-risk patient, not confusion).
    confused = any(kw in msg for kw in [
        "what does", "what is", "don't understand", "dont understand",
        "what does it mean", "confused", "not sure what",
        "what are these", "what do you mean", "i don't know what",
        "never heard of", "no idea what",
    ]) or ("explain" in msg and any(kw in msg for kw in ["don't", "dont", "confused", "mean", "what"]))

    # ── Anxious signals ────────────────────────────────────────────────────
    late_night = hour >= 22 or hour <= 5
    anxious = (
        late_night
        or any(kw in msg for kw in [
            "worried", "scared", "serious", "dangerous", "bad result",
            "afraid", "fear", "panic", "urgent", "emergency", "dying",
            "cancer", "heart attack", "stroke", "should i be worried",
            "how bad", "is it bad", "very bad", "cant sleep", "can't sleep",
            "keep thinking", "awake", "up at night",
        ])
        or msg.count("?") >= 3
    )

    # ── Risk profile from report ───────────────────────────────────────────
    severity = (report.overall_severity or "normal").lower()
    high_risk = severity in ("critical", "major")
    low_risk  = severity in ("normal", "minor")

    # ── Positive / celebratory signals ────────────────────────────────────
    # Keep these specific — avoid words that could appear in neutral questions
    positive = any(kw in msg for kw in [
        "great", "happy", "pleased", "amazing", "excellent", "fantastic",
        "well done", "proud", "love my", "good score", "great score",
        "so good", "really good", "doing well", "healthy",
    ])

    # Early in conversation (first 2 user turns) + high risk → more likely anxious
    user_turns = sum(1 for m in history if m.get("role") == "user")
    early_high_risk = user_turns <= 1 and high_risk

    # ── Decision tree ──────────────────────────────────────────────────────
    # Priority order (highest → lowest):
    #   1. frustrated/angry  → empathetic (acknowledge before explaining)
    #   2. low risk + happy  → celebratory (happy patient asking questions still
    #                          deserves celebration, not a plain-language lecture)
    #   3. anxious/high risk → calm_structured (anxiety beats confusion;
    #                          a worried patient asking "what is X" needs calm
    #                          reassurance first, not simplified jargon)
    #   4. confused          → plain_language (pure comprehension gap, no anxiety)
    #   5. default           → calm_structured (safest fallback)
    if frustrated:
        return "empathetic"
    if low_risk and positive:
        return "celebratory"
    if anxious or early_high_risk:
        return "calm_structured"
    if confused:
        return "plain_language"
    return "calm_structured"   # safe default for ambiguous cases


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


def build_report_context(report) -> str:
    findings = mongo.Finding.find({"report_id": report["id"]})
    organs = mongo.OrganScore.find({"report_id": report["id"]})
    order = mongo.Order.find_one({"id": report["order_id"]}) or {}

    # Strip findings the patient should never see (wrong gender, or admin
    # explicitly ignored) so Zeno doesn't reference them in chat replies.
    from .section_params import SECTION_PARAMETERS, _gender_norm
    g = _gender_norm(order.get("patient_gender"))
    excluded_names = set()
    if g:
        for plist in SECTION_PARAMETERS.values():
            for p in plist:
                pg = (p.get("gender") or "").upper()
                if pg in ("M", "F") and pg != g:
                    excluded_names.add(p["name"].lower().strip())
    ignored = {n.lower().strip() for n in (report.get("ignored_params") or [])}
    findings = [f for f in findings
                if f.name.lower().strip() not in excluded_names
                and f.name.lower().strip() not in ignored]

    critical = [f for f in findings if f.severity == "critical"]
    major    = [f for f in findings if f.severity == "major"]
    minor    = [f for f in findings if f.severity == "minor"]
    normal   = [f for f in findings if f.severity == "normal"]

    def fmt_finding(f, include_clinical=False):
        line = f"  • {f.name}: {f.value or 'N/A'} {f.unit or ''} (Normal: {f.normal_range or 'N/A'})"
        if include_clinical and f.clinical_findings:
            line += f"\n    → {f.clinical_findings}"
        return line

    rd = report.get("report_date")
    rd_str = rd.strftime('%d %b %Y') if rd else "N/A"
    lines = [
        "=== PATIENT OVERVIEW ===",
        f"Name: {order.get('patient_name', 'Patient')}",
        f"Age: {order.get('patient_age', 'N/A')}  |  Gender: {order.get('patient_gender', 'N/A')}",
        f"Report Date: {rd_str}",
        f"Overall Health Status: {(report.get('overall_severity') or 'normal').upper()}",
        f"Scan Coverage: {report.get('coverage_index', 0)}%",
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


def chat_with_zeno(report, user_message: str) -> str:
    """Zeno AI chat — powered by Google Gemini 2.5 Flash."""
    report_context = build_report_context(report)

    # Load chat history (last 20 messages, oldest first)
    history_rows = sorted(
        mongo.ChatMessage.find({"report_id": report["id"]}),
        key=lambda m: m.get("created_at") or 0,
    )[-20:]
    history = [{"role": m.get("role"), "content": m.get("content")} for m in history_rows]

    # ── Persona classification (rule-based, zero cost) ─────────────────────
    persona = classify_persona(report, user_message, history)
    persona_instruction = PERSONA_STYLES[persona]

    # ── System prompt ──────────────────────────────────────────────────────
    system_prompt = (
        f"{ZENO_SYSTEM_PROMPT}"
        f"\n\n{persona_instruction}"
        f"\n\n=== PATIENT REPORT CONTEXT ===\n{report_context}"
    )

    # ── Gemini call ────────────────────────────────────────────────────────
    client = google_genai.Client(api_key=settings.google_api_key)

    # Convert history to Gemini format (role: "assistant" → "model")
    gemini_contents = []
    for msg in history:
        gemini_contents.append(google_types.Content(
            role="model" if msg["role"] == "assistant" else "user",
            parts=[google_types.Part(text=msg["content"])],
        ))
    gemini_contents.append(google_types.Content(
        role="user",
        parts=[google_types.Part(text=user_message)],
    ))

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=gemini_contents,
            config=google_types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=1024,
                temperature=0.7,
            ),
        )
        reply = response.text
    except Exception as e:
        print(f"[Zeno] Gemini error: {type(e).__name__}: {e}")
        reply = (
            "I'm having a brief technical issue right now. "
            "Please try again in a moment — I'll be back shortly."
        )

    # Save to MongoDB
    now = mongo.now()
    mongo.ChatMessage.insert({"report_id": report["id"], "role": "user", "content": user_message, "created_at": now})
    mongo.ChatMessage.insert({"report_id": report["id"], "role": "assistant", "content": reply, "created_at": now})

    return reply


def extract_report_parameters(section_type: str, file_b64: str, file_mime: str, gender=None) -> dict:
    """
    Use the AI engine to extract parameter values from an uploaded report file.
    Returns {param_name: {value, unit, normal, severity, clinical_findings, recommendations}}.
    Also classifies each value as critical/major/minor/normal and generates AI clinical findings + recommendations.
    """
    if not settings.anthropic_api_key:
        return {"error": "No API key configured"}

    from .section_params import filter_params_by_gender
    params = filter_params_by_gender(SECTION_PARAMETERS.get(section_type, []), gender)
    param_list = "\n".join(
        f'- "{p["name"]}" (unit: {p["unit"] or "text"}, normal: {p["normal"]})'
        for p in params
    )
    section_label = SECTION_META.get(section_type, {}).get("label", section_type)

    prompt = f"""You are a friendly health coach reading a {section_label} report for a patient who has no medical training. Extract every parameter listed below.

For EACH parameter:
1. value: extract the exact value shown in the report (or "Not Found" if absent)
2. severity: one of critical / major / minor / normal
   - critical = urgently abnormal, needs immediate medical attention
   - major = significantly abnormal, needs medical follow-up soon
   - minor = mildly abnormal, worth monitoring
   - normal = within healthy range
3. clinical_findings: ONE short sentence (max 20 words) in PLAIN ENGLISH explaining what this value means for the patient. NO medical jargon. NO Latin. Use everyday words. Example: "Your blood sugar is slightly above the healthy range, which can stress your body over time."
4. recommendations: ONE clear, doable action (max 15 words). Start with a verb. Example: "Cut back on sweet drinks and aim for 30 min of walking after dinner."

For parameters that are NORMAL, keep clinical_findings to a single short reassurance ("This is in the healthy range — no action needed.") and leave recommendations empty.

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

    # Token budget scales with parameter count: ~120 tokens / param for the
    # JSON object (value + severity + clinical_findings + recommendations).
    # Pad generously so MRI/USG (100+ params) don't get truncated mid-JSON.
    max_tokens = max(4096, len(params) * 140 + 1024)
    max_tokens = min(max_tokens, 32000)  # safety cap

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    stop_reason = getattr(response, "stop_reason", None)

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()

    # Attempt 1 — direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Attempt 2 — repair truncated JSON. The model's last incomplete object
    # is often the cause; trim to the last complete top-level entry and close
    # the outer brace.
    repaired = _repair_truncated_json(raw)
    if repaired is not None:
        try:
            data = json.loads(repaired)
            if stop_reason == "max_tokens":
                data["_warning"] = (
                    f"AI output reached the token limit; some parameters "
                    f"may be missing. Try splitting the report or entering "
                    f"the remaining values manually."
                )
            return data
        except Exception:
            pass

    return {
        "_parse_error": (
            f"AI returned malformed JSON (stop_reason={stop_reason}). "
            f"Try a smaller PDF or enter values manually. "
            f"First 300 chars: {raw[:300]}"
        )
    }


def _repair_truncated_json(text: str):
    """
    Best-effort repair of JSON that was cut off mid-output. Strategy:
      1. Find the last position where a top-level value finished (closing '}'
         followed by ',' or end of input at the right nesting level).
      2. Trim everything after that and append a closing '}' for the outer
         object.
    Returns the repaired JSON string, or None if not recoverable.
    """
    if not text or not text.lstrip().startswith("{"):
        return None
    # Walk the string tracking brace depth; remember the position right after
    # the last time depth dropped from 2 → 1 (i.e. one inner object closed).
    depth = 0
    in_str = False
    escape = False
    last_safe = -1
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 1:
                last_safe = i  # just closed an inner entry
    if last_safe < 0:
        return None
    return text[: last_safe + 1] + "\n}"


def generate_priorities(report, findings: list, organs: list) -> list:
    """
    Use the AI engine to generate 3-5 prioritised health action plans for the patient.
    Returns a list of dicts: {title, why_important, diet, exercise, sleep, supplements}.
    """
    if not settings.anthropic_api_key:
        return []

    order = mongo.Order.find_one({"id": report.get("order_id")}) or {}

    critical = [f for f in findings if f.get("severity") == "critical"]
    major = [f for f in findings if f.get("severity") == "major"]
    minor = [f for f in findings if f.get("severity") == "minor"]

    def fmt(items):
        return "\n".join(f"  - {f.get('name')}: {f.get('value') or 'N/A'} {f.get('unit') or ''}" for f in items) or "  None"

    organ_lines = "\n".join(
        f"  - {o.get('organ_name')}: {(o.get('severity') or 'normal').upper()} ({o.get('critical_count', 0)}C/{o.get('major_count', 0)}M/{o.get('minor_count', 0)}m/{o.get('normal_count', 0)}n)"
        for o in organs
    )

    prompt = f"""Patient: {order.get('patient_name', 'Patient')}, Age: {order.get('patient_age', 'N/A')}, Gender: {order.get('patient_gender', 'N/A')}
Overall Severity: {(report.get('overall_severity') or 'normal').upper()}

=== ORGAN SCORES ===
{organ_lines}

=== CRITICAL FINDINGS ===
{fmt(critical)}

=== MAJOR FINDINGS ===
{fmt(major)}

=== MINOR FINDINGS (sample) ===
{fmt(minor[:10])}

Based on the above, generate 3 (maximum 5) personalised health priorities for this patient, ranked by urgency.

Write for someone with NO medical background. Be warm, direct and practical.

STYLE RULES — follow strictly:
- title: 4–6 words, action-oriented, plain English (e.g. "Lower your heart attack risk", NOT "Mitigate cardiovascular morbidity").
- why_important: ONE short sentence (max 25 words). Explain WHY in everyday language, mentioning the specific finding that triggered this priority.
- Each recommendation list item: ONE concrete action, max 12 words. Start with a verb. NO jargon. Specific quantities where useful (e.g. "Walk 30 min after dinner, 5 days a week").
- Keep each list to 2–4 items (no walls of text).
- Skip supplement_recommendations entirely if no supplement is needed (return [] or omit).

Return ONLY a valid JSON array (no markdown):
[
  {{
    "title": "short action title (4-6 words)",
    "why_important": "one short plain-English sentence (max 25 words)",
    "diet_recommendations": ["short action 1", "short action 2"],
    "exercise_recommendations": ["short action 1", "short action 2"],
    "sleep_recommendations": ["short action 1"],
    "supplement_recommendations": []
  }}
]"""

    client = Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"[generate_priorities] AI engine error: {e}")
        return []

    raw = (response.content[0].text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()

    # Direct parse
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        # Some models return {"priorities": [...]} or similar
        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list):
                    return v
        return []
    except Exception as e:
        # Repair truncated array — find last complete object and close the array
        try:
            depth = 0
            in_str = False
            escape = False
            last_close = -1
            for i, ch in enumerate(raw):
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        last_close = i
            if last_close > 0:
                start = raw.find("[")
                if start >= 0:
                    repaired = raw[start : last_close + 1] + "\n]"
                    result = json.loads(repaired)
                    if isinstance(result, list):
                        return result
        except Exception:
            pass
        print(f"[generate_priorities] Could not parse AI response: {e}\nFirst 400 chars: {raw[:400]}")
        return []


def generate_finding_explanations(findings: list) -> dict:
    """
    Bulk-generate `clinical_findings` (What this means) + `recommendations`
    (What to do) for a batch of findings. Returns {finding_name: {what, do}}.

    Designed for back-filling rows where the admin / AI extraction left
    these fields blank. Patient-facing — keep tone warm and plain English.
    """
    if not settings.anthropic_api_key or not findings:
        return {}

    rows = "\n".join(
        f"{i+1}. {f.get('name')} = {f.get('value') or 'N/A'} {f.get('unit') or ''} "
        f"(normal: {f.get('normal_range') or 'N/A'}, severity: {f.get('severity') or 'normal'})"
        for i, f in enumerate(findings)
    )

    prompt = f"""For each of the following lab/imaging measurements, write:
  - "what": a 1-sentence plain-English explanation of what this value means for the patient (max 30 words).
  - "do":   a 1-sentence concrete next step (max 25 words). Start with a verb.

Reference the actual value vs the normal range. No medical jargon. No abbreviations beyond common ones (BP, HR, BMI). Be honest about severity but not alarmist.

If a value is normal, "what" can reassure ("Within healthy range — no action needed.") and "do" can be empty string OR a maintenance tip.

=== MEASUREMENTS ===
{rows}

Return ONLY a valid JSON object keyed by exact measurement name (case-sensitive, exactly as given):
{{
  "Fasting Blood Glucose": {{"what": "...", "do": "..."}},
  "HbA1c": {{"what": "...", "do": "..."}}
}}"""

    client = Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"[generate_finding_explanations] AI engine error: {e}")
        return {}

    raw = (response.content[0].text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except Exception as e:
        print(f"[generate_finding_explanations] Parse error: {e}\nFirst 400 chars: {raw[:400]}")
    return {}


def generate_health_plan(report, findings: list, organs: list, priorities: list) -> dict:
    """
    Generate a holistic, personalised health plan that mixes medical
    follow-ups, diet, exercise, sleep, stress and monitoring. Returns a
    dict of category → list of action strings. Categories are chosen so
    the patient sees a single integrated plan rather than priority-by-
    priority recommendations.
    """
    if not settings.anthropic_api_key:
        return {}

    order = mongo.Order.find_one({"id": report.get("order_id")}) or {}

    crit = [f for f in findings if (f.get("severity") or "").lower() == "critical"]
    major = [f for f in findings if (f.get("severity") or "").lower() == "major"]
    minor = [f for f in findings if (f.get("severity") or "").lower() == "minor"]

    def fmt(items):
        return "\n".join(
            f"  - {f.get('name')}: {f.get('value') or 'N/A'} {f.get('unit') or ''}"
            for f in items
        ) or "  None"

    organ_lines = "\n".join(
        f"  - {o.get('organ_name')}: {(o.get('severity') or 'normal').upper()}"
        for o in organs if (o.get('severity') or 'normal').lower() != 'normal'
    ) or "  All organ systems healthy"

    priority_titles = "\n".join(f"  {i+1}. {p.get('title')}" for i, p in enumerate(priorities)) or "  None defined"

    prompt = f"""Patient: {order.get('patient_name','Patient')}, Age: {order.get('patient_age','N/A')}, Gender: {order.get('patient_gender','N/A')}
Overall Severity: {(report.get('overall_severity') or 'normal').upper()}

=== ORGAN SYSTEMS NEEDING ATTENTION ===
{organ_lines}

=== TOP HEALTH PRIORITIES (already identified) ===
{priority_titles}

=== CRITICAL FINDINGS ===
{fmt(crit)}

=== MAJOR FINDINGS ===
{fmt(major)}

=== MINOR FINDINGS (sample) ===
{fmt(minor[:8])}

You are creating ONE integrated health plan for this patient — a doctor's prescription written in plain English that covers every angle. The patient already sees per-priority recommendations elsewhere; this is the holistic single plan.

Categories to fill (return ONLY these exact keys):
- medical_consultations: 2-4 specific specialist visits or tests to schedule (e.g. "Cardiologist consult within 2 weeks", "Repeat lipid panel in 3 months").
- diet_plan: 3-5 overarching eating principles tailored to this patient's findings.
- exercise_plan: 2-4 specific activity recommendations with duration / frequency.
- sleep_and_stress: 2-3 actions for sleep hygiene + stress management.
- supplements: 0-3 supplements with dose. Empty list if none indicated.
- monitoring: 2-3 vitals/parameters they should track between scans.

STYLE RULES (strict):
- Each item: ONE concrete action, max 14 words. Start with a verb.
- No medical jargon. No abbreviations beyond common ones (BP, HR, BMI).
- Specific quantities where useful (mg, minutes, days/week).
- Reference the actual findings — generic advice is wrong.

Return ONLY a valid JSON object (no markdown, no preamble):
{{
  "medical_consultations": ["..."],
  "diet_plan": ["..."],
  "exercise_plan": ["..."],
  "sleep_and_stress": ["..."],
  "supplements": [],
  "monitoring": ["..."]
}}"""

    client = Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"[generate_health_plan] AI engine error: {e}")
        return {}

    raw = (response.content[0].text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()

    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except Exception as e:
        print(f"[generate_health_plan] Could not parse AI response: {e}\nFirst 400 chars: {raw[:400]}")
    return {}


_FALLBACK_STARTERS = [
    "What are my most critical findings?",
    "What lifestyle changes should I make?",
    "How serious is my ZenScore?",
    "Which findings need urgent attention?",
]


def generate_chat_starters(report, findings, organs, body_age=None) -> list:
    """Generate 4 personalised conversation-starter questions based on this report."""
    if not settings.anthropic_api_key:
        return _FALLBACK_STARTERS

    crit = [f for f in findings if (f.get("severity") or "").lower() == "critical"]
    major = [f for f in findings if (f.get("severity") or "").lower() == "major"]
    crit_organs = [o for o in organs if (o.get("severity") or "").lower() == "critical"]
    major_organs = [o for o in organs if (o.get("severity") or "").lower() == "major"]

    def fmt(items, key="name"):
        return ", ".join(f.get(key) or "" for f in items[:6]) or "none"

    body_age_line = ""
    if body_age and body_age.get("zen_age") is not None:
        body_age_line = f"ZenAge: {body_age.get('zen_age')} (chronological {body_age.get('chronological_age', '?')})"

    prompt = f"""Generate exactly 4 short conversation-starter questions a patient might
ask their AI health assistant about their own ZenScan report. Each question
should be in the patient's voice (first person), under 10 words, and SPECIFIC
to findings in this report (not generic).

Patient report context:
- ZenScore: {report.get('coverage_index')}, Overall severity: {(report.get('overall_severity') or 'normal').upper()}
- Critical organ systems: {fmt(crit_organs, 'organ_name')}
- Major organ systems: {fmt(major_organs, 'organ_name')}
- Critical findings: {fmt(crit)}
- Major findings: {fmt(major)}
{body_age_line}

Return ONLY a JSON array of 4 strings. No prose, no markdown.
Example: ["Why is my LDL so high?", "What does a CAC of 480 mean?", "How can I lower my fatty liver risk?", "Should I see a cardiologist?"]"""

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = (response.content[0].text or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rstrip("`").strip()
        result = json.loads(raw)
        if isinstance(result, list):
            cleaned = [str(s).strip() for s in result if str(s).strip()]
            if cleaned:
                return cleaned[:4]
    except Exception as e:
        print(f"[generate_chat_starters] Falling back to defaults: {e}")
    return _FALLBACK_STARTERS
