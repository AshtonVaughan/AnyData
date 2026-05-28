"""Phase 1 probe.

Calls MockProvider (always) and DeepSeekFlashProvider (when DEEPSEEK_API_KEY is
set), runs each through CostLedger, and prints the result. Never prints, logs,
or otherwise leaks the API key.

Run:
    python -m scripts.probe_provider
"""

from __future__ import annotations

import os
import sys
import traceback

from factory.engine.cost import CostLedger
from factory.engine.provider import (
    DeepSeekFlashProvider,
    MockProvider,
    ProviderError,
)


SYSTEM = "You are a math tutor. Reply with only a single number."
PROMPT = "What is 7 * 8?"


def probe_mock(ledger: CostLedger) -> None:
    p = MockProvider(responses=["56"])
    c = p.complete(system=SYSTEM, prompt=PROMPT, thinking=False, max_tokens=8)
    spent = ledger.record(c.usage)
    print(
        f"[mock]     text={c.text!r}  usage={c.usage.model_dump()}  cost=${spent:.6f}"
    )


def probe_deepseek(ledger: CostLedger) -> None:
    key_present = bool(os.environ.get("DEEPSEEK_API_KEY"))
    if not key_present:
        print("[deepseek] SKIPPED (DEEPSEEK_API_KEY not set in environment)")
        return
    try:
        p = DeepSeekFlashProvider()
    except ProviderError as exc:
        print(f"[deepseek] could not construct provider: {exc}")
        return
    except Exception:
        print("[deepseek] unexpected error constructing provider:")
        traceback.print_exc()
        return

    try:
        c = p.complete(system=SYSTEM, prompt=PROMPT, thinking=False, max_tokens=32)
    except ProviderError as exc:
        print(f"[deepseek] live call failed: {exc}")
        return
    except Exception:
        print("[deepseek] unexpected error on live call:")
        traceback.print_exc()
        return

    spent = ledger.record(c.usage)
    print(
        f"[deepseek] model={p.model}  text={c.text!r}  "
        f"usage={c.usage.model_dump()}  cost=${spent:.6f}"
    )


def main() -> int:
    ledger = CostLedger()
    probe_mock(ledger)
    probe_deepseek(ledger)
    print("\n--- ledger summary ---")
    for k, v in ledger.summary().items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
