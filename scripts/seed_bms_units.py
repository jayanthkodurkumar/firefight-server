#!/usr/bin/env python3
"""Seed synthetic BMS units for local telemetry simulation (unit_id + site_id)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

import app.core.db.models  # noqa: F401
from app.core.db.session import SessionLocal
from app.features.bms.models import BmsUnit


def make_units(count: int, start_number: int) -> list[BmsUnit]:
    rows: list[BmsUnit] = []
    for offset in range(count):
        number = start_number + offset
        unit_id = f"SIM-{number}"
        site_id = f"SITE-{number}"
        site_name = f"Sim Site {number}"
        extra = {"synthetic": True}
        rows.append(BmsUnit(unit_id=unit_id, site_id=site_id, site_name=site_name, extra=extra))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Insert synthetic BMS units.")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument(
        "--start",
        type=int,
        default=1001,
        help="Starting numeric suffix, e.g. 1001 -> SIM-1001 / SITE-1001",
    )
    args = parser.parse_args()

    candidates = make_units(args.count, args.start)
    candidate_unit_ids = [u.unit_id for u in candidates]

    session = SessionLocal()
    try:
        existing = set(
            session.scalars(select(BmsUnit.unit_id).where(BmsUnit.unit_id.in_(candidate_unit_ids)))
        )
        to_insert = [u for u in candidates if u.unit_id not in existing]
        if not to_insert:
            print("No new rows to insert (all unit_id values already exist).")
            return 0
        session.add_all(to_insert)
        session.commit()
        skipped = len(candidates) - len(to_insert)
        print(f"Inserted {len(to_insert)} BMS unit(s).")
        if skipped:
            print(f"Skipped {skipped} duplicate unit_id(s).")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
