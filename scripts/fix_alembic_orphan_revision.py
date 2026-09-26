#!/usr/bin/env python3
"""
Reset alembic_version when the DB points at a revision file that was removed.

Normally you should run:
  uv run alembic upgrade head

If Alembic cannot load the current revision at all, this script sets version_num
to a known revision so upgrade can proceed.

  uv run python scripts/fix_alembic_orphan_revision.py --to 2f00228655b3
  uv run alembic upgrade head
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.core.db.session import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--to",
        default="2f00228655b3",
        help="Revision id to stamp in alembic_version (default: initial schema)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        row = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        print(f"current alembic_version: {row!r}")
        db.execute(
            text("UPDATE alembic_version SET version_num = :rev"),
            {"rev": args.to},
        )
        db.commit()
        new_row = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        print(f"updated alembic_version: {new_row!r}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("Now run: uv run alembic upgrade head")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
