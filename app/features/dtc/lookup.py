from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.dtc.models import DtcCatalogMeta, DtcEntry


def get_dtc(session: Session, code: str) -> DtcEntry | None:
    """Resolve a telemetry fault_code (e.g. THM-002) to catalog row."""
    normalized = code.strip().upper()
    return session.get(DtcEntry, normalized)


def severity_label(session: Session, severity: int) -> str | None:
    meta = session.get(DtcCatalogMeta, 1)
    if meta is None or meta.severity is None:
        return None
    return meta.severity.get(str(severity))


def list_dtcs_by_category(session: Session, category_code: str) -> list[DtcEntry]:
    cat = category_code.strip().upper()
    return list(
        session.scalars(
            select(DtcEntry)
            .where(DtcEntry.category_code == cat)
            .order_by(DtcEntry.code)
        ).all()
    )
