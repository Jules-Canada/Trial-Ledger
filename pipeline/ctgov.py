"""ClinicalTrials.gov v2 API — authoritative trial skeleton.

Shared by the authoring orchestrator (author.py) and the prefill CLI
(prefill.py). Skeleton ONLY (phases, dates, sponsor, status, conditions); the
registry does NOT carry topline efficacy. See docs/data-pipeline.md.

Uses the stdlib (urllib) so the pipeline has no HTTP dependency beyond the
Anthropic SDK.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

_API = "https://clinicaltrials.gov/api/v2/studies/"

_PHASE = {"PHASE1": "1", "PHASE2": "2", "PHASE3": "3", "PHASE4": "4"}
_STATUS = {
    "COMPLETED": "completed",
    "TERMINATED": "terminated",
    "WITHDRAWN": "terminated",
    "SUSPENDED": "terminated",
    "RECRUITING": "ongoing",
    "ENROLLING_BY_INVITATION": "ongoing",
    "ACTIVE_NOT_RECRUITING": "ongoing",
    "NOT_YET_RECRUITING": "ongoing",
}

_NCT_RE = re.compile(r"^NCT\d{8}$")


@dataclass
class TrialSkeleton:
    registry_id: str
    official_name: str
    acronym: Optional[str]
    phases: list[str]
    start_date: Optional[str]
    status: str
    sponsor: Optional[str]
    conditions: list[str]
    enrollment: Optional[int]


def is_nct(value: object) -> bool:
    return isinstance(value, str) and bool(_NCT_RE.match(value.strip()))


def fetch_trial_skeleton(nct: str) -> Optional[TrialSkeleton]:
    url = f"{_API}{urllib.parse.quote(nct)}?format=json"
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                return None
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    ps = payload.get("protocolSection", {}) or {}
    idm = ps.get("identificationModule", {}) or {}
    st = ps.get("statusModule", {}) or {}
    design = ps.get("designModule", {}) or {}
    spon = ps.get("sponsorCollaboratorsModule", {}) or {}
    cond = ps.get("conditionsModule", {}) or {}

    phases = [_PHASE[p] for p in (design.get("phases") or []) if p in _PHASE]
    overall = st.get("overallStatus") or ""

    return TrialSkeleton(
        registry_id=idm.get("nctId") or nct,
        official_name=idm.get("briefTitle") or idm.get("officialTitle") or nct,
        acronym=idm.get("acronym"),
        phases=phases or ["?"],
        start_date=(st.get("startDateStruct") or {}).get("date"),
        status=_STATUS.get(overall, overall.lower() or "unknown"),
        sponsor=(spon.get("leadSponsor") or {}).get("name"),
        conditions=cond.get("conditions") or [],
        enrollment=(design.get("enrollmentInfo") or {}).get("count"),
    )
