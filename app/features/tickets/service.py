"""Run ticket_policy evaluation after telemetry ingest."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.telemetry.models import BmsTelemetryRecord
from app.features.telemetry.service import _ensure_aware
from app.features.tickets.evaluator import MERGE_POLICY_ID, TicketPolicyEvaluator, create_ticket_from_hits
from app.features.tickets.models import Ticket, TicketPolicy


class TicketStreamService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._evaluator = TicketPolicyEvaluator(db)

    def evaluate_record(
        self,
        *,
        bms_pk: uuid.UUID,
        telemetry_record_pk: uuid.UUID,
        signals: dict,
        recorded_at: datetime,
    ) -> Ticket | None:
        prior = self._db.scalar(
            select(BmsTelemetryRecord)
            .where(
                BmsTelemetryRecord.bms_pk == bms_pk,
                BmsTelemetryRecord.id != telemetry_record_pk,
            )
            .order_by(BmsTelemetryRecord.recorded_at.desc())
            .limit(1)
        )
        hits = self._evaluator.evaluate(
            bms_pk=bms_pk,
            signals=signals,
            recorded_at=_ensure_aware(recorded_at),
            prior_record=prior,
        )
        merge_row = self._db.get(TicketPolicy, MERGE_POLICY_ID)
        merge = merge_row.definition if merge_row else {}
        return create_ticket_from_hits(
            self._db,
            bms_pk=bms_pk,
            telemetry_record_pk=telemetry_record_pk,
            signals=signals,
            recorded_at=recorded_at,
            hits=hits,
            merge=merge,
        )
