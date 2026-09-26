"""Bundled home-battery DTC catalog (source of truth when data/dtc_catalog.json is absent)."""

from app.features.dtc.bundled.meta import META
from app.features.dtc.bundled.entries import DTCS


def get_catalog() -> dict:
    return {"meta": META, "dtcs": DTCS}
