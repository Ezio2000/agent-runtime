"""Serializable run checkpoint protocol."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from agent_runtime.runtime import RuntimeContext
from agent_runtime.state import AgentState


@dataclass(slots=True, frozen=True)
class RunSnapshot:
    """Durable run checkpoint owned by host persistence."""

    state: AgentState
    context: RuntimeContext

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RunSnapshot:
        return cls(
            state=AgentState.from_dict(cast(dict[str, Any], value["state"])),
            context=RuntimeContext.from_dict(cast(Mapping[str, Any], value["context"])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "context": self.context.to_dict(),
        }
