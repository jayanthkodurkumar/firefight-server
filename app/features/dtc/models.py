from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


class DtcCatalogMeta(Base):
    """Singleton-style catalog header (severity scale, category labels)."""

    __tablename__ = "dtc_catalog_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    title: Mapped[str] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[dict[str, Any]] = mapped_column(JSONB)
    categories: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class DtcEntry(Base):
    """One diagnostic trouble code (e.g. THM-002, INV-001)."""

    __tablename__ = "dtc_entries"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    category_code: Mapped[str] = mapped_column(String(8), index=True)
    title: Mapped[str] = mapped_column(String(512))
    detect: Mapped[str] = mapped_column(Text)
    reaction: Mapped[str] = mapped_column(Text)
    severity: Mapped[int] = mapped_column(Integer, index=True)
    dispatch: Mapped[str] = mapped_column(String(32))
    recovery: Mapped[str] = mapped_column(String(32))
    inject: Mapped[str | None] = mapped_column(Text, nullable=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
