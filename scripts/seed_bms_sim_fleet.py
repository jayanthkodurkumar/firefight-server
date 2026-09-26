#!/usr/bin/env python3
"""Seed our sim fleet as U01, U02, … with matching SITE ids (not example JSONL files)."""

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Uxx / SITE-xx BMS units for simulation.")
    parser.add_argument("--count", type=int, default=14)
    parser.add_argument("--start", type=int, default=1, help="First unit number (default: 1 -> U01)")
    args = parser.parse_args()

    session = SessionLocal()
    inserted = 0
    try:
        for n in range(args.start, args.start + args.count):
            unit_id = f"U{n:02d}"
            site_id = f"SITE-{n:04d}"
            exists = session.scalar(select(BmsUnit).where(BmsUnit.unit_id == unit_id))
            if exists:
                continue
            session.add(
                BmsUnit(
                    unit_id=unit_id,
                    site_id=site_id,
                    site_name=f"Sim site {n}",
                    extra={"source": "simulation"},
                )
            )
            inserted += 1
        session.commit()
        print(f"Inserted {inserted} BMS unit(s) (U{args.start:02d} …).")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
