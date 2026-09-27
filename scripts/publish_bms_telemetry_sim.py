#!/usr/bin/env python3
"""
Publish BMS telemetry to SQS until Ctrl+C.

- One message every 0.5 s.
- Every 2 s that tick advances one ticket scenario.
- Rules are shuffled in balanced rounds. Multi-sample rules receive exactly the
  consecutive samples they need before the next rule starts.
"""

import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import boto3
from sqlalchemy import select, update

import app.core.db.models  # noqa: F401
from app.core.config.settings import get_settings
from app.core.db.session import SessionLocal
from app.features.bms.models import BmsUnit
from app.features.tickets.models import Ticket, TicketStatus
from app.features.telemetry.schemas import BmsTelemetryRecordMessage
from app.features.telemetry.simulator import BmsTelemetrySimulator
from app.features.telemetry.sqs_payload import build_message_body
from app.features.telemetry.ticket_sim_scenarios import TICKET_SIM_SCENARIOS_PUBLISH, TicketSimScenario

PUBLISH_INTERVAL_S = 0.5
TICKET_EVERY_S = 2.0
TICKS_PER_TICKET = int(TICKET_EVERY_S / PUBLISH_INTERVAL_S)
SIM_SEED = 7

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("bms_telemetry_producer")


def _jitter_ticket_patch(rng: random.Random, scenario: TicketSimScenario) -> dict:
    patch = dict(scenario.patch)

    if scenario.rule_id == "R-THM-02":
        patch["OffGasH2"] = round(rng.uniform(135.0, 260.0), 1)
        patch["TcellMax"] = round(rng.uniform(38.0, 58.0), 1)
        patch["TcellMin"] = round(patch["TcellMax"] - rng.uniform(3.0, 8.0), 1)
    elif scenario.rule_id in {"R-ELE-01", "R-ELE-02"}:
        patch["BusVoltage"] = round(rng.uniform(360.0, 430.0), 1)
    elif scenario.rule_id == "R-COM-02":
        if rng.random() < 0.5:
            patch["State_CrcOk"] = False
            patch["PackStatus_CrcOk"] = True
        else:
            patch["State_CrcOk"] = True
            patch["PackStatus_CrcOk"] = False

    return patch


def clear_open_ticket_assignments(db, units: list[BmsUnit]) -> None:
    """Assigned-to / assigned-by must be unset for sim-published tickets."""
    bms_pks = [unit.id for unit in units]
    if not bms_pks:
        return
    db.execute(
        update(Ticket)
        .where(
            Ticket.bms_pk.in_(bms_pks),
            Ticket.status == TicketStatus.open,
        )
        .values(
            assigned_technician_id=None,
            assigned_by_user_id=None,
            assigned_at=None,
            dispatch_notes=None,
        )
    )
    db.commit()


def _ticket_record(
    sim: BmsTelemetrySimulator,
    rng: random.Random,
    unit_id: str,
    site_id: str,
    scenario: TicketSimScenario,
) -> dict:
    raw = sim.next_record(unit_id, site_id)
    raw.update(_jitter_ticket_patch(rng, scenario))
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

    scenarios = TICKET_SIM_SCENARIOS_PUBLISH
    rng = random.Random(SIM_SEED)
    sim = BmsTelemetrySimulator(seed=SIM_SEED, enable_episodes=False)
    sqs = boto3.client("sqs", region_name=settings.aws_region)
    queue_url = settings.telemetry_queue_url

    logger.info(
        "Publish every %.1fs; ticket event every %.1fs (%s rules) — worker must run",
        PUBLISH_INTERVAL_S,
        TICKET_EVERY_S,
        len(scenarios),
    )

    sent = 0
    tick = 0
    normal_idx = 0
    next_at = time.monotonic()

    def publish(raw: dict) -> None:
        nonlocal sent
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

    ticket_units = {
        scenario.rule_id: units[index % len(units)]
        for index, scenario in enumerate(scenarios)
    }
    reserved_ticket_unit_ids = {unit.unit_id for unit in ticket_units.values()}
    normal_units = [unit for unit in units if unit.unit_id not in reserved_ticket_unit_ids]
    if not normal_units:
        logger.warning(
            "Not enough units to reserve ticket units separately; normal data may reset multi-sample ticket streaks."
        )
        normal_units = units

    scenario_bag: list[TicketSimScenario] = []
    active_scenario: TicketSimScenario | None = None
    active_samples_left = 0
    last_completed_rule_id: str | None = None

    def next_normal_unit() -> BmsUnit:
        nonlocal normal_idx
        unit = normal_units[normal_idx % len(normal_units)]
        normal_idx += 1
        return unit

    def next_ticket_scenario() -> TicketSimScenario:
        nonlocal scenario_bag
        nonlocal active_scenario
        nonlocal active_samples_left
        nonlocal last_completed_rule_id

        if active_scenario is None:
            if not scenario_bag:
                scenario_bag = list(scenarios)
                rng.shuffle(scenario_bag)
                if (
                    len(scenario_bag) > 1
                    and scenario_bag[-1].rule_id == last_completed_rule_id
                ):
                    scenario_bag[0], scenario_bag[-1] = scenario_bag[-1], scenario_bag[0]

            active_scenario = scenario_bag.pop()
            active_samples_left = active_scenario.samples

        scenario = active_scenario
        active_samples_left -= 1
        if active_samples_left == 0:
            last_completed_rule_id = scenario.rule_id
            active_scenario = None
        return scenario

    def reset_ticket_streaks() -> None:
        streak_db = SessionLocal()
        try:
            clear_open_ticket_assignments(streak_db, list(ticket_units.values()))
        finally:
            streak_db.close()
        for scenario in scenarios:
            unit = ticket_units[scenario.rule_id]
            publish(sim.next_record(unit.unit_id, unit.site_id))
            logger.info("reset unit=%s rule=%s", unit.unit_id, scenario.rule_id)

    try:
        reset_ticket_streaks()
        while True:
            now = time.monotonic()
            if now < next_at:
                time.sleep(next_at - now)

            tick += 1

            if tick % TICKS_PER_TICKET == 0:
                scenario = next_ticket_scenario()
                unit = ticket_units[scenario.rule_id]
                publish(
                    _ticket_record(
                        sim,
                        rng,
                        unit.unit_id,
                        unit.site_id,
                        scenario,
                    )
                )
                logger.info(
                    "ticket event unit=%s rule=%s sample=%s/%s",
                    unit.unit_id,
                    scenario.rule_id,
                    scenario.samples - active_samples_left if active_scenario else scenario.samples,
                    scenario.samples,
                )
            else:
                unit = next_normal_unit()
                publish(sim.next_record(unit.unit_id, unit.site_id))

            next_at += PUBLISH_INTERVAL_S

            if tick == 1 or tick % 40 == 0:
                logger.info("tick=%s total_sent=%s", tick, sent)
    except KeyboardInterrupt:
        logger.info("stopped tick=%s total_sent=%s", tick, sent)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
