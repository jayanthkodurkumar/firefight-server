#!/usr/bin/env python3
"""
Long-poll SQS and insert bms_telemetry_records (+ update bms_metric_snapshots).

Run from repo root:
  uv run python worker/bms_telemetry_consumer.py
"""

import logging
import sys
import time
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ProcessedRecord:
    message: BmsTelemetryRecordMessage
    inserted: bool
    ticket_id: str | None = None
    rule_id: str | None = None
    priority: str | None = None
    severity: str | None = None


def handle_records(messages: list[BmsTelemetryRecordMessage]) -> None:
    """Ingest one SQS receive batch in one database transaction."""
    db = SessionLocal()
    try:
        ingest = BmsTelemetryIngestService(db)
        tickets = TicketStreamService(db)
        processed: list[ProcessedRecord] = []

        for message in messages:
            inserted, bms_pk, record_pk = ingest.ingest(message)
            ticket = None
            if inserted and bms_pk and record_pk:
                ticket = tickets.evaluate_record(
                    bms_pk=bms_pk,
                    telemetry_record_pk=record_pk,
                    signals=message.signals(),
                    recorded_at=message.ts,
                )
            processed.append(
                ProcessedRecord(
                    message=message,
                    inserted=inserted,
                    ticket_id=ticket.ticket_id if ticket else None,
                    rule_id=ticket.primary_rule_id if ticket else None,
                    priority=ticket.priority if ticket else None,
                    severity=ticket.severity if ticket else None,
                )
            )

        db.commit()

        for result in processed:
            message = result.message
            if not result.inserted:
                logger.info(
                    "duplicate skipped unit=%s site=%s ts=%s (no ticket eval)",
                    message.unit,
                    message.site,
                    message.ts.isoformat(),
                )
                continue

            logger.info(
                "ingested unit=%s site=%s ts=%s",
                message.unit,
                message.site,
                message.ts.isoformat(),
            )
            if result.ticket_id is not None:
                logger.info(
                    "ticket %s rule=%s priority=%s severity=%s",
                    result.ticket_id,
                    result.rule_id,
                    result.priority,
                    result.severity,
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

        valid: list[tuple[dict, BmsTelemetryRecordMessage]] = []
        delete_entries: list[dict[str, str]] = []
        for index, raw in enumerate(messages):
            try:
                record = parse_message_body(raw.get("Body", ""))
                message = BmsTelemetryRecordMessage.model_validate(record)
                valid.append((raw, message))
            except ValidationError as exc:
                logger.error("invalid message, deleting poison: %s", exc)
                delete_entries.append(
                    {"Id": f"msg-{index}", "ReceiptHandle": raw["ReceiptHandle"]}
                )
            except ValueError as exc:
                logger.error("reject message (will retry): %s", exc)

        try:
            handle_records([message for _, message in valid])
            delete_entries.extend(
                {
                    "Id": f"valid-{index}",
                    "ReceiptHandle": raw["ReceiptHandle"],
                }
                for index, (raw, _) in enumerate(valid)
            )
        except Exception as exc:
            logger.exception("batch processing failed, messages will retry: %s", exc)

        if not delete_entries:
            continue

        try:
            deleted = sqs.delete_message_batch(QueueUrl=queue_url, Entries=delete_entries)
            for failure in deleted.get("Failed", []):
                logger.error("SQS delete failed id=%s: %s", failure.get("Id"), failure)
        except (ClientError, BotoCoreError) as exc:
            logger.exception("SQS batch delete failed; messages may retry: %s", exc)


def main() -> int:
    try:
        return run_forever()
    except KeyboardInterrupt:
        logger.info("stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
