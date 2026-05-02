"""One-shot purge of the deprecated `Reproductive Health` organ.

Removes leftover `OrganScore` documents tied to the dropped organ system
so existing reports stop rendering an empty Reproductive Health card on
the frontend. Reproductive parameters are now exclusively under the
sex-specific Women's Health and Men's Health organs.

Usage:
    cd backend && python scripts/cleanup_reproductive_health.py
"""
import sys
from pathlib import Path

# Make `app` importable when run from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import mongo  # noqa: E402

ORGAN_NAME = "Reproductive Health"


def main() -> int:
    matched = mongo.organ_scores.count_documents({"organ_name": ORGAN_NAME})
    print(f"Found {matched} `{ORGAN_NAME}` organ_score documents")
    if not matched:
        print("Nothing to delete.")
        return 0

    confirm = input(f"Delete all {matched} rows? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return 1

    res = mongo.organ_scores.delete_many({"organ_name": ORGAN_NAME})
    print(f"Deleted {res.deleted_count} documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
