# AnyData Factory

A closed-loop, domain-agnostic dataset factory. One command names a domain;
the system generates candidate examples, verifies each one's correctness,
grades and dedupes them, curates for coverage, and writes a versioned dataset
with provenance, evidence, and cost.

## The one principle that shapes everything

A dataset's quality is capped by how strongly each example's correctness can
be **verified**. Every Domain Pack declares a verification *tier*:

| Tier          | Correctness signal                                         | Autonomy | Human review     |
|---------------|------------------------------------------------------------|----------|------------------|
| `EXECUTABLE`  | it runs / passes tests (code, SQL, scripts)                | full     | calibration only |
| `CHECKABLE`   | matches a spec / property / independently recomputed answer| full     | calibration only |
| `COMPARATIVE` | independent methods or models agree                        | partial  | mandatory %      |
| `JUDGMENT`    | no oracle; subjective quality                              | low      | mandatory %      |

**Anti-collapse rule:** a model may never be the sole grader of its own
output. Packs declaring `COMPARATIVE` or `JUDGMENT` are rejected at load
time if `human_review_pct == 0`.

## Layout

```
factory/
  engine/        # headless core - NO Qt imports, ever
  packs/         # reference + user-authored domain packs
  cli/           # `factory` entry point
  gui/           # `factory-gui` (PySide6) - the only place Qt is imported
tests/
  engine/        # headless tests (incl. a grep test for engine purity)
config/
  default.yaml   # backend, budgets, concurrency, review %, pricing
scripts/
  probe_provider.py   # Phase 1 verification
```

## Status

- [x] Phase 1 - engine skeleton: schemas, provider abstraction with
      DeepSeekFlashProvider + MockProvider, domain ABC + registry +
      anti-collapse validation, cost ledger, event bus.
- [ ] Phase 2 - planner / generator / verifier / grader / curator /
      orchestrator + `arithmetic` pack (CHECKABLE).
- [ ] Phase 3 - `python_snippets` pack (EXECUTABLE) + sandbox.
- [ ] Phase 4 - PySide6 / Qt 6.7+ control panel.
- [ ] Phase 5 - domain-pack authoring guide + template.

## Backend

Default backend is DeepSeek-V4-Flash via the OpenAI-compatible HTTP API
(`https://api.deepseek.com`). The API key is read from `DEEPSEEK_API_KEY`
and is never logged, stored, or displayed.

Cache-friendly: keep `system` prompts stable across calls so most input
bills at the cache-hit rate.

## Development

```bash
pip install -e ".[dev]"
pytest tests/
python -m scripts.probe_provider
```

The engine-purity test (`tests/engine/test_engine_purity.py`) fails if any
file under `factory/engine/` imports PySide6 or PyQt.
