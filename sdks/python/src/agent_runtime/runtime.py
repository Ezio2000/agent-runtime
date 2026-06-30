"""Runtime context shared across model calls, tools, and hooks."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from time import time
from typing import Any, cast
from uuid import uuid4


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


@dataclass(slots=True)
class RuntimeContext:
    """Per-run context passed through runtime extension points.

    `started_at` and `deadline` are wall-clock epoch seconds so serialized
    contexts can be used as durable checkpoint data. The loop keeps monotonic
    timeout bookkeeping separately.
    """

    run_id: str = field(default_factory=lambda: uuid4().hex)
    started_at: float = field(default_factory=time)
    deadline: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=_empty_metadata)
    extra: Mapping[str, Any] = field(default_factory=_empty_metadata)
    _sequence: int = 0

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must not be empty")
        if self.deadline is not None and self.deadline <= self.started_at:
            raise ValueError("deadline must be after started_at")
        self.metadata = _copy_mapping(self.metadata)
        self.extra = _copy_extra(
            self.extra,
            {"run_id", "started_at", "deadline", "metadata", "sequence"},
            "runtime context",
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RuntimeContext:
        known = {"run_id", "started_at", "deadline", "metadata", "sequence"}
        deadline = value.get("deadline")
        context = cls(
            run_id=str(value["run_id"]),
            started_at=float(value["started_at"]),
            deadline=None if deadline is None else float(deadline),
            metadata=cast(Mapping[str, Any], value.get("metadata") or {}),
            extra={key: deepcopy(item) for key, item in value.items() if key not in known},
        )
        context._sequence = int(value.get("sequence", 0))
        return context

    def next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    @property
    def sequence(self) -> int:
        return self._sequence

    @sequence.setter
    def sequence(self, value: int) -> None:
        if value < 0:
            raise ValueError("sequence must be >= 0")
        self._sequence = value

    def remaining_seconds(self) -> float | None:
        if self.deadline is None:
            return None
        return max(0.0, self.deadline - time())

    def snapshot(self) -> dict[str, Any]:
        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "deadline": self.deadline,
            "metadata": _copy_mapping(self.metadata),
            "sequence": self._sequence,
        }
        data.update(
            _copy_extra(
                self.extra,
                {"run_id", "started_at", "deadline", "metadata", "sequence"},
                "runtime context",
            )
        )
        return data
