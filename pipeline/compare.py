"""Author one drug across multiple models and compare cost + output.

Usage:
  tl-compare "sotorasib"
  tl-compare --models claude-opus-4-8,claude-sonnet-4-6,claude-haiku-4-5 "sotorasib"

Runs the full authoring flow once per model, writes each record to
_compare/<id>__<model>.json (gitignored scratch, so the canonical
data/drugs/<id>.json is never touched), and prints a side-by-side of cost and
record shape. Diff the written files to compare the actual content. Per-model
failures are caught and reported so one bad model doesn't abort the comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from pipeline.author import build_record, get_provider, require_key

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local", override=False)

OUT_DIR = ROOT / "_compare"
DEFAULT_MODELS = ["claude-opus-4-8", "claude-sonnet-4-6"]


def _stats(record: dict) -> dict:
    sources = sum(
        len(item.get("sources", []))
        for key in ("trials", "efficacy", "timeline")
        for item in record.get(key, [])
    )
    return {
        "trials": len(record.get("trials", [])),
        "efficacy": len(record.get("efficacy", [])),
        "timeline": len(record.get("timeline", [])),
        "sources": sources,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tl-compare",
        description="Author a drug across models and compare cost + output.",
    )
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help=f"Comma-separated model ids (default: {','.join(DEFAULT_MODELS)})",
    )
    parser.add_argument("drug", nargs="+", help="Drug name (may be multiple words)")
    args = parser.parse_args()
    drug = " ".join(args.drug).strip()
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for model in models:
        provider = get_provider(model=model)
        require_key(provider)  # fail fast before spending if no key
        print(f"\n=== authoring {drug!r} with {model} ===", file=sys.stderr)
        try:
            record = build_record(drug, provider)
            out = OUT_DIR / f"{record['id']}__{model}.json"
            out.write_text(json.dumps(record, indent=2) + "\n")
            cost = provider.cost_usd() if hasattr(provider, "cost_usd") else 0.0
            rows.append((model, cost, provider.usage.calls, _stats(record), out.name, None))
        except Exception as e:  # one model failing shouldn't kill the run
            # A failed run still spent tokens/searches — report the real cost.
            calls = getattr(getattr(provider, "usage", None), "calls", 0)
            cost = provider.cost_usd() if hasattr(provider, "cost_usd") else 0.0
            rows.append((model, cost, calls, None, None, str(e)[:90]))
            print(f"[compare] {model} FAILED (${cost:.2f} spent): {e}", file=sys.stderr)

    # Comparison table
    print("\n" + "=" * 74)
    print(f"COMPARISON — {drug}")
    print("=" * 74)
    header = (
        f"{'model':24} {'cost':>7} {'calls':>5} "
        f"{'trials':>6} {'effic':>6} {'timel':>6} {'srcs':>5}"
    )
    print(header)
    print("-" * len(header))
    for model, cost, calls, stats, fname, err in rows:
        if stats is None:
            print(f"{model:24} ${cost:6.2f} {calls:5}   ERROR: {err}")
        else:
            print(
                f"{model:24} ${cost:6.2f} {calls:5} "
                f"{stats['trials']:6} {stats['efficacy']:6} "
                f"{stats['timeline']:6} {stats['sources']:5}"
            )
    print(f"\nrecords written to {OUT_DIR.name}/ — diff them to compare content, e.g.:")
    ok = [f for *_, f, err in rows if err is None]
    if len(ok) >= 2:
        print(f"  diff {OUT_DIR.name}/{ok[0]} {OUT_DIR.name}/{ok[1]}")


if __name__ == "__main__":
    main()
