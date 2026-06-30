from __future__ import annotations

import pytest

from agent_runtime import LoopLimits


def test_limit_validation() -> None:
    with pytest.raises(ValueError, match="max_iterations"):
        LoopLimits(max_iterations=0).validate()

    with pytest.raises(ValueError, match="max_total_tool_calls"):
        LoopLimits(max_total_tool_calls=-1).validate()

    with pytest.raises(ValueError, match="timeout_seconds"):
        LoopLimits(timeout_seconds=0).validate()

    with pytest.raises(ValueError, match="max_parallel_tool_calls"):
        LoopLimits(max_parallel_tool_calls=0).validate()
