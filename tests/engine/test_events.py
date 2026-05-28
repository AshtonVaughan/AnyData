from __future__ import annotations

from factory.engine.events import (
    EventBus,
    LogMessage,
    RunFinished,
    RunStarted,
)


def test_pubsub_delivers_in_order() -> None:
    bus = EventBus()
    received: list = []
    bus.subscribe(received.append)
    bus.publish(LogMessage(level="info", text="hi"))
    bus.publish(RunStarted(run_id="r1", pack_name="p", target_tokens=100))
    bus.publish(RunFinished(run_id="r1", accepted=10, rejected=2, cost_usd=0.5))
    assert len(received) == 3
    assert isinstance(received[0], LogMessage)
    assert received[1].pack_name == "p"
    assert received[2].cost_usd == 0.5


def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus()
    received: list = []
    cancel = bus.subscribe(received.append)
    cancel()
    bus.publish(LogMessage(text="x"))
    assert received == []


def test_subscriber_exception_is_isolated() -> None:
    bus = EventBus()
    received: list = []

    def angry(_event: object) -> None:
        raise RuntimeError("boom")

    bus.subscribe(angry)
    bus.subscribe(received.append)
    bus.publish(LogMessage(text="x"))
    assert len(received) == 1


def test_multiple_subscribers_each_get_event() -> None:
    bus = EventBus()
    a: list = []
    b: list = []
    bus.subscribe(a.append)
    bus.subscribe(b.append)
    bus.publish(LogMessage(text="hello"))
    assert len(a) == 1
    assert len(b) == 1
