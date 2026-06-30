from __future__ import annotations

from typing import Any, cast

import pytest

from agent_runtime import RuntimeContext, ToolCall, ToolRegistry, ToolResult, ToolSpec
from agent_runtime.errors import DuplicateToolError


class EchoTool:
    spec = ToolSpec(
        name="echo",
        description="Return input text.",
        input_schema={"type": "object", "properties": {}},
    )

    async def execute(self, arguments: dict[str, Any], context: RuntimeContext) -> ToolResult:
        _ = context
        return ToolResult.text(str(arguments.get("text", "")))


class MutatingTool:
    spec = ToolSpec(
        name="mutate",
        description="Mutate arguments.",
        input_schema={"type": "object", "properties": {}},
    )

    async def execute(self, arguments: dict[str, Any], context: RuntimeContext) -> ToolResult:
        _ = context
        arguments["changed"] = True
        return ToolResult.text("ok")


def test_tool_specs_are_defensive_copies() -> None:
    registry = ToolRegistry([EchoTool()])

    first = registry.specs()
    second = registry.specs()
    assert first is not second
    assert first[0].name == "echo"
    cast(dict[str, Any], first[0].input_schema)["mutated"] = True
    assert "mutated" not in registry.specs()[0].input_schema


def test_duplicate_tool_name_rejected() -> None:
    with pytest.raises(DuplicateToolError):
        ToolRegistry([EchoTool(), EchoTool()])


@pytest.mark.asyncio
async def test_tool_arguments_are_defensive_copies() -> None:
    call = ToolCall(id="call-1", name="mutate", arguments={"value": 1})
    result = await ToolRegistry([MutatingTool()]).execute(call, RuntimeContext())

    assert result.text_content == "ok"
    assert call.arguments == {"value": 1}
