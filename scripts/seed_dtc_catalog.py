#!/usr/bin/env python3
"""Load home battery DTC catalog JSON into dtc_catalog_meta + dtc_entries.

  uv run python scripts/seed_dtc_catalog.py
  uv run python scripts/seed_dtc_catalog.py --file /path/to/catalog.json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

import app.core.db.models  # noqa: F401
from app.core.db.session import SessionLocal
from app.features.dtc.models import DtcCatalogMeta, DtcEntry

DEFAULT_CATALOG = ROOT / "data" / "dtc_catalog.json"


def load_catalog(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def upsert_catalog(session, catalog: dict) -> tuple[int, int]:
    meta = catalog["meta"]
    existing_meta = session.get(DtcCatalogMeta, 1)
    if existing_meta is None:
        existing_meta = DtcCatalogMeta(id=1)
        session.add(existing_meta)

    existing_meta.title = meta["title"]
    existing_meta.note = meta.get("note")
    existing_meta.severity = meta["severity"]
    existing_meta.categories = meta["categories"]

    existing_codes = {
        row.code: row
        for row in session.scalars(select(DtcEntry)).all()
    }

    inserted = 0
    updated = 0
    for item in catalog["dtcs"]:
        code = item["code"]
        row = existing_codes.get(code)
        if row is None:
            row = DtcEntry(code=code)
            session.add(row)
            inserted += 1
        else:
            updated += 1

        row.category_code = item["cat"]
        row.title = item["title"]
        row.detect = item["detect"]
        row.reaction = item["reaction"]
        row.severity = int(item["sev"])
        row.dispatch = item["dispatch"]
        row.recovery = item["recovery"]
        row.inject = item.get("inject")
        row.demo = bool(item.get("demo", False))

    return inserted, updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed DTC catalog tables from JSON.")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_CATALOG,
        help=f"Catalog JSON path (default: {DEFAULT_CATALOG.relative_to(ROOT)})",
    )
    args = parser.parse_args()

    if not args.file.is_file():
        print(f"Catalog file not found: {args.file}", file=sys.stderr)
        return 1

    catalog = load_catalog(args.file)
    if "meta" not in catalog or "dtcs" not in catalog:
        print("Invalid catalog: expected top-level 'meta' and 'dtcs'", file=sys.stderr)
        return 1

    session = SessionLocal()
    try:
        inserted, updated = upsert_catalog(session, catalog)
        session.commit()
        total = len(catalog["dtcs"])
        print(
            f"DTC catalog loaded: {total} codes "
            f"({inserted} inserted, {updated} updated). Meta id=1."
        )
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
