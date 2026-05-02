"""DEXA derived-metric auto-computation.

Some DEXA reports omit the calculated indices (Appendicular Lean Mass, ASMI,
Fat Mass Index) even though their inputs are present. We compute them from
the available raw values rather than leaving the patient's report blank.

All formulas use only inputs that are extractable from a standard
body-composition DEXA report:

  height² (m²)              = (Total Fat Mass + Fat Free Mass) / BMI
  Appendicular Lean Mass    = Total Lean Mass − Trunk Lean
  ASMI (kg/m²)              = ALM / height²
  Fat Mass Index (kg/m²)    = Total Fat Mass / height²
"""

import math
import re
from typing import Optional, List, Tuple

# Param names this module fills in (must match SECTION_PARAMETERS["dexa"]).
DERIVED_PARAMS = ("Appendicular Lean Mass", "ASMI", "Fat Mass Index")


def _num(v):
    """Pull the first numeric value out of a string like '36.232 kg' or '29.1'."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def _val(params, name):
    """Read the numeric value from `params[name]` (the section's stored shape)."""
    p = params.get(name)
    if p is None:
        return None
    raw = p.get("value") if isinstance(p, dict) else p
    if raw in (None, "", "—", "-", "Not Found"):
        return None
    return _num(raw)


def _missing(params, name):
    """A param counts as missing if its value is empty / placeholder / Not Found."""
    p = params.get(name)
    if p is None:
        return True
    raw = p.get("value") if isinstance(p, dict) else p
    return raw in (None, "", "—", "-", "Not Found")


def autocompute_dexa(params: dict, gender: Optional[str] = None) -> Tuple[dict, List[str]]:
    """Mutate `params` in place: fill any missing derived metrics from inputs.

    Returns the (possibly updated) params dict and a list of names that
    were filled in this pass.
    """
    if not params:
        return params, []

    filled = []

    # Inputs
    bmi = _val(params, "BMI")
    total_fat = _val(params, "Total Fat Mass")
    fat_free = _val(params, "Fat Free Mass")
    total_lean = _val(params, "Total Lean Mass") or _val(params, "Lean Mass")
    trunk_lean = _val(params, "Trunk Lean")

    # height² in m² — derive from BMI and total weight when not given directly.
    weight = None
    if total_fat is not None and fat_free is not None:
        weight = total_fat + fat_free
    h2 = (weight / bmi) if (weight is not None and bmi) else None

    # Gender-aware normal cutoffs (informational for the clinical_findings note).
    g = (gender or "").upper()
    asmi_cutoff = 7.0 if g.startswith("M") else 5.5
    fmi_cutoff = 9.0 if g.startswith("M") else 13.0

    def _set(name: str, value: float, unit: str, severity: str, note: str):
        # Round sensibly for display
        rounded = round(value, 2)
        existing = params.get(name) or {}
        params[name] = {
            "value": f"{rounded} {unit}",
            "severity": severity,
            "clinical_findings": note,
            "recommendations": existing.get("recommendations", "") if isinstance(existing, dict) else "",
        }
        filled.append(name)

    # 1. Appendicular Lean Mass = Total Lean − Trunk Lean
    if _missing(params, "Appendicular Lean Mass") and total_lean is not None and trunk_lean is not None:
        alm = total_lean - trunk_lean
        _set(
            "Appendicular Lean Mass", alm, "kg", "normal",
            f"Calculated from Total Lean Mass ({total_lean} kg) − Trunk Lean ({trunk_lean} kg). "
            f"Represents lean mass in arms + legs, the basis for sarcopenia screening (ASMI).",
        )

    # Re-read in case ALM was just set
    alm_val = _val(params, "Appendicular Lean Mass")

    # 2. ASMI = ALM / height²
    if _missing(params, "ASMI") and alm_val is not None and h2:
        asmi = alm_val / h2
        sev = "normal" if asmi >= asmi_cutoff else "minor"
        _set(
            "ASMI", asmi, "kg/m²", sev,
            f"Calculated from Appendicular Lean Mass ({round(alm_val, 2)} kg) ÷ height² ({round(h2, 3)} m²). "
            f"Cutoff for sarcopenia in {'males' if g.startswith('M') else 'females'}: < {asmi_cutoff} kg/m².",
        )

    # 3. Fat Mass Index = Total Fat Mass / height²
    if _missing(params, "Fat Mass Index") and total_fat is not None and h2:
        fmi = total_fat / h2
        sev = "normal" if fmi < fmi_cutoff else ("major" if fmi >= fmi_cutoff + 4 else "minor")
        _set(
            "Fat Mass Index", fmi, "kg/m²", sev,
            f"Calculated from Total Fat Mass ({total_fat} kg) ÷ height² ({round(h2, 3)} m²). "
            f"Normal upper limit for {'males' if g.startswith('M') else 'females'}: {fmi_cutoff} kg/m².",
        )

    return params, filled
