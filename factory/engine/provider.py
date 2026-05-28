"""Model provider abstraction.

The engine talks to LLMs only through ``ModelProvider``. ``MockProvider`` is
deterministic and used in tests; ``DeepSeekFlashProvider`` wraps DeepSeek's
OpenAI-compatible HTTP API (base ``https://api.deepseek.com``). Exact numeric
limits (context, max output) are treated as backend config, not hardcoded.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional

from .schemas import Completion, TokenUsage


class ProviderError(RuntimeError):
    """Raised when a provider cannot fulfill a call."""


class ModelProvider(ABC):
    """Abstract LLM provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier of the provider implementation (for provenance)."""

    @property
    @abstractmethod
    def model(self) -> str:
        """The model id the provider is configured to call."""

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        prompt: str,
        thinking: bool = True,
        max_tokens: int | None = None,
    ) -> Completion:
        """Run a single completion. Implementations must populate ``Completion.usage``."""


class MockProvider(ModelProvider):
    """Offline, deterministic provider for tests.

    Round-robins through ``responses``; estimates tokens by character count.
    """

    def __init__(
        self,
        responses: Optional[list[str]] = None,
        *,
        model: str = "mock-1",
    ) -> None:
        self._responses = list(responses) if responses else ["mock response"]
        self._idx = 0
        self._model = model
        self.calls: list[dict[str, str]] = []

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        thinking: bool = True,
        max_tokens: int | None = None,
    ) -> Completion:
        self.calls.append({"system": system, "prompt": prompt})
        text = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        if max_tokens is not None and max_tokens > 0:
            # crude char->token simulation
            text = text[: max_tokens * 4]
        usage = TokenUsage(
            input_tokens=max(1, (len(system) + len(prompt)) // 4),
            output_tokens=max(1, len(text) // 4),
            cached_input_tokens=0,
            reasoning_tokens=(max(1, len(text) // 8) if thinking else 0),
        )
        return Completion(text=text, usage=usage, model=self._model)


class DeepSeekFlashProvider(ModelProvider):
    """DeepSeek-V4-Flash via the OpenAI-compatible API.

    - Base URL: ``https://api.deepseek.com``
    - Default model: ``deepseek-v4-flash``
    - API key: ``DEEPSEEK_API_KEY`` (never logged, never printed)
    - Thinking mode is on by default. Caller may disable per-call.
    - Designed for cache-friendly prompting (callers should keep the
      ``system`` prompt stable across calls to maximise cache hits).
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-v4-flash"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - tested indirectly
            raise ProviderError(
                "openai package required for DeepSeekFlashProvider"
            ) from exc

        key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise ProviderError("DEEPSEEK_API_KEY not set")

        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._model = model or self.DEFAULT_MODEL
        self._client = OpenAI(
            api_key=key,
            base_url=self._base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        thinking: bool = True,
        max_tokens: int | None = None,
    ) -> Completion:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        kwargs: dict = {"model": self._model, "messages": messages, "stream": False}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if not thinking:
            # DeepSeek thinking-mode toggle. Tolerated via extra_body; ignored
            # by servers that don't recognise it.
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

        try:
            resp = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise ProviderError(f"deepseek call failed: {type(exc).__name__}") from exc

        if not resp.choices:
            raise ProviderError("deepseek returned no choices")

        choice = resp.choices[0]
        text = (choice.message.content or "") if choice.message else ""
        reasoning = getattr(choice.message, "reasoning_content", None) if choice.message else None

        usage = TokenUsage()
        if resp.usage:
            usage.input_tokens = int(getattr(resp.usage, "prompt_tokens", 0) or 0)
            usage.output_tokens = int(getattr(resp.usage, "completion_tokens", 0) or 0)
            usage.cached_input_tokens = int(
                getattr(resp.usage, "prompt_cache_hit_tokens", 0) or 0
            )
            details = getattr(resp.usage, "completion_tokens_details", None)
            if details is not None:
                usage.reasoning_tokens = int(getattr(details, "reasoning_tokens", 0) or 0)

        return Completion(
            text=text,
            reasoning=reasoning,
            usage=usage,
            model=self._model,
            finish_reason=(choice.finish_reason or "stop"),
        )
