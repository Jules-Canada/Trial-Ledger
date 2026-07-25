"""Automated authoring orchestrator.

Agent-agnostic: depends only on the LlmProvider base class. Select the provider
via LLM_PROVIDER (default "claude"). See docs/design/authoring-pipeline.md.

Usage: `tl-author "sotorasib"` (or `python -m pipeline.author "sotorasib"`).
Reads ANTHROPIC_API_KEY from the environment or .env.local (gitignored).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from pipeline.ctgov import fetch_trial_skeleton, is_nct
from pipeline.llm.provider import LlmProvider
from pipeline.schema import DrugRecord, Source, Trial

# Load .env.local (gitignored) if present — same contract as the old node
# --env-file-if-exists=.env.local. Never commit a key. Real env vars win.
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local", override=False)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "drugs"

# Optional convenience fields that hand-curated records may carry but the
# authoring contract doesn't require. Strip them from authored output when unset,
# so "absence is meaningful" nulls (value, met, start_date, trial, ...) stay
# distinct from fields the author simply didn't populate.
_STRIP_WHEN_NULL = {"confirmed", "comparable", "definition", "verified_on", "registry_id"}


def authoring_prompt(drug: str) -> str:
    return "\n".join(
        [
            f"Build a single-drug clinical-development record for: {drug}.",
            "",
            "Rules:",
            "- Public sources only. Attach a source (url + source_type) to every data point.",
            "- Efficacy is endpoint-agnostic: capture whatever endpoint each trial reported",
            "  (ORR, PFS, OS, ACR20, PASI, PANSS, TIS, etc.) with its value, unit, role,",
            "  and met? (true/false/null). met? is PER-ENDPOINT, not per-phase.",
            "- A trial can span phases (e.g. Phase 1/2) and belongs to one indication and",
            "  one sponsor. Sponsorship can differ across trials (transfers over time).",
            "- Give each trial its ClinicalTrials.gov NCT id in registry_id when one exists;",
            "  authoritative skeleton fields are merged from the registry afterward.",
            "- Timeline is a set of dated events (non-linear: accelerated approval can",
            "  precede the confirmatory Phase 3 readout).",
            "- If a value is not disclosed, use null rather than inventing a number.",
            "- Set discontinuation only if the drug's development was halted.",
        ]
    )


def get_provider(model: Optional[str] = None) -> LlmProvider:
    """Select the provider (LLM_PROVIDER, default claude) and model. Model
    precedence: explicit arg > LLM_MODEL env > the provider's default."""
    name = os.environ.get("LLM_PROVIDER", "claude")
    model = model or os.environ.get("LLM_MODEL")
    if name == "claude":
        from pipeline.llm.claude import ClaudeProvider

        return ClaudeProvider(model=model)
    raise ValueError(
        f'Unknown LLM_PROVIDER "{name}". Only "claude" is implemented so far.'
    )


def _phase_digits(phases: list[str]) -> set[str]:
    """Normalize phase labels to their digits for comparison, so "Phase 1",
    "1", and "Phase1" all read as {"1"} (and "Phase 1/2" as {"1","2"})."""
    out: set[str] = set()
    for p in phases:
        out.update(re.findall(r"\d+", str(p)))
    return out


def merge_prefill(trials: list[Trial]) -> int:
    """The LLM's trial skeleton (phases, dates, sponsor, status) is a guess; the
    registry is authoritative. For every trial with a real NCT, overwrite those
    fields from ClinicalTrials.gov and keep the LLM's id/indication/note/name.

    Two guards keep the registry from clobbering deliberate LLM modeling:
      - A registered study can span phases via parts (e.g. tofersen's 233AS101:
        Phase 1/2 Parts A/B + Phase 3 Part C VALOR). If the LLM's phases and the
        registry's don't overlap, the LLM is modeling a specific sub-part —
        keep its phases rather than overwrite to the whole-study phase.
      - Two trial objects sharing one NCT is a smell (usually that same
        multi-part study); warn so a curator can check."""
    filled = 0

    seen: dict[str, list[str]] = {}
    for t in trials:
        if is_nct(t.registry_id):
            seen.setdefault(t.registry_id.strip(), []).append(t.id)
    for nct, ids in seen.items():
        if len(ids) > 1:
            print(
                f"[author] prefill: WARNING {len(ids)} trials share {nct}: {ids} "
                "— likely one multi-part study; verify the split.",
                file=sys.stderr,
            )

    for t in trials:
        if not is_nct(t.registry_id):
            continue
        sk = fetch_trial_skeleton(t.registry_id.strip())
        if sk is None:
            print(
                f"[author] prefill: {t.registry_id} fetch failed, keeping LLM values",
                file=sys.stderr,
            )
            continue
        # Compare on normalized phase digits so a formatting difference
        # ("Phase 1" vs "1") isn't treated as a real mismatch — only a genuine
        # disagreement (e.g. LLM {1,2} vs registry {3}) keeps the LLM's phases.
        llm_d, reg_d = _phase_digits(t.phases), _phase_digits(sk.phases)
        if llm_d and reg_d and not (llm_d & reg_d):
            print(
                f"[author] prefill: {t.registry_id} phase mismatch "
                f"(LLM {sorted(llm_d)} vs registry {sorted(reg_d)}) — keeping LLM phases",
                file=sys.stderr,
            )
        else:
            t.phases = sk.phases
        t.start_date = sk.start_date
        t.status = sk.status
        if sk.sponsor:
            t.sponsor = sk.sponsor
        if not any(s.source_type == "registry" for s in t.sources):
            t.sources.insert(
                0,
                Source(
                    url=f"https://clinicaltrials.gov/study/{sk.registry_id}",
                    source_type="registry",
                ),
            )
        t.note = f"{t.note + ' ' if t.note else ''}[skeleton fields from ClinicalTrials.gov]"
        filled += 1
    return filled


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _serialize(record: DrugRecord) -> dict[str, Any]:
    """Dump to JSON-ready dict, keeping meaningful nulls but dropping unset
    optional-convenience fields (see _STRIP_WHEN_NULL)."""
    data = record.model_dump(mode="json", by_alias=True)

    def clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: clean(v)
                for k, v in obj.items()
                if not (k in _STRIP_WHEN_NULL and v is None)
            }
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        return obj

    return clean(data)


def require_key(provider: LlmProvider) -> None:
    """Fail fast with guidance if the provider needs a key that isn't set."""
    if provider.name == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "Missing ANTHROPIC_API_KEY. Provide it one of these ways (never commit it):\n"
            "  • Keychain (most secure): "
            'ANTHROPIC_API_KEY=$(security find-generic-password -s ANTHROPIC_API_KEY -w) '
            'tl-author "<drug>"\n'
            "  • .env.local (gitignored): copy .env.example to .env.local, fill it in, "
            'then tl-author "<drug>"\n'
            "  • This session: type  ! export ANTHROPIC_API_KEY=sk-ant-...  then run.",
            file=sys.stderr,
        )
        sys.exit(1)


def build_record(drug: str, provider: LlmProvider) -> dict[str, Any]:
    """Author one drug into a schema-valid record dict: LLM research+extract,
    CT.gov skeleton merge, provenance stamp. No file I/O — callers decide where
    it goes (tl-author -> data/drugs; tl-compare -> a scratch dir)."""
    brief = authoring_prompt(drug)
    print(
        f'[author] provider={provider.name} model={provider.model} drug="{drug}"',
        file=sys.stderr,
    )

    result = provider.research(brief=brief, output_model=DrugRecord)
    record = result.data

    # Registry override: skeleton fields come from CT.gov, not the LLM.
    n = merge_prefill(record.trials)
    print(f"[author] prefill: registry skeleton merged for {n} trial(s)", file=sys.stderr)

    record.id = record.id or _slug(drug)
    # Trust is provenance-based: stamp which model authored this, not a human sign-off.
    from pipeline.schema import Verification

    record.verification = Verification(
        status="draft-unverified",
        note=(
            f"Auto-authored by {result.provider}/{result.model}; trial skeleton fields "
            "(phases, dates, sponsor, status) merged from ClinicalTrials.gov. "
            "Provenance-based trust: source_type per data point signals confidence. "
            "Run tl-validate."
        ),
    )
    return _serialize(record)


def report_usage(provider: LlmProvider) -> None:
    """Print the per-run token tally and estimated cost (if the provider meters)."""
    usage = getattr(provider, "usage", None)
    if usage is None:
        return
    print(
        f"[author] usage: {usage.calls} API calls | "
        f"in {usage.input_tokens:,} tok | out {usage.output_tokens:,} tok | "
        f"cache_read {usage.cache_read_tokens:,} | web_searches {usage.web_searches}",
        file=sys.stderr,
    )
    cost = getattr(provider, "cost_usd", None)
    if cost is not None:
        print(f"[author] estimated cost: ${cost():.2f}", file=sys.stderr)


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        prog="tl-author",
        description='Author a drug record. e.g. tl-author --model claude-sonnet-4-6 "sotorasib"',
    )
    parser.add_argument("--model", default=None, help="Model id (default: provider default / $LLM_MODEL)")
    parser.add_argument("drug", nargs="+", help="Drug name (may be multiple words)")
    args = parser.parse_args()
    drug = " ".join(args.drug).strip()

    provider = get_provider(model=args.model)
    require_key(provider)

    record = build_record(drug, provider)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{record['id']}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"[author] wrote {out}", file=sys.stderr)
    report_usage(provider)
    print("[author] next: tl-validate", file=sys.stderr)


if __name__ == "__main__":
    main()
