#!/usr/bin/env python3
"""
Publish simulated telemetry to SQS for batteries that exist in Postgres.

  uv run python scripts/publish_telemetry_stream.py --count 100 --interval 0.1
"""

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import boto3
from sqlalchemy import select

import app.core.db.models  # noqa: F401
from app.core.config.settings import get_settings
from app.core.db.session import SessionLocal
from app.features.batteries.models import Battery

INVERTER_STATUSES = ["NORMAL", "WARNING", "FAULT"]
GRID_STATUSES = ["CONNECTED", "ISLANDED"]
CONNECTIVITY = ["ONLINE", "OFFLINE"]


def random_metric_payload(rng: random.Random, fault: bool) -> dict:
    temp = rng.uniform(32.0, 52.0) if fault else rng.uniform(28.0, 42.0)
    inverter = "FAULT" if fault else rng.choice(["NORMAL", "NORMAL", "WARNING"])
    return {
        "soc_pct": round(rng.uniform(15.0, 95.0), 1),
        "temperature_c": round(temp, 1),
        "inverter_status": inverter,
        "grid_status": rng.choice(GRID_STATUSES),
        "backup_available": rng.choice([True, False]),
        "connectivity": "ONLINE",
        "fault_code": "INV_TEMP_HIGH" if fault else None,
    }


def build_message(battery_id: str, rng: random.Random) -> dict:
    fault = rng.random() < 0.08
    return {
        "event_id": f"evt-{uuid.uuid4()}",
        "battery_id": battery_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kind": "metric",
        "payload": random_metric_payload(rng, fault),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish fake telemetry messages to SQS.")
    parser.add_argument("--count", type=int, default=50, help="Messages to send (default: 50)")
    parser.add_argument("--interval", type=float, default=0.2, help="Seconds between sends (default: 0.2)")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.telemetry_queue_url:
        print("TELEMETRY_QUEUE_URL is not set in .env", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        battery_ids = list(db.scalars(select(Battery.battery_id).order_by(Battery.battery_id)))
    finally:
        db.close()

    if not battery_ids:
        print("No batteries in DB. Run scripts/seed_batteries.py first.", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    sqs = boto3.client("sqs", region_name=settings.aws_region)

    for i in range(args.count):
        battery_id = rng.choice(battery_ids)
        body = build_message(battery_id, rng)
        sqs.send_message(QueueUrl=settings.telemetry_queue_url, MessageBody=json.dumps(body))
        if (i + 1) % 10 == 0 or i == 0:
            print(f"sent {i + 1}/{args.count} last={body['battery_id']} event_id={body['event_id']}")
        if args.interval > 0 and i + 1 < args.count:
            time.sleep(args.interval)

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
