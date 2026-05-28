from __future__ import annotations

import pytest

from factory.engine.schemas import (
    CandidateExample,
    Completion,
    Difficulty,
    HumanDecision,
    Provenance,
    Record,
    Scores,
    SkillNode,
    SkillTree,
    Task,
    TokenUsage,
    VerificationResult,
)


def test_task_defaults_and_roundtrip() -> None:
    t = Task(task_id="t1", skill_id="arith.add", params={"a": 1, "b": 2})
    assert t.difficulty == Difficulty.MEDIUM
    raw = t.model_dump_json()
    assert Task.model_validate_json(raw) == t


def test_skill_tree_leaves_walks_all_branches() -> None:
    tree = SkillTree(
        root=SkillNode(
            id="r",
            name="root",
            children=[
                SkillNode(id="r.a", name="a", leaf=True),
                SkillNode(
                    id="r.b",
                    name="b",
                    children=[
                        SkillNode(id="r.b.x", name="bx", leaf=True),
                        SkillNode(id="r.b.y", name="by", leaf=True),
                    ],
                ),
            ],
        )
    )
    assert {leaf.id for leaf in tree.leaves()} == {"r.a", "r.b.x", "r.b.y"}
    assert tree.find("r.b.x") is not None
    assert tree.find("missing") is None


def test_verification_signal_bounds_enforced() -> None:
    with pytest.raises(Exception):
        VerificationResult(passed=True, signal_strength=1.5)
    with pytest.raises(Exception):
        VerificationResult(passed=True, signal_strength=-0.01)
    # boundary values OK
    VerificationResult(passed=True, signal_strength=0.0)
    VerificationResult(passed=True, signal_strength=1.0)


def test_provenance_rejects_blanks() -> None:
    with pytest.raises(Exception):
        Provenance(pack_name="", provider="x", model="m", run_id="r")
    with pytest.raises(Exception):
        Provenance(pack_name="p", provider="x", model="m", run_id="")


def test_record_carries_full_lineage() -> None:
    rec = Record(
        record_id="rid",
        task=Task(task_id="t1", skill_id="x.y"),
        payload={"q": "1+1", "a": 2},
        verification_tier="CHECKABLE",
        verification=VerificationResult(passed=True, signal_strength=1.0),
        scores=Scores(quality=0.9),
        provenance=Provenance(
            pack_name="arithmetic", provider="mock", model="mock-1", run_id="run-1"
        ),
    )
    assert rec.human_reviewed is False
    assert rec.provenance.pack_name == "arithmetic"
    # JSON-serialisable round trip
    raw = rec.model_dump_json()
    again = Record.model_validate_json(raw)
    assert again == rec


def test_candidate_example_roundtrip() -> None:
    c = CandidateExample(
        task=Task(task_id="t1", skill_id="x.y"),
        prompt="hello",
        completion=Completion(text="world", usage=TokenUsage(input_tokens=3, output_tokens=2)),
        payload={"k": 1},
    )
    raw = c.model_dump_json()
    assert CandidateExample.model_validate_json(raw) == c


def test_human_decision_enum() -> None:
    assert HumanDecision("accept") == HumanDecision.ACCEPT
    with pytest.raises(ValueError):
        HumanDecision("maybe")
