"""Agent state types."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast

from agent_runtime.messages import ContentPart, Message, ToolCall


def _empty_pending_tool_calls() -> list[ToolCall]:
    return []


def _empty_final_parts() -> list[ContentPart]:
    return []


def _empty_mapping() -> Mapping[str, Any]:
    return {}


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _copy_extra(value: Mapping[str, Any] | None, reserved: set[str], label: str) -> dict[str, Any]:
    extra = _copy_mapping(value)
    conflicts = reserved & extra.keys()
    if conflicts:
        names = ", ".join(sorted(conflicts))
        raise ValueError(f"{label} extra cannot override reserved field(s): {names}")
    return extra


class AgentStatus(StrEnum):
    PLANNING = "planning"
    EXECUTING_TOOLS = "executing_tools"
    COMPLETED = "completed"
    FAILED = "failed"
    LIMIT_EXCEEDED = "limit_exceeded"


TERMINAL_STATUSES = {
    AgentStatus.COMPLETED,
    AgentStatus.FAILED,
    AgentStatus.LIMIT_EXCEEDED,
}


@dataclass(slots=True)
class AgentState:
    """Mutable working state owned by AgentLoop."""

    status: AgentStatus
    messages: list[Message]
    pending_tool_calls: list[ToolCall] = field(default_factory=_empty_pending_tool_calls)
    iterations: int = 0
    total_tool_calls: int = 0
    final_parts: list[ContentPart] = field(default_factory=_empty_final_parts)
    error: str | None = None
    extra: Mapping[str, Any] = field(default_factory=_empty_mapping)

    def __post_init__(self) -> None:
        self.extra = _copy_extra(
            self.extra,
            {
                "status",
                "messages",
                "pending_tool_calls",
                "iterations",
                "total_tool_calls",
                "final_parts",
                "error",
            },
            "agent state",
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AgentState:
        known = {
            "status",
            "messages",
            "pending_tool_calls",
            "iterations",
            "total_tool_calls",
            "final_parts",
            "error",
        }
        return cls(
            status=AgentStatus(str(value["status"])),
            messages=[
                Message.from_dict(cast(dict[str, Any], message))
                for message in cast(list[object], value.get("messages") or [])
            ],
            pending_tool_calls=[
                ToolCall.from_dict(cast(dict[str, Any], call))
                for call in cast(list[object], value.get("pending_tool_calls") or [])
            ],
            iterations=int(value.get("iterations", 0)),
            total_tool_calls=int(value.get("total_tool_calls", 0)),
            final_parts=[
                ContentPart.from_dict(cast(dict[str, Any], part))
                for part in cast(list[object], value.get("final_parts") or [])
            ],
            error=cast(str | None, value.get("error")),
            extra={key: deepcopy(item) for key, item in value.items() if key not in known},
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message_count": len(self.messages),
            "pending_tool_call_count": len(self.pending_tool_calls),
            "iterations": self.iterations,
            "total_tool_calls": self.total_tool_calls,
            "has_final": bool(self.final_parts),
            "error": self.error,
        }

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status.value,
            "messages": [message.to_dict() for message in self.messages],
            "pending_tool_calls": [call.to_dict() for call in self.pending_tool_calls],
            "iterations": self.iterations,
            "total_tool_calls": self.total_tool_calls,
            "final_parts": [part.to_dict() for part in self.final_parts],
            "error": self.error,
        }
        data.update(
            _copy_extra(
                self.extra,
                {
                    "status",
                    "messages",
                    "pending_tool_calls",
                    "iterations",
                    "total_tool_calls",
                    "final_parts",
                    "error",
                },
                "agent state",
            )
        )
        return data
