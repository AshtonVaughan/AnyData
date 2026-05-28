from __future__ import annotations

from factory.engine.cost import CostLedger, PricingRates, cost_for
from factory.engine.schemas import TokenUsage


def test_cost_zero_when_zero_tokens() -> None:
    assert cost_for(TokenUsage()) == 0.0


def test_cost_separates_cached_input() -> None:
    rates = PricingRates(
        input_per_million=1.0,
        cached_input_per_million=0.1,
        output_per_million=2.0,
        reasoning_per_million=2.0,
    )
    u = TokenUsage(
        input_tokens=1_000_000,
        cached_input_tokens=500_000,
        output_tokens=1_000_000,
    )
    # 500k fresh @ 1.0/M = 0.50
    # 500k cached @ 0.1/M = 0.05
    # 1M output @ 2.0/M = 2.00
    assert abs(cost_for(u, rates) - (0.50 + 0.05 + 2.00)) < 1e-9


def test_cost_reasoning_tokens_priced() -> None:
    rates = PricingRates(
        input_per_million=0,
        cached_input_per_million=0,
        output_per_million=0,
        reasoning_per_million=5.0,
    )
    u = TokenUsage(reasoning_tokens=2_000_000)
    assert abs(cost_for(u, rates) - 10.0) < 1e-9


def test_ledger_accumulates_and_summarises() -> None:
    led = CostLedger()
    led.record(TokenUsage(input_tokens=100, output_tokens=50))
    led.record(TokenUsage(input_tokens=200, output_tokens=80, cached_input_tokens=50))
    s = led.summary()
    assert s["calls"] == 2
    assert s["input_tokens"] == 300
    assert s["output_tokens"] == 130
    assert s["cached_input_tokens"] == 50
    assert "total_cost_usd" in s
    assert s["rates"]["input_per_million"] > 0


def test_ledger_incremental_cost_returned() -> None:
    rates = PricingRates(
        input_per_million=10.0,
        cached_input_per_million=1.0,
        output_per_million=20.0,
        reasoning_per_million=20.0,
    )
    led = CostLedger(rates=rates)
    inc = led.record(TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000))
    assert abs(inc - (10.0 + 20.0)) < 1e-9
    assert abs(led.total_cost - inc) < 1e-9
