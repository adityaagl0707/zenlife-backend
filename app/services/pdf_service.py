"""ZenReport PDF + CSV generators (full report, executive summary, lab data)."""
import csv
import io
from datetime import datetime

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)

from ..core import mongo

BRAND = HexColor("#0a3d2e")
BRAND_LIGHT = HexColor("#117a5c")
INK = HexColor("#1a1614")
MUTED = HexColor("#6b7280")
LINE = HexColor("#e5e7eb")
SEV_COLOR = {
    "critical": HexColor("#dc2626"),
    "major":    HexColor("#d97706"),
    "minor":    HexColor("#ca8a04"),
    "normal":   HexColor("#059669"),
}


# ── Helpers ────────────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    return {
        "title":    ParagraphStyle("title",    parent=base["Title"],   fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=BRAND, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"],  fontName="Helvetica",     fontSize=10, leading=14, textColor=MUTED, spaceAfter=12),
        "h1":       ParagraphStyle("h1",       parent=base["Heading1"],fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=BRAND, spaceBefore=14, spaceAfter=6),
        "h2":       ParagraphStyle("h2",       parent=base["Heading2"],fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK,   spaceBefore=8,  spaceAfter=4),
        "body":     ParagraphStyle("body",     parent=base["Normal"],  fontName="Helvetica",     fontSize=9.5, leading=13, textColor=INK),
        "small":    ParagraphStyle("small",    parent=base["Normal"],  fontName="Helvetica",     fontSize=8.5, leading=11, textColor=MUTED),
        "kpi":      ParagraphStyle("kpi",      parent=base["Normal"],  fontName="Helvetica-Bold", fontSize=22, leading=24, textColor=BRAND, alignment=TA_CENTER),
        "kpiLbl":   ParagraphStyle("kpiLbl",   parent=base["Normal"],  fontName="Helvetica",     fontSize=8,  leading=10, textColor=MUTED, alignment=TA_CENTER),
        "right":    ParagraphStyle("right",    parent=base["Normal"],  fontName="Helvetica",     fontSize=9,  leading=11, textColor=MUTED, alignment=TA_RIGHT),
    }


def _gather(report_id: int) -> dict:
    report = mongo.Report.find_one({"id": report_id})
    if not report:
        return {}
    order = mongo.Order.find_one({"id": report.get("order_id")}) or {}
    user = mongo.User.find_one({"id": order.get("user_id")}) or {}
    findings = mongo.Finding.find({"report_id": report_id})
    organs = sorted(
        mongo.OrganScore.find({"report_id": report_id}),
        key=lambda o: o.get("display_order", 0),
    )
    priorities = sorted(
        mongo.HealthPriority.find({"report_id": report_id}),
        key=lambda p: p.get("priority_order", 0),
    )
    body_age = mongo.BodyAgeDoc.find_one({"report_id": report_id})

    crit = sum(1 for f in findings if (f.get("severity") or "").lower() == "critical")
    major = sum(1 for f in findings if (f.get("severity") or "").lower() == "major")
    minor = sum(1 for f in findings if (f.get("severity") or "").lower() == "minor")
    normal = sum(1 for f in findings if (f.get("severity") or "").lower() == "normal")

    return {
        "report": report, "order": order, "user": user,
        "findings": findings, "organs": organs, "priorities": priorities,
        "body_age": body_age,
        "counts": {"critical": crit, "major": major, "minor": minor, "normal": normal},
    }


def _fmt_date(d):
    if not d: return "—"
    if isinstance(d, datetime): return d.strftime("%d %b %Y")
    return str(d)


def _header_block(ctx):
    s = _styles()
    o, u, r = ctx["order"], ctx["user"], ctx["report"]
    name = o.get("patient_name") or u.get("name") or "Patient"
    age  = o.get("patient_age") or u.get("age")
    gender = o.get("patient_gender") or u.get("gender")
    zen_id = u.get("zen_id") or "—"
    booking = o.get("booking_id") or "—"
    scan_dt = _fmt_date(o.get("scan_date"))
    rep_dt = _fmt_date(r.get("report_date"))
    next_dt = _fmt_date(r.get("next_visit"))
    parts = []
    if age: parts.append(f"{age} yrs")
    if gender: parts.append(gender)
    parts.append(o.get("scan_type") or "ZenScan")
    sub = " · ".join(parts)

    info_data = [
        ["Patient", name, "Zen ID", zen_id],
        ["Booking", booking, "Scan Date", scan_dt],
        ["Report Date", rep_dt, "Next Visit", next_dt],
    ]
    info = Table(info_data, colWidths=[22*mm, 60*mm, 22*mm, 56*mm])
    info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR", (2, 0), (2, -1), MUTED),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))

    return [
        Paragraph(name, s["title"]),
        Paragraph(sub, s["subtitle"]),
        info,
        Spacer(1, 6),
    ]


def _zenscore_kpis(ctx):
    s = _styles()
    r = ctx["report"]
    cnt = ctx["counts"]
    score = int(r.get("coverage_index") or 0)
    severity = (r.get("overall_severity") or "normal").upper()
    sev_color = SEV_COLOR.get((r.get("overall_severity") or "normal").lower(), MUTED)

    kpi = [
        [Paragraph(str(score), ParagraphStyle("k1", parent=s["kpi"], textColor=sev_color)),
         Paragraph(str(cnt["critical"]), ParagraphStyle("k2", parent=s["kpi"], textColor=SEV_COLOR["critical"])),
         Paragraph(str(cnt["major"]),    ParagraphStyle("k3", parent=s["kpi"], textColor=SEV_COLOR["major"])),
         Paragraph(str(cnt["minor"]),    ParagraphStyle("k4", parent=s["kpi"], textColor=SEV_COLOR["minor"])),
         Paragraph(str(cnt["normal"]),   ParagraphStyle("k5", parent=s["kpi"], textColor=SEV_COLOR["normal"])),
        ],
        [Paragraph(f"ZenScore<br/><font size='7' color='#9ca3af'>{severity}</font>", s["kpiLbl"]),
         Paragraph("Critical", s["kpiLbl"]),
         Paragraph("Major", s["kpiLbl"]),
         Paragraph("Minor", s["kpiLbl"]),
         Paragraph("Normal", s["kpiLbl"]),
        ],
    ]
    t = Table(kpi, colWidths=[32*mm]*5, rowHeights=[16*mm, 8*mm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8f7f4")),
    ]))
    return t


def _organ_table(ctx):
    s = _styles()
    rows = [["Organ System", "Severity", "Crit", "Maj", "Min", "Norm"]]
    for o in ctx["organs"]:
        sev = (o.get("severity") or "normal").lower()
        rows.append([
            Paragraph(o.get("organ_name") or "—", s["body"]),
            Paragraph(f'<font color="{SEV_COLOR.get(sev, MUTED).hexval()}"><b>{sev.upper()}</b></font>', s["small"]),
            str(o.get("critical_count", 0)),
            str(o.get("major_count", 0)),
            str(o.get("minor_count", 0)),
            str(o.get("normal_count", 0)),
        ])
    t = Table(rows, colWidths=[70*mm, 30*mm, 15*mm, 15*mm, 15*mm, 15*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#fafaf9")]),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _findings_table(ctx, only_severities=None):
    s = _styles()
    findings = [f for f in ctx["findings"] if (f.get("severity") or "").lower() != "normal"] \
        if only_severities is None else \
        [f for f in ctx["findings"] if (f.get("severity") or "").lower() in only_severities]
    findings = sorted(findings, key=lambda f: ["critical","major","minor","normal"].index((f.get("severity") or "normal").lower()))

    rows = [["Test / Marker", "Value", "Normal", "Severity"]]
    for f in findings:
        sev = (f.get("severity") or "normal").lower()
        rows.append([
            Paragraph(f.get("name") or "—", s["body"]),
            f"{f.get('value') or '—'} {f.get('unit') or ''}".strip(),
            f.get("normal_range") or "—",
            Paragraph(f'<font color="{SEV_COLOR.get(sev, MUTED).hexval()}"><b>{sev.upper()}</b></font>', s["small"]),
        ])
    if len(rows) == 1:
        return Paragraph("No abnormal findings.", s["small"])

    t = Table(rows, colWidths=[70*mm, 35*mm, 30*mm, 25*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#fafaf9")]),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _priorities_block(ctx):
    s = _styles()
    out = []
    for p in ctx["priorities"]:
        block = []
        block.append(Paragraph(f"{p.get('priority_order', '')}. {p.get('title') or ''}", s["h2"]))
        if p.get("why_important"):
            block.append(Paragraph(p["why_important"], s["body"]))
            block.append(Spacer(1, 4))
        for label, key in (("Diet", "diet_recommendations"),
                            ("Exercise", "exercise_recommendations"),
                            ("Sleep", "sleep_recommendations"),
                            ("Supplements", "supplement_recommendations")):
            recs = p.get(key) or []
            if recs:
                items = "<br/>".join(f"• {r}" for r in recs)
                block.append(Paragraph(f"<b>{label}:</b><br/>{items}", s["small"]))
                block.append(Spacer(1, 2))
        out.append(KeepTogether(block))
        out.append(Spacer(1, 6))
    if not out:
        out = [Paragraph("No personalised priorities generated yet.", s["small"])]
    return out


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(15*mm, 10*mm, "ZenLife Health Intelligence · Confidential")
    canvas.drawRightString(A4[0] - 15*mm, 10*mm, f"Page {doc.page}")
    canvas.restoreState()


# ── Public generators ──────────────────────────────────────────────────────

def generate_full_report_pdf(report_id: int) -> bytes:
    ctx = _gather(report_id)
    if not ctx:
        return b""
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=18*mm,
        title=f"ZenReport — {ctx['order'].get('patient_name', 'Patient')}",
    )
    story = []
    story.extend(_header_block(ctx))
    story.append(_zenscore_kpis(ctx))
    story.append(Spacer(1, 8))

    if ctx["report"].get("summary"):
        story.append(Paragraph("AI Health Assessment", s["h1"]))
        story.append(Paragraph(ctx["report"]["summary"], s["body"]))

    if ctx["body_age"]:
        ba = ctx["body_age"]
        story.append(Paragraph("ZenAge — Biological Age", s["h1"]))
        line = (f"Chronological age: <b>{ba.get('chronological_age', '—')}</b> · "
                f"PhenoAge: <b>{ba.get('pheno_age', '—')}</b> · "
                f"ZenAge: <b>{ba.get('zen_age', '—')}</b> "
                f"({'+' if (ba.get('age_difference') or 0) > 0 else ''}{ba.get('age_difference', 0)} yrs)")
        story.append(Paragraph(line, s["body"]))
        if ba.get("interpretation"):
            story.append(Paragraph(ba["interpretation"], s["small"]))

    story.append(Paragraph("Organ-System Scorecard", s["h1"]))
    story.append(_organ_table(ctx))

    story.append(Paragraph("Health Priorities", s["h1"]))
    story.extend(_priorities_block(ctx))

    story.append(PageBreak())
    story.append(Paragraph("Abnormal Findings", s["h1"]))
    story.append(Paragraph("All findings classified as Minor, Major, or Critical.", s["small"]))
    story.append(Spacer(1, 4))
    story.append(_findings_table(ctx))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def generate_summary_pdf(report_id: int) -> bytes:
    ctx = _gather(report_id)
    if not ctx:
        return b""
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=18*mm,
        title=f"ZenReport Summary — {ctx['order'].get('patient_name', 'Patient')}",
    )
    story = []
    story.extend(_header_block(ctx))
    story.append(_zenscore_kpis(ctx))
    story.append(Spacer(1, 8))

    if ctx["report"].get("summary"):
        story.append(Paragraph("AI Summary", s["h1"]))
        story.append(Paragraph(ctx["report"]["summary"], s["body"]))

    story.append(Paragraph("Top Health Priorities", s["h1"]))
    for p in ctx["priorities"][:5]:
        story.append(Paragraph(f"<b>{p.get('priority_order', '')}. {p.get('title') or ''}</b>", s["body"]))
        if p.get("why_important"):
            story.append(Paragraph(p["why_important"], s["small"]))
        story.append(Spacer(1, 4))

    story.append(Paragraph("Critical & Major Findings", s["h1"]))
    story.append(_findings_table(ctx, only_severities={"critical", "major"}))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def generate_lab_csv(report_id: int) -> bytes:
    ctx = _gather(report_id)
    if not ctx:
        return b""
    buf = io.StringIO()
    w = csv.writer(buf)
    o, u, r = ctx["order"], ctx["user"], ctx["report"]
    w.writerow(["ZenLife Lab Data Export"])
    w.writerow(["Patient", o.get("patient_name") or u.get("name")])
    w.writerow(["Zen ID", u.get("zen_id") or ""])
    w.writerow(["Booking", o.get("booking_id") or ""])
    w.writerow(["Scan Date", _fmt_date(o.get("scan_date"))])
    w.writerow(["Report Date", _fmt_date(r.get("report_date"))])
    w.writerow([])
    w.writerow(["Test / Marker", "Test Type", "Value", "Unit", "Normal Range", "Severity",
                "Clinical Findings", "Recommendations"])
    for f in ctx["findings"]:
        w.writerow([
            f.get("name") or "",
            f.get("test_type") or "",
            f.get("value") or "",
            f.get("unit") or "",
            f.get("normal_range") or "",
            f.get("severity") or "",
            (f.get("clinical_findings") or "").replace("\n", " "),
            (f.get("recommendations") or "").replace("\n", " "),
        ])
    return buf.getvalue().encode("utf-8")


def safe_filename(name: str, ext: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in (name or "Patient"))
    safe = safe.strip().replace(" ", "_") or "Patient"
    return f"ZenReport_{safe}.{ext}"
