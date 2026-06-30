"""Loop limit configuration."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from agent_runtime.state import AgentState


@dataclass(slots=True, frozen=True)
class LoopLimits:
    """Resource limits for a single agent run."""

    max_iterations: int = 8
    max_total_tool_calls: int = 20
    timeout_seconds: float | None = None
    stop_on_tool_error: bool = False
    max_parallel_tool_calls: int = 1

    def validate(self) -> None:
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.max_total_tool_calls < 0:
            raise ValueError("max_total_tool_calls must be >= 0")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if self.max_parallel_tool_calls < 1:
            raise ValueError("max_parallel_tool_calls must be >= 1")

    def timeout_reason(self, started_at: float) -> str | None:
        if self.timeout_seconds is not None and monotonic() - started_at >= self.timeout_seconds:
            return "timeout_seconds"
        return None

    def iteration_reason(self, state: AgentState) -> str | None:
        if state.iterations >= self.max_iterations:
            return "max_iterations"
        return None

    def tool_call_reason(self, state: AgentState) -> str | None:
        if state.total_tool_calls >= self.max_total_tool_calls:
            return "max_total_tool_calls"
        return None
