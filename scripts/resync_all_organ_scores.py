"""Re-sync OrganScore documents for every report after the organ-system merger.

Reuses the existing `_sync_organs_bg` logic from the admin API so the
migration follows the same gender-filter + severity-counting rules as
fresh report generation.

After running:
- Stale orgs (Endocrine & Metabolic, Hormonal & Vitality, Brain &
  Cognitive, Mental & Stress Resilience, General Health Blood &
  Nutrients, Inflammation & Immune) are deleted.
- New merged orgs (Endocrine & Hormonal Health, Brain & Mental Health,
  Blood, Immunity & Nutrition) are created/updated with recomputed
  severity counts derived from each report's findings.

Usage:
    cd backend && python scripts/resync_all_organ_scores.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.admin import _sync_organs_bg  # noqa: E402
from app.core import mongo  # noqa: E402


def main() -> int:
    reports = list(mongo.Report.find({}))
    print(f"Re-syncing {len(reports)} reports…")
    for r in reports:
        rid = r.get("id")
        if not rid:
            continue
        _sync_organs_bg(rid)
        print(f"  ✓ report {rid}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
