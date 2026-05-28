from __future__ import annotations

import pytest

from factory.engine.domain import (
    DomainPack,
    PackValidationError,
    Tier,
    _clear_registry_for_tests,
    get_pack,
    list_packs,
    register_pack,
    validate_pack,
)
from factory.engine.schemas import (
    CandidateExample,
    Completion,
    SkillNode,
    SkillTree,
    VerificationResult,
)


def _tree(leaf_id: str = "x.y") -> SkillTree:
    return SkillTree(
        root=SkillNode(
            id="x",
            name="x",
            children=[SkillNode(id=leaf_id, name="y", leaf=True)],
        )
    )


class _DummyPack(DomainPack):
    name = "dummy"
    tier = Tier.CHECKABLE
    skill_map = _tree()
    allowlist: list[str] = []

    def generate(self, task, model):  # type: ignore[override]
        return CandidateExample(task=task, prompt="p", completion=Completion(text="x"))

    def verify(self, ex):  # type: ignore[override]
        return VerificationResult(passed=True, signal_strength=1.0)


def setup_function(_: object) -> None:
    _clear_registry_for_tests()


def test_register_and_get() -> None:
    p = _DummyPack()
    register_pack(p)
    assert "dummy" in list_packs()
    assert get_pack("dummy") is p


def test_get_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_pack("missing")


def test_validate_rejects_blank_name() -> None:
    class P(_DummyPack):
        name = ""

    with pytest.raises(PackValidationError, match="non-empty"):
        validate_pack(P())


def test_validate_rejects_empty_skill_map() -> None:
    empty_tree = SkillTree(root=SkillNode(id="r", name="r"))

    class P(_DummyPack):
        skill_map = empty_tree

    with pytest.raises(PackValidationError, match="leaf scenarios"):
        validate_pack(P())


def test_validate_rejects_non_tier() -> None:
    class P(_DummyPack):
        tier = "CHECKABLE"  # type: ignore[assignment]

    with pytest.raises(PackValidationError, match="Tier enum"):
        validate_pack(P())


def test_validate_comparative_requires_human_review() -> None:
    class P(_DummyPack):
        tier = Tier.COMPARATIVE
        human_review_pct = 0.0

    with pytest.raises(PackValidationError, match="anti-collapse"):
        validate_pack(P())


def test_validate_judgment_requires_human_review() -> None:
    class P(_DummyPack):
        tier = Tier.JUDGMENT
        human_review_pct = 0.0

    with pytest.raises(PackValidationError, match="anti-collapse"):
        validate_pack(P())


def test_validate_comparative_with_review_pct_is_ok() -> None:
    class P(_DummyPack):
        tier = Tier.COMPARATIVE
        human_review_pct = 0.05

    validate_pack(P())  # no raise


def test_validate_rejects_review_pct_above_one() -> None:
    class P(_DummyPack):
        tier = Tier.JUDGMENT
        human_review_pct = 1.2

    with pytest.raises(PackValidationError, match=">"):
        validate_pack(P())


def test_register_rejects_duplicates() -> None:
    register_pack(_DummyPack())
    with pytest.raises(PackValidationError, match="already registered"):
        register_pack(_DummyPack())
