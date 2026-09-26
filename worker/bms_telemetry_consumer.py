#!/usr/bin/env python3
"""
Long-poll SQS and insert bms_telemetry_records (+ update bms_metric_snapshots).

Run from repo root:
  uv run python worker/bms_telemetry_consumer.py
"""

import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

import app.core.db.models  # noqa: F401
from app.core.config.settings import get_settings
from app.core.db.session import SessionLocal
from app.features.telemetry.schemas import BmsTelemetryRecordMessage
from app.features.tickets.service import TicketStreamService
from app.features.telemetry.service import BmsTelemetryIngestService
from app.features.telemetry.sqs_payload import parse_message_body

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("bms_telemetry_worker")


def handle_record(body: str) -> None:
    record = parse_message_body(body)
    message = BmsTelemetryRecordMessage.model_validate(record)
    db = SessionLocal()
    try:
        ingest = BmsTelemetryIngestService(db)
        inserted, bms_pk, record_pk = ingest.ingest(message)
        ticket = None
        if inserted and bms_pk and record_pk:
            ticket = TicketStreamService(db).evaluate_record(
                bms_pk=bms_pk,
                telemetry_record_pk=record_pk,
                signals=message.signals(),
                recorded_at=message.ts,
            )
        db.commit()
        if inserted:
            logger.info(
                "ingested unit=%s site=%s ts=%s",
                message.unit,
                message.site,
                message.ts.isoformat(),
            )
            if ticket is not None:
                logger.info(
                    "ticket %s rule=%s priority=%s severity=%s",
                    ticket.ticket_id,
                    ticket.primary_rule_id,
                    ticket.priority,
                    ticket.severity,
                )
        else:
            logger.info(
                "duplicate skipped unit=%s site=%s ts=%s (no ticket eval)",
                message.unit,
                message.site,
                message.ts.isoformat(),
            )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_forever() -> int:
    settings = get_settings()
    if not settings.telemetry_queue_url:
        logger.error("TELEMETRY_QUEUE_URL is not set in .env")
        return 1

    sqs = boto3.client("sqs", region_name=settings.aws_region)
    queue_url = settings.telemetry_queue_url

    logger.info("Polling queue %s (region=%s)", queue_url, settings.aws_region)

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=settings.sqs_max_messages,
                WaitTimeSeconds=settings.sqs_wait_time_seconds,
                AttributeNames=["ApproximateReceiveCount"],
            )
        except (ClientError, BotoCoreError) as exc:
            logger.exception("SQS receive failed: %s", exc)
            time.sleep(5)
            continue

        messages = response.get("Messages", [])
        if not messages:
            continue

        for raw in messages:
            receipt = raw["ReceiptHandle"]
            body = raw.get("Body", "")
            try:
                handle_record(body)
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            except ValidationError as exc:
                logger.error("invalid message, deleting poison: %s", exc)
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            except ValueError as exc:
                logger.error("reject message (will retry): %s", exc)
            except Exception as exc:
                logger.exception("processing failed, message will retry: %s", exc)


def main() -> int:
    try:
        return run_forever()
    except KeyboardInterrupt:
        logger.info("stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
