"""Back-fill `clinical_findings` (What this means) and `recommendations`
(What to do) on every Finding doc that has them blank.

The patient-facing FindingsPanel hides the expand button when both fields
are empty, so blanks make the row look like a dead-end card. This walks
each report's findings, batches missing rows, and asks the AI to generate
both fields in one pass per batch.

Usage:
    cd backend && python scripts/backfill_finding_explanations.py [report_id]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import mongo  # noqa: E402
from app.services.ai_service import generate_finding_explanations  # noqa: E402

PLACEHOLDERS = {"", "—", "-", "n/a", "na", "not found", "not measured"}
BATCH_SIZE = 25  # 25 findings per AI call keeps prompts manageable


def _is_filled(v: str) -> bool:
    return bool(v) and str(v).strip().lower() not in PLACEHOLDERS


def backfill_for_report(report_id: int) -> tuple[int, int]:
    """Returns (findings_filled, findings_skipped_already_had_text)."""
    findings = list(mongo.Finding.find({"report_id": report_id}))
    todo = [
        f for f in findings
        if _is_filled(f.get("value"))
        and (not (f.get("clinical_findings") or "").strip()
             or not (f.get("recommendations") or "").strip())
    ]
    if not todo:
        print(f"  report {report_id}: nothing to fill ({len(findings)} findings, all have explanations)")
        return 0, len(findings) - 0

    print(f"  report {report_id}: filling {len(todo)} of {len(findings)} findings…")
    filled = 0
    for i in range(0, len(todo), BATCH_SIZE):
        chunk = todo[i:i + BATCH_SIZE]
        results = generate_finding_explanations(chunk)
        if not results:
            print(f"    batch {i // BATCH_SIZE + 1}: AI returned nothing, skipping")
            continue
        for f in chunk:
            entry = results.get(f.get("name"))
            if not entry or not isinstance(entry, dict):
                continue
            update = {}
            what = (entry.get("what") or "").strip()
            do = (entry.get("do") or "").strip()
            if what and not (f.get("clinical_findings") or "").strip():
                update["clinical_findings"] = what
            if do and not (f.get("recommendations") or "").strip():
                update["recommendations"] = do
            if update:
                mongo.Finding.update_one({"id": f["id"]}, {"$set": update})
                filled += 1
        print(f"    batch {i // BATCH_SIZE + 1}: +{len(results)} explanations")
    return filled, len(findings) - len(todo)


def main() -> int:
    if len(sys.argv) > 1:
        report_ids = [int(sys.argv[1])]
    else:
        report_ids = [r["id"] for r in mongo.Report.find({})]
    print(f"Back-filling explanations for {len(report_ids)} report(s)…\n")
    total_filled = 0
    for rid in report_ids:
        f, _ = backfill_for_report(rid)
        total_filled += f
    print(f"\nDone. {total_filled} findings updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
