"""Validate data/drugs/*.json against the canonical schema.

Run: `tl-validate` (or `python -m pipeline.validate`). Replaces the old
dependency-free scripts/validate.mjs — validation now comes from the same
Pydantic model that constrains authoring, so there's one source of truth.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from pipeline.schema import DrugRecord

DRUGS_DIR = Path(__file__).resolve().parent.parent / "data" / "drugs"


def _format_errors(exc: ValidationError) -> list[str]:
    lines: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        lines.append(f"{loc or '<root>'}: {err['msg']}")
    return lines


def main() -> None:
    files = sorted(DRUGS_DIR.glob("*.json"))
    if not files:
        print(f"No records found in {DRUGS_DIR}", file=sys.stderr)
        sys.exit(1)

    failed = 0
    for path in files:
        errs: list[str] = []
        try:
            data = json.loads(path.read_text())
            DrugRecord.model_validate(data)
        except json.JSONDecodeError as e:
            errs.append(f"invalid JSON: {e}")
        except ValidationError as e:
            errs.extend(_format_errors(e))

        if errs:
            failed += 1
            print(f"✗ {path.name}", file=sys.stderr)
            for e in errs:
                print(f"    {e}", file=sys.stderr)
        else:
            print(f"✓ {path.name}")

    print(f"\n{len(files) - failed}/{len(files)} records valid.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
