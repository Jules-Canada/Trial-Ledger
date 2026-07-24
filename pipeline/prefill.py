"""CT.gov skeleton pre-fill CLI.

Emits trial stubs (matching docs/drug-schema.md) for one or more NCT IDs.
Efficacy/timeline stay hand-/LLM-curated.

Usage: `tl-prefill NCT03600883 NCT04303780` (or `python -m pipeline.prefill ...`).
"""

from __future__ import annotations

import json
import re
import sys

from pipeline.ctgov import fetch_trial_skeleton


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:40]


def main() -> None:
    ncts = sys.argv[1:]
    if not ncts:
        print("Usage: tl-prefill <NCT_ID> [NCT_ID...]", file=sys.stderr)
        sys.exit(1)

    stubs = []
    for nct in ncts:
        sk = fetch_trial_skeleton(nct)
        if sk is None:
            print(f"! {nct}: fetch failed", file=sys.stderr)
            continue
        name = sk.acronym or sk.official_name
        stubs.append(
            {
                "id": _slug(sk.acronym or sk.official_name or nct),
                "name": name,
                "registry_id": sk.registry_id,
                "indication": "; ".join(sk.conditions) or "TODO: set indication",
                "sponsor": sk.sponsor or "TODO: set sponsor",
                "phases": sk.phases,
                "start_date": sk.start_date,
                "status": sk.status,
                "note": (
                    f"TODO: efficacy + timeline are curated. "
                    f"Enrollment: {sk.enrollment if sk.enrollment is not None else '?'}. "
                    f"Conditions: {', '.join(sk.conditions) or '?'}."
                ),
                "sources": [
                    {
                        "url": f"https://clinicaltrials.gov/study/{sk.registry_id}",
                        "source_type": "registry",
                    }
                ],
            }
        )

    print(json.dumps(stubs, indent=2))


if __name__ == "__main__":
    main()
