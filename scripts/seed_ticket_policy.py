#!/usr/bin/env python3
"""Load rules.yaml into ticket_policy (rules + ticket_policy merge row)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml
from sqlalchemy import delete

import app.core.db.models  # noqa: F401
from app.core.db.session import SessionLocal
from app.features.tickets.evaluator import MERGE_POLICY_ID
from app.features.tickets.models import Ticket, TicketEvalState, TicketPolicy


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def upsert_policies(session, doc: dict) -> tuple[int, int]:
    rules = doc.get("rules") or []
    merge = doc.get("ticket_policy") or {}

    session.execute(delete(Ticket))
    session.execute(delete(TicketEvalState))
    session.execute(delete(TicketPolicy))
    session.flush()

    for rule in rules:
        rule_id = str(rule["id"])
        session.add(
            TicketPolicy(
                id=rule_id,
                name=rule.get("name"),
                enabled=True,
                rule_type=rule.get("type"),
                definition=rule,
            )
        )

    session.add(
        TicketPolicy(
            id=MERGE_POLICY_ID,
            name="ticket_policy merge settings",
            enabled=True,
            rule_type="merge",
            definition=merge,
        )
    )
    session.flush()
    return len(rules), 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed ticket_policy from rules.yaml")
    parser.add_argument(
        "--rules",
        type=Path,
        default=ROOT / "rules.yaml",
        help="Path to rules.yaml (default: repo root rules.yaml)",
    )
    args = parser.parse_args()

    if not args.rules.is_file():
        print(f"Rules file not found: {args.rules}", file=sys.stderr)
        return 1

    doc = load_yaml(args.rules)
    session = SessionLocal()
    try:
        rule_count, merge_count = upsert_policies(session, doc)
        session.commit()
        print(f"Loaded {rule_count} rule(s) and {merge_count} merge row into ticket_policy.")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
