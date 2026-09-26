#!/usr/bin/env python3
"""Insert fake technicians. Run from repo root: uv run python scripts/seed_technicians.py"""

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
from app.features.technicians.models import Technician

FIRST_NAMES = [
    "James",
    "Maria",
    "Robert",
    "Linda",
    "Michael",
    "Patricia",
    "David",
    "Jennifer",
    "Carlos",
    "Angela",
    "Daniel",
    "Sandra",
    "Kevin",
    "Ashley",
    "Brian",
    "Nicole",
    "Jason",
    "Stephanie",
    "Ryan",
    "Michelle",
    "Eric",
    "Laura",
    "Marcus",
    "Rachel",
    "Tyler",
    "Kimberly",
    "Brandon",
    "Christina",
    "Justin",
    "Melissa",
    "Anthony",
    "Rebecca",
    "Jonathan",
    "Amanda",
    "Nathan",
    "Heather",
    "Aaron",
    "Elizabeth",
    "Jose",
    "Samantha",
]

LAST_NAMES = [
    "Martinez",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Wilson",
    "Anderson",
    "Taylor",
    "Thomas",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Clark",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
]

# Texas dispatch regions (technicians.region) and home office cities (skills.home_hub)
TEXAS_REGIONS: dict[str, list[str]] = {
    "DFW": ["Dallas, TX", "Fort Worth, TX", "Arlington, TX", "Plano, TX", "Irving, TX"],
    "Houston Metro": ["Houston, TX", "Sugar Land, TX", "The Woodlands, TX", "Pasadena, TX"],
    "Central Texas": ["Austin, TX", "Round Rock, TX", "San Marcos, TX", "Killeen, TX"],
    "San Antonio": ["San Antonio, TX", "New Braunfels, TX", "Boerne, TX"],
    "Gulf Coast": ["Corpus Christi, TX", "Victoria, TX", "Galveston, TX"],
    "West Texas": ["El Paso, TX", "Midland, TX", "Odessa, TX", "Lubbock, TX"],
    "East Texas": ["Tyler, TX", "Longview, TX", "Beaumont, TX"],
    "Rio Grande Valley": ["McAllen, TX", "Brownsville, TX", "Harlingen, TX"],
}

TEXAS_AREA_CODES = [210, 214, 254, 281, 325, 361, 409, 430, 432, 469, 512, 682, 713, 726, 737, 806, 817, 830, 832, 903, 915, 936, 940, 956, 972, 979]

SPECIALTIES = [
    "inverter_repair",
    "thermal_diagnostics",
    "bms_firmware",
    "grid_interconnection",
    "residential_install",
    "commercial_site",
    "emergency_response",
    "connectivity_rf",
    "battery_module_swap",
    "preventive_maintenance",
]

CERTIFICATIONS = [
    "NABCEP PV Associate",
    "OSHA 30",
    "NFPA 70E",
    "Manufacturer Inverter L2",
    "Commercial ESS",
    "High Voltage Safety",
]

LEVELS = ["journeyman", "senior", "lead"]


def _unique_name_pairs(count: int, rng: random.Random) -> list[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    attempts = 0
    while len(pairs) < count and attempts < count * 20:
        attempts += 1
        pairs.add((rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)))
    if len(pairs) < count:
        raise RuntimeError("Could not generate enough unique technician names")
    return list(pairs)


def make_technicians(count: int, start_employee: int, rng: random.Random) -> list[Technician]:
    region_names = list(TEXAS_REGIONS.keys())
    name_pairs = _unique_name_pairs(count, rng)
    rows: list[Technician] = []

    for index, (first, last) in enumerate(name_pairs):
        employee_id = f"TECH-{start_employee + index:04d}"
        region = region_names[index % len(region_names)]
        hub = rng.choice(TEXAS_REGIONS[region])
        area_code = rng.choice(TEXAS_AREA_CODES)
        level = rng.choices(LEVELS, weights=[50, 35, 15], k=1)[0]
        years = rng.randint(2, 18) if level == "journeyman" else rng.randint(6, 22)
        specialty_count = rng.randint(2, 4)
        specialties = rng.sample(SPECIALTIES, k=specialty_count)
        cert_count = rng.randint(1, 3)
        certifications = rng.sample(CERTIFICATIONS, k=cert_count)
        on_call = rng.random() < 0.35

        display_name = f"{first} {last}"
        skills = {
            "employee_id": employee_id,
            "state": "TX",
            "level": level,
            "years_experience": years,
            "specialties": specialties,
            "certifications": certifications,
            "home_hub": hub,
            "on_call": on_call,
            "phone": f"+1-{area_code}-{rng.randint(200, 989):03d}-{rng.randint(1000, 9999):04d}",
        }

        rows.append(
            Technician(
                name=display_name,
                region=region,
                skills=skills,
            )
        )

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed technicians table with Texas-based field roster data.")
    parser.add_argument("--count", type=int, default=50, help="Number of technicians (default: 50)")
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Starting employee number for skills.employee_id, e.g. 1 -> TECH-0001 (default: 1)",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducible data (default: 42)")
    args = parser.parse_args()

    if args.count < 1:
        print("--count must be >= 1", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    candidates = make_technicians(args.count, args.start, rng)

    session = SessionLocal()
    try:
        existing = session.scalars(select(Technician)).all()
        existing_employee_ids = {
            row.skills.get("employee_id")
            for row in existing
            if row.skills and row.skills.get("employee_id")
        }
        existing_names = {row.name for row in existing}

        to_insert = [
            t
            for t in candidates
            if t.skills
            and t.skills["employee_id"] not in existing_employee_ids
            and t.name not in existing_names
        ]

        if not to_insert:
            print("No new technicians to insert (employee_id / name already present).")
            return 0

        session.add_all(to_insert)
        session.commit()
        skipped = len(candidates) - len(to_insert)
        first_id = to_insert[0].skills["employee_id"]
        last_id = to_insert[-1].skills["employee_id"]
        print(f"Inserted {len(to_insert)} technicians ({first_id} .. {last_id}).")
        if skipped:
            print(f"Skipped {skipped} duplicate(s).")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
