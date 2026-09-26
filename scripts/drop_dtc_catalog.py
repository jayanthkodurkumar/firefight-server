#!/usr/bin/env python3
"""Remove DTC catalog tables from Postgres and reset Alembic if needed.

  uv run python scripts/drop_dtc_catalog.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.core.db.session import SessionLocal

DTC_REVISION = "edd0d13b9436"
PRIOR_REVISION = "2f00228655b3"


def main() -> int:
    session = SessionLocal()
    try:
        session.execute(text("DROP TABLE IF EXISTS dtc_entries CASCADE"))
        session.execute(text("DROP TABLE IF EXISTS dtc_catalog_meta CASCADE"))

        row = session.execute(text("SELECT version_num FROM alembic_version")).one_or_none()
        if row is not None and row[0] == DTC_REVISION:
            session.execute(
                text("UPDATE alembic_version SET version_num = :rev"),
                {"rev": PRIOR_REVISION},
            )
            print(f"alembic_version set to {PRIOR_REVISION}")
        elif row is not None:
            print(f"alembic_version unchanged ({row[0]})")

        session.commit()
        print("Dropped dtc_entries and dtc_catalog_meta (if they existed).")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
