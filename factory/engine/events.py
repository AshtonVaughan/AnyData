"""Plain-Python event objects + a synchronous in-process bus.

This module is deliberately Qt-free. The GUI's ``factory.gui.bridge`` subscribes
to the bus and re-emits each event as a Qt signal -- that is how the engine
drives a live UI without ever importing PySide6.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Event:
    ts: datetime = field(default_factory=_utcnow)


# Lifecycle ------------------------------------------------------------------


@dataclass(frozen=True)
class RunStarted(Event):
    run_id: str = ""
    pack_name: str = ""
    target_tokens: int = 0


@dataclass(frozen=True)
class RunFinished(Event):
    run_id: str = ""
    accepted: int = 0
    rejected: int = 0
    cost_usd: float = 0.0


@dataclass(frozen=True)
class RunPaused(Event):
    run_id: str = ""


@dataclass(frozen=True)
class RunResumed(Event):
    run_id: str = ""


# Per-item -------------------------------------------------------------------


@dataclass(frozen=True)
class TaskGenerated(Event):
    task_id: str = ""
    skill_id: str = ""


@dataclass(frozen=True)
class CandidateGenerated(Event):
    task_id: str = ""
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass(frozen=True)
class CandidateVerified(Event):
    task_id: str = ""
    passed: bool = False
    signal_strength: float = 0.0


@dataclass(frozen=True)
class RecordStored(Event):
    record_id: str = ""
    skill_id: str = ""


@dataclass(frozen=True)
class CandidateRejected(Event):
    task_id: str = ""
    reason: str = ""


# Aggregates -----------------------------------------------------------------


@dataclass(frozen=True)
class CoverageUpdated(Event):
    leaves_total: int = 0
    leaves_covered: int = 0
    samples_per_leaf: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class CostUpdated(Event):
    total_cost_usd: float = 0.0
    calls: int = 0


# Human-in-the-loop ----------------------------------------------------------


@dataclass(frozen=True)
class AuditQueued(Event):
    record_id: str = ""
    task_id: str = ""


@dataclass(frozen=True)
class AuditDecided(Event):
    record_id: str = ""
    decision: str = ""


# General log ----------------------------------------------------------------


@dataclass(frozen=True)
class LogMessage(Event):
    level: str = "info"
    text: str = ""


Subscriber = Callable[[Event], None]


class EventBus:
    """Synchronous in-process pub/sub. Thread-safety is the caller's concern;
    the orchestrator publishes from one thread and the GUI bridge marshals
    onto the Qt event loop via queued signals."""

    def __init__(self) -> None:
        self._subs: list[Subscriber] = []

    def subscribe(self, fn: Subscriber) -> Callable[[], None]:
        self._subs.append(fn)

        def unsubscribe() -> None:
            try:
                self._subs.remove(fn)
            except ValueError:
                pass

        return unsubscribe

    def publish(self, event: Event) -> None:
        # Copy so a subscriber can unsubscribe during iteration without
        # mutating the live list.
        for fn in list(self._subs):
            try:
                fn(event)
            except Exception:
                # Subscribers must not be able to crash the engine. A logging
                # subscriber can capture these, but the bus stays alive.
                continue
