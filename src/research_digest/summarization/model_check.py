"""Detect drift between configured MODEL_CHAIN and Google's live ListModels API.

Calls https://generativelanguage.googleapis.com/v1beta/models and reports:
  - chain models missing from the API (likely retired)
  - newer family-mates not yet in the chain (e.g. gemini-3.6-flash)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

import httpx

from research_digest.summarization.gemini import API_BASE, MODEL_CHAIN

logger = logging.getLogger(__name__)

LIST_MODELS_URL = API_BASE  # already ends in "/models"


# Family prefix → matcher. Used to surface "newer-than-chain" siblings.
# We treat a chain entry like "gemini-3.5-flash" as the family "gemini-*-flash"
# so anything matching that pattern but not in the chain is flagged.
_FAMILY_PATTERNS: dict[str, re.Pattern[str]] = {
    "gemini-flash": re.compile(r"^gemini-\d[\d.]*-flash(?!-lite)(?:-.*)?$"),
    "gemini-flash-lite": re.compile(r"^gemini-\d[\d.]*-flash-lite(?:-.*)?$"),
    "gemini-pro": re.compile(r"^gemini-\d[\d.]*-pro(?:-.*)?$"),
    "gemma": re.compile(r"^gemma-\d.*$"),
}

# Substrings that indicate a non-text-summarization variant. ListModels reports
# generateContent as a supported method even for image/tts/audio models since
# they share the endpoint, so we filter by name.
_SPECIALTY_INDICATORS = (
    "-tts", "-image", "-audio", "-vision", "-robotics",
    "-embedding", "-live", "-thinking-",
    "imagen", "veo", "lyria", "nano-banana",
)

# Match gemini X.Y in a name → (major, minor); minor defaults to 0.
_GEMINI_VERSION_RE = re.compile(r"^gemini-(\d+)(?:\.(\d+))?-")
# Match gemma N → (major,)
_GEMMA_VERSION_RE = re.compile(r"^gemma-(\d+)")


def _is_specialty(name: str) -> bool:
    lo = name.lower()
    return any(ind in lo for ind in _SPECIALTY_INDICATORS)


def _model_version(name: str) -> tuple[int, ...] | None:
    """Version tuple for ordering within a family. Gemini → (major, minor); Gemma → (major,)."""
    if (m := _GEMMA_VERSION_RE.match(name)):
        return (int(m.group(1)),)
    if (m := _GEMINI_VERSION_RE.match(name)):
        return (int(m.group(1)), int(m.group(2) or 0))
    return None


@dataclass
class RemoteModel:
    """A model returned by ListModels."""

    name: str  # bare ID, e.g. "gemini-3.5-flash" (with "models/" stripped)
    display_name: str
    supported_methods: list[str]

    @property
    def supports_generate_content(self) -> bool:
        return "generateContent" in self.supported_methods


@dataclass
class ModelCheckReport:
    """Diff between configured MODEL_CHAIN and remote ListModels output."""

    chain: list[str]
    remote_models: dict[str, RemoteModel] = field(default_factory=dict)
    missing_from_remote: list[str] = field(default_factory=list)
    newer_in_family: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def has_drift(self) -> bool:
        return bool(self.missing_from_remote or self.newer_in_family or self.error)


def list_remote_models(api_key: str, *, timeout: float = 30.0) -> dict[str, RemoteModel]:
    """Page through ListModels and return a {bare_name: RemoteModel} map.

    Uses the x-goog-api-key header (not ?key= query param) so the key never
    appears in URLs that might be logged on error.
    """
    out: dict[str, RemoteModel] = {}
    page_token: str | None = None
    headers = {"x-goog-api-key": api_key}
    with httpx.Client(timeout=timeout, headers=headers) as client:
        while True:
            params: dict[str, str | int] = {"pageSize": 1000}
            if page_token:
                params["pageToken"] = page_token
            response = client.get(LIST_MODELS_URL, params=params)
            response.raise_for_status()
            data = response.json()
            for m in data.get("models", []):
                full_name = m.get("name", "")
                bare = full_name.split("/", 1)[1] if "/" in full_name else full_name
                if not bare:
                    continue
                out[bare] = RemoteModel(
                    name=bare,
                    display_name=m.get("displayName", ""),
                    supported_methods=m.get("supportedGenerationMethods", []),
                )
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    return out


def check_drift(chain: list[str], remote: dict[str, RemoteModel]) -> ModelCheckReport:
    """Pure diff: compare chain against remote inventory."""
    report = ModelCheckReport(chain=list(chain), remote_models=remote)

    # 1. chain models missing from remote (retired or renamed)
    report.missing_from_remote = [m for m in chain if m not in remote]

    # 2. newer siblings in same families that the chain doesn't include.
    #    Filters: must support generateContent, must not be a specialty
    #    (image/tts/audio/etc.), must have a version strictly newer than the
    #    highest version of that family already in the chain.
    chain_set = set(chain)
    family_members: dict[str, list[str]] = {fam: [] for fam in _FAMILY_PATTERNS}
    for name, model in remote.items():
        if not model.supports_generate_content:
            continue
        if _is_specialty(name):
            continue
        for fam, pat in _FAMILY_PATTERNS.items():
            if pat.match(name):
                family_members[fam].append(name)
                break

    candidates: list[str] = []
    for fam, members in family_members.items():
        chain_in_family = [m for m in chain if _FAMILY_PATTERNS[fam].match(m)]
        if not chain_in_family:
            continue  # we don't use this family yet — don't spam
        chain_versions = [v for v in (_model_version(m) for m in chain_in_family) if v]
        max_chain_version = max(chain_versions) if chain_versions else None
        for m in members:
            if m in chain_set:
                continue
            # skip dated/preview variants of models already in the chain
            # (e.g. skip "gemini-3.5-flash-001" when "gemini-3.5-flash" is in chain)
            if any(m.startswith(c + "-") for c in chain_in_family):
                continue
            # only flag if strictly newer than what's already in the chain
            if max_chain_version is not None:
                v = _model_version(m)
                if v is None or v <= max_chain_version:
                    continue
            candidates.append(m)
    report.newer_in_family = sorted(set(candidates))
    return report


def format_report(report: ModelCheckReport) -> str:
    """Human-readable summary for CLI/log output."""
    lines: list[str] = []
    lines.append("=== Gemini model drift check ===")
    if report.error:
        lines.append(f"ERROR: {report.error}")
        return "\n".join(lines)
    lines.append(f"Chain length: {len(report.chain)}")
    lines.append(f"Remote models (generateContent-capable): "
                 f"{sum(1 for m in report.remote_models.values() if m.supports_generate_content)}")
    lines.append("")
    if report.missing_from_remote:
        lines.append("MISSING FROM REMOTE (likely retired):")
        for m in report.missing_from_remote:
            lines.append(f"  - {m}")
    else:
        lines.append("All chain models present in remote API.")
    lines.append("")
    if report.newer_in_family:
        lines.append("NEWER FAMILY MEMBERS NOT IN CHAIN:")
        for m in report.newer_in_family:
            rm = report.remote_models.get(m)
            label = rm.display_name if rm and rm.display_name else m
            lines.append(f"  - {m}  ({label})")
    else:
        lines.append("No newer family members detected.")
    if report.has_drift:
        lines.append("")
        lines.append("ACTION: review chain in src/research_digest/summarization/gemini.py")
    return "\n".join(lines)


def run_check(api_key: str | None = None) -> ModelCheckReport:
    """End-to-end: fetch remote, diff, return report. Network errors are captured."""
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return ModelCheckReport(chain=list(MODEL_CHAIN), error="GEMINI_API_KEY not set")
    try:
        remote = list_remote_models(key)
    except httpx.HTTPError as e:
        logger.exception("ListModels request failed")
        return ModelCheckReport(chain=list(MODEL_CHAIN), error=f"HTTP error: {e}")
    return check_drift(list(MODEL_CHAIN), remote)
