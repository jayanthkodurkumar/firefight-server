#!/usr/bin/env python3
"""Register fleet BMS units from bms_json_logs/out/examples/units.json."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

import app.core.db.models  # noqa: F401
from app.core.db.session import SessionLocal
from app.features.bms.catalog import DEFAULT_UNITS_CATALOG, load_units_catalog
from app.features.bms.models import BmsUnit


def main() -> int:
    parser = argparse.ArgumentParser(description="Register catalog units as bms_units.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_UNITS_CATALOG)
    args = parser.parse_args()

    if not args.catalog.is_file():
        print(f"Catalog not found: {args.catalog}", file=sys.stderr)
        return 1

    units = load_units_catalog(args.catalog)
    if not units:
        print("No units in catalog", file=sys.stderr)
        return 1

    session = SessionLocal()
    inserted = 0
    updated = 0
    try:
        for row in units:
            unit_id = row["unit"]
            site_id = row["site"]
            existing = session.scalar(select(BmsUnit).where(BmsUnit.unit_id == unit_id))
            extra = {
                "region": row.get("region"),
                "area": row.get("area"),
                "firmware": row.get("fw"),
                "hardware_rev": row.get("hw_rev"),
                "mfg_lot": row.get("mfg_lot"),
                "install": row.get("install"),
                "json_log": row.get("json_log"),
            }
            if existing is None:
                session.add(
                    BmsUnit(
                        unit_id=unit_id,
                        site_id=site_id,
                        site_name=site_id,
                        extra=extra,
                    )
                )
                inserted += 1
            else:
                existing.site_id = site_id
                existing.site_name = site_id
                existing.extra = extra
                updated += 1
        session.commit()
        print(f"Registered {len(units)} BMS units ({inserted} inserted, {updated} updated).")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
