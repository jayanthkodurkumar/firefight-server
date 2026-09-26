#!/usr/bin/env python3
"""
Long-poll SQS and write telemetry_events (and metric snapshots).

Run from repo root:
  uv run python worker/telemetry_consumer.py
"""

import json
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
from app.features.telemetry.schemas import TelemetryMessage
from app.features.telemetry.service import TelemetryIngestService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("telemetry_worker")


def parse_body(body: str) -> TelemetryMessage:
    data = json.loads(body)
    return TelemetryMessage.model_validate(data)


def handle_record(body: str) -> None:
    message = parse_body(body)
    db = SessionLocal()
    try:
        service = TelemetryIngestService(db)
        inserted = service.process_message(message)
        db.commit()
        if inserted:
            logger.info(
                "ingested event_id=%s battery_id=%s kind=%s",
                message.event_id,
                message.battery_id,
                message.kind.value,
            )
        else:
            logger.debug("duplicate event_id=%s skipped", message.event_id)
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
                logger.error("invalid message JSON/schema, deleting poison message: %s", exc)
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            except ValueError as exc:
                logger.error("reject message (deleting): %s", exc)
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
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
