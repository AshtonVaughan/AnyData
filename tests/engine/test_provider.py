from __future__ import annotations

import pytest

from factory.engine.provider import (
    DeepSeekFlashProvider,
    MockProvider,
    ProviderError,
)


def test_mock_provider_round_robins_and_estimates_tokens() -> None:
    p = MockProvider(responses=["alpha", "beta", "gamma"])
    a = p.complete(system="sys", prompt="p1")
    b = p.complete(system="sys", prompt="p2")
    c = p.complete(system="sys", prompt="p3")
    d = p.complete(system="sys", prompt="p4")
    assert [a.text, b.text, c.text, d.text] == ["alpha", "beta", "gamma", "alpha"]
    for completion in (a, b, c, d):
        assert completion.usage.input_tokens > 0
        assert completion.usage.output_tokens > 0
        assert completion.model == "mock-1"
    assert len(p.calls) == 4
    assert p.name == "mock"


def test_mock_thinking_off_zeros_reasoning_tokens() -> None:
    p = MockProvider()
    c_on = p.complete(system="s", prompt="p", thinking=True)
    c_off = p.complete(system="s", prompt="p", thinking=False)
    assert c_on.usage.reasoning_tokens > 0
    assert c_off.usage.reasoning_tokens == 0


def test_mock_max_tokens_truncates_simulated_output() -> None:
    p = MockProvider(responses=["a" * 100])
    c = p.complete(system="s", prompt="p", max_tokens=4)
    # max_tokens=4 -> ~16 chars in the crude simulation
    assert len(c.text) <= 16


def test_deepseek_provider_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="DEEPSEEK_API_KEY"):
        DeepSeekFlashProvider()
