"""Runtime error hierarchy."""

from __future__ import annotations


class AgentError(Exception):
    """Base class for runtime errors."""


class ModelError(AgentError):
    """The model client failed."""


class ToolError(AgentError):
    """A tool failed before it could return a ToolResult."""


class LimitExceeded(AgentError):
    """A configured loop limit was exceeded."""


class InvalidToolCall(AgentError):
    """The model requested an invalid or unknown tool call."""


class DuplicateToolError(AgentError):
    """A tool registry received duplicate tool names."""
