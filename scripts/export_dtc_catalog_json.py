#!/usr/bin/env python3
"""Write bundled DTC catalog to data/dtc_catalog.json for external tooling.

  uv run python scripts/export_dtc_catalog_json.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.features.dtc.bundled import get_catalog

OUT = ROOT / "data" / "dtc_catalog.json"


def main() -> int:
    catalog = get_catalog()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog['dtcs'])} DTCs to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
