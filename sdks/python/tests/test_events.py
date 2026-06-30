from __future__ import annotations

from agent_runtime import AgentEvent, EventTypes


def test_event_to_dict() -> None:
    event = AgentEvent(
        EventTypes.MODEL_STARTED,
        {"iteration": 1},
        run_id="run-1",
        sequence=7,
        created_at=1.5,
    )

    assert event.to_dict() == {
        "type": "model_started",
        "data": {"iteration": 1},
        "run_id": "run-1",
        "sequence": 7,
        "created_at": 1.5,
        "schema_version": "v0",
    }


def test_custom_event_type_is_allowed() -> None:
    event = AgentEvent("memory_compacted", {"tokens": 120})

    assert event.type == "memory_compacted"
