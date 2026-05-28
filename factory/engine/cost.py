"""Token and spend accounting.

Pricing defaults are placeholders for DeepSeek-V4-Flash. They are configurable
(``config/default.yaml``) and should be reconciled against the live API price
page at run time -- not treated as hardcoded truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import TokenUsage


@dataclass(frozen=True)
class PricingRates:
    """USD per 1M tokens. Defaults are placeholders; override from config."""

    input_per_million: float = 0.27
    cached_input_per_million: float = 0.07
    output_per_million: float = 1.10
    reasoning_per_million: float = 1.10


DEFAULT_RATES = PricingRates()


def cost_for(usage: TokenUsage, rates: PricingRates = DEFAULT_RATES) -> float:
    """USD cost of one or more calls' aggregate usage."""
    fresh_input = max(0, usage.input_tokens - usage.cached_input_tokens)
    return (
        fresh_input * rates.input_per_million / 1_000_000
        + usage.cached_input_tokens * rates.cached_input_per_million / 1_000_000
        + usage.output_tokens * rates.output_per_million / 1_000_000
        + usage.reasoning_tokens * rates.reasoning_per_million / 1_000_000
    )


@dataclass
class CostLedger:
    """Running tally of token usage and dollars spent."""

    rates: PricingRates = field(default_factory=lambda: DEFAULT_RATES)
    total: TokenUsage = field(default_factory=TokenUsage)
    calls: int = 0

    def record(self, usage: TokenUsage) -> float:
        """Accumulate a single call's usage; return its incremental cost."""
        self.calls += 1
        self.total.input_tokens += usage.input_tokens
        self.total.output_tokens += usage.output_tokens
        self.total.cached_input_tokens += usage.cached_input_tokens
        self.total.reasoning_tokens += usage.reasoning_tokens
        return cost_for(usage, self.rates)

    @property
    def total_cost(self) -> float:
        return cost_for(self.total, self.rates)

    def summary(self) -> dict:
        return {
            "calls": self.calls,
            "input_tokens": self.total.input_tokens,
            "cached_input_tokens": self.total.cached_input_tokens,
            "output_tokens": self.total.output_tokens,
            "reasoning_tokens": self.total.reasoning_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "rates": {
                "input_per_million": self.rates.input_per_million,
                "cached_input_per_million": self.rates.cached_input_per_million,
                "output_per_million": self.rates.output_per_million,
                "reasoning_per_million": self.rates.reasoning_per_million,
            },
        }
