from __future__ import annotations

from typing import Any

import pytest

from agent_runtime import (
    AgentLoop,
    ContentPart,
    Message,
    ModelRequest,
    ModelResponse,
    RuntimeContext,
    ToolCall,
    ToolResult,
    ToolSpec,
)


class InspectingModel:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_messages: list[Message] = []

    async def complete(self, request: ModelRequest, context: RuntimeContext) -> ModelResponse:
        _ = context
        self.calls += 1
        self.seen_messages = list(request.messages)
        if self.calls == 1:
            assert request.messages[-1].parts[0].type == "text"
            assert request.messages[-1].parts[1].type == "image"
            return ModelResponse(tool_calls=[ToolCall(id="call-1", name="make_file", arguments={})])
        return ModelResponse(
            parts=[
                ContentPart.text_part("Generated file."),
                ContentPart.file_ref(
                    "artifact-1",
                    media_type="text/csv",
                    name="data.csv",
                ),
            ]
        )


class FileTool:
    spec = ToolSpec(
        name="make_file",
        description="Return a generated file artifact.",
        input_schema={"type": "object", "properties": {}},
    )

    async def execute(self, arguments: dict[str, Any], context: RuntimeContext) -> ToolResult:
        _ = arguments, context
        return ToolResult(
            parts=[
                ContentPart.text_part("created"),
                ContentPart.file_ref("artifact-tool-1", media_type="text/csv", name="tool.csv"),
            ]
        )


@pytest.mark.asyncio
async def test_multimodal_user_message_and_file_result() -> None:
    model = InspectingModel()
    result = await AgentLoop(model=model, tools=[FileTool()]).run(
        [
            Message.user(
                [
                    ContentPart.text_part("Analyze this image"),
                    ContentPart.image_uri(
                        "https://example.com/car.png",
                        media_type="image/png",
                        name="car.png",
                    ),
                ]
            )
        ]
    )

    assert result.messages[0].to_dict()["parts"][1]["type"] == "image"
    assert result.messages[-2].role == "tool"
    assert result.messages[-2].parts[1].type == "file"
    assert result.final_parts[1].type == "file"
    assert result.final_parts[1].ref == "artifact-1"


def test_custom_content_part_round_trip_preserves_extra_fields() -> None:
    part = ContentPart.from_dict(
        {
            "type": "audio",
            "ref": "artifact-audio-1",
            "media_type": "audio/wav",
            "provider_cache_control": {"ttl": 60},
        }
    )

    assert part.type == "audio"
    assert part.to_dict()["provider_cache_control"] == {"ttl": 60}


def test_model_response_extra_is_preserved_on_assistant_message() -> None:
    response = ModelResponse.text("hello")
    response.extra = {"provider_state": {"cursor": "abc"}}

    message = response.to_assistant_message()

    assert message.to_dict()["provider_state"] == {"cursor": "abc"}


def test_tool_result_extra_is_preserved_on_tool_message() -> None:
    result = ToolResult.text("created", is_error=False)
    result.extra = {"artifact_state": {"id": "a1"}}

    message = result.to_message(ToolCall(id="call-1", name="tool"))

    assert message.to_dict()["artifact_state"] == {"id": "a1"}


def test_extra_fields_cannot_override_reserved_protocol_fields() -> None:
    with pytest.raises(ValueError, match="reserved"):
        ContentPart.text_part("hello", extra={"type": "image"})

    with pytest.raises(ValueError, match="reserved"):
        Message.assistant_text("hello", extra={"role": "user"})

    with pytest.raises(ValueError, match="reserved"):
        ModelResponse(parts=[ContentPart.text_part("hello")], extra={"parts": []})

    response = ModelResponse.text("hello")
    response.extra = {"parts": []}
    with pytest.raises(ValueError, match="reserved"):
        response.to_dict()

    request = ModelRequest(messages=(Message.user_text("hello"),))
    request.extra = {"messages": []}
    with pytest.raises(ValueError, match="reserved"):
        request.to_dict()
