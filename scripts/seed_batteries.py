#!/usr/bin/env python3
"""Insert fake batteries into Postgres. Run from repo root: uv run python scripts/seed_batteries.py"""

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

import app.core.db.models  # noqa: F401 — register all ORM mappers
from app.core.db.session import SessionLocal
from app.features.batteries.models import Battery

CITIES = [
    "Austin",
    "Dallas",
    "Houston",
    "San Antonio",
    "Phoenix",
    "Denver",
    "Atlanta",
    "Charlotte",
    "Nashville",
    "Orlando",
    "Tampa",
    "Raleigh",
    "Columbus",
    "Indianapolis",
    "Kansas City",
    "Omaha",
    "Salt Lake City",
    "Boise",
    "Portland",
    "Seattle",
]

REGIONS = ["South", "West", "Midwest", "Northeast", "Central"]


def make_batteries(count: int, start_number: int) -> list[Battery]:
    rows: list[Battery] = []
    for offset in range(count):
        number = start_number + offset
        battery_id = f"BAT-{number}"
        city = random.choice(CITIES)
        site_name = f"{city} Residency #{random.randint(1, 120)}"
        extra = {
            "region": random.choice(REGIONS),
            "install_year": random.randint(2020, 2025),
            "capacity_kwh": random.choice([10, 13.5, 15, 20]),
        }
        rows.append(Battery(battery_id=battery_id, site_name=site_name, extra=extra))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed batteries table with fake fleet data.")
    parser.add_argument("--count", type=int, default=200, help="Number of batteries to insert (default: 200)")
    parser.add_argument(
        "--start",
        type=int,
        default=1001,
        help="Starting numeric suffix for battery_id, e.g. 1001 -> BAT-1001 (default: 1001)",
    )
    args = parser.parse_args()

    if args.count < 1:
        print("--count must be >= 1", file=sys.stderr)
        return 1

    candidates = make_batteries(args.count, args.start)
    candidate_ids = [b.battery_id for b in candidates]

    session = SessionLocal()
    try:
        existing_ids = set(session.scalars(select(Battery.battery_id).where(Battery.battery_id.in_(candidate_ids))))
        to_insert = [b for b in candidates if b.battery_id not in existing_ids]

        if not to_insert:
            print("No new rows to insert (all battery_id values already exist).")
            return 0

        session.add_all(to_insert)
        session.commit()
        skipped = len(candidates) - len(to_insert)
        print(f"Inserted {len(to_insert)} batteries (BAT-{args.start} .. BAT-{args.start + args.count - 1}).")
        if skipped:
            print(f"Skipped {skipped} duplicate battery_id(s).")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
