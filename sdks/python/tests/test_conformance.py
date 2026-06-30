from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from agent_runtime import (
    AgentLoop,
    AgentStatus,
    ContentPart,
    EventTypes,
    LoopLimits,
    Message,
    ModelRequest,
    ModelResponse,
    RunSnapshot,
    RuntimeContext,
    ToolCall,
    ToolResult,
    ToolSpec,
)


class ScriptedModel:
    def __init__(self, steps: Sequence[ModelResponse]) -> None:
        self._steps = list(steps)
        self.calls = 0

    async def complete(self, request: ModelRequest, context: RuntimeContext) -> ModelResponse:
        _ = request, context
        if self.calls >= len(self._steps):
            return ModelResponse.text("fallback")
        response = self._steps[self.calls]
        self.calls += 1
        return response


class EchoTool:
    spec = ToolSpec(
        name="echo",
        description="Return input text.",
        input_schema={"type": "object", "properties": {}},
    )

    async def execute(self, arguments: dict[str, Any], context: RuntimeContext) -> ToolResult:
        _ = context
        return ToolResult.text(str(arguments.get("text", "")))


class FailTool:
    spec = ToolSpec(
        name="fail",
        description="Raise an error.",
        input_schema={"type": "object", "properties": {}},
    )

    async def execute(self, arguments: dict[str, Any], context: RuntimeContext) -> ToolResult:
        _ = arguments, context
        raise RuntimeError("tool failed")


class DelayedEchoTool:
    spec = ToolSpec(
        name="delayed_echo",
        description="Return input text after an optional delay.",
        input_schema={"type": "object", "properties": {}},
        annotations={"parallel_safe": True, "read_only": True, "idempotent": True},
    )

    async def execute(self, arguments: dict[str, Any], context: RuntimeContext) -> ToolResult:
        _ = context
        await asyncio.sleep(float(arguments.get("delay", 0)))
        return ToolResult.text(str(arguments.get("text", "")))


CASES_DIR = Path(__file__).resolve().parents[3] / "conformance" / "cases"


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in sorted(CASES_DIR.glob("*.json"))]


def content_part_from_case(part: dict[str, Any]) -> ContentPart:
    return ContentPart.from_dict(part)


def model_response_from_case_step(step: dict[str, Any]) -> ModelResponse:
    calls = [ToolCall.from_dict(call) for call in step.get("tool_calls", [])]
    parts = [
        content_part_from_case(part) for part in cast(list[dict[str, Any]], step.get("parts", []))
    ]
    return ModelResponse(parts=parts, tool_calls=calls)


def limits_from_case(case: dict[str, Any]) -> LoopLimits:
    raw_limits = cast(dict[str, Any], case.get("limits") or {})
    return LoopLimits(
        max_iterations=int(raw_limits.get("max_iterations", 8)),
        max_total_tool_calls=int(raw_limits.get("max_total_tool_calls", 20)),
        timeout_seconds=cast(float | None, raw_limits.get("timeout_seconds")),
        max_parallel_tool_calls=int(raw_limits.get("max_parallel_tool_calls", 1)),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", load_cases(), ids=lambda case: str(case["name"]))
async def test_conformance_case(case: dict[str, Any]) -> None:
    steps = [model_response_from_case_step(step) for step in case["model_steps"]]
    result = await AgentLoop(
        model=ScriptedModel(steps),
        tools=[EchoTool(), FailTool(), DelayedEchoTool()],
        limits=limits_from_case(case),
    ).run([Message.user_text("run conformance case")])

    assert result.status is AgentStatus(case["expected_status"])
    assert result.total_tool_calls == case["expected_tool_calls"]
    if "expected_final_text" in case:
        assert (
            "".join(part.text or "" for part in result.final_parts) == case["expected_final_text"]
        )
    if "expected_tool_texts" in case:
        assert [message.text for message in result.messages if message.role == "tool"] == case[
            "expected_tool_texts"
        ]
    if "forbidden_checkpoint_tool_counts" in case:
        events = [
            event
            async for event in AgentLoop(
                model=ScriptedModel(steps),
                tools=[EchoTool(), FailTool(), DelayedEchoTool()],
                limits=limits_from_case(case),
            ).run_events([Message.user_text("run conformance case")])
        ]
        forbidden = set(cast(list[int], case["forbidden_checkpoint_tool_counts"]))
        checkpoint_counts = [
            RunSnapshot.from_dict(event.data).state.total_tool_calls
            for event in events
            if event.type == EventTypes.CHECKPOINT
        ]
        assert not (forbidden & set(checkpoint_counts))
