"""Tool protocol and registry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

from agent_runtime.errors import DuplicateToolError, InvalidToolCall
from agent_runtime.messages import ContentPart, Message, ToolCall, content_parts_summary
from agent_runtime.runtime import RuntimeContext


def _empty_mapping() -> Mapping[str, Any]:
    return {}


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _expect_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return cast(Mapping[str, Any], value)


def _copy_extra(value: Mapping[str, Any] | None, reserved: set[str], label: str) -> dict[str, Any]:
    extra = _copy_mapping(value)
    conflicts = reserved & extra.keys()
    if conflicts:
        names = ", ".join(sorted(conflicts))
        raise ValueError(f"{label} extra cannot override reserved field(s): {names}")
    return extra


@dataclass(slots=True)
class ToolSpec:
    """Model-neutral tool contract exposed to model adapters."""

    name: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any] | None = None
    annotations: Mapping[str, Any] = field(default_factory=_empty_mapping)
    metadata: Mapping[str, Any] = field(default_factory=_empty_mapping)
    extra: Mapping[str, Any] = field(default_factory=_empty_mapping)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("tool name must not be empty")
        if not self.description:
            raise ValueError("tool description must not be empty")
        self.input_schema = _copy_mapping(self.input_schema)
        if self.output_schema is not None:
            self.output_schema = _copy_mapping(self.output_schema)
        self.annotations = _copy_mapping(self.annotations)
        self.metadata = _copy_mapping(self.metadata)
        self.extra = _copy_extra(
            self.extra,
            {"name", "description", "input_schema", "output_schema", "annotations", "metadata"},
            "tool spec",
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ToolSpec:
        known = {
            "name",
            "description",
            "input_schema",
            "output_schema",
            "annotations",
            "metadata",
        }
        output_schema = value.get("output_schema")
        return cls(
            name=str(value["name"]),
            description=str(value["description"]),
            input_schema=_expect_mapping(value["input_schema"], "tool input_schema"),
            output_schema=None
            if output_schema is None
            else _expect_mapping(output_schema, "tool output_schema"),
            annotations=_expect_mapping(value.get("annotations") or {}, "tool annotations"),
            metadata=_expect_mapping(value.get("metadata") or {}, "tool metadata"),
            extra={key: deepcopy(item) for key, item in value.items() if key not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "input_schema": _copy_mapping(self.input_schema),
        }
        if self.output_schema is not None:
            data["output_schema"] = _copy_mapping(self.output_schema)
        if self.annotations:
            data["annotations"] = _copy_mapping(self.annotations)
        if self.metadata:
            data["metadata"] = _copy_mapping(self.metadata)
        data.update(
            _copy_extra(
                self.extra,
                {"name", "description", "input_schema", "output_schema", "annotations", "metadata"},
                "tool spec",
            )
        )
        return data


@dataclass(slots=True)
class ToolResult:
    """Normalized tool result."""

    parts: list[ContentPart]
    metadata: Mapping[str, Any] = field(default_factory=_empty_mapping)
    is_error: bool = False
    extra: Mapping[str, Any] = field(default_factory=_empty_mapping)

    def __post_init__(self) -> None:
        self.parts = [ContentPart.from_dict(part.to_dict()) for part in self.parts]
        self.metadata = _copy_mapping(self.metadata)
        self.extra = _copy_extra(
            self.extra,
            {"parts", "metadata", "is_error"},
            "tool result",
        )

    @classmethod
    def text(
        cls,
        text: str,
        *,
        metadata: Mapping[str, Any] | None = None,
        is_error: bool = False,
    ) -> ToolResult:
        return cls(
            parts=[ContentPart.text_part(text)],
            metadata=metadata or {},
            is_error=is_error,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ToolResult:
        known = {"parts", "metadata", "is_error"}
        return cls(
            parts=[
                ContentPart.from_dict(_expect_mapping(part, "tool result part"))
                for part in cast(Sequence[object], value.get("parts") or ())
            ],
            metadata=_expect_mapping(value.get("metadata") or {}, "tool result metadata"),
            is_error=bool(value.get("is_error", False)),
            extra={key: deepcopy(item) for key, item in value.items() if key not in known},
        )

    def to_message(self, call: ToolCall) -> Message:
        metadata: dict[str, Any] = {}
        if self.is_error:
            metadata["is_error"] = True
        if self.metadata:
            metadata["result_metadata"] = _copy_mapping(self.metadata)
        return Message.tool(self.parts, call.id, metadata=metadata, extra=self.extra)

    @property
    def text_content(self) -> str:
        return "".join(part.text or "" for part in self.parts if part.type == "text")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "parts": [part.to_dict() for part in self.parts],
            "is_error": self.is_error,
        }
        if self.metadata:
            data["metadata"] = _copy_mapping(self.metadata)
        data.update(
            _copy_extra(
                self.extra,
                {"parts", "metadata", "is_error"},
                "tool result",
            )
        )
        return data

    def summary(self) -> dict[str, Any]:
        return content_parts_summary(self.parts) | {
            "is_error": self.is_error,
            "metadata": _copy_mapping(self.metadata),
        }


class Tool(Protocol):
    """Protocol implemented by runtime tools."""

    spec: ToolSpec

    async def execute(self, arguments: dict[str, Any], context: RuntimeContext) -> ToolResult:
        """Execute the tool."""
        ...


class ToolRegistry:
    """O(1) tool lookup with cached model-neutral specs."""

    __slots__ = ("_specs", "_tools")

    _specs: tuple[ToolSpec, ...]
    _tools: dict[str, Tool]

    def __init__(self, tools: Sequence[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        if tools:
            for tool in tools:
                self._register_without_rebuild(tool)
        self._specs = self._build_specs()

    def register(self, tool: Tool) -> None:
        self._register_without_rebuild(tool)
        self._specs = self._build_specs()

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(ToolSpec.from_dict(spec.to_dict()) for spec in self._specs)

    def spec_for(self, name: str) -> ToolSpec | None:
        tool = self._tools.get(name)
        if tool is None:
            return None
        return ToolSpec.from_dict(tool.spec.to_dict())

    async def execute(self, call: ToolCall, context: RuntimeContext) -> ToolResult:
        tool = self._tools.get(call.name)
        if tool is None:
            raise InvalidToolCall(f"unknown tool: {call.name}")
        return await tool.execute(deepcopy(dict(call.arguments)), context)

    def _register_without_rebuild(self, tool: Tool) -> None:
        spec = ToolSpec.from_dict(tool.spec.to_dict())
        if spec.name in self._tools:
            raise DuplicateToolError(f"duplicate tool name: {spec.name}")
        self._tools[spec.name] = tool

    def _build_specs(self) -> tuple[ToolSpec, ...]:
        return tuple(ToolSpec.from_dict(tool.spec.to_dict()) for tool in self._tools.values())
