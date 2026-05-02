"""
Body Age calculation service.

Uses:
1. PhenoAge (Levine et al. 2018) — scientifically validated formula using 9 blood biomarkers
2. AI synthesis — combines PhenoAge + DEXA + cardiac calcium + other markers for ZenAge
"""
import math
import re
import json
import os
from typing import Optional

import anthropic

# ── PhenoAge marker lookup ────────────────────────────────────────────────────
# Maps canonical marker name → list of aliases (all lowercase, trimmed)
PHENO_MARKERS = {
    "albumin":          ["albumin", "serum albumin", "serum albumin/globulin"],
    "creatinine":       ["creatinine", "creatinine serum", "serum creatinine"],
    "glucose":          ["glucose", "fasting blood glucose test", "fasting glucose",
                         "blood glucose", "glucose (fasting)", "fbs", "fasting blood sugar"],
    "crp":              ["crp", "hs-crp", "hscrp", "c-reactive protein",
                         "c reactive protein", "high sensitivity crp", "hs crp"],
    "lymphocyte_pct":   ["lymphocyte %", "lymphocyte%", "lymphocyte percentage",
                         "lymphocytes %", "lymph %", "lymphocytes%"],
    "mcv":              ["mcv", "mean corpuscular volume", "mean cell volume"],
    "rdw":              ["rdw", "rdw-cv", "red cell distribution width",
                         "red blood cell distribution width"],
    "alp":              ["alp", "alkaline phosphatase", "alk phos", "alkaline phos",
                         "serum alkaline phosphatase"],
    "wbc":              ["wbc", "white blood cell count", "white blood cells",
                         "total leukocyte count", "tlc", "leukocytes"],
}

# PhenoAge formula coefficients (Levine et al. 2018)
PHENO_COEFFICIENTS = {
    "albumin":        -0.0336,
    "creatinine":      0.0095,
    "glucose":         0.1953,
    "crp":             0.0954,   # applied to ln(CRP)
    "lymphocyte_pct": -0.0120,
    "mcv":             0.0268,
    "rdw":             0.3306,
    "alp":             0.00188,
    "wbc":             0.0554,
}
PHENO_INTERCEPT = -19.907


def _parse_float(value_str: str) -> Optional[float]:
    """Extract a numeric value from a string."""
    if not value_str:
        return None
    cleaned = re.sub(r"[^\d.\-]", "", str(value_str).strip())
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _convert_crp_to_mg_dl(value: float, unit: str) -> float:
    """CRP formula needs mg/dL. Labs often report in mg/L."""
    unit_lower = (unit or "").lower().strip()
    if "mg/l" in unit_lower or unit_lower == "mg/l":
        return value / 10.0
    # Already mg/dL or unknown — assume mg/dL
    return value


def _convert_glucose_to_mg_dl(value: float, unit: str) -> float:
    """Convert glucose to mg/dL if reported in mmol/L."""
    unit_lower = (unit or "").lower().strip()
    if "mmol" in unit_lower:
        return value * 18.016
    return value


def _convert_wbc(value: float, unit: str) -> float:
    """WBC formula needs 10³/μL (K/μL). Some labs report as cells/μL."""
    unit_lower = (unit or "").lower()
    if "/ul" in unit_lower and "10" not in unit_lower and "k" not in unit_lower:
        # Reported as cells/μL — divide by 1000
        if value > 1000:
            return value / 1000.0
    return value


def _find_marker_value(marker_key: str, findings: list) -> tuple[Optional[float], Optional[str]]:
    """Search findings for a marker by alias match. Returns (value_float, unit)."""
    aliases = set(PHENO_MARKERS.get(marker_key, []))
    for f in findings:
        name = (f.name or "").lower().strip()
        if name in aliases:
            val = _parse_float(f.value)
            return val, (f.unit or "")
    return None, None


def calculate_pheno_age(findings: list) -> dict:
    """
    Apply the PhenoAge formula (Levine 2018) using findings.
    Returns {pheno_age, markers_found, markers_missing, values_used}
    """
    marker_values = {}
    markers_found = []
    markers_missing = []
    values_used = {}

    for key in PHENO_MARKERS:
        val, unit = _find_marker_value(key, findings)
        if val is None:
            markers_missing.append(key)
            continue

        # Unit conversions
        if key == "crp":
            val = _convert_crp_to_mg_dl(val, unit)
            val = max(val, 0.001)  # prevent log(0)
        elif key == "glucose":
            val = _convert_glucose_to_mg_dl(val, unit)
        elif key == "wbc":
            val = _convert_wbc(val, unit)

        marker_values[key] = val
        markers_found.append(key)
        values_used[key] = {"value": val, "unit": unit}

    if len(markers_found) < 5:
        return {
            "pheno_age": None,
            "markers_found": markers_found,
            "markers_missing": markers_missing,
            "values_used": values_used,
            "error": f"Insufficient markers: only {len(markers_found)}/9 found",
        }

    # Compute xb using available markers
    xb = PHENO_INTERCEPT
    for key, coeff in PHENO_COEFFICIENTS.items():
        if key in marker_values:
            if key == "crp":
                xb += coeff * math.log(marker_values[key])
            else:
                xb += coeff * marker_values[key]

    # Mortality score and phenotypic age
    try:
        mortality = 1 - math.exp(-math.exp(xb) * 0.0076927)
        mortality = min(max(mortality, 1e-10), 1 - 1e-10)
        inner = -0.00553 * math.log(1 - mortality)
        if inner <= 0:
            pheno_age = None
        else:
            pheno_age = round(141.50225 + math.log(inner) / 0.09165, 1)
    except (ValueError, OverflowError):
        pheno_age = None

    return {
        "pheno_age": pheno_age,
        "markers_found": markers_found,
        "markers_missing": markers_missing,
        "values_used": values_used,
    }


def calculate_zen_age(report, findings: list, pheno_result: dict) -> dict:
    """
    Use the AI engine to synthesize a comprehensive ZenAge from all available data.
    Combines PhenoAge with DEXA, cardiac calcium, metabolic markers, organ scores, etc.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Build a rich context for the AI engine. `report` is a Mongo dict — load the order
    from ..core import mongo
    order = mongo.Order.find_one({"id": report.get("order_id") if isinstance(report, dict) else getattr(report, "order_id", None)}) or {}
    actual_age = order.get("patient_age")
    gender = order.get("patient_gender", "Unknown")

    # Gather all findings with values for the AI engine
    findings_summary = []
    for f in findings:
        if f.value:
            findings_summary.append(
                f"  - {f.name}: {f.value} {f.unit or ''} "
                f"(range: {f.normal_range or 'N/A'}, severity: {f.severity})"
            )

    pheno_age = pheno_result.get("pheno_age")
    markers_missing = pheno_result.get("markers_missing", [])

    prompt = f"""You are a medical AI expert in biological age assessment. Analyze the following health data and compute a precise biological "ZenAge" for this patient.

PATIENT:
- Chronological Age: {actual_age} years
- Gender: {gender}
- PhenoAge (Levine 2018 formula): {f"{pheno_age:.1f} years" if pheno_age else "Could not compute (missing markers: " + ", ".join(markers_missing) + ")"}

ALL LAB & SCAN FINDINGS:
{chr(10).join(findings_summary[:80]) if findings_summary else "No findings available"}

YOUR TASK:
1. Calculate a "ZenAge" (biological age) between 18-90 based on ALL available evidence
2. If PhenoAge is available, use it as a strong anchor but adjust based on scan findings (DEXA bone density, calcium score, body composition, organ health)
3. Calculate sub-ages for each domain where data is available:
   - metabolic_age: from glucose, HbA1c, insulin, lipids, BMI, body fat
   - cardiovascular_age: from calcium score, cholesterol, BP markers, ECG
   - bone_age: from DEXA T-score, Z-score, bone density
   - inflammatory_age: from CRP, homocysteine, WBC, immune markers
   - renal_age: from creatinine, eGFR, albumin/creatinine
4. Write a 2-3 sentence plain-language interpretation

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{
  "zen_age": <number>,
  "age_difference": <zen_age minus chronological_age, negative means younger>,
  "confidence": "<high|medium|low>",
  "sub_ages": {{
    "metabolic_age": <number or null>,
    "cardiovascular_age": <number or null>,
    "bone_age": <number or null>,
    "inflammatory_age": <number or null>,
    "renal_age": <number or null>
  }},
  "interpretation": "<2-3 sentence plain-language explanation>"
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
        return result
    except Exception as e:
        # Fallback: use PhenoAge if available
        fallback_age = pheno_age or actual_age
        return {
            "zen_age": fallback_age,
            "age_difference": round(fallback_age - actual_age, 1) if fallback_age and actual_age else 0,
            "confidence": "low",
            "sub_ages": {},
            "interpretation": f"ZenAge estimated from available biomarkers. Error in AI synthesis: {str(e)[:100]}",
        }
