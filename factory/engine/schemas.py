"""Pydantic v2 schemas for the engine.

Every persisted ``Record`` carries provenance, the verification tier under which
it was accepted, the verifier's evidence, and graded scores. Records without
provenance must be rejected (see ``factory.engine.store``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Difficulty(str, Enum):
    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class SkillNode(BaseModel):
    """A node in a domain pack's skill tree.

    ``leaf=True`` means this node is a generation target. Categories have
    ``leaf=False`` and carry children. The orchestrator only ever generates
    against leaves.
    """

    model_config = ConfigDict(frozen=False)

    id: str
    name: str
    description: str = ""
    children: list["SkillNode"] = Field(default_factory=list)
    leaf: bool = False


class SkillTree(BaseModel):
    """A pack's coverage map."""

    root: SkillNode

    def leaves(self) -> list[SkillNode]:
        out: list[SkillNode] = []
        stack: list[SkillNode] = [self.root]
        while stack:
            n = stack.pop()
            if n.leaf:
                out.append(n)
            stack.extend(n.children)
        return out

    def find(self, skill_id: str) -> Optional[SkillNode]:
        stack: list[SkillNode] = [self.root]
        while stack:
            n = stack.pop()
            if n.id == skill_id:
                return n
            stack.extend(n.children)
        return None


class Task(BaseModel):
    """A unit of generation work: produce one example for one skill leaf."""

    task_id: str
    skill_id: str
    difficulty: Difficulty = Difficulty.MEDIUM
    params: dict[str, Any] = Field(default_factory=dict)
    seed: Optional[int] = None


class TokenUsage(BaseModel):
    """Token accounting for one model call (or a sum across calls)."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0


class Completion(BaseModel):
    """Result returned by a ``ModelProvider`` call."""

    text: str
    reasoning: Optional[str] = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str = "stop"


class CandidateExample(BaseModel):
    """Raw generation prior to verification and grading."""

    task: Task
    prompt: str
    completion: Completion
    payload: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=_utcnow)


class VerificationResult(BaseModel):
    """Output of a pack's ``verify``.

    ``signal_strength`` is the verifier's self-reported confidence in the
    correctness signal (1.0 = oracle, e.g. execution or independent
    recomputation; 0.0 = unreliable). Engine uses this to weight curation.
    """

    passed: bool
    signal_strength: float = Field(ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class Scores(BaseModel):
    """Grader output. All bounded [0,1]; extra metrics under ``extra``."""

    difficulty: float = Field(default=0.0, ge=0.0, le=1.0)
    quality: float = Field(default=0.0, ge=0.0, le=1.0)
    efficiency: float = Field(default=0.0, ge=0.0, le=1.0)
    diversity: float = Field(default=0.0, ge=0.0, le=1.0)
    extra: dict[str, float] = Field(default_factory=dict)


class Provenance(BaseModel):
    """Where a record came from. Never optional on a stored ``Record``."""

    pack_name: str
    pack_version: str = "0.0.0"
    provider: str
    model: str
    seed: Optional[int] = None
    thinking_enabled: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    run_id: str

    @field_validator("pack_name", "provider", "model", "run_id")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v:
            raise ValueError("must be non-empty")
        return v


class HumanDecision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    FLAG = "flag"


class Record(BaseModel):
    """An accepted, persisted datapoint."""

    record_id: str
    task: Task
    payload: dict[str, Any]
    verification_tier: str
    verification: VerificationResult
    scores: Scores
    provenance: Provenance
    human_reviewed: bool = False
    human_decision: Optional[HumanDecision] = None


SkillNode.model_rebuild()
