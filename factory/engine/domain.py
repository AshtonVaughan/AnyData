"""Domain Pack ABC, tier enum, registry, and load-time validation.

A Domain Pack is the only place domain-specific logic lives. The engine never
needs to change to add a new domain. The cardinal load-time guard is the
**anti-collapse rule**: a pack that declares ``COMPARATIVE`` or ``JUDGMENT``
*must* set ``human_review_pct > 0`` -- otherwise the loop would let the model
grade its own output as the sole correctness signal, which we reject.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from .provider import ModelProvider
from .schemas import (
    CandidateExample,
    Scores,
    SkillTree,
    Task,
    VerificationResult,
)


class Tier(str, Enum):
    """Strength of correctness signal a pack provides."""

    EXECUTABLE = "EXECUTABLE"      # ran/passed tests
    CHECKABLE = "CHECKABLE"        # matches spec or independent recompute
    COMPARATIVE = "COMPARATIVE"    # independent methods/models agree
    JUDGMENT = "JUDGMENT"          # subjective; needs humans


class Env:
    """Optional per-pack environment handle (sandboxes, tmpdirs, etc.)."""


class DomainPack(ABC):
    """Subclass to define a new domain. Engine code never imports the pack."""

    # Identity & coverage
    name: str = ""
    version: str = "0.0.0"
    tier: Tier = Tier.JUDGMENT
    skill_map: SkillTree

    # Safety: hard list of resources the pack is allowed to touch. The engine
    # enforces this for EXECUTABLE packs by sandboxing; non-EXECUTABLE packs
    # are still required to populate it for documentation and audit.
    allowlist: list[str] = []

    # Required > 0 for COMPARATIVE / JUDGMENT (enforced at load time).
    human_review_pct: float = 0.0

    # Lifecycle ------------------------------------------------------------
    def setup_environment(self) -> Optional[Env]:
        return None

    def teardown(self, env: Optional[Env]) -> None:
        return None

    # Core hooks -----------------------------------------------------------
    @abstractmethod
    def generate(self, task: Task, model: ModelProvider) -> CandidateExample: ...

    @abstractmethod
    def verify(self, ex: CandidateExample) -> VerificationResult: ...

    # Optional grading hook. Default is neutral (no opinion).
    def grade(self, ex: CandidateExample, model: ModelProvider) -> Scores:
        return Scores()


class PackValidationError(ValueError):
    """Raised when a pack fails load-time validation."""


def validate_pack(pack: DomainPack) -> None:
    """Reject malformed or unsafe packs before they enter the registry."""
    if not isinstance(pack, DomainPack):
        raise PackValidationError(f"expected DomainPack, got {type(pack).__name__}")

    if not pack.name:
        raise PackValidationError("pack.name must be a non-empty string")

    if not isinstance(pack.tier, Tier):
        raise PackValidationError(
            f"pack '{pack.name}' tier must be a Tier enum, got {type(pack.tier).__name__}"
        )

    smap = getattr(pack, "skill_map", None)
    if smap is None:
        raise PackValidationError(f"pack '{pack.name}' is missing skill_map")
    if not isinstance(smap, SkillTree):
        raise PackValidationError(
            f"pack '{pack.name}' skill_map must be a SkillTree"
        )

    if not smap.leaves():
        raise PackValidationError(
            f"pack '{pack.name}' skill_map has no leaf scenarios; "
            "at least one leaf is required to drive generation"
        )

    if not isinstance(pack.allowlist, list):
        raise PackValidationError(f"pack '{pack.name}' allowlist must be a list")

    if pack.tier in (Tier.COMPARATIVE, Tier.JUDGMENT):
        if not isinstance(pack.human_review_pct, (int, float)) or pack.human_review_pct <= 0:
            raise PackValidationError(
                f"pack '{pack.name}' declares tier={pack.tier.value} but "
                f"human_review_pct={pack.human_review_pct!r}. Packs at this "
                "tier MUST set human_review_pct > 0 (anti-collapse rule: a model "
                "may never be the sole grader of its own output)."
            )
        if pack.human_review_pct > 1.0:
            raise PackValidationError(
                f"pack '{pack.name}' human_review_pct={pack.human_review_pct} > 1.0"
            )


_REGISTRY: dict[str, DomainPack] = {}


def register_pack(pack: DomainPack) -> None:
    """Validate and register a pack instance."""
    validate_pack(pack)
    if pack.name in _REGISTRY:
        raise PackValidationError(f"pack '{pack.name}' already registered")
    _REGISTRY[pack.name] = pack


def get_pack(name: str) -> DomainPack:
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown pack '{name}'; registered: {sorted(_REGISTRY)!r}"
        )
    return _REGISTRY[name]


def list_packs() -> list[str]:
    return sorted(_REGISTRY)


def _clear_registry_for_tests() -> None:
    """Test-only escape hatch."""
    _REGISTRY.clear()
