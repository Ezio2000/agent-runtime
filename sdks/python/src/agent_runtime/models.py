"""Model client protocol."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

from agent_runtime.messages import Message, ModelResponse
from agent_runtime.runtime import RuntimeContext
from agent_runtime.tools import ToolSpec


def _empty_metadata() -> Mapping[str, Any]:
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


def _expect_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return cast(Mapping[str, Any], value)


@dataclass(slots=True)
class ModelRequest:
    """Model-neutral request passed to model adapters."""

    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=_empty_metadata)
    extra: Mapping[str, Any] = field(default_factory=_empty_metadata)

    def __post_init__(self) -> None:
        self.messages = tuple(Message.from_dict(message.to_dict()) for message in self.messages)
        self.tools = tuple(ToolSpec.from_dict(tool.to_dict()) for tool in self.tools)
        self.metadata = _copy_mapping(self.metadata)
        self.extra = _copy_extra(
            self.extra,
            {"messages", "tools", "metadata"},
            "model request",
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ModelRequest:
        known = {"messages", "tools", "metadata"}
        return cls(
            messages=tuple(
                Message.from_dict(_expect_mapping(message, "model request message"))
                for message in cast(Sequence[object], value.get("messages") or ())
            ),
            tools=tuple(
                ToolSpec.from_dict(_expect_mapping(tool, "model request tool"))
                for tool in cast(Sequence[object], value.get("tools") or ())
            ),
            metadata=_expect_mapping(value.get("metadata") or {}, "model request metadata"),
            extra={key: deepcopy(item) for key, item in value.items() if key not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "messages": [message.to_dict() for message in self.messages],
            "tools": [tool.to_dict() for tool in self.tools],
        }
        if self.metadata:
            data["metadata"] = _copy_mapping(self.metadata)
        data.update(
            _copy_extra(
                self.extra,
                {"messages", "tools", "metadata"},
                "model request",
            )
        )
        return data


class ModelClient(Protocol):
    """Protocol implemented by model adapters."""

    async def complete(self, request: ModelRequest, context: RuntimeContext) -> ModelResponse:
        """Return the next model decision."""
        ...
