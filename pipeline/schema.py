"""Canonical drug-record schema — the single source of truth.

Mirrors docs/drug-schema.md. This Pydantic model does triple duty:
  1. Validation (`pipeline/validate.py`) — replaces the old hand-rolled JS validator.
  2. Authoring contract — passed to `messages.parse(output_format=DrugRecord)` so
     the LLM is constrained to this exact shape.
  3. Frontend types — `pipeline/gen_types.py` emits src/types.generated.ts from the
     JSON Schema this model produces.

Design rules encoded here (see CLAUDE.md and the memory notes):
  - Efficacy is endpoint-agnostic: `endpoint` is free text, `value`/`unit` hold
    whatever the trial reported, `met` is per-endpoint (true/false/null).
  - Trials are first-class and carry their own `indication` and `sponsor`
    (sponsorship can transfer over time, so `sponsor` may be a list).
  - Timeline is dated events, non-linear (accelerated approval can precede the
    confirmatory Phase 3 readout).
  - Provenance, not human sign-off: every data point carries `sources`.
"""

from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

SourceType = Literal[
    "registry",
    "press_release",
    "IR",
    "journal",
    "conference_abstract",
    "fda_label",
    "drugs_at_fda",
    "other",
]

EndpointRole = Literal["primary", "secondary", "exploratory"]

TimelineEventType = Literal[
    "first_in_human",
    "phase_start",
    "filing",
    "accelerated_approval",
    "approval",
    "data_readout",
    "regulatory_event",
    "discontinuation",
]

# Number values keep their input type (43 stays 43, 12.5 stays 12.5) so
# authored records round-trip without gaining spurious ".0".
Number = Union[int, float]


class _Base(BaseModel):
    # Strict: unknown keys are a schema violation, not silently ignored. This is
    # what makes the Pydantic model a real validator and gives structured-output
    # generation `additionalProperties: false` on every object.
    model_config = ConfigDict(extra="forbid")


class Source(_Base):
    url: str
    source_type: SourceType


class Trial(_Base):
    id: str
    name: str
    # Authoritative NCT filled from ClinicalTrials.gov during authoring. Present
    # but nullable — early-stage/unregistered programs may have none.
    registry_id: Optional[str]
    # The disease this trial studied. First-class: a drug can run trials across
    # indications with different outcomes; efficacy inherits via its trial.
    indication: str
    # Who ran it. A list when sponsorship transferred (e.g. Pfizer -> Priovant).
    sponsor: Union[str, list[str]]
    phases: list[str] = Field(min_length=1)
    start_date: Optional[str]
    status: str
    note: Optional[str]
    sources: list[Source]


class TimelineEvent(_Base):
    date: Optional[str]
    type: TimelineEventType
    # Optional: corporate events (e.g. an acquisition) may omit trial entirely.
    trial: Optional[str] = None
    confirmed: Optional[bool] = None
    note: Optional[str]
    sources: list[Source]


class EfficacyRecord(_Base):
    trial: str
    phase: str
    endpoint: str
    # Present but nullable — use null when the value wasn't disclosed.
    value: Optional[Number]
    # "" for unitless endpoints (composite scores like TIS).
    unit: str
    role: EndpointRole
    # Per-endpoint, not per-phase. null = single-arm / no formal bar.
    met: Optional[bool]
    sources: list[Source]
    comparator: Optional[str] = None
    # Whether this value is comparable across phases (same definition/population).
    comparable: Optional[bool] = None
    # Endpoint definition when it needs disambiguation (e.g. ORR per RECIST 1.1).
    definition: Optional[str] = None
    note: Optional[str] = None


class Discontinuation(_Base):
    date: str
    phase: str
    reason: str


class Identity(_Base):
    name: str
    codes: list[str]
    brand_name: str
    sponsors: list[str] = Field(min_length=1)
    modality: str
    target: str
    indications: list[str] = Field(min_length=1)


class Verification(_Base):
    status: str
    verified_on: Optional[str] = None
    note: Optional[str] = None


class DrugRecord(_Base):
    id: str
    identity: Identity
    trials: list[Trial]
    timeline: list[TimelineEvent]
    efficacy: list[EfficacyRecord]
    # Present but nullable — null when development was not halted.
    discontinuation: Optional[Discontinuation]
    # Provenance-based trust stamp (not a human sign-off). Serialized as
    # "_verification" to match the on-disk records.
    verification: Optional[Verification] = Field(default=None, alias="_verification")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _check_trial_cross_references(self) -> "DrugRecord":
        """Every efficacy/timeline `trial` must point at a real trial id."""
        trial_ids = {t.id for t in self.trials}
        problems: list[str] = []
        for i, e in enumerate(self.efficacy):
            if e.trial not in trial_ids:
                problems.append(
                    f"efficacy[{i}] ({e.endpoint}): trial {e.trial!r} "
                    f"does not match any trial id"
                )
        for i, ev in enumerate(self.timeline):
            # trial is optional (null for corporate events); only check when set.
            if ev.trial is not None and ev.trial not in trial_ids:
                problems.append(
                    f"timeline[{i}]: trial {ev.trial!r} does not match any trial id"
                )
        if problems:
            raise ValueError("; ".join(problems))
        return self
