"""Reconcile the Findings collection from each report's saved section data.

Operational drift can leave a few section_data param values without
corresponding Finding docs (e.g. when admin enters a value but doesn't
click 'Save & Apply' on that section). This walks every report, calls
the same import-findings logic the admin endpoint uses for each section,
and re-runs organ score sync.

Also purges legacy Finding docs whose names are no longer in any current
section_param definition (e.g. 'Reproductive Health: Tumours' from the
pre-merger schema).

Usage:
    cd backend && python scripts/resync_findings_from_sections.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import mongo  # noqa: E402
from app.services.section_params import SECTION_PARAMETERS  # noqa: E402
from app.api.admin import _sync_organs_bg  # noqa: E402

PLACEHOLDERS = {"", "—", "-", "n/a", "na", "not found", "not measured", "none"}


def _is_missing(value: str) -> bool:
    return not value or str(value).strip().lower() in PLACEHOLDERS


def _import_section(report_id: int, section_type: str) -> tuple[int, int]:
    """Sync one section's params into the Findings collection. Returns (created, updated)."""
    section = mongo.ReportSection.find_one({"report_id": report_id, "section_type": section_type})
    if not section or not section.get("parameters"):
        return 0, 0

    param_defs = {p["name"]: p for p in SECTION_PARAMETERS.get(section_type, [])}
    created, updated = 0, 0
    for param_name, data in section["parameters"].items():
        if isinstance(data, dict):
            value = data.get("value", "")
            severity = data.get("severity", "normal")
            clinical = data.get("clinical_findings", "")
            recs = data.get("recommendations", "")
        else:
            value = str(data); severity = "normal"; clinical = ""; recs = ""

        if _is_missing(value):
            severity = "normal"
            clinical = ""
            recs = ""
            value = "Not Found"

        p = param_defs.get(param_name, {})
        existing = mongo.Finding.find_one({"report_id": report_id, "name": param_name})
        if existing:
            if existing.get("value") != str(value) or existing.get("severity") != severity:
                mongo.Finding.update_one(
                    {"id": existing["id"]},
                    {"$set": {
                        "value": str(value),
                        "severity": severity,
                        "clinical_findings": clinical,
                        "recommendations": recs,
                    }},
                )
                updated += 1
        else:
            mongo.Finding.insert({
                "report_id": report_id,
                "test_type": section_type,
                "name": param_name,
                "severity": severity,
                "value": str(value),
                "normal_range": p.get("normal", ""),
                "unit": p.get("unit", ""),
                "clinical_findings": clinical,
                "recommendations": recs,
            })
            created += 1
    return created, updated


def _purge_orphans(report_id: int) -> int:
    """Drop Finding docs whose names no longer exist in any section_params definition."""
    defined_names = set()
    for items in SECTION_PARAMETERS.values():
        for it in items:
            nm = (it.get("name") or "").lower().strip()
            if nm:
                defined_names.add(nm)

    orphans = []
    for f in mongo.Finding.find({"report_id": report_id}):
        nm = (f.get("name") or "").lower().strip()
        if nm and nm not in defined_names:
            orphans.append(f)

    for f in orphans:
        mongo.Finding.delete_one({"id": f["id"]})
    return len(orphans)


def main() -> int:
    reports = list(mongo.Report.find({}))
    print(f"Reconciling findings for {len(reports)} reports…\n")
    for r in reports:
        rid = r.get("id")
        if not rid:
            continue
        section_types = list(SECTION_PARAMETERS.keys())
        total_created, total_updated = 0, 0
        for st in section_types:
            c, u = _import_section(rid, st)
            total_created += c
            total_updated += u
        purged = _purge_orphans(rid)
        _sync_organs_bg(rid)
        print(f"  ✓ report {rid}: +{total_created} created, ~{total_updated} updated, "
              f"-{purged} orphan(s) purged, organ scores re-synced")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
