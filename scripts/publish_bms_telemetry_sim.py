#!/usr/bin/env python3
"""
Publish BMS telemetry to SQS until Ctrl+C.

One message every 0.5 s. Every 3 s, one sample matches R-ELE-01 (cmd/fb mismatch,
for_s: 1) so one ingest can open a ticket even with SQS reordering.
"""

import logging
import sys
import time
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
from app.features.bms.models import BmsUnit
from app.features.telemetry.schemas import BmsTelemetryRecordMessage
from app.features.telemetry.simulator import BmsTelemetrySimulator
from app.features.telemetry.sqs_payload import build_message_body

PUBLISH_INTERVAL_S = 0.5
CYCLE_STEPS = 6  # 6 × 0.5 s = 3 s between ticket samples
SIM_SEED = 7

# rules.yaml R-ELE-01: ContactorPosCmd vs ContactorPosFb, for_s: 1 (single sample).
TICKET_FAULT_SIGNALS: dict[str, object] = {
    "ContactorPosCmd": 0,
    "ContactorPosFb": 1,
    "ContactorNegCmd": 0,
    "ContactorNegFb": 1,
    "BusVoltage": 395.0,
    "OffGasH2": 150.0,
    "TcellMax": 58.0,
    "BmsState": "FAULT",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("bms_telemetry_producer")


def _ticket_fault_record(sim: BmsTelemetrySimulator, unit_id: str, site_id: str) -> dict:
    raw = sim.next_record(unit_id, site_id)
    raw.update(TICKET_FAULT_SIGNALS)
    raw["ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return raw


def main() -> int:
    settings = get_settings()
    if not settings.telemetry_queue_url:
        logger.error("TELEMETRY_QUEUE_URL is not set in .env")
        return 1

    db = SessionLocal()
    try:
        units = list(db.scalars(select(BmsUnit).order_by(BmsUnit.unit_id)))
    finally:
        db.close()

    if not units:
        logger.error("No BMS units in DB. Run scripts/seed_bms_sim_fleet.py first.")
        return 1

    sim = BmsTelemetrySimulator(seed=SIM_SEED)
    sqs = boto3.client("sqs", region_name=settings.aws_region)
    queue_url = settings.telemetry_queue_url

    logger.info(
        "One event every %.1fs; ticket sample (R-ELE-01) every %.1fs — keep worker running (Ctrl+C to stop)",
        PUBLISH_INTERVAL_S,
        CYCLE_STEPS * PUBLISH_INTERVAL_S,
    )

    sent = 0
    step = 0
    next_at = time.monotonic()

    try:
        while True:
            now = time.monotonic()
            if now < next_at:
                time.sleep(next_at - now)

            step += 1
            pos = (step - 1) % CYCLE_STEPS
            cycle = (step - 1) // CYCLE_STEPS
            ticket_unit = units[cycle % len(units)]

            if pos == 5:
                raw = _ticket_fault_record(sim, ticket_unit.unit_id, ticket_unit.site_id)
                logger.info(
                    "ticket sample unit=%s site=%s rule=R-ELE-01 cmd/fb=%s/%s",
                    raw["unit"],
                    raw["site"],
                    raw.get("ContactorPosCmd"),
                    raw.get("ContactorPosFb"),
                )
            else:
                unit = units[(step - 1) % len(units)]
                raw = sim.next_record(unit.unit_id, unit.site_id)

            BmsTelemetryRecordMessage.model_validate(raw)
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=build_message_body(raw),
                MessageAttributes={
                    "ContentType": {
                        "DataType": "String",
                        "StringValue": "application/json",
                    },
                },
            )
            sent += 1
            next_at += PUBLISH_INTERVAL_S

            if step == 1 or step % 120 == 0:
                logger.info("step=%s total_sent=%s last=%s", step, sent, raw["unit"])
    except KeyboardInterrupt:
        logger.info("stopped step=%s total_sent=%s", step, sent)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
